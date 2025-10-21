import { google } from 'googleapis';
import type { Request } from 'express';

function getOAuth2Client() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || `${process.env.REPLIT_DEV_DOMAIN || 'http://localhost:5000'}/auth/google/callback`;

  if (!clientId || !clientSecret) {
    throw new Error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set");
  }

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

async function getGmailClient(req: Request) {
  const tokens = req.session.googleTokens;
  
  if (!tokens || !tokens.access_token) {
    throw new Error('Not authenticated. Please login with Google first.');
  }

  const oauth2Client = getOAuth2Client();
  oauth2Client.setCredentials({
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    expiry_date: tokens.expiry_date
  });

  // Auto-refresh token if expired
  oauth2Client.on('tokens', (newTokens) => {
    if (newTokens.access_token) {
      req.session.googleTokens = {
        access_token: newTokens.access_token,
        refresh_token: newTokens.refresh_token || tokens.refresh_token,
        expiry_date: newTokens.expiry_date || undefined
      };
      
      req.session.save((err) => {
        if (err) console.error('Error saving refreshed tokens:', err);
      });
    }
  });

  return google.gmail({ version: 'v1', auth: oauth2Client });
}

export interface GmailMessage {
  id: string;
  threadId: string;
  subject: string;
  from: string;
  to: string[];
  date: string;
  snippet: string;
  body: string;
}

export async function fetchLatestEmails(req: Request, maxResults: number = 10): Promise<GmailMessage[]> {
  try {
    const gmail = await getGmailClient(req);
    
    // Fetch message list
    const response = await gmail.users.messages.list({
      userId: 'me',
      maxResults,
      q: 'in:inbox'
    });

    const messages = response.data.messages || [];
    
    // Fetch full message details for each
    const emailPromises = messages.map(async (msg) => {
      const fullMsg = await gmail.users.messages.get({
        userId: 'me',
        id: msg.id!,
        format: 'full'
      });

      const headers = fullMsg.data.payload?.headers || [];
      const subject = headers.find(h => h.name?.toLowerCase() === 'subject')?.value || '(No subject)';
      const from = headers.find(h => h.name?.toLowerCase() === 'from')?.value || 'Unknown';
      const to = headers.find(h => h.name?.toLowerCase() === 'to')?.value?.split(',') || [];
      const date = headers.find(h => h.name?.toLowerCase() === 'date')?.value || new Date().toISOString();

      // Extract body
      let body = '';
      const parts = fullMsg.data.payload?.parts || [];
      
      function extractBody(part: any): string {
        if (part.mimeType === 'text/plain' && part.body?.data) {
          return Buffer.from(part.body.data, 'base64').toString('utf-8');
        }
        if (part.parts) {
          for (const subPart of part.parts) {
            const extracted = extractBody(subPart);
            if (extracted) return extracted;
          }
        }
        return '';
      }

      if (fullMsg.data.payload?.body?.data) {
        body = Buffer.from(fullMsg.data.payload.body.data, 'base64').toString('utf-8');
      } else {
        body = extractBody(fullMsg.data.payload);
      }

      if (!body) {
        body = fullMsg.data.snippet || '';
      }

      return {
        id: fullMsg.data.id!,
        threadId: fullMsg.data.threadId!,
        subject,
        from,
        to,
        date,
        snippet: fullMsg.data.snippet || '',
        body: body.substring(0, 5000) // Limit body length
      };
    });

    const emails = await Promise.all(emailPromises);
    return emails;
  } catch (error) {
    console.error('Error fetching Gmail emails:', error);
    throw error;
  }
}
