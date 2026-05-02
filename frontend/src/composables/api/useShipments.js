import { ref, computed } from 'vue'
import shipmentService from '@/services/apiShipments.js'

export function useShipments() {
  // ── State ────────────────────────────────────────────────────────────────────
  const shipments = ref([])
  const currentShipment = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // ── Computed ─────────────────────────────────────────────────────────────────
  const pendingShipments = computed(() =>
    shipments.value.filter(s => s.status === 'pending')
  )

  const receivedShipments = computed(() =>
    shipments.value.filter(s => s.status === 'received')
  )

  const inTransitShipments = computed(() =>
    shipments.value.filter(s => s.status === 'in_transit')
  )

  // ── Fetch All ─────────────────────────────────────────────────────────────────
  async function fetchShipments(options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.getShipments(options)
      shipments.value = response.data || []
      return shipments.value
    } catch (err) {
      error.value = err.message
      shipments.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Fetch by Supplier ─────────────────────────────────────────────────────────
  async function fetchShipmentsBySupplier(supplierId, limit = 100) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.getShipmentsBySupplier(supplierId, limit)
      shipments.value = response.data || []
      return shipments.value
    } catch (err) {
      error.value = err.message
      shipments.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Fetch by ID ───────────────────────────────────────────────────────────────
  async function fetchShipmentById(shipmentId, options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.getShipmentById(shipmentId, options)
      currentShipment.value = response.data
      return currentShipment.value
    } catch (err) {
      error.value = err.message
      currentShipment.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Fetch with Batches ────────────────────────────────────────────────────────
  async function fetchShipmentWithBatches(shipmentId, enrichWithProduct = false) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.getShipmentWithBatches(shipmentId, enrichWithProduct)
      currentShipment.value = response.data
      return currentShipment.value
    } catch (err) {
      error.value = err.message
      currentShipment.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Create ────────────────────────────────────────────────────────────────────
  async function createShipment(shipmentData) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.createShipment(shipmentData)
      const newShipment = response.data
      shipments.value.unshift(newShipment)
      return newShipment
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Update ────────────────────────────────────────────────────────────────────
  async function updateShipment(shipmentId, shipmentData) {
    loading.value = true
    error.value = null
    try {
      const response = await shipmentService.updateShipment(shipmentId, shipmentData)
      const updated = response.data

      const index = shipments.value.findIndex(s => s.shipment_id === shipmentId)
      if (index !== -1) shipments.value[index] = updated

      if (currentShipment.value?.shipment_id === shipmentId) {
        currentShipment.value = updated
      }

      return updated
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────────
  function clearError() {
    error.value = null
  }

  function clearCurrentShipment() {
    currentShipment.value = null
  }

  return {
    // State
    shipments,
    currentShipment,
    loading,
    error,

    // Computed
    pendingShipments,
    receivedShipments,
    inTransitShipments,

    // Methods
    fetchShipments,
    fetchShipmentsBySupplier,
    fetchShipmentById,
    fetchShipmentWithBatches,
    createShipment,
    updateShipment,

    // Helpers
    clearError,
    clearCurrentShipment
  }
}
