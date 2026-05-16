<template>
  <div class="dashboard">
    <!-- KPI Cards Grid - Using CardTemplate with custom sizes -->
    <div class="kpi-grid">
      <!-- Total Profit Card - Tall card spanning 2 rows -->
      <CardTemplate
        size="custom"
        width="100%"
        :min-height="300"
        :padding="20"
        title="Total Profit"
        :value="profitLoading ? 'Loading...' : formattedTotalProfit"
        value-color="primary"
        :subtitle="profitSubtitle"
        border-color="primary"
        border-position="all"
        shadow="md"
        class="profit-card"
      >
        <template #header>
          <div class="card-header-with-change">
            <span v-if="!profitError" class="change-badge positive">Live</span>
            <span v-else class="change-badge negative">Error</span>
          </div>
        </template>
      </CardTemplate>
      
      <!-- Total Products Card -->
      <CardTemplate
        size="custom"
        width="100%"
        :height="140"
        :padding="16"
        title="Total Products"
        :value="productsLoading ? 'Loading...' : totalProducts"
        value-color="success"
        :subtitle="productsLoading ? 'Fetching data...' : `Updated: ${lastUpdated}`"
        border-color="success"
        border-position="all"
        shadow="md"
      >
        <template #header>
          <div class="card-header-with-change">
            <span v-if="!productsError" class="change-badge positive">Live</span>
            <span v-else class="change-badge negative">Error</span>
          </div>
        </template>
      </CardTemplate>
      
      <!-- Monthly Revenue Card -->
      <CardTemplate
        size="custom"
        width="100%"
        :height="140"
        :padding="16"
        title="Monthly Revenue"
        :value="monthlyIncomeLoading ? 'Loading...' : formattedMonthlyRevenue"
        value-color="secondary"
        :subtitle="monthlyRevenueSubtitle"
        border-color="secondary"
        border-position="all"
        shadow="md"
      >
        <template #header>
          <div class="card-header-with-change">
            <span v-if="!monthlyIncomeError" class="change-badge positive">Live</span>
            <span v-else class="change-badge negative">Error</span>
          </div>
        </template>
      </CardTemplate>
      
      <!-- Top Performing Month Card -->
      <CardTemplate
        size="custom"
        width="100%"
        :height="140"
        :padding="16"
        title="Top Performing Month"
        :value="topMonthLoading ? 'Loading...' : topMonthName"
        value-color="info"
        :subtitle="topMonthSubtitle"
        border-color="info"
        border-position="all"
        shadow="md"
      >
        <template #header>
          <div class="card-header-with-change">
            <span v-if="!topMonthError" class="change-badge positive">Live</span>
            <span v-else class="change-badge negative">Error</span>
          </div>
        </template>
      </CardTemplate>
      
      <!-- Total Items Sold Card -->
      <CardTemplate
        size="custom"
        width="100%"
        :height="140"
        :padding="16"
        title="Total Items Sold"
        :value="salesStatsLoading ? 'Loading...' : totalOrders"
        value-color="error"
        :subtitle="salesDataSubtitle"
        border-color="error"
        border-position="all"
        shadow="md"
      >
        <template #header>
          <div class="card-header-with-change">
            <span v-if="!salesStatsError" class="change-badge positive">Live</span>
            <span v-else class="change-badge negative">Error</span>
          </div>
        </template>
      </CardTemplate>
    </div>

    <!-- Bottom Section: Real-time Transactions + Target Sales -->
    <div class="bottom-section">
      <div class="transactions-container">
        <CardTemplate
          size="custom"
          width="100%"
          :min-height="320"
          :padding="20"
          title="Real-time Sales Transactions"
          :subtitle="`Last updated: ${lastTransactionUpdate || 'Loading...'}`"
          border-color="neutral"
          border-position="all"
          shadow="md"
        >
          <template #header>
            <div class="transactions-header-controls">
              <div class="refresh-controls">
                <button 
                  @click="toggleAutoRefresh" 
                  class="btn btn-sm"
                  :class="autoRefreshEnabled ? 'btn-primary' : 'btn-secondary'"
                  :title="autoRefreshEnabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled'"
                >
                  <RefreshCw :size="14" :class="{ 'spinning': autoRefreshEnabled }" />
                  {{ autoRefreshEnabled ? 'Auto-refresh ON' : 'Auto-refresh OFF' }}
                </button>
                <button 
                  @click="loadRecentTransactions" 
                  class="btn btn-sm btn-secondary"
                  :disabled="transactionsLoading"
                  title="Refresh now"
                >
                  <RefreshCw :size="14" />
                  Refresh
                </button>
              </div>
              <div class="transaction-count">
                <span v-if="transactionsLoading">Loading...</span>
                <span v-else>{{ recentTransactions.length }} transactions</span>
              </div>
            </div>
          </template>
          
          <template #content>
            <div class="transactions-content">
              <div v-if="transactionsLoading && recentTransactions.length === 0" class="loading-state">
                <p>Loading transactions...</p>
              </div>
              <div v-else-if="transactionsError" class="error-state">
                <p>{{ transactionsError }}</p>
                <button @click="loadRecentTransactions" class="btn btn-sm btn-primary mt-2">
                  Retry
                </button>
              </div>
              <div v-else-if="recentTransactions.length === 0" class="empty-state">
                <p>No transactions found</p>
              </div>
              <div v-else class="transactions-table-container">
                <table class="transactions-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Transaction ID</th>
                      <th>Customer</th>
                      <th>Items</th>
                      <th>Payment Method</th>
                      <th>Amount</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="transaction in recentTransactions" 
                      :key="transaction._id || transaction.id"
                      class="transaction-row"
                    >
                      <td class="time-cell">
                        {{ formatTransactionTime(transaction.transaction_date || transaction.created_at) }}
                      </td>
                      <td class="id-cell">
                        {{ formatTransactionId(transaction._id || transaction.id) }}
                      </td>
                      <td class="customer-cell">
                        {{ transaction.customer_name || transaction.customer?.full_name || 'Walk-in' }}
                      </td>
                      <td class="items-cell">
                        {{ getItemCount(transaction) }} item(s)
                      </td>
                      <td class="payment-cell">
                        <span class="payment-badge" :class="getPaymentMethodClass(transaction.payment_method)">
                          {{ formatPaymentMethod(transaction.payment_method) }}
                        </span>
                      </td>
                      <td class="amount-cell">
                        {{ formatCurrency(transaction.total_amount || transaction.total || 0) }}
                      </td>
                      <td class="status-cell">
                        <span class="status-badge" :class="getStatusClass(transaction.status || transaction.voided)">
                          {{ getStatusText(transaction.status || transaction.voided) }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </CardTemplate>
      </div>
      
      <div class="top-products-container">
        <CardTemplate
          size="custom"
          width="100%"
          :min-height="320"
          :padding="20"
          title="Top Products"
          value-color="primary"
          subtitle="Top 10 best-selling products"
          border-color="primary"
          border-position="all"
          shadow="lg"
        >
          <template #header>
            <!-- Date Range Picker -->
            <div class="date-range-picker">
              
              <div class="date-input-group">
                <label class="date-label">From:</label>
                <input 
                  type="date" 
                  v-model="topProductsStartDate"
                  @change="onTopProductsDateChange"
                  class="date-input"
                  :max="topProductsEndDate || null"   
                />
              </div>

              <div class="date-input-group">
                <label class="date-label">To:</label>
                <input 
                  type="date" 
                  v-model="topProductsEndDate"
                  @change="onTopProductsDateChange"
                  class="date-input"
                  :min="topProductsStartDate || null"  
                />
              </div>

              <button 
                @click="resetTopProductsDateRange"
                class="btn btn-sm btn-secondary"
                title="Reset to default range"
              >
                Reset
              </button>
            </div>

            <!-- OPTIONAL: small inline error message -->
            <p v-if="topProductsDateError" class="text-red-600 text-sm mt-1">
              {{ topProductsDateError }}
            </p>
          </template>

          
          <template #content>
            <!-- Loading State -->
            <div v-if="topProductsLoading" class="top-products-loading">
              <p>Loading top products...</p>
            </div>
            
            <!-- Error State -->
            <div v-else-if="topProductsError" class="top-products-error">
              <p>{{ topProductsError }}</p>
              <button @click="loadTopProducts" class="btn btn-sm btn-primary mt-2">
                Retry
            </button>
            </div>
            
            <!-- Empty State -->
            <div v-else-if="topProducts.length === 0" class="top-products-empty">
              <p>No products found for the selected date range</p>
            </div>
            
            <!-- Products List -->
            <div v-else class="top-products-list">
              <div 
                v-for="(product, index) in topProducts" 
                :key="product.item_name || product.name || index"
                class="top-product-item"
              >
                <div class="product-rank">
                  <span class="rank-number">{{ index + 1 }}</span>
                </div>
                <div class="product-info">
                  <div class="product-name">{{ product.item_name || product.name || product.product_name || 'Unknown Product' }}</div>
                  <div class="product-stats">
                    <span class="product-quantity">{{ formatNumber(product.quantity || product.items_sold || product.total_quantity || 0) }} sold</span>
                    <span class="product-revenue">{{ formatCurrency(product.total_amount || product.total_sales || product.revenue || 0) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </CardTemplate>
      </div>
    </div>
  </div>
</template>

<script>
import CardTemplate from '../components/common/CardTemplate.vue'
import { formatCurrency as formatCurrencyHelper, formatNumber as formatNumberHelper } from '@/helpers/currencyHelpers'
import { useProducts } from '@/composables/api/useProducts.js'
import { useSales } from '@/composables/api/useSales.js'
import salesAPIService from '@/services/apiReports.js'
import { RefreshCw } from 'lucide-vue-next'

export default {
  name: 'Dashboard',
  components: {
    CardTemplate,
    RefreshCw
  },
  setup() {
    const { 
      products, 
      productStats, 
      fetchProducts, 
      initializeProducts,
      loading: productsLoading, 
      error: productsError 
    } = useProducts()

    const {
      totalSalesCount,
      salesStatsLoading,
      salesStatsError,
      loadTotalSalesCount,
      loadTotalSalesCountAllTime,
      totalProfit,
      profitLoading,
      profitError,
      loadTotalProfit,
      loadTotalProfitAllTime,
      monthlyIncome,
      monthlyIncomeLoading,
      monthlyIncomeError,
      loadMonthlyIncome,
      loadCurrentMonthIncome,
      chartData: salesChartData,
      selectedFrequency: salesSelectedFrequency,
      getTopChartItems,
      onFrequencyChange,
      calculateDateRange
    } = useSales()

    return {
      products,
      productStats,
      fetchProducts,
      initializeProducts,
      productsLoading,
      productsError,
      totalSalesCount,
      salesStatsLoading,
      salesStatsError,
      loadTotalSalesCount,
      loadTotalSalesCountAllTime,
      totalProfit,
      profitLoading,
      profitError,
      loadTotalProfit,
      loadTotalProfitAllTime,
      monthlyIncome,
      monthlyIncomeLoading,
      monthlyIncomeError,
      loadMonthlyIncome,
      loadCurrentMonthIncome,
      calculateDateRange
    }
  },
  data() {
    return {
      isShowingAllTimeSales: false, // Track if we're showing all-time data due to no last month sales
      isShowingAllTimeProfit: false, // Track if we're showing all-time profit due to no last month profit
      currentMonthPeriod: null, // Track current month period for monthly income
      // Raw data values
      rawData: {
        totalProfit: 78452.23,
        monthlyIncome: 120042
      },
      // Transaction viewer state
      recentTransactions: [],
      transactionsLoading: false,
      transactionsError: null,
      autoRefreshEnabled: true,
      autoRefreshInterval: null,
      refreshTimer: null,
      lastTransactionUpdate: null,
      // Top performing month state
      topPerformingMonth: null,
      topMonthLoading: false,
      topMonthError: null,
      // Top products state
      topProducts: [],
      topProductsLoading: false,
      topProductsError: null,
      topProductsStartDate: null,
      topProductsEndDate: null
    }
  },
  computed: {
    // Formatted values for display
    formattedTotalProfit() {
      return formatCurrencyHelper(this.totalProfit || 0)
    },
    profitSubtitle() {
      if (this.profitLoading) {
        return 'Fetching data...'
      }
      return this.isShowingAllTimeProfit ? 'All time' : `From ${this.lastMonthPeriod}`
    },
    totalProducts() {
      // Use dynamic data from products API - check multiple sources for total count
      let count = 0
      
      // First try productStats.total (computed from products array)
      if (this.productStats?.total !== undefined) {
        count = this.productStats.total
      }
      // Fallback to direct products array length if productStats not available yet
      else if (this.products && Array.isArray(this.products)) {
        count = this.products.length
      }
      
      return formatNumberHelper(count)
    },
    lastUpdated() {
      return new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },
    lastMonthPeriod() {
      const now = new Date()
      const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return lastMonth.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long'
      })
    },
    salesDataSubtitle() {
      if (this.salesStatsLoading) {
        return 'Fetching data...'
      }
      return this.isShowingAllTimeSales ? 'All time' : `From ${this.lastMonthPeriod}`
    },
    formattedMonthlyRevenue() {
      return formatCurrencyHelper(this.monthlyIncome || 0)
    },
    monthlyRevenueSubtitle() {
      if (this.monthlyIncomeLoading) {
        return 'Fetching data...'
      }
      return this.currentMonthPeriod || 'Current month'
    },
    totalOrders() {
      return formatNumberHelper(this.totalSalesCount)
    },
    topMonthName() {
      if (this.topMonthLoading) {
        return 'Loading...'
      }
      if (this.topMonthError) {
        return 'Error'
      }
      if (!this.topPerformingMonth) {
        return 'No data'
      }
      return this.topPerformingMonth.monthName || 'Unknown month'
    },
    topMonthSubtitle() {
      if (this.topMonthLoading) {
        return 'Fetching data...'
      }
      if (this.topMonthError) {
        return 'Error loading data'
      }
      if (!this.topPerformingMonth) {
        return 'No data available'
      }
      const revenue = formatCurrencyHelper(this.topPerformingMonth.revenue || 0)
      return `Revenue: ${revenue}`
    },
  },
  methods: {
    // ========== HELPER METHODS ==========
     onTopProductsDateChange() {
        this.topProductsDateError = null

        // Only load when BOTH dates exist
        if (this.topProductsStartDate && this.topProductsEndDate) {
          this.loadTopProducts()
        }
      },

      resetTopProductsDateRange() {
        this.topProductsStartDate = null
        this.topProductsEndDate = null
        this.topProductsDateError = null
        this.loadTopProducts()
      },
    formatCurrency(value) {
      // Use the imported formatCurrencyHelper function
      return formatCurrencyHelper(value)
    },
    
    formatNumber(value) {
      // Use the imported formatNumberHelper function
      return formatNumberHelper(value)
    },
    
    // ========== TRANSACTION VIEWER METHODS ==========
    async loadRecentTransactions() {
      this.transactionsLoading = true
      this.transactionsError = null
      
      try {
        const response = await salesAPIService.getRecentSales({ limit: 20 })
        
        // Handle different response formats
        let transactions = []
        
        if (response?.success && Array.isArray(response.data)) {
          transactions = response.data
        } else if (response?.data && Array.isArray(response.data)) {
          transactions = response.data
        } else if (response?.transactions && Array.isArray(response.transactions)) {
          transactions = response.transactions
        } else if (Array.isArray(response)) {
          transactions = response
        } else {
          // Try to extract any array from the response
          if (response && typeof response === 'object') {
            for (const key in response) {
              if (Array.isArray(response[key])) {
                transactions = response[key]
              break
            }
          }
          }
        }
        
        if (transactions.length === 0) {
          this.transactionsError = 'No transactions found'
        } else {
          // Sort by transaction date (most recent first)
          transactions.sort((a, b) => {
            const dateA = new Date(a.transaction_date || a.created_at || a.transactionDate || 0)
            const dateB = new Date(b.transaction_date || b.created_at || b.transactionDate || 0)
            return dateB - dateA
          })
          
          this.recentTransactions = transactions
          this.lastTransactionUpdate = new Date().toLocaleTimeString()
          this.transactionsError = null
        }
      } catch (error) {
        this.transactionsError = error.message || error.response?.data?.error || 'Failed to load transactions'
        this.recentTransactions = []
      } finally {
        this.transactionsLoading = false
      }
    },
    
    toggleAutoRefresh() {
      this.autoRefreshEnabled = !this.autoRefreshEnabled
      if (this.autoRefreshEnabled) {
        this.startAutoRefresh()
      } else {
        this.stopAutoRefresh()
      }
    },
    
    startAutoRefresh() {
      this.stopAutoRefresh() // Clear any existing timer
      // Refresh every 10 seconds
      this.refreshTimer = setInterval(() => {
        this.loadRecentTransactions()
      }, 10000)
    },
    
    stopAutoRefresh() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
    },
    
    formatTransactionTime(dateString) {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now - date
        const diffMins = Math.floor(diffMs / 60000)
        
        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
        
        return date.toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: true 
        })
      } catch (error) {
        return 'Invalid date'
      }
    },
    
    formatTransactionId(id) {
      if (!id) return 'N/A'
      const idStr = String(id)
      return idStr.length > 12 ? idStr.substring(0, 12) + '...' : idStr
    },
    
    getItemCount(transaction) {
      if (transaction.items && Array.isArray(transaction.items)) {
        return transaction.items.length
      }
      if (transaction.items_sold) {
        return transaction.items_sold
      }
      if (transaction.quantity) {
        return transaction.quantity
      }
      return 0
    },
    
    formatPaymentMethod(method) {
      if (!method) return 'Cash'
      return method.charAt(0).toUpperCase() + method.slice(1).toLowerCase()
    },
    
    getPaymentMethodClass(method) {
      const methodLower = (method || 'cash').toLowerCase()
      if (methodLower.includes('card') || methodLower.includes('credit') || methodLower.includes('debit')) {
        return 'payment-card'
      }
      if (methodLower.includes('cash')) {
        return 'payment-cash'
      }
      if (methodLower.includes('online') || methodLower.includes('digital')) {
        return 'payment-online'
      }
      return 'payment-other'
    },
    
    getStatusText(status) {
      if (status === true || status === 'voided' || status === 'void') {
        return 'Voided'
      }
      if (status === 'completed' || status === 'complete') {
        return 'Completed'
      }
      if (status === 'pending') {
        return 'Pending'
      }
      return 'Active'
    },
    
    getStatusClass(status) {
      if (status === true || status === 'voided' || status === 'void') {
        return 'status-voided'
      }
      if (status === 'completed' || status === 'complete') {
        return 'status-completed'
      }
      if (status === 'pending') {
        return 'status-pending'
      }
      return 'status-active'
    },
    async loadProductsData() {
      try {
        // Use initializeProducts for cleaner initial data loading
        await this.initializeProducts()
      } catch (error) {
        // Error loading products data - fallback to fetchProducts if initializeProducts fails
        try {
          await this.fetchProducts()
        } catch (fallbackError) {
          // Fallback fetchProducts also failed
          // The error is already handled by the useProducts composable
          // and will be reflected in the productsError reactive variable
        }
      }
    },
    async loadSalesData() {
      try {
        // Calculate last month's date range for reference
        const now = new Date()
        const startOfLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
        const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0) // Last day of previous month
        
        // Format dates for API (YYYY-MM-DD format)
        const startDate = startOfLastMonth.toISOString().split('T')[0]
        const endDate = endOfLastMonth.toISOString().split('T')[0]
        
        
        // Load the last month's sales count
        await this.loadTotalSalesCount(startDate, endDate)
        const lastMonthCount = this.totalSalesCount
        
        // Load all-time count for comparison
        await this.loadTotalSalesCountAllTime()
        const allTimeCount = this.totalSalesCount
        
        // Use all-time count if last month shows 0, otherwise use last month
        if (lastMonthCount > 0) {
          this.totalSalesCount = lastMonthCount
          this.isShowingAllTimeSales = false
        } else {
          this.totalSalesCount = allTimeCount
          this.isShowingAllTimeSales = true
        }
        
        // Also load profit data with the same date range
        await this.loadTotalProfit(startDate, endDate)
        const lastMonthProfit = this.totalProfit

        // Load all-time profit for comparison
        await this.loadTotalProfitAllTime()
        const allTimeProfit = this.totalProfit
        
        // Use all-time profit if last month shows 0, otherwise use last month
        if (lastMonthProfit > 0) {
          // Restore the last month profit value
          this.totalProfit = lastMonthProfit
          this.isShowingAllTimeProfit = false
        } else {
          // Keep the all-time profit value (already set)
          this.isShowingAllTimeProfit = true
        }
        
        // Load current month's revenue (separate from the last month date range used for sales/profit)
        await this.loadCurrentMonthIncome()
        
        // Set the current month period for the subtitle
        const currentDate = new Date()
        const currentMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
        this.currentMonthPeriod = currentMonth.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long'
        })
        
        // Load top performing month
        await this.loadTopPerformingMonth()
        
        // Initialize top products date range (but don't load yet - wait for transactions)
        await this.initializeTopProductsDateRange()
        
      } catch (error) {
        // Error loading sales data
      }
    },
    
    async loadTopPerformingMonth() {
      this.topMonthLoading = true
      this.topMonthError = null
      
      try {
        // Get last 12 months of data
        const now = new Date()
        const startDate = new Date(now.getFullYear(), now.getMonth() - 11, 1) // 12 months ago
        const endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0) // End of current month
        
        // Format dates for API (YYYY-MM-DD format)
        const startDateStr = startDate.toISOString().split('T')[0]
        const endDateStr = endDate.toISOString().split('T')[0]
        
        const response = await salesAPIService.getSalesByPeriod({
          start_date: startDateStr,
          end_date: endDateStr,
          period: 'monthly'
        })
        
        // Handle different response formats
        let monthlyData = []
        if (response?.periods && Array.isArray(response.periods)) {
          monthlyData = response.periods
        } else if (response?.data && Array.isArray(response.data)) {
          monthlyData = response.data
        } else if (Array.isArray(response)) {
          monthlyData = response
        } else if (response?.monthly && Array.isArray(response.monthly)) {
          monthlyData = response.monthly
        }
        
        if (monthlyData.length === 0) {
          // Fallback: use current month as top month
          const currentDate = new Date()
          this.topPerformingMonth = {
            monthName: currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
            revenue: this.monthlyIncome || 0,
            month: currentDate.getMonth(),
            year: currentDate.getFullYear()
          }
        } else {
          // Find the month with highest revenue
          let topMonth = null
          let maxRevenue = 0
          
          monthlyData.forEach(month => {
            // Handle different data structures
            const revenue = parseFloat(month.total_sales || month.revenue || month.amount || month.total || 0)
            const monthKey = month.period || month.month || month._id || month.label
            
            if (revenue > maxRevenue) {
              maxRevenue = revenue
              
              // Parse month name from various formats
              let monthName = 'Unknown'
              if (monthKey) {
                if (typeof monthKey === 'string') {
                  // Try to parse month name from string like "2025-10" or "October 2025"
                  const parts = monthKey.split('-')
                  if (parts.length === 2) {
                    const year = parseInt(parts[0])
                    const monthNum = parseInt(parts[1])
                    const date = new Date(year, monthNum - 1, 1)
                    monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
                  } else {
                    monthName = monthKey
                  }
                } else if (monthKey.year && monthKey.month) {
                  const date = new Date(monthKey.year, monthKey.month - 1, 1)
                  monthName = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
                }
              }
              
              topMonth = {
                monthName: monthName,
                revenue: revenue,
                month: monthKey?.month || new Date().getMonth(),
                year: monthKey?.year || new Date().getFullYear(),
                raw: month
              }
            }
          })
          
          if (topMonth) {
            this.topPerformingMonth = topMonth
          } else {
            // Fallback to current month
            const currentDate = new Date()
            this.topPerformingMonth = {
              monthName: currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
              revenue: this.monthlyIncome || 0,
              month: currentDate.getMonth(),
              year: currentDate.getFullYear()
            }
          }
        }
        
        this.topMonthError = null
      } catch (error) {
        this.topMonthError = error.message || 'Failed to load top month data'
        // Fallback to current month
        const currentDate = new Date()
        this.topPerformingMonth = {
          monthName: currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
          revenue: this.monthlyIncome || 0,
          month: currentDate.getMonth(),
          year: currentDate.getFullYear()
        }
      } finally {
        this.topMonthLoading = false
      }
    },
    
    // ========== TOP PRODUCTS METHODS ==========
    initializeTopProductsDateRange() {
      // Set default to last 90 days (wider range to catch more data)
      const endDate = new Date()
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - 90)
      
      // Format as YYYY-MM-DD for date inputs
      this.topProductsEndDate = endDate.toISOString().split('T')[0]
      this.topProductsStartDate = startDate.toISOString().split('T')[0]
    },
    
    resetTopProductsDateRange() {
      this.initializeTopProductsDateRange()
      this.loadTopProducts()
    },
    
    async loadTopProducts() {
      this.topProductsLoading = true
      this.topProductsError = null
      
      try {
        if (!this.topProductsStartDate || !this.topProductsEndDate) {
          this.initializeTopProductsDateRange()
        }
        
        console.log('[Top Products] Loading...', {
          start_date: this.topProductsStartDate,
          end_date: this.topProductsEndDate
        })
        
        // Try with date range first
        let response = await salesAPIService.getTopChartItems({
          limit: 10,
          start_date: this.topProductsStartDate,
          end_date: this.topProductsEndDate,
          frequency: 'monthly'
        })
        
        console.log('[Top Products] API Response:', response)
        
        // Handle different response formats
        let products = []
        if (response?.data && Array.isArray(response.data)) {
          products = response.data
        } else if (response?.items && Array.isArray(response.items)) {
          products = response.items
        } else if (Array.isArray(response)) {
          products = response
        } else if (response?.success && Array.isArray(response.data)) {
          products = response.data
        }
        
        // If no products found with date filter, try multiple fallback strategies
        if (products.length === 0) {
          console.log('[Top Products] No products with date filter, trying fallbacks...')
          
          // Strategy 1: Try the simpler endpoint without date filtering
          try {
            const fallbackResponse = await salesAPIService.getTopItems({ limit: 10 })
            console.log('[Top Products] Fallback API Response (all-time):', fallbackResponse)
            
            let fallbackProducts = []
            if (fallbackResponse?.success && Array.isArray(fallbackResponse.data)) {
              fallbackProducts = fallbackResponse.data
            } else if (fallbackResponse?.data && Array.isArray(fallbackResponse.data)) {
              fallbackProducts = fallbackResponse.data
            } else if (fallbackResponse?.items && Array.isArray(fallbackResponse.items)) {
              fallbackProducts = fallbackResponse.items
            } else if (Array.isArray(fallbackResponse)) {
              fallbackProducts = fallbackResponse
            } else if (fallbackResponse && typeof fallbackResponse === 'object') {
              // Try to find any array in the response
              for (const key in fallbackResponse) {
                if (Array.isArray(fallbackResponse[key])) {
                  fallbackProducts = fallbackResponse[key]
                  break
                }
              }
            }
            
            if (fallbackProducts.length > 0) {
              products = fallbackProducts
              console.log('[Top Products] ✅ Found via all-time API:', products.length)
            }
          } catch (fallbackError) {
            console.warn('[Top Products] ⚠️ All-time API failed:', fallbackError.message)
          }
          
          // Strategy 2: Extract products from recent transactions if still no products
          if (products.length === 0) {
            console.log('[Top Products] Checking transactions for extraction...', {
              transactionsAvailable: this.recentTransactions.length,
              transactionsLoading: this.transactionsLoading
            })
            
            // If transactions are still loading, wait a bit or use what we have
            if (this.recentTransactions.length > 0) {
              console.log('[Top Products] Extracting from transactions...')
              try {
                const productMap = new Map()
                
                // Process each transaction
                this.recentTransactions.forEach(transaction => {
                  // Handle different transaction structures
                  const items = transaction.item_list || transaction.items || transaction.line_items || []
                  
                  if (items && items.length > 0) {
                    items.forEach(item => {
                      const itemName = item.item_name || item.name || item.product_name || 'Unknown'
                      const quantity = parseFloat(item.quantity || 0)
                      const unitPrice = parseFloat(item.unit_price || item.price || 0)
                      const totalAmount = quantity * unitPrice
                      
                      if (itemName && itemName !== 'Unknown' && quantity > 0) {
                        if (productMap.has(itemName)) {
                          const existing = productMap.get(itemName)
                          existing.quantity += quantity
                          existing.total_amount += totalAmount
                        } else {
                          productMap.set(itemName, {
                            item_name: itemName,
                            quantity: quantity,
                            total_amount: totalAmount,
                            unit_price: unitPrice
                          })
                        }
                      }
                    })
                  }
                })
                
                // Convert map to array and sort by total amount
                const extractedProducts = Array.from(productMap.values())
                  .sort((a, b) => b.total_amount - a.total_amount)
                  .slice(0, 10)
                
                if (extractedProducts.length > 0) {
                  products = extractedProducts
                  console.log('[Top Products] ✅ Extracted from transactions:', products.length)
                } else {
                  console.log('[Top Products] No products found in transaction items')
                }
              } catch (extractError) {
                console.warn('[Top Products] ⚠️ Transaction extraction failed:', extractError.message)
              }
            } else {
              console.log('[Top Products] No transactions available for extraction')
            }
          }
          
          if (products.length === 0) {
            console.warn('[Top Products] ⚠️ All strategies failed - 0 products')
          }
        }
        
        // Sort by total amount/revenue (descending)
        products.sort((a, b) => {
          const revenueA = parseFloat(a.total_amount || a.total_sales || a.revenue || 0)
          const revenueB = parseFloat(b.total_amount || b.total_sales || b.revenue || 0)
          return revenueB - revenueA
        })
        
        // Limit to top 10
        this.topProducts = products.slice(0, 10)
        this.topProductsError = null
        
        console.log('[Top Products] ✅ Loaded:', this.topProducts.length, 'products')
      } catch (error) {
        console.error('[Top Products] ❌ Error:', error.message)
        this.topProductsError = error.message || 'Failed to load top products'
        this.topProducts = []
      } finally {
        this.topProductsLoading = false
      }
    }
  },
  async mounted() {
    // Load products and sales data when component mounts
    await Promise.all([
      this.loadProductsData(),
      this.loadSalesData()
    ])
    
    // Load recent transactions first
    await this.loadRecentTransactions()
    
    // Load top products after transactions are loaded (so we can extract from them if needed)
    await this.loadTopProducts()
    
    // Start auto-refresh if enabled
    if (this.autoRefreshEnabled) {
      this.startAutoRefresh()
    }
  },
  
  beforeUnmount() {
    // Clean up auto-refresh timer
    this.stopAutoRefresh()
  }
}
</script>

<style scoped>
.dashboard {
  padding: 0;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: repeat(2, 140px); /* Fixed row height */
  gap: 1.5rem;
  margin-bottom: 2rem;
  width: 100%;
}

/* Total Profit card spans 2 rows - adjust height accordingly */
.kpi-grid .profit-card {
  grid-row: 1 / 3;
  grid-column: 1;
  height: calc(280px + 1.5rem); /* Two rows + gap */
}

/* Other cards positioning */
.kpi-grid .card-template:nth-child(2) { /* Total Products */
  grid-row: 1;
  grid-column: 2;
}

.kpi-grid .card-template:nth-child(3) { /* Monthly Income */
  grid-row: 1;
  grid-column: 3;
}

.kpi-grid .card-template:nth-child(4) { /* Top Performing Month */
  grid-row: 2;
  grid-column: 2;
}

.kpi-grid .card-template:nth-child(5) { /* Total Orders */
  grid-row: 2;
  grid-column: 3;
}

/* Bottom section with transactions and target sales side by side */
.bottom-section {
  display: grid;
  grid-template-columns: 2fr 1fr; /* Transactions takes 2/3, Target Sales takes 1/3 */
  gap: 1.5rem;
  width: 100%;
  align-items: stretch; /* Ensures both items have same height */
}

.transactions-container {
  width: 100%;
  height: 100%;
}

.transactions-container .card-template {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.top-products-container {
  width: 100%;
  height: 100%;
  display: flex;
}

.top-products-container .card-template {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ==========================================================================
   CUSTOM SIZE OVERRIDE FOR KPI CARDS
   TRANSACTIONS HEADER CONTROLS
   ========================================================================== */
.transactions-header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 1rem;
}

.refresh-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.transaction-count {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.card-header-with-change {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  width: 100%;
  margin-bottom: -8px; /* Reduce spacing */
}

.change-badge {
  padding: 0.25rem 0.5rem; /* Reduced from 0.375rem 0.75rem */
  border-radius: 6px; /* Reduced from 8px */
  font-size: 0.7rem; /* Reduced from 0.8rem */
  font-weight: 700;
  white-space: nowrap;
  border: 1px solid transparent;
  position: relative;
  z-index: 2;
}

.change-badge.positive {
  background-color: var(--success-light);
  color: var(--success-dark);
  border-color: var(--success);
}

.change-badge.negative {
  background-color: var(--error-light);
  color: var(--error-dark);
  border-color: var(--error);
}

.change-badge.neutral {
  background-color: var(--neutral-light);
  color: var(--neutral-dark);
  border-color: var(--neutral);
}

/* ==========================================================================
   PROGRESS SECTION STYLING
   ========================================================================== */
.progress-section {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.progress-bar {
  width: 100%;
  height: 12px;
  background-color: var(--surface-tertiary);
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  overflow: hidden;
  margin-bottom: 1rem;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  border-radius: 6px;
  transition: width 0.6s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-info {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.5rem;
}

.progress-percentage {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--primary);
}

/* ==========================================================================
   TRANSACTIONS TABLE STYLING
   ========================================================================== */
.transactions-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  margin-top: 1rem;
}

.transactions-table-container {
  overflow-y: auto;
  max-height: 270px;
  border-radius: 8px;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.transactions-table thead {
  position: sticky;
  top: 0;
  background-color: var(--surface-primary);
  z-index: 10;
}

.transactions-table th {
  padding: 0.75rem 0.5rem;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border-primary);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.transactions-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid var(--border-secondary);
  color: var(--text-primary);
}

.transaction-row {
  transition: background-color 0.2s ease;
}

.transaction-row:hover {
  background-color: var(--state-hover);
}

.time-cell {
  font-size: 0.8rem;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.id-cell {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.customer-cell {
  font-weight: 500;
}

.items-cell {
  text-align: center;
  color: var(--text-secondary);
}

.payment-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.payment-cash {
  background-color: #d1fae5;
  color: #065f46;
}

.payment-card {
  background-color: #dbeafe;
  color: #1e40af;
}

.payment-online {
  background-color: #fef3c7;
  color: #92400e;
}

.payment-other {
  background-color: #e5e7eb;
  color: #374151;
}

.amount-cell {
  font-weight: 700;
  color: var(--success);
  text-align: right;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-active {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-completed {
  background-color: #d1fae5;
  color: #065f46;
}

.status-pending {
  background-color: #fef3c7;
  color: #92400e;
}

.status-voided {
  background-color: #fee2e2;
  color: #991b1b;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
  color: var(--text-secondary);
}

.error-state {
  color: var(--error);
}

.kpi-grid .card-template .card-title {
  font-size: 0.85rem !important; /* Smaller title */
  margin-bottom: 0.75rem !important;
  line-height: 1.3 !important;
}

.kpi-grid .card-template .card-value {
  font-size: 1.5rem !important; /* Smaller value */
  margin-bottom: 0.5rem !important;
  line-height: 1.1 !important;
}

.kpi-grid .card-template .card-subtitle {
  font-size: 0.75rem !important; /* Smaller subtitle */
  line-height: 1.4 !important;
}

/* Profit card gets larger text since it has more space */
.profit-card .card-title {
  font-size: 1rem !important;
}

.profit-card .card-value {
  font-size: 2rem !important;
}

.profit-card .card-subtitle {
  font-size: 0.85rem !important;
}
/* ==========================================================================
   CARD DECORATIVE ELEMENTS
   Add subtle corner decorations similar to original KPI cards
   ========================================================================== */
.card-template {
  position: relative;
  overflow: hidden;
}

.card-template::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 50px; /* Reduced from 60px */
  height: 50px; /* Reduced from 60px */
  opacity: 0.08;
  border-radius: 0 0 0 50px; /* Adjusted radius */
  z-index: 1;
  pointer-events: none;
}

/* Color-specific decorations */
.card-template.border-primary::before {
  background: linear-gradient(135deg, var(--primary-light), var(--primary-light));
}

.card-template.border-success::before {
  background: linear-gradient(135deg, var(--success-light), var(--success-light));
}

.card-template.border-secondary::before {
  background: linear-gradient(135deg, var(--secondary-light), var(--secondary-light));
}

.card-template.border-info::before {
  background: linear-gradient(135deg, var(--info-light), var(--info-light));
}

.card-template.border-error::before {
  background: linear-gradient(135deg, var(--error-light), var(--error-light));
}

/* ==========================================================================
   RESPONSIVE DESIGN
   ========================================================================== */
@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: repeat(3, 140px); /* Fixed heights */
    gap: 1.25rem;
  }
  
  .kpi-grid .profit-card {
    grid-row: 1 / 3;
    grid-column: 1;
    height: calc(280px + 1.25rem); /* Adjusted for new gap */
  }
  
  .kpi-grid .card-template:nth-child(2) { /* Total Products */
    grid-row: 1;
    grid-column: 2;
  }
  
  .kpi-grid .card-template:nth-child(3) { /* Monthly Income */
    grid-row: 2;
    grid-column: 2;
  }
  
  .kpi-grid .card-template:nth-child(4) { /* Top Performing Month */
    grid-row: 3;
    grid-column: 1;
  }
  
  .kpi-grid .card-template:nth-child(5) { /* Total Orders */
    grid-row: 3;
    grid-column: 2;
  }
  
  .bottom-section {
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }
}

@media (max-width: 900px) {
  .kpi-grid {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(5, 160px); /* Fixed heights for mobile */
    gap: 1rem;
    min-height: auto;
  }
  
  .kpi-grid .profit-card,
  .kpi-grid .card-template:nth-child(2),
  .kpi-grid .card-template:nth-child(3),
  .kpi-grid .card-template:nth-child(4),
  .kpi-grid .card-template:nth-child(5) {
    grid-row: auto;
    grid-column: 1;
    height: 160px !important; /* Fixed height for all cards on mobile */
  }
  
  .bottom-section {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 0 0.5rem;
  }
  
  .kpi-grid {
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .date-range-picker {
    flex-direction: column;
    align-items: stretch;
  }
  
  .date-input-group {
    width: 100%;
  }
  
  .date-input {
    flex: 1;
    width: 100%;
  }
  
  .top-products-list {
    max-height: 300px;
  }
  
  .change-badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }
  
  /* Transactions table responsive adjustments */
  .transactions-table-container {
    max-height: 300px;
  }
  
  .transactions-table {
    font-size: 0.8rem;
  }
  
  .transactions-table th,
  .transactions-table td {
    padding: 0.5rem 0.25rem;
  }
  
  .transactions-header-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .card-header-with-change {
    justify-content: center;
    margin-bottom: 0.5rem;
  }
  
  .change-badge {
    font-size: 0.7rem;
  }
  
  .progress-bar {
    height: 10px;
  }
  
  .progress-percentage {
    font-size: 0.85rem;
  }
  
  /* Transactions mobile adjustments */
  .transactions-table {
    font-size: 0.75rem;
  }
  
  .transactions-table th,
  .transactions-table td {
    padding: 0.4rem 0.2rem;
  }
  
  .transactions-table-container {
    max-height: 250px;
  }
  
  .payment-badge,
  .status-badge {
    font-size: 0.7rem;
    padding: 0.2rem 0.4rem;
  }
}

/* ==========================================================================
   ENHANCED VISUAL EFFECTS
   ========================================================================== */
.card-template:hover {
  transform: translateY(-2px);
  transition: all 0.3s ease;
}

.card-template:hover::before {
  opacity: 0.12;
  transition: opacity 0.3s ease;
}

/* ==========================================================================
   TOP PRODUCTS STYLING
   ========================================================================== */
.date-range-picker {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background-color: var(--surface-secondary);
  border-radius: 8px;
}

.date-input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.date-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

.date-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  font-size: 0.875rem;
  background-color: var(--surface-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.date-input:hover {
  border-color: var(--primary);
}

.date-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.top-products-loading,
.top-products-error,
.top-products-empty {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--text-secondary);
}

.top-products-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 270px;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.top-product-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  background-color: var(--surface-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-secondary);
  transition: all 0.2s ease;
}

.top-product-item:hover {
  background-color: var(--state-hover);
  border-color: var(--primary);
  transform: translateX(4px);
}

.product-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border-radius: 6px;
  flex-shrink: 0;
}

.rank-number {
  font-size: 0.875rem;
  font-weight: 700;
  color: white;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.product-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
}

.product-stats {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.8rem;
}

.product-quantity {
  color: var(--text-secondary);
}

.product-revenue {
  font-weight: 600;
  color: var(--primary);
}
</style>