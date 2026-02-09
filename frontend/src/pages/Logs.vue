<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="header-theme">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h1 class="text-primary mb-0">System Logs</h1>
        
        <div class="d-flex gap-3 align-items-center">
          <!-- Auto-refresh Controls -->
          <div class="surface-card d-flex align-items-center gap-2 px-3 py-2 rounded">
            <i class="bi bi-arrow-repeat text-success" :class="{ 'spinning': loading }"></i>
            <span class="text-secondary small">
              <span v-if="autoRefreshEnabled">Updates in {{ countdown }}s</span>
              <span v-else>Auto-refresh disabled</span>
            </span>
            <button 
              class="btn btn-sm"
              :class="autoRefreshEnabled ? 'btn-outline-secondary' : 'btn-outline-success'"
              @click="toggleAutoRefresh"
            >
              {{ autoRefreshEnabled ? 'Disable' : 'Enable' }}
            </button>
          </div>
          
          <!-- Connection Status -->
          <div class="d-flex align-items-center gap-2 px-3 py-2 rounded" :class="getConnectionStatusClass()">
            <i :class="getConnectionIcon()"></i>
            <span class="small fw-medium">{{ getConnectionText() }}</span>
          </div>
          
          <!-- Emergency Reconnect -->
          <button 
            v-if="error || connectionLost" 
            class="btn btn-warning btn-sm" 
            @click="emergencyReconnect"
            :disabled="loading"
          >
            <i class="bi bi-arrow-clockwise" :class="{ 'spinning': loading }"></i>
            {{ loading ? 'Reconnecting...' : 'Reconnect' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Filters Section -->
    <div class="surface-card border-theme rounded mb-4 p-4">
      <div class="row g-3">
        <div class="col-md-4">
          <label for="categoryFilter" class="form-label text-primary">Filter by Category</label>
          <select 
            id="categoryFilter" 
            v-model="categoryFilter" 
            @change="handleFilterChange" 
            :disabled="loading"
            class="form-select input-complete"
          >
            <option value="all">All Categories</option>
            <option value="session">Sessions</option>
            <option value="login">Login</option>
            <option value="logout">Logout</option>
            <option value="category">Categories</option>
            <option value="product">Products</option>
            <option value="customer">Customers</option>
            <option value="user">Users</option>
            <option value="create">Create Actions</option>
            <option value="update">Update Actions</option>
            <option value="delete">Delete Actions</option>
          </select>
        </div>

        <div class="col-md-4">
          <label for="searchFilter" class="form-label text-primary">Search User ID</label>
          <input 
            id="searchFilter" 
            v-model="searchFilter" 
            @input="handleFilterChange"
            type="text" 
            placeholder="Search specific user ID..."
            :disabled="loading"
            class="form-control input-complete"
          />
        </div>

        <div class="col-md-4">
          <label for="pageSize" class="form-label text-primary">Records per page</label>
          <select 
            id="pageSize" 
            v-model="pageSize" 
            @change="handlePageSizeChange"
            :disabled="loading"
            class="form-select input-complete"
          >
            <option value="10">10</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && session_logs.length === 0" class="text-center py-5">
      <div class="spinner-border text-accent mb-3"></div>
      <p class="text-secondary">Loading system logs...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="status-error rounded p-4 text-center mb-4">
      <i class="bi bi-exclamation-triangle fs-2 mb-3"></i>
      <p class="mb-3">{{ error }}</p>
      <button class="btn btn-submit" @click="loadLogs" :disabled="loading">
        <i class="bi bi-arrow-clockwise"></i>
        {{ loading ? 'Retrying...' : 'Try Again' }}
      </button>
    </div>

    <!-- Refresh Indicator -->
    <div v-if="loading && session_logs.length > 0" class="status-info rounded p-3 mb-4">
      <div class="d-flex align-items-center">
        <div class="spinner-border spinner-border-sm me-2"></div>
        Refreshing logs data...
      </div>
    </div>

    <!-- Table Info -->
    <div v-if="!loading && paginatedLogs.length > 0" class="surface-card border-theme-subtle rounded-top p-3 mb-0">
      <small class="text-tertiary">
        Showing {{ startRecord }}-{{ endRecord }} of {{ filteredLogs.length }} entries
        <span v-if="hasActiveFilters" class="text-accent">
          (filtered from {{ totalLogsCount }} total records)
        </span>
      </small>
    </div>

    <!-- Data Table -->
    <TableTemplate
      v-if="!loading || session_logs.length > 0"
      :items-per-page="parseInt(pageSize)"
      :total-items="filteredLogs.length"
      :current-page="currentPage"
      :show-pagination="true"
      @page-changed="goToPage"
    >
      <template #header>
        <tr>
          <th style="width: 10%;">Log ID</th>
          <th style="width: 12%;">User ID</th>
          <th style="width: 12%;">Ref. ID</th>
          <th style="width: 15%;">Event Type</th>
          <th style="width: 10%; text-align: center;">Action</th>
          <th style="width: 10%; text-align: center;">Status</th>
          <th style="width: 15%;">Timestamp</th>
          <th style="width: 16%;">Remarks</th>
        </tr>
      </template>

      <template #body>
        <tr 
          v-for="sessionLog in paginatedLogs" 
          :key="sessionLog.log_id || sessionLog._id"
          :class="{ 'table-warning': isNewEntry(sessionLog) }"
        >
          <td>
            <span class="badge fw-semibold" style="color: white;" :class="getLogTypeBadgeClass(sessionLog.logType)">
              {{ sessionLog.formattedLogId }}
            </span>
          </td>
          <td class="text-secondary">{{ sessionLog.user_id }}</td>
          <td class="text-secondary">{{ sessionLog.ref_id }}</td>
          <td class="text-secondary">{{ sessionLog.event_type }}</td>
          <td class="text-center text-tertiary">{{ getAmountQty(sessionLog) }}</td>
          <td class="text-center">
            <span class="badge" style="color: white;" :class="getStatusBadgeClass(sessionLog.status)">
              {{ sessionLog.status }}
            </span>
          </td>
          <td class="text-secondary small">{{ formatTimestamp(sessionLog.timestamp) }}</td>
          <td class="text-tertiary small" :title="sessionLog.remarks">
            {{ truncateRemarks(sessionLog.remarks) }}
          </td>
        </tr>
      </template>
    </TableTemplate>

    <!-- Empty State -->
    <div v-if="!loading && paginatedLogs.length === 0 && !error" class="card-theme text-center py-5">
      <i class="bi bi-file-text text-tertiary" style="font-size: 3rem;"></i>
      <p class="mt-3 mb-4 text-tertiary">
        {{ session_logs.length === 0 ? 'No system logs found' : 'No logs match the current filters' }}
      </p>
      <div class="d-flex gap-2 justify-content-center">
        <button v-if="session_logs.length === 0" class="btn btn-submit" @click="loadLogs">
          <i class="bi bi-arrow-clockwise"></i>
          Refresh Logs
        </button>
        <template v-else>
          <button class="btn btn-cancel" @click="clearFilters">
            <i class="bi bi-funnel"></i>
            Clear Filters
          </button>
          <button class="btn btn-refresh" @click="loadLogs">
            <i class="bi bi-arrow-clockwise"></i>
            Refresh Data
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import TableTemplate from '@/components/common/TableTemplate.vue'
import APILogs from '@/services/apiLogs'

export default {
  name: 'SystemLogs',
  components: {
    TableTemplate
  },
  
  data() {
    return {
      session_logs: [],
      loading: false,
      error: null,
      
      // Filters
      categoryFilter: 'all',
      searchFilter: '',
      
      // Pagination
      currentPage: 1,
      pageSize: 25,
      
      // Auto-refresh
      autoRefreshEnabled: true,
      autoRefreshInterval: 30000,
      baseRefreshInterval: 30000,
      autoRefreshTimer: null,
      countdown: 30,
      countdownTimer: null,
      
      // Connection tracking
      connectionLost: false,
      consecutiveErrors: 0,
      lastSuccessfulLoad: null,
      
      // Performance
      filterDebounceTimer: null,
      lastLoadTime: null,
      newEntryIds: new Set(),
      recentActivity: [],
      
      // Memoization
      memoizedFilters: {
        categoryFilter: 'all',
        searchFilter: '',
        result: []
      }
    }
  },
  
  computed: {
    filteredLogs() {
      if (
        this.memoizedFilters.categoryFilter === this.categoryFilter &&
        this.memoizedFilters.searchFilter === this.searchFilter &&
        this.memoizedFilters.result.length > 0
      ) {
        return this.memoizedFilters.result
      }
      
      let filtered = [...this.session_logs]
      
      if (this.categoryFilter !== 'all') {
        filtered = filtered.filter(log => {
          const eventType = (log.event_type || '').toLowerCase()
          return eventType.includes(this.categoryFilter.toLowerCase())
        })
      }

      if (this.searchFilter.trim()) {
        const search = this.searchFilter.toLowerCase()
        filtered = filtered.filter(log => 
          (log.user_id || '').toLowerCase().includes(search)
        )
      }
      
      filtered.sort((a, b) => {
        const dateA = new Date(a.timestamp || 0)
        const dateB = new Date(b.timestamp || 0)
        return dateB - dateA
      })
      
      this.memoizedFilters = {
        categoryFilter: this.categoryFilter,
        searchFilter: this.searchFilter,
        result: filtered
      }
      
      return filtered
    },
    
    paginatedLogs() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      const logs = this.filteredLogs.slice(start, end)
      
      return logs.map((log, index) => {
        const position = start + index + 1
        const logType = this.getLogType(log)
        
        return {
          ...log,
          positionNumber: position,
          logType: logType,
          formattedLogId: this.getFormattedLogId(log, position)
        }
      })
    },
    
    startRecord() {
      return this.filteredLogs.length === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1
    },
    
    endRecord() {
      const end = this.currentPage * this.pageSize
      return end > this.filteredLogs.length ? this.filteredLogs.length : end
    },
    
    totalLogsCount() {
      return this.session_logs.length
    },

    hasActiveFilters() {
      return this.categoryFilter !== 'all' || this.searchFilter.trim() !== ''
    }
  },
  
  methods: {
    async loadLogs(isAutoRefresh = false, isEmergencyReconnect = false) {
      // Prevent multiple simultaneous requests
      if (this.loading && !isAutoRefresh && !isEmergencyReconnect) return
      
      this.loading = true
      if (!isEmergencyReconnect) {
        this.error = null
      }
      
      try {
        let logType = 'all'
        if (['session', 'login', 'logout'].includes(this.categoryFilter)) {
          logType = 'session'
        } else if (['category', 'product', 'customer', 'user', 'create', 'update', 'delete'].includes(this.categoryFilter)) {
          logType = 'audit'
        }


        const response = await APILogs.DisplayCombinedLogs({
          limit: 100,
          type: logType
        })


        const previousLogsLength = this.session_logs.length
        
        // FIXED: Improved response handling with better error checking
        let newLogs = []
        
        // Check for different response formats
        if (response && response.success && Array.isArray(response.data)) {
          newLogs = response.data
        } else if (Array.isArray(response)) {
          newLogs = response
        } else if (response && Array.isArray(response.data)) {
          newLogs = response.data
        } else if (response && response.results && Array.isArray(response.results)) {
          // Django REST framework pagination format
          newLogs = response.results
        } else {
          console.warn("⚠️ Unexpected response format:", response)
          newLogs = []
        }


        // FIXED: Validate that we actually have data
        if (!Array.isArray(newLogs)) {
          throw new Error('Invalid response format: expected array of logs')
        }
        
        // Reset connection state on successful response
        this.connectionLost = false
        this.consecutiveErrors = 0
        this.lastSuccessfulLoad = Date.now()
        this.error = null
        
        this.trackActivityAndAdjustRefreshRate(newLogs, previousLogsLength)
        
        // FIXED: Handle new entries tracking more safely
        if (isAutoRefresh && this.session_logs.length > 0) {
          const existingIds = new Set(
            this.session_logs.map(log => log.log_id || log._id || log.id).filter(Boolean)
          )
          
          newLogs.forEach(log => {
            const id = log.log_id || log._id || log.id
            if (id && !existingIds.has(id)) {
              this.newEntryIds.add(id)
              this.recentActivity.push({
                timestamp: Date.now(),
                logId: id
              })
            }
          })
          
          // Clear new entry highlights after 5 seconds
          setTimeout(() => {
            this.newEntryIds.clear()
          }, 5000)
        }
        
        // FIXED: Always assign the data, even if empty
        this.session_logs = newLogs
        this.lastLoadTime = Date.now()
        
        // Clear memoized filters to force recalculation
        this.memoizedFilters.result = []
        
        // Reset to first page on manual refresh
        if (!isAutoRefresh) {
          this.currentPage = 1
        }


      } catch (error) {
        console.error("❌ Error loading combined logs:", error)
        
        this.consecutiveErrors++
        
        // FIXED: Better error message handling
        const errorMessage = error.response?.data?.message || 
                            error.response?.data?.error || 
                            error.message || 
                            'Failed to load logs'
        
        this.error = errorMessage
        
        // Mark connection as lost after 3 consecutive errors
        if (this.consecutiveErrors >= 3) {
          this.connectionLost = true
        }
        
        // FIXED: Only clear logs on manual refresh failure, not auto-refresh
        if (!isAutoRefresh) {
          this.session_logs = []
        }


      } finally {
        this.loading = false
      }
    },

    async emergencyReconnect() {
      this.consecutiveErrors = 0
      this.connectionLost = false
      await this.loadLogs(false, true)
      
      if (!this.autoRefreshEnabled) {
        this.autoRefreshEnabled = true
        this.startAutoRefresh()
      }
    },

    trackActivityAndAdjustRefreshRate(newLogs, previousLength) {
      const now = Date.now()
      
      this.recentActivity = this.recentActivity.filter(
        activity => now - activity.timestamp < 300000
      )
      
      const recentCount = this.recentActivity.filter(
        activity => now - activity.timestamp < 120000
      ).length
      
      if (recentCount >= 10) {
        this.autoRefreshInterval = 10000
      } else if (recentCount >= 5) {
        this.autoRefreshInterval = 20000
      } else if (recentCount === 0 && this.recentActivity.length === 0) {
        this.autoRefreshInterval = 60000
      } else {
        this.autoRefreshInterval = this.baseRefreshInterval
      }
      
      if (this.autoRefreshEnabled && this.autoRefreshTimer) {
        this.startAutoRefresh()
      }
    },

    getConnectionStatusClass() {
      const status = this.getConnectionStatus()
      const classes = {
        'connection-good': 'border-success text-success',
        'connection-unstable': 'border-warning text-warning', 
        'connection-lost': 'border-danger text-danger',
        'connection-unknown': 'border-secondary text-tertiary'
      }
      return `surface-card border ${classes[status] || classes['connection-unknown']}`
    },

    getConnectionStatus() {
      if (this.connectionLost) return 'connection-lost'
      if (this.consecutiveErrors > 0) return 'connection-unstable'
      if (this.lastSuccessfulLoad && (Date.now() - this.lastSuccessfulLoad < 60000)) return 'connection-good'
      return 'connection-unknown'
    },

    getConnectionIcon() {
      const icons = {
        'connection-good': 'bi bi-wifi text-success',
        'connection-unstable': 'bi bi-wifi-1 text-warning',
        'connection-lost': 'bi bi-wifi-off text-danger',
        'connection-unknown': 'bi bi-wifi text-muted'
      }
      return icons[this.getConnectionStatus()] || icons['connection-unknown']
    },

    getConnectionText() {
      const texts = {
        'connection-good': 'Connected',
        'connection-unstable': 'Unstable',
        'connection-lost': 'Connection Lost',
        'connection-unknown': 'Connecting...'
      }
      return texts[this.getConnectionStatus()] || texts['connection-unknown']
    },

    toggleAutoRefresh() {
      if (this.autoRefreshEnabled) {
        this.autoRefreshEnabled = false
        this.stopAutoRefresh()
      } else {
        this.autoRefreshEnabled = true
        this.startAutoRefresh()
      }
    },
    
    startAutoRefresh() {
      this.stopAutoRefresh()
      
      this.countdown = this.autoRefreshInterval / 1000
      this.countdownTimer = setInterval(() => {
        this.countdown--
        if (this.countdown <= 0) {
          this.countdown = this.autoRefreshInterval / 1000
        }
      }, 1000)
      
      this.autoRefreshTimer = setInterval(() => {
        this.loadLogs(true)
      }, this.autoRefreshInterval)
    },
    
    stopAutoRefresh() {
      if (this.autoRefreshTimer) {
        clearInterval(this.autoRefreshTimer)
        this.autoRefreshTimer = null
      }
      
      if (this.countdownTimer) {
        clearInterval(this.countdownTimer)
        this.countdownTimer = null
      }
    },

    handleFilterChange() {
      if (this.filterDebounceTimer) {
        clearTimeout(this.filterDebounceTimer)
      }
      
      this.filterDebounceTimer = setTimeout(() => {
        this.applyFilters()
      }, 300)
    },
    
    applyFilters() {
      this.currentPage = 1
      this.memoizedFilters.result = []
    },

    clearFilters() {
      this.categoryFilter = 'all'
      this.searchFilter = ''
      this.currentPage = 1
      this.memoizedFilters.result = []
    },

    goToPage(page) {
      if (page >= 1 && page <= Math.ceil(this.filteredLogs.length / this.pageSize) && page !== this.currentPage) {
        this.currentPage = page
      }
    },
    
    handlePageSizeChange() {
      this.currentPage = 1
    },

    getLogType(log) {
      const eventType = (log.event_type || '').toLowerCase()
      
      if (eventType.includes('session') || 
          eventType.includes('login') || 
          eventType.includes('logout') || 
          eventType.includes('auth')) {
        return 'session'
      }
      
      return 'audit'
    },

    getFormattedLogId(log, position) {
      const logType = this.getLogType(log)
      const prefix = logType === 'session' ? 'SES' : 'AUD'
      const typeCounter = this.getTypeCounter(position, logType)
      return `${prefix}-${typeCounter}`
    },

    getTypeCounter(currentPosition, logType) {
      // Count how many logs of this type come AFTER this position
      let counter = 0
      const totalOfType = this.filteredLogs.filter(log => this.getLogType(log) === logType).length
      
      // Count items of the same type that appear before this position
      for (let i = 0; i < currentPosition; i++) {
        if (i < this.filteredLogs.length) {
          const log = this.filteredLogs[i]
          if (this.getLogType(log) === logType) {
            counter++
          }
        }
      }
      
      // Return the reverse count
      return totalOfType - counter + 1
    },

    getLogTypeBadgeClass(logType) {
      return logType === 'session' ? 'bg-primary' : 'bg-secondary'
    },

    getStatusBadgeClass(status) {
      const statusMap = {
        'completed': 'bg-success',
        'success': 'bg-success',
        'active': 'bg-info',
        'failed': 'bg-danger',
        'error': 'bg-danger'
      }
      
      return statusMap[(status || '').toLowerCase()] || 'bg-secondary'
    },

    getAmountQty(sessionLog) {
      const eventType = (sessionLog.event_type || '').toLowerCase()
      return (eventType === 'session' || eventType === 'session complete') 
        ? 'None' 
        : sessionLog.amount_qty || '-'
    },

    formatTimestamp(timestamp) {
      if (!timestamp) return 'N/A'
      
      try {
        if (!this._timestampCache) this._timestampCache = new Map()
        
        if (this._timestampCache.has(timestamp)) {
          return this._timestampCache.get(timestamp)
        }
        
        const formatted = new Date(timestamp).toLocaleDateString('en-US', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
        
        this._timestampCache.set(timestamp, formatted)
        return formatted
      } catch (error) {
        return timestamp
      }
    },

    truncateRemarks(remarks) {
      if (!remarks) return '-'
      return remarks.length > 50 ? remarks.substring(0, 50) + '...' : remarks
    },
    
    isNewEntry(sessionLog) {
      const id = sessionLog.log_id || sessionLog._id
      return this.newEntryIds.has(id)
    }
  },
  
  async mounted() {
    await this.loadLogs()
    this.autoRefreshEnabled = true
    this.startAutoRefresh()
  },
  
  beforeUnmount() {
    this.stopAutoRefresh()
    
    if (this.filterDebounceTimer) {
      clearTimeout(this.filterDebounceTimer)
    }
    
    if (this._timestampCache) {
      this._timestampCache.clear()
    }
  }
}
</script>

<style scoped>
.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.table-warning {
  background-color: var(--status-warning-bg) !important;
  animation: highlight-fade 3s ease-out;
}

@keyframes highlight-fade {
  0% {
    background-color: var(--status-warning-bg);
    transform: scale(1.01);
  }
  100% {
    background-color: var(--surface-primary);
    transform: scale(1);
  }
}

@media (max-width: 768px) {
  .d-flex.gap-3 {
    flex-direction: column;
    gap: 1rem !important;
  }
  
  .surface-card.d-flex {
    flex-direction: column;
    align-items: flex-start !important;
  }
}
</style>