import { api } from './api.js'
import axios from 'axios'

class ApiProductsService {
  constructor() {
    this.basePath = '/products'
  }

  // Helper method to handle responses consistently with your api.js pattern
  handleResponse(response) {
    return response.data
  }

  // Helper method to handle errors consistently with your api.js pattern
  handleError(error) {
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.response?.data?.detail ||
                   error.message || 
                   'An unexpected error occurred'
    
    console.error('Products API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message
    })
    
    throw new Error(message)
  }

  // ================ PRODUCT CRUD OPERATIONS ================

  async getAllProducts(filters = {}) {
    try {
      const params = {}
      if (filters.category_id) params.category_id = filters.category_id
      if (filters.subcategory_name) params.subcategory_name = filters.subcategory_name
      if (filters.status) params.status = filters.status
      if (filters.stock_level) params.stock_level = filters.stock_level
      if (filters.search) params.search = filters.search
      if (filters.include_deleted) params.include_deleted = filters.include_deleted

      const response = await api.get(`${this.basePath}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProductById(productId, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: 'true' } : {}
      const response = await api.get(`${this.basePath}/${productId}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProductBySku(sku, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: 'true' } : {}
      const response = await api.get(`${this.basePath}/sku/${sku}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async createProduct(productData) {
    try {
      const response = await api.post(`${this.basePath}/`, productData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async updateProduct(productId, productData, partial = false) {
    try {
      const method = partial ? 'patch' : 'put'
      const response = await api[method](`${this.basePath}/${productId}/`, productData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async deleteProduct(productId, hardDelete = false) {
    try {
      const params = hardDelete ? { hard_delete: 'true' } : {}
      const response = await api.delete(`${this.basePath}/${productId}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async restoreProduct(productId) {
    try {
      const response = await api.post(`${this.basePath}/${productId}/restore/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ BATCH-INTEGRATED STOCK MANAGEMENT ================

  async updateStock(productId, stockData) {
    try {
      const response = await api.put(`${this.basePath}/${productId}/stock/`, stockData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async adjustStockForSale(productId, quantitySold) {
    try {
      const response = await api.post(`${this.basePath}/${productId}/stock/adjust/`, {
        quantity_sold: quantitySold
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async restockProduct(productId, quantityReceived, supplierInfo = null) {
    try {
      const response = await api.post(`${this.basePath}/${productId}/restock/`, {
        quantity_received: quantityReceived,
        supplier_info: supplierInfo
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // NEW: Batch-aware restock
  async restockWithBatch(productId, restockData) {
    try {
      const response = await api.post(`${this.basePath}/${productId}/restock-batch/`, restockData)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async bulkUpdateStock(stockUpdates) {
    try {
      const response = await api.post(`${this.basePath}/stock/bulk-update/`, {
        updates: stockUpdates
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getStockHistory(productId) {
    try {
      const response = await api.get(`${this.basePath}/${productId}/stock/history/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // NEW: Get product with batch information
  async getProductWithBatches(productId) {
    try {
      const response = await api.get(`${this.basePath}/${productId}/with-batches/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // NEW: Get products with expiry summary
  async getProductsWithExpirySummary() {
    try {
      const response = await api.get(`${this.basePath}/expiry-summary/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ BULK OPERATIONS ================

  async bulkCreateProducts(productsData) {
    try {
      const response = await api.post(`${this.basePath}/bulk-create/`, {
        products: productsData
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async bulkCreateProductsWithCategory(productsData, defaultCategoryId, defaultSubcategoryName = 'None') {
    try {
      const productsWithCategories = productsData.map(product => ({
        ...product,
        category_id: product.category_id || defaultCategoryId,
        subcategory_name: product.subcategory_name || defaultSubcategoryName
      }))
      
      return await this.bulkCreateProducts(productsWithCategories)
    } catch (error) {
      this.handleError(error)
    }
  }

  async bulkDeleteProducts(productIds, hardDelete = false) {
    try {
      const response = await api.post(`${this.basePath}/bulk-delete/`, {
        product_ids: productIds,
        hard_delete: hardDelete
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ PRODUCT REPORTS ================

  async getLowStockProducts(options = null) {
    try {
      let params = {}
      if (typeof options === 'object' && options !== null) {
        params = { ...options }
      } else if (options) {
        params = { branch_id: options }
      }
      const response = await api.get(`${this.basePath}/reports/low-stock/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getExpiringProducts(options = 30) {
    try {
      let params = {}
      if (typeof options === 'number') {
        params.days_ahead = options
      } else if (typeof options === 'object' && options !== null) {
        params = { days_ahead: 30, ...options }
      } else {
        params.days_ahead = 30
      }
      const response = await api.get(`${this.basePath}/reports/expiring/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProductsByCategory(categoryId, subcategoryName = null) {
    try {
      const params = subcategoryName ? { subcategory_name: subcategoryName } : {}
      const response = await api.get(`${this.basePath}/reports/by-category/${categoryId}/`, { params })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProductsBySubcategory(categoryId, subcategoryName) {
    try {
      const filters = {
        category_id: categoryId,
        subcategory_name: subcategoryName
      }
      return await this.getAllProducts(filters)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getDeletedProducts() {
    try {
      const response = await api.get(`${this.basePath}/deleted/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ PRODUCT-CATEGORY RELATIONSHIP MANAGEMENT ================

  async moveProductToCategory(productId, newCategoryId, newSubcategoryName = null) {
    try {
      const response = await api.put('/category/product-management/', {
        product_id: productId,
        new_category_id: newCategoryId,
        new_subcategory_name: newSubcategoryName
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async bulkMoveProductsToCategory(productIds, newCategoryId, newSubcategoryName = null) {
    try {
      const response = await api.post('/category/product-management/', {
        product_ids: productIds,
        new_category_id: newCategoryId,
        new_subcategory_name: newSubcategoryName
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ SYNCHRONIZATION ================

  async syncProducts(direction, products = []) {
    try {
      const payload = { direction }
      if (direction === 'to_cloud' && products.length > 0) {
        payload.products = products
      }
      const response = await api.post(`${this.basePath}/sync/`, payload)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  // ================ IMPORT/EXPORT ================

  async importProducts(file, validateOnly = false) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('validate_only', validateOnly.toString())

      const response = await api.post(`${this.basePath}/import/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  async exportProducts(filters = {}, format = 'csv') {
    try {
      const params = { format }
      
      if (filters.category_id) params.category_id = filters.category_id
      if (filters.subcategory_name) params.subcategory_name = filters.subcategory_name
      if (filters.status) params.status = filters.status
      
      const response = await api.get(`${this.basePath}/export/`, { 
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `products_export.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      return { message: 'Export completed successfully' }
    } catch (error) {
      this.handleError(error)
    }
  }

  async exportProductDetails(productId) {
    try {
      const response = await api.get(`/products/${productId}/export/details/`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `product_${productId}_details.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      this.handleError(error);
    }
  }


  async downloadImportTemplate(format = 'csv') {
    try {
      // Use raw axios WITHOUT interceptors
      const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
      const url = `${baseURL}/products/import/template/`

      const response = await axios.get(url, {
        params: { format },
        responseType: 'blob',
        // NO Authorization header
      })
      
      const blob = new Blob([response.data])
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `product_import_template.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
      
      return { message: 'Template downloaded successfully' }
    } catch (error) {
      console.error('❌ Download template error:', error)
      throw error
    }
  }

  // ================ UTILITY METHODS ================

  async searchProducts(query, filters = {}) {
    try {
      const searchFilters = { ...filters, search: query }
      return await this.getAllProducts(searchFilters)
    } catch (error) {
      this.handleError(error)
    }
  }

  async searchProductsAdvanced(query, filters = {}) {
    try {
      const searchFilters = { ...filters, search: query }
      if (filters.subcategory_name) {
        searchFilters.subcategory_name = filters.subcategory_name
      }
      return await this.getAllProducts(searchFilters)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProductStock(productId) {
    try {
      const product = await this.getProductById(productId)
      return {
        productId: product.data._id,
        productName: product.data.product_name,
        currentStock: product.data.stock,
        totalStock: product.data.total_stock || product.data.stock,
        lowStockThreshold: product.data.low_stock_threshold,
        isLowStock: product.data.stock <= product.data.low_stock_threshold,
        isOutOfStock: product.data.stock === 0,
        oldestBatchExpiry: product.data.oldest_batch_expiry,
        newestBatchExpiry: product.data.newest_batch_expiry,
        expiryAlert: product.data.expiry_alert
      }
    } catch (error) {
      this.handleError(error)
    }
  }

  async createProductWithCategory(productData, categoryId, subcategoryName = 'None') {
    try {
      const productWithCategory = {
        ...productData,
        category_id: categoryId,
        subcategory_name: subcategoryName
      }
      
      const validation = await this.validateProductData(productWithCategory)
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`)
      }
      
      return await this.createProduct(productWithCategory)
    } catch (error) {
      this.handleError(error)
    }
  }

  async validateProductData(productData) {
    const errors = []
    
    if (!productData.product_name?.trim()) {
      errors.push('Product name is required')
    }
    
    if (!productData.selling_price || productData.selling_price <= 0) {
      errors.push('Selling price must be greater than 0')
    }
    
    // UPDATED: Stock is now optional, but cannot be negative if provided
    if (productData.stock !== undefined && productData.stock < 0) {
      errors.push('Stock cannot be negative')
    }
    
    // NEW: If stock is provided and > 0, cost_price is required
    if (productData.stock && productData.stock > 0) {
      if (!productData.cost_price || productData.cost_price <= 0) {
        errors.push('Cost price is required when stock is provided')
      }
    }
    
    if (productData.low_stock_threshold !== undefined && productData.low_stock_threshold < 0) {
      errors.push('Low stock threshold cannot be negative')
    }

    if (!productData.category_id?.trim()) {
      errors.push('Category is required')
    }
    
    return {
      isValid: errors.length === 0,
      errors
    }
  }
  
  async getAllSuppliers() {
    try {
      const response = await api.get(`/suppliers/`)
      return this.handleResponse(response)
    } catch (error) {
      this.handleError(error)
    }
  }

  
}

const apiProductsService = new ApiProductsService()
export default apiProductsService