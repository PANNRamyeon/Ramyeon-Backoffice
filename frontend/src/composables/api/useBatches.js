import { ref, reactive, computed, watch } from 'vue'
import batchService from '../../services/apiBatches.js'

export function useBatches() {
  // State
  const batches = ref([])
  const currentBatch = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const filters = reactive({
    productId: null,
    status: null,
    supplierId: null,
    expiringSoon: false,
    daysAhead: 30
  })

  // Statistics
  const statistics = ref({
    total_batches: 0,
    active_batches: 0,
    depleted_batches: 0,
    expired_batches: 0,
    expiring_within_7_days: 0,
    total_active_stock: 0
  })

  // Computed
  const activeBatches = computed(() => 
    batches.value.filter(batch => batch.status === 'active')
  )

  const expiredBatches = computed(() => 
    batches.value.filter(batch => batch.status === 'expired')
  )

  const depletedBatches = computed(() => 
    batches.value.filter(batch => batch.status === 'depleted')
  )

  const expiringBatches = computed(() => {
    const now = new Date()
    const warningDate = new Date(now.getTime() + (filters.daysAhead * 24 * 60 * 60 * 1000))
    
    return batches.value.filter(batch => {
      if (!batch.expiry_date || batch.status !== 'active') return false
      const expiryDate = new Date(batch.expiry_date)
      return expiryDate <= warningDate && expiryDate > now
    })
  })

  const hasActiveFilters = computed(() => 
    filters.productId || filters.status || filters.supplierId || filters.expiringSoon
  )

  // Methods
  async function fetchBatches() {
    loading.value = true
    error.value = null

    try {
      const filterParams = {}
      
      if (filters.productId) filterParams.product_id = filters.productId
      if (filters.status) filterParams.status = filters.status
      if (filters.supplierId) filterParams.supplier_id = filters.supplierId
      if (filters.expiringSoon) {
        filterParams.expiring_soon = true
        filterParams.days_ahead = filters.daysAhead
      }

      const response = await batchService.getAllBatches(filterParams)
      batches.value = response.data || []
    } catch (err) {
      error.value = err.message
      batches.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchBatchById(batchId) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.getBatchById(batchId)
      currentBatch.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      currentBatch.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchBatchesByProduct(productId, status = null) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.getBatchesByProduct(productId, status)
      const productBatches = response.data || []
      
      // ✅ FIX: Always update batches.value when called directly
      // This ensures ProductAdjustments component gets the data
      batches.value = productBatches
      
      // Also update filters to reflect current view
      filters.productId = productId
      if (status) {
        filters.status = status
      }
      
      return productBatches
    } catch (err) {
      error.value = err.message
      batches.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchBatchesBySupplier(supplierId, customFilters = {}) {
    loading.value = true
    error.value = null

    try {
      const filterParams = { ...customFilters }
      
      const response = await batchService.getBatchesBySupplier(supplierId, filterParams)
      const supplierBatches = response.data || []
      
      // Update batches.value when called directly
      batches.value = supplierBatches
      
      // Update filters to reflect current view
      filters.supplierId = supplierId
      
      return supplierBatches
    } catch (err) {
      error.value = err.message
      batches.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createBatch(batchData) {
    loading.value = true
    error.value = null

    try {
      // Validate data
      const validation = batchService.validateBatchData(batchData)
      if (!validation.isValid) {
        throw new Error(validation.errors.join(', '))
      }

      const response = await batchService.createBatch(batchData)
      const newBatch = response.data

      // Add to local state if it matches current filters
      if (!hasActiveFilters.value || matchesFilters(newBatch)) {
        batches.value.unshift(newBatch)
      }

      return newBatch
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBatchQuantity(batchId, quantityUsed, adjustmentType = 'correction', adjustedBy = null, notes = null) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.updateBatchQuantity(batchId, quantityUsed, adjustmentType, adjustedBy, notes)
      const updatedBatch = response.data

      // Update local state
      const index = batches.value.findIndex(batch => batch._id === batchId)
      if (index !== -1) {
        batches.value[index] = updatedBatch
      }

      if (currentBatch.value && currentBatch.value._id === batchId) {
        currentBatch.value = updatedBatch
      }

      return updatedBatch
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function processSaleFIFO(productId, quantitySold) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.processSaleFIFO(productId, quantitySold)
      
      // Refresh batches for this product to get updated quantities
      await fetchBatchesByProduct(productId)
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function processBatchAdjustment(productId, quantityUsed, adjustmentType = 'correction', adjustedBy = null, notes = null) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.processBatchAdjustment(productId, quantityUsed, adjustmentType, adjustedBy, notes)
      
      // Refresh batches for this product to get updated quantities
      await fetchBatchesByProduct(productId)
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStatistics() {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.getBatchStatistics()
      statistics.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkExpiryAlerts(daysAhead = 7) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.checkExpiryAlerts(daysAhead)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function markExpiredBatches() {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.markExpiredBatches()
      
      // Refresh batches to show updated statuses
      await fetchBatches()
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restockWithBatch(productId, restockData) {
    loading.value = true
    error.value = null

    try {
      const response = await batchService.restockWithBatch(productId, restockData)
      
      // Refresh batches to include the new batch
      await fetchBatches()
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Helper functions
  function matchesFilters(batch) {
    if (filters.productId && batch.product_id !== filters.productId) return false
    if (filters.status && batch.status !== filters.status) return false
    if (filters.supplierId && batch.supplier_id !== filters.supplierId) return false
    
    if (filters.expiringSoon) {
      const now = new Date()
      const warningDate = new Date(now.getTime() + (filters.daysAhead * 24 * 60 * 60 * 1000))
      const expiryDate = new Date(batch.expiry_date)
      
      if (!batch.expiry_date || expiryDate > warningDate || expiryDate <= now) {
        return false
      }
    }
    
    return true
  }

  function clearFilters() {
    filters.productId = null
    filters.status = null
    filters.supplierId = null
    filters.expiringSoon = false
    filters.daysAhead = 30
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentBatch() {
    currentBatch.value = null
  }

  function formatBatchForDisplay(batch) {
    return batchService.formatBatchForDisplay(batch)
  }

  function formatBatchesForDisplay(batchArray) {
    return batchService.formatBatchesForDisplay(batchArray)
  }

  // Watch for filter changes
  watch(() => ({ ...filters }), 
    () => {
      if (hasActiveFilters.value) {
        fetchBatches()
      }
    },
    { deep: true }
  )

  return {
    // State
    batches,
    currentBatch,
    loading,
    error,
    filters,
    statistics,

    // Computed
    activeBatches,
    expiredBatches,
    depletedBatches,
    expiringBatches,
    hasActiveFilters,

    // Methods
    fetchBatches,
    fetchBatchById,
    fetchBatchesByProduct,
    fetchBatchesBySupplier,
    createBatch,
    updateBatchQuantity,
    processSaleFIFO,
    fetchStatistics,
    checkExpiryAlerts,
    markExpiredBatches,
    restockWithBatch,
    processBatchAdjustment,

    // Helpers
    clearFilters,
    clearError,
    clearCurrentBatch,
    formatBatchForDisplay,
    formatBatchesForDisplay
  }
}