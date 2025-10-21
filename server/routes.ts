import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { fetchLatestEmails } from "./gmail";

export async function registerRoutes(app: Express): Promise<Server> {
  
  app.get("/api/fetch-gmail-emails", async (req, res) => {
    try {
      const maxResults = parseInt(req.query.maxResults as string) || 10;
      const emails = await fetchLatestEmails(maxResults);
      
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
      res.status(500).json({
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

      const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      
      const response = await fetch(`${pythonBackendUrl}/triage`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ messages: emails })
      });

      if (!response.ok) {
        throw new Error(`Python backend error: ${response.statusText}`);
      }

      const result = await response.json();
      res.json(result);
    } catch (error: any) {
      console.error("Error analyzing emails:", error);
      res.status(500).json({
        success: false,
        error: error.message || "Failed to analyze emails"
      });
    }
  });

  const httpServer = createServer(app);

  return httpServer;
}
