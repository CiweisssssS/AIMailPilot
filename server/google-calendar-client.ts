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
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=google-calendar',
    {
      headers: {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }
    }
  ).then(res => res.json()).then(data => data.items?.[0]);

  const accessToken = connectionSettings?.settings?.access_token || connectionSettings.settings?.oauth?.credentials?.access_token;

  if (!connectionSettings || !accessToken) {
    throw new Error('Google Calendar not connected');
  }
  return accessToken;
}

// WARNING: Never cache this client.
// Access tokens expire, so a new client must be created each time.
// Always call this function again to get a fresh client.
export async function getUncachableGoogleCalendarClient() {
  const accessToken = await getAccessToken();

  const oauth2Client = new google.auth.OAuth2();
  oauth2Client.setCredentials({
    access_token: accessToken
  });

  return google.calendar({ version: 'v3', auth: oauth2Client });
}

// Helper to parse "Mon DD, YYYY, HH:mm" to Date object
function parseDeadlineToDate(deadlineStr: string): Date {
  // Example: "Nov 10, 2025, 23:59"
  const monthMap: { [key: string]: number } = {
    Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
    Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11
  };
  
  const parts = deadlineStr.split(', ');
  const [monthDay, year, time] = parts;
  const [month, day] = monthDay.split(' ');
  const [hours, minutes] = time.split(':').map(Number);
  
  return new Date(
    parseInt(year),
    monthMap[month],
    parseInt(day),
    hours,
    minutes
  );
}

export async function createCalendarEvent(
  title: string,
  description: string,
  startDateTime: string
): Promise<{ eventId: string; eventLink: string }> {
  try {
    const calendar = await getUncachableGoogleCalendarClient();

    // Parse the deadline format "Mon DD, YYYY, HH:mm" to Date object
    const deadlineDate = parseDeadlineToDate(startDateTime);
    const endDate = new Date(deadlineDate.getTime() + 60 * 60 * 1000); // 1 hour duration

    const event = {
      summary: title,
      description: description,
      start: {
        dateTime: deadlineDate.toISOString(),
        timeZone: 'UTC',
      },
      end: {
        dateTime: endDate.toISOString(),
        timeZone: 'UTC',
      },
    };

    const response = await calendar.events.insert({
      calendarId: 'primary',
      requestBody: event,
    });

    return {
      eventId: response.data.id!,
      eventLink: response.data.htmlLink!,
    };
  } catch (error) {
    console.error('Failed to create calendar event:', error);
    throw error;
  }
}
