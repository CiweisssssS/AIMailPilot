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

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/triage`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ messages: emails })
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
        return res.status(400).json({
          success: false,
          error: "Invalid request: question and thread required"
        });
      }

      console.log(`Chatbot question: ${question.substring(0, 100)}...`);

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/api/chatbot-qa`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question, thread })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Python backend error (${response.status}):`, errorText);
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      console.log(`Chatbot response received`);
      res.json(result);
    } catch (error: any) {
      console.error("Error in chatbot:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to process chatbot request"
      });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
