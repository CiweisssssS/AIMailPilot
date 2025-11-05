import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { fetchLatestEmails } from "./gmail";
import { handleGoogleAuth, handleGoogleCallback, handleAuthStatus, handleLogout } from "./oauth";

export async function registerRoutes(app: Express): Promise<Server> {
  
  // OAuth routes
  app.get("/auth/google", handleGoogleAuth);
  app.get("/auth/google/callback", handleGoogleCallback);
  app.get("/api/auth/status", handleAuthStatus);
  app.post("/api/auth/logout", handleLogout);
  
  app.get("/api/fetch-gmail-emails/:maxResults?", async (req, res) => {
    try {
      const maxResults = parseInt(req.params.maxResults || "10") || 10;
      const emails = await fetchLatestEmails(req, maxResults);
      
      res.json({
        success: true,
        emails: emails.map(email => ({
          id: email.id,
          threadId: email.threadId,
          subject: email.subject,
          from_: email.from,
          to: email.to,
          date: email.date,
          snippet: email.snippet,
          body: email.body,
          clean_body: email.body
        }))
      });
    } catch (error: any) {
      console.error("Error fetching Gmail emails:", error);
      
      // Return 401 if not authenticated, 500 for other errors
      const statusCode = error.message?.includes('Not authenticated') ? 401 : 500;
      res.status(statusCode).json({
        success: false,
        error: error.message || "Failed to fetch emails"
      });
    }
  });

  // PATCH endpoint for updating task deadlines
  // NOTE: Current architecture limitation - tasks are not persisted in database.
  // Tasks are generated on-the-fly from email analysis and stored in frontend React Query cache.
  // Manual deadline updates via this endpoint are validated server-side but stored client-side only.
  // Updates will be lost on page refresh or re-analysis. For persistent storage, tasks would need
  // to be moved to the database (e.g., PostgreSQL with Drizzle ORM).
  app.patch("/api/tasks/:emailId/:taskIndex", async (req, res) => {
    try {
      const { emailId, taskIndex } = req.params;
      const { due } = req.body;
      
      if (!due || typeof due !== 'string') {
        return res.status(400).json({
          success: false,
          error: "Invalid request: due date required"
        });
      }
      
      // Validate deadline format: "Mon DD, YYYY, HH:mm" or "TBD"
      const deadlinePattern = /^([A-Z][a-z]{2} \d{2}, \d{4}, \d{2}:\d{2}|TBD)$/;
      if (!deadlinePattern.test(due)) {
        return res.status(400).json({
          success: false,
          error: "Invalid deadline format. Expected 'Mon DD, YYYY, HH:mm' or 'TBD'"
        });
      }
      
      // Return success - frontend will update its React Query cache
      // TODO: Add database persistence for task deadline overrides
      res.json({
        success: true,
        emailId,
        taskIndex: parseInt(taskIndex),
        due
      });
    } catch (error: any) {
      console.error("Error updating task deadline:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to update task deadline"
      });
    }
  });

  app.post("/api/analyze-emails", async (req, res) => {
    try {
      const { emails } = req.body;
      
      if (!emails || !Array.isArray(emails)) {
        return res.status(400).json({
          success: false,
          error: "Invalid request: emails array required"
        });
      }

      console.log(`Analyzing ${emails.length} emails...`);
      console.log('First email sample:', JSON.stringify(emails[0]).substring(0, 200));

      // Get user email from session for Supabase queries
      const userEmail = (req.session as any)?.user?.email || null;
      console.log(`User email from session: ${userEmail || 'not authenticated'}`);

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/triage`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          messages: emails,
          user_email: userEmail
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText} - ${errorText.substring(0, 200)}`);
      }

      const result = await response.json();
      console.log(`Analysis complete: ${result.analyzed_emails?.length || 0} emails analyzed`);
      res.json(result);
    } catch (error: any) {
      console.error("Error analyzing emails:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to analyze emails"
      });
    }
  });

  app.post("/api/chatbot-qa", async (req, res) => {
    try {
      const { question, thread } = req.body;
      
      if (!question || !thread) {
        console.error("Missing question or thread in request");
        return res.status(400).json({
          success: false,
          error: "Invalid request: question and thread required"
        });
      }

      console.log(`Chatbot question: "${question.substring(0, 100)}..."`);
      console.log(`Thread has ${thread.normalized_messages?.length || 0} messages`);

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      const backendUrl = `${pythonBackendUrl}/api/chatbot-qa`;
      
      console.log(`Forwarding to Python backend: ${backendUrl}`);
      
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question, thread })
      });

      console.log(`Python backend responded with status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText.substring(0, 200));
        return res.status(response.status).json({
          success: false,
          error: `Python backend error: ${errorText.substring(0, 200)}`
        });
      }

      const result = await response.json();
      console.log(`Chatbot response received:`, JSON.stringify(result).substring(0, 100));
      res.json(result);
    } catch (error: any) {
      console.error("Error in chatbot:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to process chatbot request"
      });
    }
  });

  // Flag status API routes - forward to Python backend
  app.post("/api/flags/toggle", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const { email_id, is_flagged } = req.body;

      if (!email_id || typeof is_flagged !== 'boolean') {
        return res.status(400).json({
          success: false,
          error: "Invalid request: email_id and is_flagged required"
        });
      }

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/flags/toggle`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_email: userEmail,
          email_id,
          is_flagged
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error toggling flag:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to toggle flag"
      });
    }
  });

  app.get("/api/flags", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/flags?user_email=${encodeURIComponent(userEmail)}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error fetching flagged emails:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to fetch flagged emails"
      });
    }
  });

  app.delete("/api/flags/:emailId", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const { emailId } = req.params;
      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/flags/${emailId}?user_email=${encodeURIComponent(userEmail)}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error deleting flag:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to delete flag"
      });
    }
  });

  // Deadline override API routes - forward to Python backend
  app.post("/api/deadline-overrides", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const { email_id, task_index, original_deadline, override_deadline } = req.body;

      if (!email_id || task_index === undefined || !override_deadline) {
        return res.status(400).json({
          success: false,
          error: "Invalid request: email_id, task_index, and override_deadline required"
        });
      }

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/deadline-overrides`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_email: userEmail,
          email_id,
          task_index,
          original_deadline,
          override_deadline
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error setting deadline override:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to set deadline override"
      });
    }
  });

  app.get("/api/deadline-overrides", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/deadline-overrides?user_email=${encodeURIComponent(userEmail)}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error fetching deadline overrides:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to fetch deadline overrides"
      });
    }
  });

  app.delete("/api/deadline-overrides/:emailId/:taskIndex", async (req, res) => {
    try {
      // Check authentication
      if (!(req.session as any)?.user?.email) {
        return res.status(401).json({
          success: false,
          error: "Not authenticated"
        });
      }

      const userEmail = (req.session as any).user.email;
      const { emailId, taskIndex } = req.params;
      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/deadline-overrides/${emailId}/${taskIndex}?user_email=${encodeURIComponent(userEmail)}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error deleting deadline override:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to delete deadline override"
      });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
