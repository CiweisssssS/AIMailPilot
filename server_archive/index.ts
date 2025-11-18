import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import { spawn } from "child_process";
import { sessionMiddleware } from "./session";

const app = express();

// Trust proxy to correctly identify protocol (http/https) behind reverse proxy
app.set('trust proxy', 1);

// Increase payload size limit for email analysis (50 emails can be large)
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: false, limit: '50mb' }));
app.use(sessionMiddleware);

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api") || path.startsWith("/auth")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
    }
  });

  next();
});

let pythonBackend: any = null;

(async () => {
  const server = await registerRoutes(app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (app.get("env") === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || '5000', 10);
  server.listen({
    port,
    host: "0.0.0.0",
    reusePort: true,
  }, () => {
    log(`serving on port ${port}`);
    
    log(`starting FastAPI backend on port 8000...`);
    pythonBackend = spawn("uvicorn", ["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"], {
      stdio: "inherit",
      shell: true,
    });

    pythonBackend.on("error", (err: Error) => {
      console.error("Failed to start FastAPI backend:", err);
    });

    pythonBackend.on("exit", (code: number) => {
      if (code !== 0) {
        console.error(`FastAPI backend exited with code ${code}`);
      }
    });
  });

  process.on("SIGTERM", () => {
    if (pythonBackend) {
      pythonBackend.kill();
    }
    process.exit(0);
  });
})();
