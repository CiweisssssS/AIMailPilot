/**
 * Centralized API endpoints mapping
 * Matches backend Swagger/OpenAPI specification
 * 
 * Note: Some endpoints have /api prefix, others don't (e.g., /triage)
 */
export const ENDPOINTS = {
  // Auth endpoints
  authStatus: '/api/auth/status',
  oauthGoogle: '/oauth/google',
  oauthCallback: '/oauth/google/callback',
  logout: '/api/auth/logout',

  // Email triage (NO /api prefix per backend)
  triage: '/triage',

  // Thread processing
  processThread: '/api/process-thread',
  extractTasks: '/api/extract-tasks',
  prioritize: '/api/prioritize',

  // Flags
  flagsGet: '/api/flags',
  flagsToggle: '/api/flags/toggle',
  flagsDelete: (emailId: string) => `/api/flags/${emailId}`,

  // Deadline overrides
  deadlineGet: '/api/deadline-overrides',
  deadlineSet: '/api/deadline-overrides',
  deadlineDelete: (emailId: string, taskIndex: number) => `/api/deadline-overrides/${emailId}/${taskIndex}`,

  // Chatbot
  chatbotQA: '/api/chatbot-qa',

  // Calendar
  calendarCreateEvent: '/api/calendar/create-event',

  // Health check
  health: '/health',
} as const;

