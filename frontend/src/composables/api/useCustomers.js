// composables/api/useCustomers.js
import { ref, computed, readonly } from 'vue'
import customerApiService from '@/services/apiCustomers.js'

export function useCustomers() {
  // Reactive state
  const customers = ref([])
  const selectedCustomer = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const statistics = ref(null)
  
  // Pagination state
  const currentPage = ref(1)
  const totalCustomers = ref(0)
  const hasMore = ref(false)
  const filtersApplied = ref({})

  // Computed properties
  const customersCount = computed(() => customers.value.length)
  const hasCustomers = computed(() => customers.value.length > 0)
  const activeCustomers = computed(() => 
    customers.value.filter(c => c.status === 'active')
  )
  const inactiveCustomers = computed(() => 
    customers.value.filter(c => c.status !== 'active')
  )

  // Helper functions
  const clearError = () => {
    error.value = null
  }

  const resetPagination = () => {
    currentPage.value = 1
    hasMore.value = false
    totalCustomers.value = 0
  }

  // CRUD Operations

  /**
   * Fetch customers with pagination and filters
   * @param {Object} params - Query parameters
   * @param {boolean} append - Whether to append to existing customers or replace
   */
  const fetchCustomers = async (params = {}, append = false) => {
    isLoading.value = true
    error.value = null

    try {
      const queryParams = {
        page: currentPage.value,
        limit: 50,
        ...params
      }

      const response = await customerApiService.getCustomers(queryParams)
      
      if (append) {
        customers.value.push(...(response.customers || []))
      } else {
        customers.value = response.customers || []
      }

      // Update pagination info
      totalCustomers.value = response.total || 0
      hasMore.value = response.has_more || false
      filtersApplied.value = response.filters_applied || {}

      return response
    } catch (err) {
      error.value = err.message || 'Failed to fetch customers'
      if (!append) {
        customers.value = []
      }
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Load more customers (pagination)
   */
  const loadMoreCustomers = async (params = {}) => {
    if (!hasMore.value || isLoading.value) return

    currentPage.value += 1
    await fetchCustomers(params, true)
  }

  /**
   * Refresh customers list
   */
  const refreshCustomers = async (params = {}) => {
    resetPagination()
    await fetchCustomers(params)
  }

  /**
   * Get single customer by ID
   */
  const getCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.getCustomer(customerId)
      selectedCustomer.value = response.customer || response
      return selectedCustomer.value
    } catch (err) {
      error.value = err.message || 'Failed to fetch customer'
      selectedCustomer.value = null
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Create new customer
   */
  const createCustomer = async (customerData) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.createCustomer(customerData)
      const newCustomer = response.customer || response

      // Add to beginning of local array
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

  /**
   * Update existing customer
   */
  const updateCustomer = async (customerId, customerData) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.updateCustomer(customerId, customerData)
      const updatedCustomer = response.customer || response

      // Update in local array
      const index = customers.value.findIndex(c => 
        c._id === customerId || c.customer_id === customerId
      )
      if (index !== -1) {
        customers.value[index] = updatedCustomer
      }

      // Update selected customer if it's the same one
      if (selectedCustomer.value && 
          (selectedCustomer.value._id === customerId || 
           selectedCustomer.value.customer_id === customerId)) {
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

  /**
   * Delete customer (soft delete)
   */
  const deleteCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.deleteCustomer(customerId)

      // Remove from local array since it's now soft deleted
      customers.value = customers.value.filter(c => 
        c._id !== customerId && c.customer_id !== customerId
      )
      totalCustomers.value = Math.max(0, totalCustomers.value - 1)

      // Clear selected customer if it's the deleted one
      if (selectedCustomer.value && 
          (selectedCustomer.value._id === customerId || 
          selectedCustomer.value.customer_id === customerId)) {
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

  /**
   * Delete multiple customers
   */
  const deleteMultipleCustomers = async (customerIds) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.deleteMultipleCustomers(customerIds)

      // Remove from local array
      customers.value = customers.value.filter(c => 
        !customerIds.includes(c._id) && !customerIds.includes(c.customer_id)
      )
      totalCustomers.value = Math.max(0, totalCustomers.value - customerIds.length)

      return response
    } catch (err) {
      error.value = err.message || 'Failed to delete customers'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Restore deleted customer
   */
  const restoreCustomer = async (customerId) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.restoreCustomer(customerId)
      const restoredCustomer = response.customer || response

      // Add back to customers list if we're viewing all customers
      if (!filtersApplied.value.include_deleted) {
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

  /**
   * Get deleted customers
   */
  const getDeletedCustomers = async (params = {}) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.getDeletedCustomers(params)
      return response
    } catch (err) {
      error.value = err.message || 'Failed to fetch deleted customers'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Search and Filter Operations

  /**
   * Search customers
   */
  const searchCustomers = async (query) => {
    if (!query || !query.trim()) {
      return await refreshCustomers()
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.searchCustomers(query)
      customers.value = response.customers || response || []
      
      // Reset pagination for search results
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

  /**
   * Filter customers by status
   */
  const filterByStatus = async (status) => {
    const params = status ? { status } : {}
    resetPagination()
    await fetchCustomers(params)
  }

  // Loyalty Operations

  /**
   * Update customer loyalty points
   */
  const updateLoyaltyPoints = async (customerId, points, reason = 'Manual adjustment') => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.updateLoyaltyPoints(customerId, points, reason)
      const updatedCustomer = response.customer || response

      // Update in local arrays
      const index = customers.value.findIndex(c => 
        c._id === customerId || c.customer_id === customerId
      )
      if (index !== -1) {
        customers.value[index] = updatedCustomer
      }

      if (selectedCustomer.value && 
          (selectedCustomer.value._id === customerId || 
           selectedCustomer.value.customer_id === customerId)) {
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

  // Analytics Operations

  /**
   * Fetch customer statistics
   */
  const fetchStatistics = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await customerApiService.getCustomerStatistics()
      statistics.value = response.statistics || response
      return statistics.value
    } catch (err) {
      error.value = err.message || 'Failed to fetch statistics'
      statistics.value = null
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Export customers to CSV
   */
  const exportCustomers = async (includeDeleted = false) => {
    isLoading.value = true;
    error.value = null;

    try {
      const blob = await customerApiService.exportCustomers(includeDeleted);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'customers_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      error.value = err.message || 'Failed to export customers';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Import customers from CSV file
   */
  const importCustomers = async (file) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await customerApiService.importCustomers(file);
      await refreshCustomers(); // Refresh after import
      return response;
    } catch (err) {
      error.value = err.message || 'Failed to import customers';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  // Utility methods

  /**
   * Find customer by ID in local array
   */
  const findCustomerById = (customerId) => {
    return customers.value.find(c => 
      c._id === customerId || c.customer_id === customerId
    )
  }

  /**
   * Clear all data
   */
  const clearData = () => {
    customers.value = []
    selectedCustomer.value = null
    statistics.value = null
    error.value = null
    resetPagination()
  }

  return {
    exportCustomers,
    importCustomers,
    // State (readonly)
    customers: readonly(customers),
    selectedCustomer: readonly(selectedCustomer),
    isLoading: readonly(isLoading),
    error: readonly(error),
    statistics: readonly(statistics),
    
    // Pagination state (readonly)
    currentPage: readonly(currentPage),
    totalCustomers: readonly(totalCustomers),
    hasMore: readonly(hasMore),
    filtersApplied: readonly(filtersApplied),

    // Computed
    customersCount,
    hasCustomers,
    activeCustomers,
    inactiveCustomers,

    // CRUD methods
    fetchCustomers,
    loadMoreCustomers,
    refreshCustomers,
    getCustomer,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    deleteMultipleCustomers,
    restoreCustomer,
    getDeletedCustomers,

    // Search and filter methods
    searchCustomers,
    filterByStatus,

    // Loyalty methods
    updateLoyaltyPoints,

    // Analytics methods
    fetchStatistics,

    // Utility methods
    findCustomerById,
    clearData,
    clearError
  }
}