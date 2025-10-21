import session from "express-session";
import { randomBytes } from "crypto";

declare module "express-session" {
  interface SessionData {
    googleTokens?: {
      access_token: string;
      refresh_token?: string;
      expiry_date?: number;
    };
    user?: {
      email: string;
      name: string;
      picture?: string;
    };
  }
}

const sessionSecret = process.env.SESSION_SECRET || randomBytes(32).toString("hex");

if (!process.env.SESSION_SECRET) {
  console.warn("⚠️  SESSION_SECRET not set, using random secret (sessions will reset on restart)");
}

export const sessionMiddleware = session({
  secret: sessionSecret,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    sameSite: "lax"
  }
});
