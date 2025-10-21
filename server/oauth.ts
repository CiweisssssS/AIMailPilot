import { google } from "googleapis";
import type { Request, Response } from "express";

const SCOPES = [
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/userinfo.email",
  "https://www.googleapis.com/auth/userinfo.profile"
];

function getOAuth2Client() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || `${process.env.REPLIT_DEV_DOMAIN || 'http://localhost:5000'}/auth/google/callback`;

  if (!clientId || !clientSecret) {
    throw new Error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set");
  }

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

export async function handleGoogleAuth(req: Request, res: Response) {
  try {
    const oauth2Client = getOAuth2Client();
    
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: "offline",
      scope: SCOPES,
      prompt: "consent" // Force to get refresh token
    });

    res.redirect(authUrl);
  } catch (error: any) {
    console.error("Error initiating Google OAuth:", error);
    res.status(500).json({ 
      error: "Failed to initiate OAuth",
      message: error.message 
    });
  }
}

export async function handleGoogleCallback(req: Request, res: Response) {
  try {
    const code = req.query.code as string;
    
    if (!code) {
      return res.status(400).send("Authorization code not provided");
    }

    const oauth2Client = getOAuth2Client();
    
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
