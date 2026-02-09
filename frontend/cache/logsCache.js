// utils/logsCache.js - CRITICAL OPTIMIZATION

class LogsCache {
  constructor() {
    // CRITICAL: Limit memory usage
    this.MAX_LOGS_IN_MEMORY = 1000  // Max logs to keep in memory
    this.MAX_PAGES_CACHED = 10      // Max pages to cache
    this.TTL_MINUTES = 2            // Cache expires after 2 minutes (shorter for logs)
    
    // Cache storage
    this.pageCache = new Map()      // Cache for paginated results
    this.incrementalCache = []      // Recent logs for incremental updates
    this.searchCache = new Map()    // Cache for search results
    
    // Memory management
    this.lastCleanup = Date.now()
    this.cleanupInterval = 5 * 60 * 1000 // Cleanup every 5 minutes
    
    // Performance tracking
    this.stats = {
      hits: 0,
      misses: 0,
      memoryUsage: 0
    }
    
    // Auto-cleanup timer
    this.startAutoCleanup()
  }

  // CRITICAL OPTIMIZATION: Page-based caching
  getCachedPage(page, filters = {}) {
    const cacheKey = this.generatePageKey(page, filters)
    const cached = this.pageCache.get(cacheKey)
    
    if (cached && this.isValidCache(cached.timestamp)) {
      this.stats.hits++
      return cached.data
    }
    
    this.stats.misses++
    return null
  }

  setCachedPage(page, data, filters = {}) {
    const cacheKey = this.generatePageKey(page, filters)
    
    // CRITICAL: Limit cache size to prevent memory bloat
    if (this.pageCache.size >= this.MAX_PAGES_CACHED) {
      this.evictOldestPage()
    }
    
    this.pageCache.set(cacheKey, {
      data: data,
      timestamp: Date.now(),
      page: page,
      filters: { ...filters }
    })
    
    this.updateMemoryStats()
  }

  // CRITICAL OPTIMIZATION: Incremental log management
  addIncrementalLogs(newLogs) {
    // Add to beginning of array (newest first)
    this.incrementalCache.unshift(...newLogs)
    
    // CRITICAL: Limit memory usage
    if (this.incrementalCache.length > this.MAX_LOGS_IN_MEMORY) {
      this.incrementalCache = this.incrementalCache.slice(0, this.MAX_LOGS_IN_MEMORY)
    }
    
    // Invalidate related page caches since new data arrived
    this.invalidatePageCaches()
    
    this.updateMemoryStats()
  }

  getRecentLogs(limit = 50) {
    return this.incrementalCache.slice(0, limit)
  }

  // CRITICAL OPTIMIZATION: Search result caching
  getCachedSearch(query, options = {}) {
    const cacheKey = this.generateSearchKey(query, options)
    const cached = this.searchCache.get(cacheKey)
    
    if (cached && this.isValidCache(cached.timestamp)) {
      this.stats.hits++
      return cached.data
    }
    
    this.stats.misses++
    return null
  }

  setCachedSearch(query, data, options = {}) {
    const cacheKey = this.generateSearchKey(query, options)
    
    // Limit search cache size
    if (this.searchCache.size >= 20) {
      this.evictOldestSearch()
    }
    
    this.searchCache.set(cacheKey, {
      data: data,
      timestamp: Date.now(),
      query: query,
      options: { ...options }
    })
    
  }

  // CRITICAL: Memory management methods
  evictOldestPage() {
    let oldestKey = null
    let oldestTime = Date.now()
    
    for (const [key, value] of this.pageCache.entries()) {
      if (value.timestamp < oldestTime) {
        oldestTime = value.timestamp
        oldestKey = key
      }
    }
    
    if (oldestKey) {
      this.pageCache.delete(oldestKey)
    }
  }

  evictOldestSearch() {
    let oldestKey = null
    let oldestTime = Date.now()
    
    for (const [key, value] of this.searchCache.entries()) {
      if (value.timestamp < oldestTime) {
        oldestTime = value.timestamp
        oldestKey = key
      }
    }
    
    if (oldestKey) {
      this.searchCache.delete(oldestKey)
    }
  }

  // CRITICAL: Automatic cleanup to prevent memory leaks
  startAutoCleanup() {
    setInterval(() => {
      this.cleanup()
    }, this.cleanupInterval)
  }

  cleanup() {
    const now = Date.now()
    const ttlMs = this.TTL_MINUTES * 60 * 1000
    
    // Clean expired page caches
    for (const [key, value] of this.pageCache.entries()) {
      if (now - value.timestamp > ttlMs) {
        this.pageCache.delete(key)
      }
    }
    
    // Clean expired search caches
    for (const [key, value] of this.searchCache.entries()) {
      if (now - value.timestamp > ttlMs) {
        this.searchCache.delete(key)
      }
    }
    
    // Clean old incremental logs (keep only last hour)
    const oneHourAgo = now - (60 * 60 * 1000)
    this.incrementalCache = this.incrementalCache.filter(log => {
      const logTime = new Date(log.timestamp).getTime()
      return logTime > oneHourAgo
    })
    
    this.updateMemoryStats()
    this.lastCleanup = now
  }

  // Utility methods
  generatePageKey(page, filters) {
    const filterStr = Object.keys(filters)
      .sort()
      .map(key => `${key}:${filters[key]}`)
      .join('|')
    return `page_${page}_${filterStr}`
  }

  generateSearchKey(query, options) {
    const optStr = Object.keys(options)
      .sort()
      .map(key => `${key}:${options[key]}`)
      .join('|')
    return `search_${query}_${optStr}`
  }

  isValidCache(timestamp) {
    const ttlMs = this.TTL_MINUTES * 60 * 1000
    return (Date.now() - timestamp) < ttlMs
  }

  invalidatePageCaches() {
    this.pageCache.clear()
  }

  invalidateSearchCaches() {
    this.searchCache.clear()
  }

  updateMemoryStats() {
    // Rough memory calculation
    const pageMemory = this.pageCache.size * 50 // ~50KB per page
    const incrementalMemory = this.incrementalCache.length * 0.5 // ~0.5KB per log
    const searchMemory = this.searchCache.size * 25 // ~25KB per search
    
    this.stats.memoryUsage = Math.round(pageMemory + incrementalMemory + searchMemory)
  }

  getStats() {
    const hitRate = this.stats.hits + this.stats.misses > 0 
      ? Math.round((this.stats.hits / (this.stats.hits + this.stats.misses)) * 100)
      : 0

    return {
      hitRate: `${hitRate}%`,
      totalRequests: this.stats.hits + this.stats.misses,
      memoryUsage: `${this.stats.memoryUsage}KB`,
      cachedPages: this.pageCache.size,
      cachedSearches: this.searchCache.size,
      incrementalLogs: this.incrementalCache.length,
      lastCleanup: new Date(this.lastCleanup).toLocaleTimeString()
    }
  }

  // Complete cache reset
  clear() {
    this.pageCache.clear()
    this.searchCache.clear()
    this.incrementalCache = []
    this.stats = { hits: 0, misses: 0, memoryUsage: 0 }
  }

  // Get cache status for debugging
  getDebugInfo() {
    return {
      pageKeys: Array.from(this.pageCache.keys()),
      searchKeys: Array.from(this.searchCache.keys()),
      incrementalCount: this.incrementalCache.length,
      stats: this.getStats()
    }
  }
}

export default new LogsCache()