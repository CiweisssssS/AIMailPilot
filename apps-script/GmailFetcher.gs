/**
 * Gmail Fetcher
 * Handles delta fetch logic and unresolved pool management
 */

/**
 * Fetch candidate threads using delta + unresolved pool strategy
 * Core principle: "Read = Processed" - hide read emails unless saved/flagged
 * @param {string} displayMode - Legacy parameter, now uses "all" by default
 * @returns {Array} Array of thread IDs to analyze
 */
function fetchCandidateThreads(displayMode) {
  const lastOpenTs = getLastOpenTs();
  const unresolvedIds = getUnresolvedThreadIds();
  
  // Always fetch delta (threads since last open or last 7 days)
  const deltaIds = fetchDeltaThreads(lastOpenTs);
  
  // Get saved and flagged thread IDs (always show these)
  const savedTasks = getSavedTasks();
  const flaggedMails = getFlaggedMails();
  const savedIds = savedTasks.map(task => task.threadId);
  const flaggedIds = flaggedMails.map(mail => mail.threadId);
  
  // Combine delta + unresolved + saved + flagged
  let candidateIds = [...new Set([...deltaIds, ...unresolvedIds, ...savedIds, ...flaggedIds])];
  
  // Filter based on "Read = Processed" principle
  candidateIds = candidateIds.filter(threadId => {
    const thread = GmailApp.getThreadById(threadId);
    if (!thread) return false;
    
    const isRead = !thread.isUnread();
    const isSaved = savedIds.includes(threadId);
    const isFlagged = flaggedIds.includes(threadId);
    
    // Show if: unread OR saved OR flagged
    return !isRead || isSaved || isFlagged;
  });
  
  // Update unresolved pool with delta
  if (deltaIds.length > 0) {
    addUnresolvedThreadIds(deltaIds);
  }
  
  // Update last open timestamp
  setLastOpenTs(Date.now());
  
  return candidateIds;
}

/**
 * Fetch threads since last open or last 7 days
 */
function fetchDeltaThreads(lastOpenTs) {
  try {
    let query = 'is:unread';
    
    if (lastOpenTs) {
      // Convert timestamp to Gmail search format (seconds since epoch)
      const afterSeconds = Math.floor(lastOpenTs / 1000);
      query += ` after:${afterSeconds}`;
    } else {
      // First run: fetch from last 7 days
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      const afterSeconds = Math.floor(sevenDaysAgo.getTime() / 1000);
      query += ` after:${afterSeconds}`;
    }
    
    // Fetch threads matching query
    const threads = GmailApp.search(query, 0, 50);
    const threadIds = threads.map(thread => thread.getId());
    
    return threadIds;
    
  } catch (error) {
    console.error('Error fetching delta threads:', error);
    return [];
  }
}

/**
 * Get thread details for analysis
 * @param {string} threadId
 * @returns {Object} Thread input object for backend
 */
function getThreadDetails(threadId) {
  try {
    const thread = GmailApp.getThreadById(threadId);
    if (!thread) return null;
    
    const messages = thread.getMessages();
    if (messages.length === 0) return null;
    
    const firstMessage = messages[0];
    const lastMessage = messages[messages.length - 1];
    
    return {
      id: threadId,
      subject: firstMessage.getSubject(),
      snippet: thread.getFirstMessageSubject().substring(0, 200),
      last_message: lastMessage.getPlainBody().substring(0, 500),
      from: lastMessage.getFrom(),
      to: [lastMessage.getTo()],
      date: lastMessage.getDate().toISOString()
    };
    
  } catch (error) {
    console.error(`Error getting thread details for ${threadId}:`, error);
    return null;
  }
}

/**
 * Batch fetch thread details
 * @param {Array} threadIds
 * @returns {Array} Array of thread input objects
 */
function batchGetThreadDetails(threadIds) {
  const threads = [];
  
  for (let i = 0; i < threadIds.length; i++) {
    const threadDetails = getThreadDetails(threadIds[i]);
    if (threadDetails) {
      threads.push(threadDetails);
    }
  }
  
  return threads;
}

/**
 * Open a Gmail thread by ID
 * @param {string} threadId
 */
function openGmailThread(threadId) {
  const thread = GmailApp.getThreadById(threadId);
  if (thread) {
    const url = `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
    return CardService.newOpenLink()
      .setUrl(url)
      .setOpenAs(CardService.OpenAs.FULL_SIZE)
      .setOnClose(CardService.OnClose.NOTHING);
  }
  return null;
}
