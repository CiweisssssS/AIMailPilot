/**
 * Configuration file for the Gmail Add-on
 * Update BACKEND_URL with your deployed Replit backend URL
 */

// Replace with your actual Replit backend URL
// Example: https://your-repl-name.your-username.replit.dev
const BACKEND_URL = 'https://ai-mail-pilot-yulingsong44.replit.app';

// API Endpoints
const API_ENDPOINTS = {
  PROCESS_THREAD: '/api/process-thread',
  BATCH_ANALYZE: '/api/batch-analyze',
  SUMMARIZE: '/api/summarize',
  EXTRACT_TASKS: '/api/extract-tasks',
  PRIORITIZE: '/api/prioritize',
  CHATBOT_QA: '/api/chatbot-qa',
  UPDATE_SETTINGS: '/api/update-user-settings',
  HEALTH: '/healthz'
};

// User ID (can be customized per user)
function getUserId() {
  return Session.getActiveUser().getEmail();
}
