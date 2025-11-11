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

// Helper to parse "Mon DD, YYYY, HH:mm" directly to RFC3339 datetime string
// This bypasses Date object to avoid timezone conversion issues
function parseDeadlineToRFC3339(deadlineStr: string): string {
  // Example: "Nov 10, 2025, 23:59" → "2025-11-10T23:59:00"
  const monthMap: { [key: string]: string } = {
    Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
    Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12'
  };
  
  // Validate input format
  if (!deadlineStr || typeof deadlineStr !== 'string') {
    throw new Error(`Invalid deadline: expected string, got ${typeof deadlineStr}`);
  }
  
  const parts = deadlineStr.split(', ');
  if (parts.length !== 3) {
    throw new Error(`Invalid deadline format: expected "Mon DD, YYYY, HH:mm", got "${deadlineStr}"`);
  }
  
  const [monthDay, year, time] = parts;
  const monthDayParts = monthDay.split(' ');
  if (monthDayParts.length !== 2) {
    throw new Error(`Invalid month/day format in "${deadlineStr}"`);
  }
  
  const [month, day] = monthDayParts;
  const timeParts = time.split(':');
  if (timeParts.length !== 2) {
    throw new Error(`Invalid time format in "${deadlineStr}"`);
  }
  
  const [hours, minutes] = timeParts;
  
  // Validate month is recognized
  if (!monthMap[month]) {
    throw new Error(`Unknown month "${month}" in deadline "${deadlineStr}"`);
  }
  
  const paddedDay = day.padStart(2, '0');
  const paddedHours = hours.padStart(2, '0');
  const paddedMinutes = minutes.padStart(2, '0');
  
  return `${year}-${monthMap[month]}-${paddedDay}T${paddedHours}:${paddedMinutes}:00`;
}

// Helper to add hours to an RFC3339 datetime string using pure arithmetic
// This avoids all Date object timezone complications
function addHoursToRFC3339(dateTimeStr: string, hoursToAdd: number): string {
  // Parse the RFC3339 string: "2025-11-11T17:00:00"
  const match = dateTimeStr.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})$/);
  if (!match) {
    throw new Error(`Invalid RFC3339 format: ${dateTimeStr}`);
  }
  
  let [, yearStr, monthStr, dayStr, hoursStr, minutesStr, secondsStr] = match;
  let year = parseInt(yearStr);
  let month = parseInt(monthStr);
  let day = parseInt(dayStr);
  let hours = parseInt(hoursStr);
  let minutes = parseInt(minutesStr);
  let seconds = parseInt(secondsStr);
  
  // Add hours with overflow handling
  hours += hoursToAdd;
  
  // Handle hour overflow (carry to days)
  while (hours >= 24) {
    hours -= 24;
    day += 1;
    
    // Handle day overflow (carry to months)
    const daysInMonth = new Date(year, month, 0).getDate(); // JS Date is only used for calendar math
    if (day > daysInMonth) {
      day = 1;
      month += 1;
      
      // Handle month overflow (carry to years)
      if (month > 12) {
        month = 1;
        year += 1;
      }
    }
  }
  
  // Format back to RFC3339 (without 'Z' suffix)
  const paddedMonth = String(month).padStart(2, '0');
  const paddedDay = String(day).padStart(2, '0');
  const paddedHours = String(hours).padStart(2, '0');
  const paddedMinutes = String(minutes).padStart(2, '0');
  const paddedSeconds = String(seconds).padStart(2, '0');
  
  return `${year}-${paddedMonth}-${paddedDay}T${paddedHours}:${paddedMinutes}:${paddedSeconds}`;
}

export async function createCalendarEvent(
  title: string,
  description: string,
  startDateTime: string
): Promise<{ eventId: string; eventLink: string }> {
  try {
    const calendar = await getUncachableGoogleCalendarClient();

    // Parse deadline directly to RFC3339 format (bypassing Date object to avoid timezone issues)
    const startDateTimeRFC3339 = parseDeadlineToRFC3339(startDateTime);
    const endDateTimeRFC3339 = addHoursToRFC3339(startDateTimeRFC3339, 1); // 1 hour duration

    // Use configurable timezone (defaults to America/Los_Angeles)
    // This can be overridden via CALENDAR_TIMEZONE environment variable
    const calendarTimeZone = process.env.CALENDAR_TIMEZONE || 'America/Los_Angeles';

    const event = {
      summary: title,
      description: description,
      start: {
        dateTime: startDateTimeRFC3339,
        timeZone: calendarTimeZone,
      },
      end: {
        dateTime: endDateTimeRFC3339,
        timeZone: calendarTimeZone,
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
