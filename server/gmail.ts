import { google } from 'googleapis';

let connectionSettings: any;

async function getAccessToken() {
  if (connectionSettings && connectionSettings.settings.expires_at && new Date(connectionSettings.settings.expires_at).getTime() > Date.now()) {
    return connectionSettings.settings.access_token;
  }
  
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME
  const xReplitToken = process.env.REPL_IDENTITY 
    ? 'repl ' + process.env.REPL_IDENTITY 
    : process.env.WEB_REPL_RENEWAL 
    ? 'depl ' + process.env.WEB_REPL_RENEWAL 
    : null;

  if (!xReplitToken) {
    throw new Error('X_REPLIT_TOKEN not found for repl/depl');
  }

  connectionSettings = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=google-mail',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  ).then(res => res.json()).then(data => data.items?.[0]);

  const accessToken = connectionSettings?.settings?.access_token || connectionSettings.settings?.oauth?.credentials?.access_token;

  if (!connectionSettings || !accessToken) {
    throw new Error('Gmail not connected');
  }
  return accessToken;
}

export async function getUncachableGmailClient() {
  const accessToken = await getAccessToken();

  const oauth2Client = new google.auth.OAuth2();
  oauth2Client.setCredentials({
    access_token: accessToken
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

export async function fetchLatestEmails(maxResults: number = 10): Promise<GmailMessage[]> {
  try {
    const gmail = await getUncachableGmailClient();
    
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
