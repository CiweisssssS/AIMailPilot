/**
 * Cache Manager
 * In-memory cache with TTL for analysis results
 * Note: CacheService in Apps Script has quota limits, so we use it carefully
 */

/**
 * Get cache instance
 */
function getCache() {
  return CacheService.getUserCache();
}

/**
 * Get cache service (alias for getCache)
 */
function getCacheService() {
  return getCache();
}

/**
 * Generate cache key for thread analysis
 */
function getCacheKey(threadId) {
  return `analysis_${threadId}`;
}

/**
 * Get cached analysis result
 * @param {string} threadId
 * @returns {Object|null} Cached analysis or null
 */
function getCachedAnalysis(threadId) {
  try {
    const cache = getCache();
    const cacheKey = getCacheKey(threadId);
    const cached = cache.get(cacheKey);
    
    if (cached) {
      return JSON.parse(cached);
    }
    
    return null;
  } catch (error) {
    console.error('Error getting cached analysis:', error);
    return null;
  }
}

/**
 * Set cached analysis result
 * @param {string} threadId
 * @param {Object} analysis - Analysis result from backend
 */
function setCachedAnalysis(threadId, analysis) {
  try {
    const cache = getCache();
    const cacheKey = getCacheKey(threadId);
    const ttlMin = getCacheTtlMin();
    const ttlSeconds = ttlMin * 60;
    
    cache.put(cacheKey, JSON.stringify(analysis), ttlSeconds);
  } catch (error) {
    console.error('Error setting cached analysis:', error);
  }
}

/**
 * Clear cache for a specific thread
 */
function clearThreadCache(threadId) {
  try {
    const cache = getCache();
    const cacheKey = getCacheKey(threadId);
    cache.remove(cacheKey);
  } catch (error) {
    console.error('Error clearing thread cache:', error);
  }
}

/**
 * Clear all analysis cache
 */
function clearAllCache() {
  try {
    const cache = getCache();
    cache.removeAll(['analysis_']);
  } catch (error) {
    console.error('Error clearing all cache:', error);
  }
}
