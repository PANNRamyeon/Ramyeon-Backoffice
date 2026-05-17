import { api } from './api.js'

class SupplierService {
  constructor() {
    this.baseEndpoint = '/suppliers'
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

    console.error('Supplier API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    })

    throw new Error(message)
  }

  // ================================================================
  // SUPPLIER CRUD
  // ================================================================

  async getSuppliers(filters = {}) {
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.type) params.type = filters.type
      if (filters.include_deleted) params.include_deleted = 'true'

      const response = await api.get(`${this.baseEndpoint}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getSupplierById(supplierId, options = {}) {
    try {
      const params = {}
      if (options.include_deleted) params.include_deleted = 'true'
      if (options.include_stats) params.include_stats = 'true'

      const response = await api.get(`${this.baseEndpoint}/${supplierId}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async createSupplier(supplierData) {
    try {
      const response = await api.post(`${this.baseEndpoint}/`, supplierData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async updateSupplier(supplierId, supplierData) {
    try {
      const response = await api.put(`${this.baseEndpoint}/${supplierId}/`, supplierData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async deleteSupplier(supplierId) {
    try {
      const response = await api.delete(`${this.baseEndpoint}/${supplierId}/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================================================================
  // SUPPLIER RESTORE & HARD DELETE (admin)
  // ================================================================

  async restoreSupplier(supplierId) {
    try {
      const response = await api.post(`${this.baseEndpoint}/${supplierId}/restore/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async hardDeleteSupplier(supplierId) {
    try {
      const response = await api.delete(`${this.baseEndpoint}/${supplierId}/hard-delete/`, {
        params: { confirm: 'yes' }
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getDeletedSuppliers() {
    try {
      const response = await api.get(`${this.baseEndpoint}/deleted/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================================================================
  // SUPPLIER BATCHES
  // ================================================================

  async getSupplierBatches(supplierId, filters = {}) {
    try {
      const params = {}
      if (filters.status) params.status = filters.status
      if (filters.product_id) params.product_id = filters.product_id

      const response = await api.get(`${this.baseEndpoint}/${supplierId}/batches/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async createBatchForSupplier(supplierId, batchData) {
    try {
      const response = await api.post(`${this.baseEndpoint}/${supplierId}/batches/create/`, batchData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================================================================
  // STATISTICS
  // ================================================================

  async getSupplierStatistics(supplierId) {
    try {
      const response = await api.get(`${this.baseEndpoint}/${supplierId}/`, {
        params: { include_stats: 'true' }
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }
}

const supplierService = new SupplierService()

export default supplierService
