/**
 * Backend API client for calling FastAPI endpoints
 */

/**
 * Make a POST request to the backend API
 */
function callBackendAPI(endpoint, payload) {
  const url = BACKEND_URL + endpoint;
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const statusCode = response.getResponseCode();
    
    if (statusCode === 200) {
      return JSON.parse(response.getContentText());
    } else {
      console.error('Backend API error:', statusCode, response.getContentText());
      return null;
    }
  } catch (error) {
    console.error('Failed to call backend API:', error);
    return null;
  }
}

/**
 * Process an email thread through the backend
 */
function processThread(messages, keywords) {
  const payload = {
    user_id: getUserId(),
    personalized_keywords: keywords || [],
    messages: messages
  };
  
  return callBackendAPI(API_ENDPOINTS.PROCESS_THREAD, payload);
}

/**
 * Ask a question about the thread
 */
function askQuestion(question, thread) {
  const payload = {
    question: question,
    thread: thread
  };
  
  return callBackendAPI(API_ENDPOINTS.CHATBOT_QA, payload);
}

/**
 * Update user settings (keywords)
 */
function updateUserSettings(addKeywords, removeKeywords) {
  const payload = {
    user_id: getUserId(),
    add_keywords: addKeywords || [],
    remove_keywords: removeKeywords || []
  };
  
  return callBackendAPI(API_ENDPOINTS.UPDATE_SETTINGS, payload);
}
