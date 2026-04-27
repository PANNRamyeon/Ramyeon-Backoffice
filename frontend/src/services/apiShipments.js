import { api } from './api.js'

class ShipmentService {
  constructor() {
    this.baseEndpoint = '/shipments'
  }

  handleResponse(response) {
    return response.data
  }

  handleError(error) {
    const message =
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'

    console.error('Shipment API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    })

    throw new Error(message)
  }

  // ================================================================
  // SHIPMENT CRUD
  // ================================================================

  /**
   * List all shipments.
   * @param {object} options - { supplier_id, limit, enrich_with_supplier_name }
   */
  async getShipments(options = {}) {
    try {
      const params = {}
      if (options.supplier_id) params.supplier_id = options.supplier_id
      if (options.limit) params.limit = options.limit
      if (options.enrich_with_supplier_name) params.enrich_with_supplier_name = 'true'

      const response = await api.get(`${this.baseEndpoint}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  /**
   * Create a shipment.
   * Required: supplier_id, batch_number
   * Optional: shipment_date, invoice_number, status, freight_cost, notes, received_by
   */
  async createShipment(shipmentData) {
    try {
      const response = await api.post(`${this.baseEndpoint}/`, shipmentData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  /**
   * Get a single shipment by ID.
   * @param {string} shipmentId
   * @param {object} options - { include_batches, enrich_with_product }
   */
  async getShipmentById(shipmentId, options = {}) {
    try {
      const params = {}
      if (options.include_batches) params.include_batches = 'true'
      if (options.enrich_with_product) params.enrich_with_product = 'true'

      const response = await api.get(`${this.baseEndpoint}/${shipmentId}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  /**
   * Update a shipment.
   * Allowed fields: status, invoice_number, freight_cost, notes, received_by, total_products
   */
  async updateShipment(shipmentId, shipmentData) {
    try {
      const response = await api.put(`${this.baseEndpoint}/${shipmentId}/`, shipmentData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================================================================
  // SHIPMENT WITH BATCHES
  // ================================================================

  /**
   * Get a shipment and all its associated batches.
   * @param {string} shipmentId
   * @param {boolean} enrichWithProduct - include full product data on each batch
   */
  async getShipmentWithBatches(shipmentId, enrichWithProduct = false) {
    try {
      const params = enrichWithProduct ? { enrich_with_product: 'true' } : {}
      const response = await api.get(`${this.baseEndpoint}/${shipmentId}/batches/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================================================================
  // BY SUPPLIER
  // ================================================================

  /**
   * List all shipments for a given supplier.
   * @param {string} supplierId
   * @param {number} limit
   */
  async getShipmentsBySupplier(supplierId, limit = 100) {
    try {
      const response = await api.get(`${this.baseEndpoint}/supplier/${supplierId}/`, {
        params: { limit }
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }
}

const shipmentService = new ShipmentService()

export default shipmentService
