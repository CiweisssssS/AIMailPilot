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
  ANALYSIS_CACHE_TTL_MIN: 'analysis_cache_ttl_min'
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
