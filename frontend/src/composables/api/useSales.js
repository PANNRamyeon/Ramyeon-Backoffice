import { ref, computed } from 'vue'
import axios from 'axios'
import salesAPIService from '../../services/apiReports.js'
import apiProductsService from '../../services/apiProducts.js'

const _API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const _authHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
const _fetchSalesByItem = (startDate, endDate, includeVoided = false) =>
  axios.get(`${_API_BASE}/admin/reports/sales-by-item/`, {
    headers: _authHeaders(),
    params: { start_date: startDate, end_date: endDate, include_voided: includeVoided },
  }).then(r => r.data)

// Global state for sales data
const salesByItemRows = ref([])
const allSalesByItemRows = ref([])
const topItems = ref([])
const chartData = ref({
  labels: ['Loading...'],
  datasets: [{
    label: 'Sales Amount',
    data: [0],
    backgroundColor: ['#e5e7eb'],
    borderColor: ['#d1d5db'],
    borderWidth: 1
  }]
})

// Loading states
const loadingTopItems = ref(false)
const salesByItemLoading = ref(false)
const importing = ref(false)
const exporting = ref(false)

// Error states
const salesByItemError = ref(null)
const error = ref(null)

// Sales statistics state
const totalSalesCount = ref(0)
const totalProfit = ref(0)
const salesStatsLoading = ref(false)
const salesStatsError = ref(null)
const profitLoading = ref(false)
const profitError = ref(null)

// Monthly revenue state
const monthlyIncome = ref(0)
const monthlyIncomeLoading = ref(false)
const monthlyIncomeError = ref(null)

// Product cost cache for profit calculations
const productCostCache = ref(new Map())

// Pagination
const salesByItemPagination = ref({
  current_page: 1,
  page_size: 10,
  total_records: 0,
  total_pages: 0,
  has_next: false,
  has_prev: false
})

// Chart and analytics
const selectedFrequency = ref('monthly')

// Auto-refresh states
const autoRefreshEnabled = ref(true)
const autoRefreshInterval = ref(30000)
const baseRefreshInterval = ref(30000)
const autoRefreshTimer = ref(null)
const countdown = ref(30)
const countdownTimer = ref(null)

// Connection health tracking
const connectionLost = ref(false)
const consecutiveErrors = ref(0)
const lastSuccessfulLoad = ref(null)

// Smart refresh rate tracking
const recentActivity = ref([])

export function useSales() {
  // ================ COMPUTED PROPERTIES ================
  
  const showSalesByItemPagination = computed(() => {
    return salesByItemPagination.value.total_pages > 1
  })
  
  const getSalesByItemVisiblePages = computed(() => {
    const current = salesByItemPagination.value.current_page
    const total = salesByItemPagination.value.total_pages
    const delta = 2
    
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1)
    }
    
    let start = Math.max(1, current - delta)
    let end = Math.min(total, current + delta)
    
    if (current <= delta + 1) {
      end = Math.min(total, 2 * delta + 2)
    }
    if (current >= total - delta) {
      start = Math.max(1, total - 2 * delta - 1)
    }
    
    const pages = []
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    
    return pages
  })

  // ================ UTILITY METHODS ================
  
  /**
   * Format date for API (YYYY-MM-DD) using local timezone
   */
  const formatDateForAPI = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  /**
   * Validate that start date is before end date
   */
  const validateDateRange = (startDate, endDate) => {
    if (!startDate || !endDate) return true
    
    const start = new Date(startDate)
    const end = new Date(endDate)
    
    if (start > end) {
      console.error('Invalid date range: start date is after end date', { startDate, endDate })
      return false
    }
    
    return true
  }

  /**
   * Get user-friendly error messages
   */
  const getErrorMessage = (error) => {
    if (error.response?.status === 400) {
      return 'Invalid date range or parameters. Please try a different time period.'
    } else if (error.response?.status === 404) {
      return 'Sales data not found for the selected period.'
    } else if (error.response?.status === 500) {
      return 'Server error. Please try again later.'
    } else if (error.message?.includes('Network Error') || error.message?.includes('Failed to fetch')) {
      return 'Network connection failed. Please check your internet connection.'
    } else if (error.message?.includes('Invalid date range')) {
      return error.message
    } else {
      return error.message || 'Failed to load sales data. Please try again.'
    }
  }

  /**
   * Fetch and cache product cost prices for profit calculations
   */
  const fetchProductCostPrices = async (productIds) => {
    try {
      // Filter out product IDs we don't have cached
      const missingIds = productIds.filter(id => !productCostCache.value.has(id))
      
      if (missingIds.length === 0) {
        return
      }
      
      // Fetch all products to get their cost prices
      const response = await apiProductsService.getAllProducts({ limit: 10000 })
      const products = response.data || []
      
      // Cache all product cost prices for future use
      let cachedCount = 0
      products.forEach(product => {
        if (product._id && product.cost_price !== undefined) {
          productCostCache.value.set(product._id, parseFloat(product.cost_price) || 0)
          cachedCount++
        }
      })
      
    } catch (error) {
      console.warn('Failed to fetch product cost prices:', error)
    }
  }

  /**
   * Get cached cost price for a product, or return 0 if not found
   */
  const getProductCostPrice = (productId) => {
    const costPrice = productCostCache.value.get(productId) || 0
    // Only provide debug info when cost price is missing and we're in a profit calculation context
    // Chart operations don't need cost prices, so we'll keep this quiet for chart-only operations
    return costPrice
  }

  /**
   * Format currency amount
   */
  const formatCurrency = (amount) => {
    let numericAmount = amount
    
    if (typeof amount === 'string') {
      numericAmount = parseFloat(amount)
    }
    
    if (typeof numericAmount !== 'number' || isNaN(numericAmount)) {
      numericAmount = 0
    }
    
    return `₱${numericAmount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  /**
   * Calculate date range based on frequency
   */
  const calculateDateRange = (frequency) => {
    const now = new Date()
    const end_date = formatDateForAPI(now)
    let start_date
    
    // Start from October of current year (if we're past October) or previous year
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() // 0-indexed (0 = January, 9 = October)
    
    switch (frequency) {
      case 'daily':
        // Last 30 days, but not before October
        const dailyDate = new Date(now)
        dailyDate.setDate(dailyDate.getDate() - 30)
        
        // If going back 30 days would be before October of current year, start from October
        const octoberDate = new Date(currentYear, 9, 1) // October 1st
        if (dailyDate < octoberDate && currentMonth >= 9) {
          start_date = formatDateForAPI(octoberDate)
        } else {
          start_date = formatDateForAPI(dailyDate)
        }
        break
      case 'weekly':
        // Start from October or last 12 weeks, whichever is more recent
        const weeklyDate = new Date(now)
        weeklyDate.setDate(weeklyDate.getDate() - (12 * 7))
        
        const octoberWeekly = new Date(currentYear, 9, 1) // October 1st
        if (weeklyDate < octoberWeekly && currentMonth >= 9) {
          start_date = formatDateForAPI(octoberWeekly)
        } else {
          start_date = formatDateForAPI(weeklyDate)
        }
        break
      case 'monthly':
        // Start from October of current year if we're past October, otherwise previous year's October
        const startYear = currentMonth >= 9 ? currentYear : currentYear - 1
        const monthlyStart = new Date(startYear, 9, 1) // October 1st
        start_date = formatDateForAPI(monthlyStart)
        break
      case 'yearly':
        // Last 3 years starting from October of earliest year
        const yearlyStart = new Date(currentYear - 2, 9, 1) // October of 3 years ago
        start_date = formatDateForAPI(yearlyStart)
        break
      default:
        // Default to October of current year or previous year
        const defaultYear = currentMonth >= 9 ? currentYear : currentYear - 1
        const defaultStart = new Date(defaultYear, 9, 1) // October 1st
        start_date = formatDateForAPI(defaultStart)
    }
    
    return { start_date, end_date }
  }

  /**
   * Generate colors for chart items
   */
  const generateChartColors = (count) => {
    const baseColors = [
      '#ef4444', '#3b82f6', '#eab308', '#22c55e', '#8b5cf6',
      '#f59e0b', '#10b981', '#6366f1', '#f97316', '#84cc16'
    ]
    
    const borderColors = [
      '#dc2626', '#2563eb', '#ca8a04', '#16a34a', '#7c3aed',
      '#d97706', '#059669', '#4f46e5', '#ea580c', '#65a30d'
    ]
    
    const background = []
    const border = []
    
    for (let i = 0; i < count; i++) {
      background.push(baseColors[i % baseColors.length])
      border.push(borderColors[i % borderColors.length])
    }
    
    return { background, border }
  }

  /**
   * Set default chart data when no API data available
   */
  const setDefaultChartData = () => {
    chartData.value = {
      labels: ['No Data Available'],
      datasets: [{
        label: 'Sales Amount',
        data: [0],
        backgroundColor: ['#e5e7eb'],
        borderColor: ['#d1d5db'],
        borderWidth: 1
      }]
    }
  }

  // ================ DATA LOADING METHODS ================
  
  /**
   * Load top items for the list display only
   */
  const getTopItems = async () => {
    try {
      loadingTopItems.value = true
      
      const dateRange = calculateDateRange(selectedFrequency.value)
      
      const items = await _fetchSalesByItem(dateRange.start_date, dateRange.end_date)

      if (items && items.length > 0) {
        // Sort by total_sales and take top 5
        const sortedItems = items
          .sort((a, b) => (b.total_sales || 0) - (a.total_sales || 0))
          .slice(0, 5)

        topItems.value = sortedItems.map((item) => ({
          name: item.product_name || 'Unknown Product',
          price: formatCurrency(item.total_sales || 0)
        }))
      } else {
        topItems.value = [
          { name: 'No data available', price: '₱0.00' }
        ]
      }
      
      connectionLost.value = false
      consecutiveErrors.value = 0
      lastSuccessfulLoad.value = Date.now()
      error.value = null
      
    } catch (err) {
      console.error("❌ Error loading top items:", err)
      
      consecutiveErrors.value++
      error.value = `Failed to load top items: ${err.message}`

      if (consecutiveErrors.value >= 3) {
        connectionLost.value = true
      }

      topItems.value = [{ name: 'Error loading data', price: '₱0.00' }]
    } finally {
      loadingTopItems.value = false
    }
  }

  /**
   * Load chart data with date filtering
   */
  const getTopChartItems = async () => {
    try {
      const dateRange = calculateDateRange(selectedFrequency.value)
      
      const items = await _fetchSalesByItem(dateRange.start_date, dateRange.end_date)

      if (items && items.length > 0) {
        // Sort by total_sales and take top 10 for chart
        const sortedItems = items
          .sort((a, b) => (b.total_sales || 0) - (a.total_sales || 0))
          .slice(0, 10)

        // Map to chart format
        const chartItems = sortedItems.map(item => ({
          item_name: item.product_name || 'Unknown Product',
          total_amount: item.total_sales || 0
        }))

        updateChartData(chartItems)

        connectionLost.value = false
        consecutiveErrors.value = 0
        lastSuccessfulLoad.value = Date.now()
        error.value = null

      } else {
        setDefaultChartData()
      }
      
    } catch (err) {
      console.error("❌ Error in getTopChartItems:", err)
      
      consecutiveErrors.value++
      error.value = `Failed to load chart data: ${err.message}`

      if (consecutiveErrors.value >= 3) {
        connectionLost.value = true
      }

      setDefaultChartData()
    }
  }

  /**
   * Load sales by item table data with improved date filtering and error handling
   */
  const loadSalesByItemTable = async () => {
    try {
      salesByItemLoading.value = true
      salesByItemError.value = null
      
      const dateRange = calculateDateRange(selectedFrequency.value)
      
      // Validate date range
      if (!validateDateRange(dateRange.start_date, dateRange.end_date)) {
        salesByItemError.value = 'Invalid date range: start date cannot be after end date'
        allSalesByItemRows.value = []
        salesByItemRows.value = []
        return
      }
      
      const data = await _fetchSalesByItem(dateRange.start_date, dateRange.end_date, false)

      // Store all data and update pagination
      allSalesByItemRows.value = data
        .filter(item => item && typeof item === 'object') // Filter out invalid items
        .sort((a, b) => {
          const salesA = parseFloat(a.total_sales) || 0
          const salesB = parseFloat(b.total_sales) || 0
          return salesB - salesA // Descending order by total sales
        })
        .map(item => ({
          id: item.product_id || item.id || 'N/A',
          product: item.product_name || item.name || item.product || 'Unknown Product',
          category: item.category_name || item.category || 'Uncategorized',
          stock: parseInt(item.stock) || 0,
          items_sold: parseInt(item.items_sold) || 0,
          total_sales: parseFloat(item.total_sales) || 0,
          selling_price: parseFloat(item.selling_price) || 0,
          unit: item.unit || 'unit',
          sku: item.sku || 'N/A',
          is_taxable: Boolean(item.is_taxable)
        }))

      // Reset to first page and update displayed data
      salesByItemPagination.value.current_page = 1
      updateSalesByItemPageData()

      // Update connection health on success
      connectionLost.value = false
      consecutiveErrors.value = 0
      lastSuccessfulLoad.value = Date.now()
      error.value = null

    } catch (err) {
      console.error('❌ loadSalesByItemTable error:', err)
      
      // Update connection health on error
      consecutiveErrors.value++
      salesByItemError.value = getErrorMessage(err)

      if (consecutiveErrors.value >= 3) {
        connectionLost.value = true
      }

      // Set empty data state
      allSalesByItemRows.value = []
      salesByItemRows.value = []
      salesByItemPagination.value.current_page = 1
      updateSalesByItemPageData()
      
    } finally {
      salesByItemLoading.value = false
    }
  }

  /**
   * Load total sales count with date filtering
   * This counts the total number of items sold, not just transactions/invoices
   */
  const loadTotalSalesCount = async (startDate = null, endDate = null) => {
    try {
      salesStatsLoading.value = true
      salesStatsError.value = null
      
      // Calculate date range if not provided
      let dateRange = null
      if (startDate && endDate) {
        dateRange = { start_date: startDate, end_date: endDate }
      }
      
      try {
        const data = await _fetchSalesByItem(dateRange?.start_date || null, dateRange?.end_date || null, false)
        totalSalesCount.value = data.reduce((sum, item) => sum + (parseInt(item.items_sold) || 0), 0)
        return totalSalesCount.value
      } catch (salesByItemError) {
        console.warn('Failed to get sales count from sales-by-item API:', salesByItemError)
      }

      totalSalesCount.value = 0
      return totalSalesCount.value
      
    } catch (err) {
      console.error('❌ loadTotalSalesCount error:', err)
      salesStatsError.value = getErrorMessage(err)
      totalSalesCount.value = 0
      throw err
    } finally {
      salesStatsLoading.value = false
    }
  }

  /**
   * Load total sales count without date filtering (all time)
   * This counts the total number of items sold across all time, not just transactions/invoices
   */
  const loadTotalSalesCountAllTime = async () => {
    try {
      salesStatsLoading.value = true
      salesStatsError.value = null
      
      try {
        const data = await _fetchSalesByItem(null, null, false)
        totalSalesCount.value = data.reduce((sum, item) => sum + (parseInt(item.items_sold) || 0), 0)
        return totalSalesCount.value
      } catch (salesByItemError) {
        console.warn('Failed to get sales count from sales-by-item API:', salesByItemError)
      }

      totalSalesCount.value = 0
      return totalSalesCount.value
      
    } catch (err) {
      console.error('❌ loadTotalSalesCountAllTime error:', err)
      salesStatsError.value = getErrorMessage(err)
      totalSalesCount.value = 0
      throw err
    } finally {
      salesStatsLoading.value = false
    }
  }

  /**
   * Load total profit with date filtering
   * This calculates actual profit (Revenue - Costs) from sales data, not just total_sales
   */
  const loadTotalProfit = async (startDate = null, endDate = null) => {
    try {
      profitLoading.value = true
      profitError.value = null
      
      // Calculate date range if not provided
      let dateRange = null
      if (startDate && endDate) {
        dateRange = { start_date: startDate, end_date: endDate }
      }
      
      try {
        const data = await _fetchSalesByItem(dateRange?.start_date || null, dateRange?.end_date || null, false)
        const productIds = data.map(item => item.product_id).filter(Boolean)
        if (productIds.length > 0) await fetchProductCostPrices(productIds)

        let calculatedProfit = 0
        data.forEach(item => {
          const revenue = parseFloat(item.total_sales) || 0
          const itemsSold = parseInt(item.items_sold) || 0
          const costPrice = parseFloat(item.cost_price) || getProductCostPrice(item.product_id)
          if (costPrice > 0) calculatedProfit += revenue - costPrice * itemsSold
        })
        totalProfit.value = calculatedProfit
        return totalProfit.value
      } catch (salesByItemError) {
        console.warn('Failed to get profit from sales-by-item API:', salesByItemError)
      }

      totalProfit.value = 0
      return totalProfit.value
      
    } catch (err) {
      console.error('❌ loadTotalProfit error:', err)
      profitError.value = getErrorMessage(err)
      totalProfit.value = 0
      throw err
    } finally {
      profitLoading.value = false
    }
  }

  /**
   * Load total profit without date filtering (all time)
   * This calculates actual profit (Revenue - Costs) from all sales data, not just total_sales
   */
  const loadTotalProfitAllTime = async () => {
    try {
      profitLoading.value = true
      profitError.value = null
      
      try {
        const data = await _fetchSalesByItem(null, null, false)
        const productIds = data.map(item => item.product_id).filter(Boolean)
        if (productIds.length > 0) await fetchProductCostPrices(productIds)

        let calculatedProfit = 0
        data.forEach(item => {
          const revenue = parseFloat(item.total_sales) || 0
          const itemsSold = parseInt(item.items_sold) || 0
          const costPrice = parseFloat(item.cost_price) || getProductCostPrice(item.product_id)
          if (costPrice > 0) calculatedProfit += revenue - costPrice * itemsSold
        })
        totalProfit.value = calculatedProfit
        return totalProfit.value
      } catch (salesByItemError) {
        console.warn('Failed to get profit from sales-by-item API:', salesByItemError)
      }

      totalProfit.value = 0
      return totalProfit.value
      
    } catch (err) {
      console.error('❌ loadTotalProfitAllTime error:', err)
      profitError.value = getErrorMessage(err)
      totalProfit.value = 0
      throw err
    } finally {
      profitLoading.value = false
    }
  }

  /**
   * Load monthly revenue with date filtering
   * This calculates total revenue from sales data for a specific month
   */
  const loadMonthlyIncome = async (startDate = null, endDate = null) => {
    try {
      monthlyIncomeLoading.value = true
      monthlyIncomeError.value = null
      
      // Calculate date range if not provided
      let dateRange = null
      if (startDate && endDate) {
        dateRange = { start_date: startDate, end_date: endDate }
      }
      
      try {
        const data = await _fetchSalesByItem(dateRange?.start_date || null, dateRange?.end_date || null, false)
        monthlyIncome.value = data.reduce((sum, item) => sum + (parseFloat(item.total_sales) || 0), 0)
        return monthlyIncome.value
      } catch (salesByItemError) {
        console.warn('Failed to get revenue from sales-by-item API:', salesByItemError)
      }

      monthlyIncome.value = 0
      return monthlyIncome.value
      
    } catch (err) {
      console.error('❌ loadMonthlyIncome error:', err)
      monthlyIncomeError.value = getErrorMessage(err)
      monthlyIncome.value = 0
      throw err
    } finally {
      monthlyIncomeLoading.value = false
    }
  }

  /**
   * Load current month's revenue (without date filtering)
   */
  const loadCurrentMonthIncome = async () => {
    try {
      monthlyIncomeLoading.value = true
      monthlyIncomeError.value = null
      
      // Calculate current month's date range
      const now = new Date()
      const startOfCurrentMonth = new Date(now.getFullYear(), now.getMonth(), 1)
      const endOfCurrentMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0) // Last day of current month
      
      const startDate = startOfCurrentMonth.toISOString().split('T')[0]
      const endDate = endOfCurrentMonth.toISOString().split('T')[0]
      
      return await loadMonthlyIncome(startDate, endDate)
      
    } catch (err) {
      console.error('❌ loadCurrentMonthIncome error:', err)
      monthlyIncomeError.value = getErrorMessage(err)
      monthlyIncome.value = 0
      throw err
    } finally {
      monthlyIncomeLoading.value = false
    }
  }

  // ================ PAGINATION METHODS ================
  
  /**
   * Update sales by item pagination data
   */
  const updateSalesByItemPageData = () => {
    const startIndex = (salesByItemPagination.value.current_page - 1) * salesByItemPagination.value.page_size
    const endIndex = startIndex + salesByItemPagination.value.page_size
    
    salesByItemRows.value = allSalesByItemRows.value.slice(startIndex, endIndex)
    
    // Update pagination info
    salesByItemPagination.value.total_records = allSalesByItemRows.value.length
    salesByItemPagination.value.total_pages = Math.ceil(allSalesByItemRows.value.length / salesByItemPagination.value.page_size)
    salesByItemPagination.value.has_prev = salesByItemPagination.value.current_page > 1
    salesByItemPagination.value.has_next = salesByItemPagination.value.current_page < salesByItemPagination.value.total_pages
  }
  
  /**
   * Go to specific page for sales by item
   */
  const goToSalesByItemPage = (page) => {
    if (page >= 1 && page <= salesByItemPagination.value.total_pages) {
      salesByItemPagination.value.current_page = page
      updateSalesByItemPageData()
    }
  }

  /**
   * Change page size for sales by item
   */
  const changeSalesByItemPageSize = (newPageSize) => {
    salesByItemPagination.value.page_size = newPageSize
    salesByItemPagination.value.current_page = 1
    updateSalesByItemPageData()
  }

  // ================ CHART METHODS ================
  
  /**
   * Update chart data with API response
   */
  const updateChartData = (items) => {
    const colors = generateChartColors(items.length)
    
    chartData.value = {
      labels: items.map(item => item.item_name || 'Unknown Item'),
      datasets: [{
        label: `Sales Amount (${selectedFrequency.value})`,
        data: items.map(item => item.total_amount || 0),
        backgroundColor: colors.background,
        borderColor: colors.border,
        borderWidth: 1
      }]
    }
  }

  /**
   * Handle frequency change
   */
  const onFrequencyChange = async () => {
    // Refresh all data with new time frame
    await Promise.all([
      getTopItems(),
      getTopChartItems(),
      loadSalesByItemTable()
    ])
  }

  // ================ AUTO REFRESH METHODS ================
  
  const toggleAutoRefresh = () => {
    if (autoRefreshEnabled.value) {
      autoRefreshEnabled.value = false
      stopAutoRefresh()
    } else {
      autoRefreshEnabled.value = true
      startAutoRefresh()
    }
  }
  
  const startAutoRefresh = () => {
    stopAutoRefresh() // Clear any existing timers
    
    // Start countdown
    countdown.value = autoRefreshInterval.value / 1000
    countdownTimer.value = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        countdown.value = autoRefreshInterval.value / 1000
      }
    }, 1000)
    
    // Start auto-refresh timer
    autoRefreshTimer.value = setInterval(() => {
      refreshData()
    }, autoRefreshInterval.value)
  }

  const stopAutoRefresh = () => {
    if (autoRefreshTimer.value) {
      clearInterval(autoRefreshTimer.value)
      autoRefreshTimer.value = null
    }

    if (countdownTimer.value) {
      clearInterval(countdownTimer.value)
      countdownTimer.value = null
    }
  }

  // Emergency reconnect method
  const emergencyReconnect = async () => {
    consecutiveErrors.value = 0
    connectionLost.value = false
    error.value = null
    await refreshData()

    if (!autoRefreshEnabled.value) {
      autoRefreshEnabled.value = true
      startAutoRefresh()
    }
  }

  // ================ CONNECTION STATUS METHODS ================
  
  const getConnectionStatus = () => {
    if (connectionLost.value) return 'connection-lost'
    if (consecutiveErrors.value > 0) return 'connection-unstable'
    if (lastSuccessfulLoad.value && (Date.now() - lastSuccessfulLoad.value < 60000)) return 'connection-good'
    return 'connection-unknown'
  }

  const getConnectionIcon = () => {
    switch (getConnectionStatus()) {
      case 'connection-good': return 'bi bi-wifi text-success'
      case 'connection-unstable': return 'bi bi-wifi-1 text-warning'
      case 'connection-lost': return 'bi bi-wifi-off text-danger'
      default: return 'bi bi-wifi text-muted'
    }
  }

  const getConnectionText = () => {
    switch (getConnectionStatus()) {
      case 'connection-good': return 'Connected'
      case 'connection-unstable': return 'Unstable'
      case 'connection-lost': return 'Connection Lost'
      default: return 'Connecting...'
    }
  }

  // ================ REFRESH METHODS ================
  
  /**
   * Refresh all data
   */
  const refreshData = async () => {
    try {
      error.value = null

      await Promise.all([
        getTopItems(),
        getTopChartItems(),
        loadSalesByItemTable()
      ])

      // Connection health tracking - SUCCESS
      connectionLost.value = false
      consecutiveErrors.value = 0
      lastSuccessfulLoad.value = Date.now()

    } catch (err) {
      console.error('Error refreshing data:', err)
      consecutiveErrors.value++
      error.value = `Failed to refresh data: ${err.message}`

      if (consecutiveErrors.value >= 3) {
        connectionLost.value = true
      }
    }
  }

  // ================ EXPORTS ================
  
  return {
    // State
    salesByItemRows,
    allSalesByItemRows,
    topItems,
    chartData,
    selectedFrequency,
    
    // Loading states
    loadingTopItems,
    salesByItemLoading,
    importing,
    exporting,
    salesStatsLoading,
    
    // Error states
    salesByItemError,
    error,
    salesStatsError,
    
    // Sales statistics state
    totalSalesCount,
    totalProfit,
    profitLoading,
    profitError,
    
    // Monthly revenue state
    monthlyIncome,
    monthlyIncomeLoading,
    monthlyIncomeError,
    
    // Product cost cache
    productCostCache,
    
    // Pagination
    salesByItemPagination,
    
    // Auto-refresh
    autoRefreshEnabled,
    autoRefreshInterval,
    baseRefreshInterval,
    autoRefreshTimer,
    countdown,
    countdownTimer,
    
    // Connection health
    connectionLost,
    consecutiveErrors,
    lastSuccessfulLoad,
    recentActivity,
    
    // Computed
    showSalesByItemPagination,
    getSalesByItemVisiblePages,
    
    // Methods - Data Loading
    getTopItems,
    getTopChartItems,
    loadSalesByItemTable,
    loadTotalSalesCount,
    loadTotalSalesCountAllTime,
    loadTotalProfit,
    loadTotalProfitAllTime,
    loadMonthlyIncome,
    loadCurrentMonthIncome,
    
    // Methods - Utilities
    formatDateForAPI,
    validateDateRange,
    getErrorMessage,
    fetchProductCostPrices,
    getProductCostPrice,
    formatCurrency,
    calculateDateRange,
    generateChartColors,
    setDefaultChartData,
    
    // Methods - Pagination
    updateSalesByItemPageData,
    goToSalesByItemPage,
    changeSalesByItemPageSize,
    
    // Methods - Chart
    updateChartData,
    onFrequencyChange,
    
    // Methods - Auto Refresh
    toggleAutoRefresh,
    startAutoRefresh,
    stopAutoRefresh,
    emergencyReconnect,
    
    // Methods - Connection Status
    getConnectionStatus,
    getConnectionIcon,
    getConnectionText,
    
    // Methods - Refresh
    refreshData
  }
}
