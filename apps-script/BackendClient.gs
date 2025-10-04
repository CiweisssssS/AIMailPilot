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

/**
 * Batch analyze multiple threads
 * @param {Array} threads - Array of thread input objects
 * @param {Array} keywords - User keywords
 * @returns {Object} Batch analysis results
 */
function batchAnalyzeThreads(threads, keywords) {
  const payload = {
    threads: threads,
    keywords: keywords || []
  };
  
  return callBackendAPI(API_ENDPOINTS.BATCH_ANALYZE, payload);
}

/**
 * Analyze threads with caching
 * @param {Array} threadIds - Array of thread IDs
 * @returns {Object} Map of threadId -> analysis result
 */
function analyzeThreadsWithCache(threadIds) {
  const results = {};
  const threadsToAnalyze = [];
  const keywords = getUserKeywords();
  
  // Check cache first
  for (let i = 0; i < threadIds.length; i++) {
    const threadId = threadIds[i];
    const cached = getCachedAnalysis(threadId);
    
    if (cached) {
      results[threadId] = cached;
    } else {
      threadsToAnalyze.push(threadId);
    }
  }
  
  // Batch analyze uncached threads (in chunks of 25)
  if (threadsToAnalyze.length > 0) {
    const chunkSize = 25;
    
    for (let i = 0; i < threadsToAnalyze.length; i += chunkSize) {
      const chunk = threadsToAnalyze.slice(i, i + chunkSize);
      const threadDetails = batchGetThreadDetails(chunk);
      
      if (threadDetails.length > 0) {
        const batchResult = batchAnalyzeThreads(threadDetails, keywords);
        
        if (batchResult && batchResult.results) {
          batchResult.results.forEach(result => {
            results[result.id] = result;
            setCachedAnalysis(result.id, result);
          });
        }
      }
    }
  }
  
  return results;
}
