/**
 * State Manager for Gmail Add-on
 * Manages persistent state using PropertiesService
 */

const STATE_KEYS = {
  LAST_OPEN_TS: 'last_open_ts',
  UNRESOLVED_THREAD_IDS: 'unresolved_thread_ids',
  SNOOZED_UNTIL: 'snoozed_until',
  DISMISSED_SET: 'dismissed_set',
  USER_KEYWORDS: 'user_keywords',
  ANALYSIS_CACHE_TTL_MIN: 'analysis_cache_ttl_min',
  SAVED_TASKS: 'saved_tasks',
  FLAGGED_MAILS: 'flagged_mails',
  CUSTOM_TAGS: 'custom_tags'
};

const MAX_UNRESOLVED = 1000;
const DEFAULT_CACHE_TTL_MIN = 5;

/**
 * Get user properties service
 */
function getUserProps() {
  return PropertiesService.getUserProperties();
}

/**
 * Get last open timestamp
 */
function getLastOpenTs() {
  const props = getUserProps();
  const ts = props.getProperty(STATE_KEYS.LAST_OPEN_TS);
  return ts ? parseInt(ts) : null;
}

/**
 * Set last open timestamp
 */
function setLastOpenTs(timestamp) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.LAST_OPEN_TS, timestamp.toString());
}

/**
 * Get unresolved thread IDs (LRU capped at MAX_UNRESOLVED)
 */
function getUnresolvedThreadIds() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.UNRESOLVED_THREAD_IDS);
  return json ? JSON.parse(json) : [];
}

/**
 * Set unresolved thread IDs
 */
function setUnresolvedThreadIds(threadIds) {
  const props = getUserProps();
  const limited = threadIds.slice(0, MAX_UNRESOLVED);
  props.setProperty(STATE_KEYS.UNRESOLVED_THREAD_IDS, JSON.stringify(limited));
}

/**
 * Add thread IDs to unresolved pool
 */
function addUnresolvedThreadIds(newIds) {
  const existing = getUnresolvedThreadIds();
  const combined = [...new Set([...newIds, ...existing])];
  setUnresolvedThreadIds(combined.slice(0, MAX_UNRESOLVED));
}

/**
 * Remove thread ID from unresolved pool (mark as done)
 */
function removeUnresolvedThreadId(threadId) {
  const existing = getUnresolvedThreadIds();
  const filtered = existing.filter(id => id !== threadId);
  setUnresolvedThreadIds(filtered);
}

/**
 * Get snoozed threads map {threadId: ISO datetime}
 */
function getSnoozedUntil() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.SNOOZED_UNTIL);
  return json ? JSON.parse(json) : {};
}

/**
 * Set snoozed until map
 */
function setSnoozedUntil(snoozedMap) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.SNOOZED_UNTIL, JSON.stringify(snoozedMap));
}

/**
 * Snooze a thread until a specific time
 */
function snoozeThread(threadId, untilIso) {
  const snoozed = getSnoozedUntil();
  snoozed[threadId] = untilIso;
  setSnoozedUntil(snoozed);
}

/**
 * Check if thread is currently snoozed
 */
function isThreadSnoozed(threadId) {
  const snoozed = getSnoozedUntil();
  const untilIso = snoozed[threadId];
  
  if (!untilIso) return false;
  
  const now = new Date();
  const until = new Date(untilIso);
  return until > now;
}

/**
 * Get dismissed thread IDs
 */
function getDismissedSet() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.DISMISSED_SET);
  return json ? JSON.parse(json) : [];
}

/**
 * Set dismissed thread IDs
 */
function setDismissedSet(threadIds) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.DISMISSED_SET, JSON.stringify(threadIds));
}

/**
 * Dismiss a thread
 */
function dismissThread(threadId) {
  const dismissed = getDismissedSet();
  if (!dismissed.includes(threadId)) {
    dismissed.push(threadId);
    setDismissedSet(dismissed);
  }
}

/**
 * Check if thread is dismissed
 */
function isThreadDismissed(threadId) {
  const dismissed = getDismissedSet();
  return dismissed.includes(threadId);
}

/**
 * Get user keywords with weights
 */
function getUserKeywords() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.USER_KEYWORDS);
  return json ? JSON.parse(json) : [];
}

/**
 * Set user keywords
 */
function setUserKeywords(keywords) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.USER_KEYWORDS, JSON.stringify(keywords));
}

/**
 * Add a keyword
 */
function addKeyword(term, weight, scope) {
  const keywords = getUserKeywords();
  keywords.push({
    term: term,
    weight: weight || 'Medium',
    scope: scope || 'subject|body|sender'
  });
  setUserKeywords(keywords);
}

/**
 * Remove a keyword by term
 */
function removeKeyword(term) {
  const keywords = getUserKeywords();
  const filtered = keywords.filter(kw => kw.term !== term);
  setUserKeywords(filtered);
}

/**
 * Get cache TTL in minutes
 */
function getCacheTtlMin() {
  const props = getUserProps();
  const ttl = props.getProperty(STATE_KEYS.ANALYSIS_CACHE_TTL_MIN);
  return ttl ? parseInt(ttl) : DEFAULT_CACHE_TTL_MIN;
}

/**
 * Set cache TTL in minutes
 */
function setCacheTtlMin(minutes) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.ANALYSIS_CACHE_TTL_MIN, minutes.toString());
}

/**
 * Clear all state (for testing/reset)
 */
function clearAllState() {
  const props = getUserProps();
  props.deleteAllProperties();
}

// ==================== SAVED TASKS ====================

/**
 * Get saved tasks
 * Format: [{taskId, threadId, title, deadline, owner, savedAt}]
 */
function getSavedTasks() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.SAVED_TASKS);
  return json ? JSON.parse(json) : [];
}

/**
 * Set saved tasks
 */
function setSavedTasks(tasks) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.SAVED_TASKS, JSON.stringify(tasks));
}

/**
 * Save a task
 */
function saveTask(taskData) {
  const tasks = getSavedTasks();
  const taskId = taskData.taskId || `task_${Date.now()}`;
  
  tasks.push({
    taskId: taskId,
    threadId: taskData.threadId,
    title: taskData.title,
    deadline: taskData.deadline || null,
    owner: taskData.owner || null,
    savedAt: new Date().toISOString()
  });
  
  setSavedTasks(tasks);
  return taskId;
}

/**
 * Remove a saved task
 */
function removeSavedTask(taskId) {
  const tasks = getSavedTasks();
  const filtered = tasks.filter(t => t.taskId !== taskId);
  setSavedTasks(filtered);
}

/**
 * Check if task is saved
 */
function isTaskSaved(taskId) {
  const tasks = getSavedTasks();
  return tasks.some(t => t.taskId === taskId);
}

// ==================== FLAGGED MAILS ====================

/**
 * Get flagged mails
 * Format: [{threadId, subject, flaggedAt, tags[]}]
 */
function getFlaggedMails() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.FLAGGED_MAILS);
  return json ? JSON.parse(json) : [];
}

/**
 * Set flagged mails
 */
function setFlaggedMails(mails) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.FLAGGED_MAILS, JSON.stringify(mails));
}

/**
 * Flag a mail
 */
function flagMail(mailData) {
  const mails = getFlaggedMails();
  
  const existing = mails.findIndex(m => m.threadId === mailData.threadId);
  if (existing >= 0) {
    mails[existing].tags = mailData.tags || [];
    mails[existing].flaggedAt = new Date().toISOString();
  } else {
    mails.push({
      threadId: mailData.threadId,
      subject: mailData.subject,
      flaggedAt: new Date().toISOString(),
      tags: mailData.tags || []
    });
  }
  
  setFlaggedMails(mails);
}

/**
 * Unflag a mail
 */
function unflagMail(threadId) {
  const mails = getFlaggedMails();
  const filtered = mails.filter(m => m.threadId !== threadId);
  setFlaggedMails(filtered);
}

/**
 * Check if mail is flagged
 */
function isMailFlagged(threadId) {
  const mails = getFlaggedMails();
  return mails.some(m => m.threadId === threadId);
}

/**
 * Update tags for a flagged mail
 */
function updateMailTags(threadId, tags) {
  const mails = getFlaggedMails();
  const mail = mails.find(m => m.threadId === threadId);
  if (mail) {
    mail.tags = tags;
    setFlaggedMails(mails);
  }
}

// ==================== CUSTOM TAGS ====================

/**
 * Get custom tags
 * Format: ['urgent', 'follow-up', 'review', ...]
 */
function getCustomTags() {
  const props = getUserProps();
  const json = props.getProperty(STATE_KEYS.CUSTOM_TAGS);
  return json ? JSON.parse(json) : ['urgent', 'follow-up', 'review'];
}

/**
 * Set custom tags
 */
function setCustomTags(tags) {
  const props = getUserProps();
  props.setProperty(STATE_KEYS.CUSTOM_TAGS, JSON.stringify(tags));
}

/**
 * Add a custom tag
 */
function addCustomTag(tag) {
  const tags = getCustomTags();
  if (!tags.includes(tag)) {
    tags.push(tag);
    setCustomTags(tags);
  }
}

/**
 * Remove a custom tag
 */
function removeCustomTag(tag) {
  const tags = getCustomTags();
  const filtered = tags.filter(t => t !== tag);
  setCustomTags(filtered);
}
