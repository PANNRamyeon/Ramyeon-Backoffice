// composables/api/useCustomers.js
import { ref, computed, readonly } from 'vue'
import customerApiService from '@/services/apiCustomers.js'

export function useCustomers() {
  // State
  const customers = ref([])
  const selectedCustomer = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const statistics = ref(null)

  // Cursor-based pagination (backend uses next_key, not page numbers)
  const nextKey = ref(null)
  const hasMore = ref(false)
  const totalCustomers = ref(0)

  // Computed
  const customersCount = computed(() => customers.value.length)
  const hasCustomers = computed(() => customers.value.length > 0)
  const activeCustomers = computed(() => customers.value.filter(c => c.status === 'active'))
  const inactiveCustomers = computed(() => customers.value.filter(c => c.status !== 'active'))

  const clearError = () => { error.value = null }

  const resetPagination = () => {
    nextKey.value = null
    hasMore.value = false
    totalCustomers.value = 0
  }

  // ==================== CRUD ====================

  const fetchCustomers = async (params = {}, append = false) => {
    isLoading.value = true
    error.value = null

    try {
      const queryParams = { limit: 50, ...params }

      // Pass cursor key for subsequent pages
      if (append && nextKey.value) {
        queryParams.start_key = nextKey.value
      }

      const response = await customerApiService.getCustomers(queryParams)
      const page = response.customers || []

      if (append) {
        customers.value.push(...page)
      } else {
        customers.value = page
      }

      // Backend returns next_key and has_more, no total count
      nextKey.value = response.next_key || null
      hasMore.value = response.has_more || false
      totalCustomers.value = append
        ? totalCustomers.value + page.length
        : page.length

      return response
    } catch (err) {
      error.value = err.message || 'Failed to fetch customers'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Append next page using the cursor from the last response
  const loadMoreCustomers = async (params = {}) => {
    if (!hasMore.value || isLoading.value) return
    await fetchCustomers(params, true)
  }

  const refreshCustomers = async (params = {}) => {
    resetPagination()
    await fetchCustomers(params)
  }

  const getCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.getCustomer(customerId)
      selectedCustomer.value = response
      return selectedCustomer.value
    } catch (err) {
      error.value = err.message || 'Failed to fetch customer'
      selectedCustomer.value = null
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const createCustomer = async (customerData) => {
    isLoading.value = true
    error.value = null

    try {
      const newCustomer = await customerApiService.createCustomer(customerData)
      customers.value.unshift(newCustomer)
      totalCustomers.value += 1
      return newCustomer
    } catch (err) {
      error.value = err.message || 'Failed to create customer'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const updateCustomer = async (customerId, customerData) => {
    isLoading.value = true
    error.value = null

    try {
      const updatedCustomer = await customerApiService.updateCustomer(customerId, customerData)

      const index = customers.value.findIndex(c => c.customer_id === customerId)
      if (index !== -1) customers.value[index] = updatedCustomer

      if (selectedCustomer.value?.customer_id === customerId) {
        selectedCustomer.value = updatedCustomer
      }

      return updatedCustomer
    } catch (err) {
      error.value = err.message || 'Failed to update customer'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const deleteCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.deleteCustomer(customerId)

      customers.value = customers.value.filter(c => c.customer_id !== customerId)
      totalCustomers.value = Math.max(0, totalCustomers.value - 1)

      if (selectedCustomer.value?.customer_id === customerId) {
        selectedCustomer.value = null
      }

      return response
    } catch (err) {
      error.value = err.message || 'Failed to delete customer'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Restore re-fetches the customer from the API since the backend only
  // returns {"message": "..."} — not the restored customer data
  const restoreCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      await customerApiService.restoreCustomer(customerId)
      const restoredCustomer = await customerApiService.getCustomer(customerId)

      const index = customers.value.findIndex(c => c.customer_id === customerId)
      if (index !== -1) {
        customers.value[index] = restoredCustomer
      } else {
        customers.value.unshift(restoredCustomer)
        totalCustomers.value += 1
      }

      return restoredCustomer
    } catch (err) {
      error.value = err.message || 'Failed to restore customer'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const hardDeleteCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.hardDeleteCustomer(customerId)

      customers.value = customers.value.filter(c => c.customer_id !== customerId)
      totalCustomers.value = Math.max(0, totalCustomers.value - 1)

      if (selectedCustomer.value?.customer_id === customerId) {
        selectedCustomer.value = null
      }

      return response
    } catch (err) {
      error.value = err.message || 'Failed to permanently delete customer'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== SEARCH & FILTER ====================

  // Backend search returns a plain array, not a paginated object
  const searchCustomers = async (query) => {
    if (!query?.trim()) return refreshCustomers()

    isLoading.value = true
    error.value = null

    try {
      const results = await customerApiService.searchCustomers(query)
      customers.value = Array.isArray(results) ? results : (results.customers || [])
      resetPagination()
      totalCustomers.value = customers.value.length
      return customers.value
    } catch (err) {
      error.value = err.message || 'Search failed'
      customers.value = []
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const filterByStatus = async (status) => {
    resetPagination()
    await fetchCustomers(status ? { status } : {})
  }

  // ==================== EXPORT / IMPORT ====================

  const exportCustomers = async (params = {}) => {
    error.value = null
    try {
      await customerApiService.exportCustomers(params)
    } catch (err) {
      error.value = err.message || 'Export failed'
      throw err
    }
  }

  const importCustomers = async (file) => {
    isLoading.value = true
    error.value = null
    try {
      return await customerApiService.importCustomers(file)
    } catch (err) {
      error.value = err.message || 'Import failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== LOYALTY ====================

  const updateLoyaltyPoints = async (customerId, points, reason = 'Manual adjustment') => {
    isLoading.value = true
    error.value = null

    try {
      const updatedCustomer = await customerApiService.updateLoyaltyPoints(customerId, points, reason)

      const index = customers.value.findIndex(c => c.customer_id === customerId)
      if (index !== -1) customers.value[index] = updatedCustomer

      if (selectedCustomer.value?.customer_id === customerId) {
        selectedCustomer.value = updatedCustomer
      }

      return updatedCustomer
    } catch (err) {
      error.value = err.message || 'Failed to update loyalty points'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== STATISTICS ====================

  const fetchStatistics = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.getCustomerStatistics()
      // Backend returns stats dict directly, no wrapping key
      statistics.value = response
      return statistics.value
    } catch (err) {
      error.value = err.message || 'Failed to fetch statistics'
      statistics.value = null
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== QR CODE ====================

  const generateQRToken = async (customerId, expiryHours = 720) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.generateQRToken(customerId, expiryHours)
      return response
    } catch (err) {
      error.value = err.message || 'Failed to generate QR token'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const verifyQRToken = async (token) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.verifyQRToken(token)
      return response
    } catch (err) {
      error.value = err.message || 'QR token verification failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // ==================== UTILITIES ====================

  const findCustomerById = (customerId) =>
    customers.value.find(c => c.customer_id === customerId)

  const clearData = () => {
    customers.value = []
    selectedCustomer.value = null
    statistics.value = null
    error.value = null
    resetPagination()
  }

  return {
    // State (readonly)
    customers: readonly(customers),
    selectedCustomer: readonly(selectedCustomer),
    isLoading: readonly(isLoading),
    error: readonly(error),
    statistics: readonly(statistics),
    nextKey: readonly(nextKey),
    hasMore: readonly(hasMore),
    totalCustomers: readonly(totalCustomers),

    // Computed
    customersCount,
    hasCustomers,
    activeCustomers,
    inactiveCustomers,

    // CRUD
    fetchCustomers,
    loadMoreCustomers,
    refreshCustomers,
    getCustomer,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    restoreCustomer,
    hardDeleteCustomer,

    // Export / Import
    exportCustomers,
    importCustomers,

    // Search & filter
    searchCustomers,
    filterByStatus,

    // Loyalty
    updateLoyaltyPoints,

    // Statistics
    fetchStatistics,

    // QR
    generateQRToken,
    verifyQRToken,

    // Utilities
    findCustomerById,
    clearData,
    clearError,
  }
}
