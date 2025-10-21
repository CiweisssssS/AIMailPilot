import { google } from "googleapis";
import type { Request, Response } from "express";

const SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/userinfo.profile"
];

function getOAuth2Client(req: Request) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  
  // Construct redirect URI dynamically from the request
  let redirectUri = process.env.GOOGLE_REDIRECT_URI;
  if (!redirectUri) {
    // Get the protocol (http or https) and host from the request
    const protocol = req.protocol || 'https';
    const host = req.get('host');
    
    if (host) {
      redirectUri = `${protocol}://${host}/auth/google/callback`;
    } else {
      // Fallback to environment variable or localhost
      const replitDomain = process.env.REPLIT_DEV_DOMAIN;
      if (replitDomain) {
        redirectUri = `https://${replitDomain}/auth/google/callback`;
      } else {
        redirectUri = 'http://localhost:5000/auth/google/callback';
      }
    }
  }

  if (!clientId || !clientSecret) {
    throw new Error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set");
  }

  console.log("=== OAuth2 Client Configuration ===");
  console.log("- Client ID:", clientId.substring(0, 20) + "...");
  console.log("- Redirect URI:", redirectUri);
  console.log("- Request Host:", req.get('host'));
  console.log("- Request Protocol:", req.protocol);
  console.log("====================================");

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

export async function handleGoogleAuth(req: Request, res: Response) {
  try {
    const oauth2Client = getOAuth2Client(req);
    
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: "offline",
      scope: SCOPES,
      prompt: "consent" // Force to get refresh token
    });

    console.log("Redirecting to Google OAuth URL...");
    res.redirect(authUrl);
  } catch (error: any) {
    console.error("Error initiating Google OAuth:", error);
    
    // Return HTML page with error details for better UX
    res.status(500).send(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>OAuth Configuration Error</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
              max-width: 600px;
              margin: 100px auto;
              padding: 20px;
              background: #f5f5f5;
            }
            .error-box {
              background: white;
              border-left: 4px solid #ef4444;
              padding: 20px;
              border-radius: 8px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            h1 { color: #ef4444; margin-top: 0; }
            code {
              background: #f3f4f6;
              padding: 2px 6px;
              border-radius: 4px;
              font-size: 0.9em;
            }
            .instructions {
              margin-top: 20px;
              padding: 15px;
              background: #fef3c7;
              border-radius: 6px;
            }
            a {
              color: #2563eb;
              text-decoration: none;
            }
            a:hover {
              text-decoration: underline;
            }
          </style>
        </head>
        <body>
          <div class="error-box">
            <h1>⚠️ OAuth Configuration Error</h1>
            <p><strong>Error:</strong> ${error.message}</p>
            
            <div class="instructions">
              <h3>📋 Setup Required</h3>
              <p>Please configure Google OAuth credentials:</p>
              <ol>
                <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                <li>Create OAuth 2.0 credentials (Web application)</li>
                <li>Add this redirect URI:<br><code>${process.env.REPLIT_DEV_DOMAIN ? `https://${process.env.REPLIT_DEV_DOMAIN}/auth/google/callback` : 'Your Replit URL + /auth/google/callback'}</code></li>
                <li>Copy Client ID and Secret to Replit Secrets</li>
                <li>Enable Gmail API in the project</li>
              </ol>
            </div>
            
            <p style="margin-top: 20px;">
              <a href="/">← Back to Home</a>
            </p>
          </div>
        </body>
      </html>
    `);
  }
}

export async function handleGoogleCallback(req: Request, res: Response) {
  try {
    const code = req.query.code as string;
    
    if (!code) {
      return res.status(400).send("Authorization code not provided");
    }

    const oauth2Client = getOAuth2Client(req);
    
    // Exchange code for tokens
    const { tokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(tokens);

    // Get user info
    const oauth2 = google.oauth2({ version: "v2", auth: oauth2Client });
    const userInfo = await oauth2.userinfo.get();

    // Store tokens and user info in session
    req.session.googleTokens = {
      access_token: tokens.access_token!,
      refresh_token: tokens.refresh_token || undefined,
      expiry_date: tokens.expiry_date || undefined
    };

    req.session.user = {
      email: userInfo.data.email!,
      name: userInfo.data.name!,
      picture: userInfo.data.picture || undefined
    };

    await new Promise<void>((resolve, reject) => {
      req.session.save((err) => {
        if (err) reject(err);
        else resolve();
      });
    });

    // Redirect to frontend
    res.redirect("/");
  } catch (error: any) {
    console.error("Error in Google OAuth callback:", error);
    res.status(500).send(`
      <html>
        <body>
          <h1>Authentication Failed</h1>
          <p>${error.message}</p>
          <a href="/">Return to Home</a>
        </body>
      </html>
    `);
  }
}

export async function handleAuthStatus(req: Request, res: Response) {
  if (req.session.user && req.session.googleTokens) {
    res.json({
      authenticated: true,
      user: req.session.user
    });
  } else {
    res.json({
      authenticated: false
    });
  }
}

export async function handleLogout(req: Request, res: Response) {
  req.session.destroy((err) => {
    if (err) {
      console.error("Error destroying session:", err);
      return res.status(500).json({ error: "Failed to logout" });
    }
    // Clear the session cookie
    res.clearCookie('connect.sid');
    res.json({ success: true });
  });
}
