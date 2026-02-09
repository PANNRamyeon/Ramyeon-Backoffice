import { ref, computed, watch, nextTick } from 'vue'
import apiProductsService from '../../services/apiProducts.js'
import { useToast } from '../ui/useToast.js'
import categoryApiService from '../../services/apiCategory.js'

const toast = useToast()

// Global state for products
const products = ref([])
const currentProduct = ref(null)
const deletedProducts = ref([])
const lowStockProducts = ref([])
const expiringProducts = ref([])

// Loading states - Fixed naming conflicts
const loading = ref(false)
const deleteLoading = ref(false)
const bulkDeleteLoading = ref(false)
const exportLoading = ref(false)
const stockLoading = ref(false)
const importLoading = ref(false)
const categoryMoveLoading = ref(false)

// Filters and pagination
const filters = ref({
  category_id: '',
  subcategory_name: '',
  status: '',
  stock_level: '',
  search: '',
  include_deleted: false
})

// Error states
const error = ref(null)
const validationErrors = ref([])

export function useProducts() {
  // ================ COMPUTED PROPERTIES ================
  
  const filteredProducts = computed(() => {
    let result = products.value
    
    if (filters.value.search) {
      const searchTerm = filters.value.search.toLowerCase()
      result = result.filter(product => 
        product.product_name?.toLowerCase().includes(searchTerm) ||
        product.SKU?.toLowerCase().includes(searchTerm) ||
        product._id?.toLowerCase().includes(searchTerm) ||
        product.barcode?.toLowerCase().includes(searchTerm)
      )
    }
    
    if (filters.value.category_id) {
      result = result.filter(product => product.category_id === filters.value.category_id)
    }

    if (filters.value.subcategory_name) {
      result = result.filter(product => product.subcategory_name === filters.value.subcategory_name)
    }
    
    if (filters.value.status) {
      result = result.filter(product => product.status === filters.value.status)
    }
    
    if (filters.value.stock_level) {
      if (filters.value.stock_level === 'out_of_stock') {
        result = result.filter(product => (product.total_stock || product.stock) === 0)
      } else if (filters.value.stock_level === 'low_stock') {
        result = result.filter(product => {
          const currentStock = product.total_stock || product.stock
          return currentStock > 0 && currentStock <= product.low_stock_threshold
        })
      }
    }
    
    return result
  })

  const isTrackedStock = (product) => {
    if (!product) return false
    const stockField = product.total_stock ?? product.stock
    return typeof stockField === 'number'
  }

  const lowStockItems = computed(() => products.value.filter(p => {
    if (!isTrackedStock(p)) return false
    const currentStock = p.total_stock ?? p.stock
    const threshold = typeof p.low_stock_threshold === 'number' ? p.low_stock_threshold : 0
    return currentStock > 0 && currentStock < threshold
  }))

  const productStats = computed(() => ({
    total: products.value.length,
    active: products.value.filter(p => p.status === 'active').length,
    inactive: products.value.filter(p => p.status === 'inactive').length,
    outOfStock: products.value.filter(p => {
      if (!isTrackedStock(p)) return false
      const currentStock = p.total_stock ?? p.stock
      return currentStock === 0
    }).length,
    lowStock: lowStockItems.value.length
  }))

  const productsByCategory = computed(() => {
    const grouped = {}
    products.value.forEach(product => {
      const categoryId = product.category_id || 'uncategorized'
      if (!grouped[categoryId]) {
        grouped[categoryId] = {}
      }
      
      const subcategory = product.subcategory_name || 'None'
      if (!grouped[categoryId][subcategory]) {
        grouped[categoryId][subcategory] = []
      }
      
      grouped[categoryId][subcategory].push(product)
    })
    return grouped
  })

  const hasProducts = computed(() => products.value.length > 0)
  const hasCurrentProduct = computed(() => currentProduct.value !== null)

  // ================ VALIDATION METHODS ================

  const checkSkuExists = async (sku) => {
    try {
      const response = await apiProductsService.getProductBySku(sku)
      return true
    } catch (err) {
      if (err.message.includes('404') || err.message.includes('not found')) {
        return false
      }
      throw err
    }
  }

  // ================ CRUD OPERATIONS ================

  const fetchProducts = async (customFilters = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const mergedFilters = { ...filters.value, ...customFilters }
      const response = await apiProductsService.getAllProducts(mergedFilters)
      products.value = response.data || []
      
      if (Object.keys(customFilters).length > 0 || products.value.length > 0) {
        toast.success(`Loaded ${products.value.length} products`)
      }
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to load products: ${err.message}`)
      products.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchProductById = async (productId, includeDeleted = false) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductById(productId, includeDeleted)
      currentProduct.value = response.data
      return response
    } catch (err) {
      error.value = err.message
      currentProduct.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchProductBySku = async (sku, includeDeleted = false) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductBySku(sku, includeDeleted)
      currentProduct.value = response.data
      return response
    } catch (err) {
      error.value = err.message
      currentProduct.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  const createProduct = async (productData) => {
    loading.value = true
    error.value = null
    validationErrors.value = []
    
    try {
      const response = await apiProductsService.createProduct(productData)
      
      products.value.unshift(response.data)
      currentProduct.value = response.data
      
      toast.success(`Product "${productData.product_name}" created successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to create product: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  const createProductWithCategory = async (productData, categoryId, subcategoryName = 'None') => {
    loading.value = true
    error.value = null
    validationErrors.value = []
    
    try {
      const response = await apiProductsService.createProductWithCategory(productData, categoryId, subcategoryName)
      
      products.value.unshift(response.data)
      currentProduct.value = response.data
      
      toast.success(`Product "${productData.product_name}" created successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to create product: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateProduct = async (productId, productData, partial = false) => {
    loading.value = true
    error.value = null
    validationErrors.value = []
    
    try {
      const response = await apiProductsService.updateProduct(productId, productData, partial)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = response.data
      }
      
      toast.success(`Product updated successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to update product: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteProduct = async (productId, hardDelete = false) => {
    deleteLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.deleteProduct(productId, hardDelete)
      
      if (hardDelete) {
        products.value = products.value.filter(p => p._id !== productId)
        deletedProducts.value = deletedProducts.value.filter(p => p._id !== productId)
      } else {
        const deletedProduct = products.value.find(p => p._id === productId)
        if (deletedProduct) {
          deletedProduct.isDeleted = true
          products.value = products.value.filter(p => p._id !== productId)
          deletedProducts.value.unshift(deletedProduct)
        }
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = null
      }
      
      toast.success(`Product deleted successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to delete product: ${err.message}`)
      throw err
    } finally {
      deleteLoading.value = false
    }
  }

  const restoreProduct = async (productId) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.restoreProduct(productId)
      
      const restoredProduct = deletedProducts.value.find(p => p._id === productId)
      if (restoredProduct) {
        restoredProduct.isDeleted = false
        deletedProducts.value = deletedProducts.value.filter(p => p._id !== productId)
        products.value.unshift(restoredProduct)
      }
      
      toast.success(`Product restored successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to restore product: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ BULK OPERATIONS ================

const bulkDeleteProducts = async (productIds, hardDelete = false) => {
  bulkDeleteLoading.value = true
  error.value = null
  
  try {
    const response = await apiProductsService.bulkDeleteProducts(productIds, hardDelete)
    
    // Update local state - remove deleted products
    products.value = products.value.filter(p => !productIds.includes(p._id))
    
    // Handle the response structure from your backend
    const deletedCount = response.details?.deleted_count || productIds.length
    const failedCount = response.details?.failed_count || 0
    
    if (failedCount > 0) {
      toast.success(`${deletedCount} products deleted successfully. ${failedCount} failed.`)
    } else {
      toast.success(`${deletedCount} products deleted successfully`)
    }
    
    return response
  } catch (err) {
    error.value = err.message
    toast.error(`Failed to delete products: ${err.message}`)
    throw err
  } finally {
    bulkDeleteLoading.value = false
  }
}

  // ================ EXPORT OPERATIONS ================

  const exportProducts = async (customFilters = {}, format = 'csv') => {
    exportLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.exportProducts(customFilters, format)
      toast.success('Products exported successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Export failed: ${err.message}`)
      throw err
    } finally {
      exportLoading.value = false
    }
  }

  

  // ================ PRODUCT-CATEGORY RELATIONSHIP MANAGEMENT ================

  const moveProductToCategory = async (productId, newCategoryId, newSubcategoryName = null) => {
    categoryMoveLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.moveProductToCategory(productId, newCategoryId, newSubcategoryName)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = response.data
      }
      
      toast.success(`Product moved to different category successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move product: ${err.message}`)
      throw err
    } finally {
      categoryMoveLoading.value = false
    }
  }

  const bulkMoveProductsToCategory = async (productIds, newCategoryId, newSubcategoryName = null) => {
    bulkDeleteLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.bulkMoveProductsToCategory(productIds, newCategoryId, newSubcategoryName)
      
      await fetchProducts()
      
      toast.success(`${response.moved_count} products moved successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move products: ${err.message}`)
      throw err
    } finally {
      bulkDeleteLoading.value = false
    }
  }

  // ================ BATCH-AWARE STOCK MANAGEMENT ================

  const updateStock = async (productId, stockData) => {
    stockLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.updateStock(productId, stockData)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = response.data
      }
      
      toast.success(`Stock updated successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to update stock: ${err.message}`)
      throw err
    } finally {
      stockLoading.value = false
    }
  }

  const adjustStockForSale = async (productId, quantitySold) => {
    stockLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.adjustStockForSale(productId, quantitySold)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      stockLoading.value = false
    }
  }

  const restockProduct = async (productId, quantityReceived, supplierInfo = null) => {
    stockLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.restockProduct(productId, quantityReceived, supplierInfo)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = response.data
      }
      
      toast.success(`Product restocked successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to restock product: ${err.message}`)
      throw err
    } finally {
      stockLoading.value = false
    }
  }

  // NEW: Batch-aware restock
  const restockWithBatch = async (productId, restockData) => {
    stockLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.restockWithBatch(productId, restockData)
      
      const index = products.value.findIndex(p => p._id === productId)
      if (index !== -1) {
        products.value[index] = response.data
      }
      
      if (currentProduct.value?._id === productId) {
        currentProduct.value = response.data
      }
      
      toast.success(`Product restocked with batch successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to restock product: ${err.message}`)
      throw err
    } finally {
      stockLoading.value = false
    }
  }

  const bulkUpdateStock = async (stockUpdates) => {
    bulkDeleteLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.bulkUpdateStock(stockUpdates)
      
      await fetchProducts()
      
      toast.success(`Bulk stock update completed`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to update stock: ${err.message}`)
      throw err
    } finally {
      bulkDeleteLoading.value = false
    }
  }

  const getStockHistory = async (productId) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getStockHistory(productId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // NEW: Get product with batch information
  const getProductWithBatches = async (productId) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductWithBatches(productId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // NEW: Get products with expiry summary
  const getProductsWithExpirySummary = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductsWithExpirySummary()
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ BULK OPERATIONS (CONTINUED) ================

  const bulkCreateProducts = async (productsData) => {
    bulkDeleteLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.bulkCreateProducts(productsData)
      
      if (response.results?.successful) {
        products.value.unshift(...response.results.successful)
      }
      
      toast.success(`Bulk creation completed`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to create products: ${err.message}`)
      throw err
    } finally {
      bulkDeleteLoading.value = false
    }
  }

  const bulkCreateProductsWithCategory = async (productsData, defaultCategoryId, defaultSubcategoryName = 'None') => {
    bulkDeleteLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.bulkCreateProductsWithCategory(productsData, defaultCategoryId, defaultSubcategoryName)
      
      if (response.results?.successful) {
        products.value.unshift(...response.results.successful)
      }
      
      toast.success(`Bulk creation with category completed`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to create products: ${err.message}`)
      throw err
    } finally {
      bulkDeleteLoading.value = false
    }
  }

  // ================ REPORTS AND ANALYTICS ================

  const fetchLowStockProducts = async (branchId = null) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getLowStockProducts(branchId)
      lowStockProducts.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchExpiringProducts = async (daysAhead = 30) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getExpiringProducts(daysAhead)
      expiringProducts.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchProductsByCategory = async (categoryId, subcategoryName = null) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductsByCategory(categoryId, subcategoryName)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchProductsBySubcategory = async (categoryId, subcategoryName) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getProductsBySubcategory(categoryId, subcategoryName)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchDeletedProducts = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getDeletedProducts()
      deletedProducts.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ IMPORT/EXPORT ================

  const importProducts = async (file, validateOnly = false) => {
    importLoading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.importProducts(file, validateOnly)
      
      if (!validateOnly) {
        await fetchProducts()
        toast.success('Products imported successfully')
      } else {
        toast.info('Validation completed')
      }
      
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Import failed: ${err.message}`)
      throw err
    } finally {
      importLoading.value = false
    }
  }

  const downloadImportTemplate = async (format = 'csv') => {
    try {
      const response = await apiProductsService.downloadImportTemplate(format)
      toast.success('Template downloaded successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Download failed: ${err.message}`)
      throw err
    }
  }

  const exportProductDetails = async (productId) => {
    try {
      await apiProductsService.exportProductDetails(productId);
    } catch (err) {
      console.error('❌ Export product details failed:', err);
      throw err;
    }
  }

  // ================ UTILITY METHODS ================

  const searchProducts = async (query) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.searchProducts(query, filters.value)
      products.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const searchProductsAdvanced = async (query, customFilters = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const mergedFilters = { ...filters.value, ...customFilters }
      const response = await apiProductsService.searchProductsAdvanced(query, mergedFilters)
      products.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const getProductStock = async (productId) => {
    try {
      const response = await apiProductsService.getProductStock(productId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const clearError = () => {
    error.value = null
    validationErrors.value = []
  }

  const clearCurrentProduct = () => {
    currentProduct.value = null
  }

  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const resetFilters = () => {
    filters.value = {
      category_id: '',
      subcategory_name: '',
      status: '',
      stock_level: '',
      search: '',
      include_deleted: false
    }
  }

  // ================ INITIALIZATION ================

  const initializeProducts = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiProductsService.getAllProducts(filters.value)
      products.value = response.data || []
      return response
    } catch (err) {
      error.value = err.message
      products.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ UI COMPOSABLES: ADD PRODUCT MODAL ================
  
  // Modal State for Add/Edit Product
  const showAddProductModal = ref(false)
  const addProductModalProduct = ref(null)
  const addProductModalLoading = ref(false)
  const addProductModalError = ref(null)
  const autoCalculateSellingPrice = ref(true)
  const hasUserEditedSellingPrice = ref(false)
  const hasManuallyEditedSellingPrice = ref(false)
  
  // Form data for Add Product
  const addProductForm = ref({
    product_name: '',
    category_id: '',
    SKU: '',
    unit: '',
    stock: 0,
    low_stock_threshold: 10,
    cost_price: 0,
    selling_price: 0,
    expiry_date: '',
    status: 'active',
    is_taxable: false,
    barcode: '',
    description: '',
    image: null
  })
  
  // Image handling
  const imagePreview = ref(null)
  const imageFile = ref(null)
  
  // SKU validation
  const skuError = ref(null)
  const isValidatingSku = ref(false)
  
  // Computed for Add Product Modal
  const isEditMode = computed(() => addProductModalProduct.value !== null)
  
  const isAddProductFormValid = computed(() => {
    return addProductForm.value.product_name.trim() !== '' &&
           addProductForm.value.SKU.trim() !== '' &&
           addProductForm.value.category_id !== '' &&
           addProductForm.value.unit !== '' &&
           addProductForm.value.cost_price >= 0 &&
           addProductForm.value.selling_price >= 0 &&
           addProductForm.value.stock >= 0 &&
           addProductForm.value.low_stock_threshold >= 0 &&
           !skuError.value
  })
  
  // Watcher for auto-calculating selling price
  watch(() => addProductForm.value.cost_price, (newCostPrice) => {
    const costPrice = parseFloat(newCostPrice) || 0
    if (costPrice > 0 && !hasManuallyEditedSellingPrice.value) {
      const markup = costPrice * 0.30
      const sellingPrice = costPrice + markup
      addProductForm.value.selling_price = Math.round(sellingPrice * 100) / 100
    }
  })

  // Watch for modal show/hide
  watch(showAddProductModal, (newVal) => {
    if (newVal) {
      initializeAddProductForm()
      nextTick(() => {
        const firstInput = document.querySelector('#product_name')
        if (firstInput) firstInput.focus()
      })
    }
  })
  
  watch(addProductModalProduct, () => {
    if (showAddProductModal.value) {
      initializeAddProductForm()
    }
  }, { deep: true })
  
  // Add Product Modal Methods
  const handleSellingPriceChange = () => {
    hasManuallyEditedSellingPrice.value = true
  }

  const initializeAddProductForm = () => {
    hasManuallyEditedSellingPrice.value = false
    
    if (isEditMode.value && addProductModalProduct.value) {
      hasManuallyEditedSellingPrice.value = true
      addProductForm.value = {
        product_name: addProductModalProduct.value.product_name || '',
        category_id: addProductModalProduct.value.category_id || '',
        SKU: addProductModalProduct.value.SKU || '',
        unit: addProductModalProduct.value.unit || '',
        stock: addProductModalProduct.value.stock || 0,
        low_stock_threshold: addProductModalProduct.value.low_stock_threshold || 10,
        cost_price: addProductModalProduct.value.cost_price || 0,
        selling_price: addProductModalProduct.value.selling_price || 0,
        expiry_date: addProductModalProduct.value.expiry_date ? addProductModalProduct.value.expiry_date.split('T')[0] : '',
        status: addProductModalProduct.value.status || 'active',
        is_taxable: addProductModalProduct.value.is_taxable || false,
        barcode: addProductModalProduct.value.barcode || '',
        description: addProductModalProduct.value.description || '',
        image: null
      }
      
      if (addProductModalProduct.value.image_url || addProductModalProduct.value.image) {
        imagePreview.value = addProductModalProduct.value.image_url || addProductModalProduct.value.image
      } else {
        imagePreview.value = null
      }
      imageFile.value = null
    } else {
      addProductForm.value = {
        product_name: '',
        category_id: '',
        SKU: '',
        unit: '',
        stock: 0,
        low_stock_threshold: 10,
        cost_price: 0,
        selling_price: 0,
        expiry_date: '',
        status: 'active',
        is_taxable: false,
        barcode: '',
        description: '',
        image: null
      }
      imagePreview.value = null
      imageFile.value = null
      skuError.value = null
      isValidatingSku.value = false
    }
  }
  
  const validateSKU = async () => {
    if (!addProductForm.value.SKU || addProductForm.value.SKU.trim() === '') {
      skuError.value = null
      return
    }

    if (isEditMode.value && addProductModalProduct.value && addProductForm.value.SKU === addProductModalProduct.value.SKU) {
      skuError.value = null
      return
    }

    isValidatingSku.value = true
    
    try {
      const exists = await apiProductsService.productExistsBySku(addProductForm.value.SKU)
      if (exists) {
        skuError.value = 'This SKU already exists'
      } else {
        skuError.value = null
      }
    } catch (error) {
      if (error.response?.status === 404) {
        skuError.value = null
      } else {
        console.error('Error validating SKU:', error)
        skuError.value = null
      }
    } finally {
      isValidatingSku.value = false
    }
  }
  
  const handleImageUpload = (event) => {
    const file = event.target.files[0]

    if (!file) return

    if (!file.type.startsWith('image/')) {
      alert('Please select a valid image file (PNG, JPG, JPEG)')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('Image size should be less than 5MB')
      return
    }

    imageFile.value = file

    const reader = new FileReader()
    reader.onload = (e) => {
      imagePreview.value = e.target.result
    }
    reader.onerror = (error) => {
      console.error('Error creating preview:', error)
    }
    reader.readAsDataURL(file)
  }
  
  const removeImage = () => {
    imagePreview.value = null
    imageFile.value = null
    addProductForm.value.image = null

    const fileInput = document.querySelector('input[type="file"]')
    if (fileInput) {
      fileInput.value = ''
    }
  }
  
  const convertImageToBase64 = async () => {
    if (!imageFile.value) return null

    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        resolve(e.target.result)
      }
      reader.onerror = (error) => {
        console.error('Base64 conversion failed:', error)
        reject(error)
      }
      reader.readAsDataURL(imageFile.value)
    })
  }
  
  const generateBarcode = () => {
    const timestamp = Date.now().toString().slice(-6)
    const sku = addProductForm.value.SKU.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()
    addProductForm.value.barcode = `${sku}${timestamp}`
  }
  
  const openAddProductModal = () => {
    addProductModalProduct.value = null
    addProductModalError.value = null
    showAddProductModal.value = true
  }
  
  const openEditProductModal = (productData) => {
    addProductModalProduct.value = productData
    addProductModalError.value = null
    showAddProductModal.value = true
  }
  
  const closeAddProductModal = () => {
    showAddProductModal.value = false
    addProductModalProduct.value = null
    addProductModalError.value = null
    addProductModalLoading.value = false
  }
  
  const submitProduct = async (onSuccess) => {
    if (!isAddProductFormValid.value) return
  
    addProductModalLoading.value = true
    addProductModalError.value = null
  
    try {
      const formData = {
        product_name: addProductForm.value.product_name,
        category_id: addProductForm.value.category_id,
        SKU: addProductForm.value.SKU,
        unit: addProductForm.value.unit,
        stock: addProductForm.value.stock,
        low_stock_threshold: addProductForm.value.low_stock_threshold,
        cost_price: addProductForm.value.cost_price,
        selling_price: addProductForm.value.selling_price,
        status: addProductForm.value.status,
        is_taxable: addProductForm.value.is_taxable
      }
      
      if (addProductForm.value.expiry_date?.trim()) {
        formData.expiry_date = addProductForm.value.expiry_date.trim()
      }
      if (addProductForm.value.barcode?.trim()) {
        formData.barcode = addProductForm.value.barcode.trim()
      }
      if (addProductForm.value.description?.trim()) {
        formData.description = addProductForm.value.description.trim()
      }
      
      if (imageFile.value && imagePreview.value) {
        formData.image_filename = imageFile.value.name
        formData.image_size = imageFile.value.size
        formData.image_type = imageFile.value.type
        formData.image_url = imagePreview.value
        formData.image_uploaded_at = new Date().toISOString()
      }
      
      let result
      if (isEditMode.value) {
        result = await apiProductsService.updateProduct(addProductModalProduct.value._id, formData)
      } else {
        result = await apiProductsService.createProduct(formData)
      }
      
      if (onSuccess) {
        onSuccess(result, isEditMode.value)
      }
      
      closeAddProductModal()
      
    } catch (err) {
      console.error('Error saving product:', err)
      addProductModalError.value = err.response?.data?.error || err.message || 'Failed to save product'
    } finally {
      addProductModalLoading.value = false
    }
  }
  
  const handleAddProductEscape = (e) => {
    if (e.key === 'Escape' && showAddProductModal.value && !addProductModalLoading.value) {
      closeAddProductModal()
    }
  }
  
  const setupAddProductKeyboardListeners = () => {
    document.addEventListener('keydown', handleAddProductEscape)
  }
  
  const cleanupAddProductKeyboardListeners = () => {
    document.removeEventListener('keydown', handleAddProductEscape)
  }

  // ================ UI COMPOSABLES: STOCK UPDATE MODAL ================
  
  // Modal State for Stock Update
  const showStockUpdateModal = ref(false)
  const stockUpdateProduct = ref(null)
  const stockUpdateLoading = ref(false)
  const stockUpdateError = ref(null)
  
  // Form data for Stock Update
  const stockUpdateForm = ref({
    operation_type: 'add',
    quantity: 0,
    reason: ''
  })
  
  const selectedStockReason = ref('')
  const newStockPreview = ref(null)
  
  const stockReasons = {
    increase: [
      'Purchase/Delivery',
      'Stock Return',
      'Stock Transfer In',
      'Manual Recount'
    ],
    decrease: [
      'Sale',
      'Damaged/Expired',
      'Stock Transfer Out',
      'Theft/Loss',
      'Manual Adjustment'
    ],
    other: [
      'Inventory Correction',
      'System Migration',
      'Custom'
    ]
  }
  
  const isStockUpdateFormValid = computed(() => {
    return stockUpdateForm.value.operation_type &&
           stockUpdateForm.value.quantity > 0 &&
           stockUpdateForm.value.reason.trim() !== '' &&
           (stockUpdateForm.value.operation_type !== 'remove' || stockUpdateForm.value.quantity <= (stockUpdateProduct.value?.stock || 0))
  })
  
  const operationDescription = computed(() => {
    switch (stockUpdateForm.value.operation_type) {
      case 'add':
        return 'Add the specified quantity to current stock'
      case 'remove':
        return 'Remove the specified quantity from current stock'
      case 'set':
        return 'Set the stock to the exact quantity specified'
      default:
        return ''
    }
  })
  
  watch(showStockUpdateModal, (newVal) => {
    if (newVal) {
      initializeStockUpdateForm()
      nextTick(() => {
        const firstInput = document.querySelector('#operation_type')
        if (firstInput) firstInput.focus()
      })
    }
  })
  
  watch(stockUpdateProduct, () => {
    if (showStockUpdateModal.value) {
      initializeStockUpdateForm()
    }
  }, { deep: true })
  
  const initializeStockUpdateForm = () => {
    stockUpdateForm.value = {
      operation_type: 'add',
      quantity: 0,
      reason: ''
    }
    selectedStockReason.value = ''
    newStockPreview.value = null
    stockUpdateError.value = null
  }
  
  const onStockOperationChange = () => {
    stockUpdateForm.value.quantity = 0
    newStockPreview.value = null
    selectedStockReason.value = ''
    stockUpdateForm.value.reason = ''
  }
  
  const onStockReasonChange = () => {
    if (selectedStockReason.value && selectedStockReason.value !== 'Custom') {
      stockUpdateForm.value.reason = selectedStockReason.value
    } else {
      stockUpdateForm.value.reason = ''
    }
  }
  
  const calculateNewStock = () => {
    if (!stockUpdateProduct.value || !stockUpdateForm.value.quantity) {
      newStockPreview.value = null
      return
    }
    
    const currentStock = stockUpdateProduct.value.stock
    const quantity = parseInt(stockUpdateForm.value.quantity) || 0
    
    switch (stockUpdateForm.value.operation_type) {
      case 'add':
        newStockPreview.value = currentStock + quantity
        break
      case 'remove':
        newStockPreview.value = Math.max(0, currentStock - quantity)
        break
      case 'set':
        newStockPreview.value = quantity
        break
      default:
        newStockPreview.value = null
    }
  }
  
  const getStockClass = (productData) => {
    if (!productData) return ''
    if (productData.stock === 0) return 'text-danger fw-bold'
    if (productData.stock <= productData.low_stock_threshold) return 'text-warning fw-semibold'
    return 'text-success fw-medium'
  }
  
  const getPreviewStockClass = (stock) => {
    if (!stockUpdateProduct.value) return ''
    if (stock === 0) return 'text-danger fw-bold'
    if (stock <= stockUpdateProduct.value.low_stock_threshold) return 'text-warning fw-semibold'
    return 'text-success fw-medium'
  }
  
  const getStockSubmitButtonClass = () => {
    switch (stockUpdateForm.value.operation_type) {
      case 'add':
        return 'btn-save'
      case 'remove':
        return 'btn-delete'
      case 'set':
        return 'btn-submit'
      default:
        return 'btn-submit'
    }
  }
  
  const getStockSubmitButtonText = () => {
    switch (stockUpdateForm.value.operation_type) {
      case 'add':
        return `Add ${stockUpdateForm.value.quantity || 0} Units`
      case 'remove':
        return `Remove ${stockUpdateForm.value.quantity || 0} Units`
      case 'set':
        return `Set to ${stockUpdateForm.value.quantity || 0} Units`
      default:
        return 'Update Stock'
    }
  }
  
  const openStockUpdateModal = (productData) => {
    stockUpdateProduct.value = productData
    stockUpdateError.value = null
    showStockUpdateModal.value = true
  }
  
  const closeStockUpdateModal = () => {
    showStockUpdateModal.value = false
    stockUpdateProduct.value = null
    stockUpdateError.value = null
    stockUpdateLoading.value = false
  }
  
  const submitStockUpdate = async (onSuccess) => {
    if (!isStockUpdateFormValid.value) return
    
    stockUpdateLoading.value = true
    stockUpdateError.value = null
    
    try {
      const formData = {
        operation_type: stockUpdateForm.value.operation_type,
        quantity: stockUpdateForm.value.quantity,
        reason: stockUpdateForm.value.reason
      }
      
      const result = await apiProductsService.updateProductStock(stockUpdateProduct.value._id, formData)
      
      if (onSuccess) {
        onSuccess(result, formData)
      }
      
      closeStockUpdateModal()
      
    } catch (err) {
      console.error('Error updating stock:', err)
      stockUpdateError.value = err.message || 'Failed to update stock'
    } finally {
      stockUpdateLoading.value = false
    }
  }
  
  const handleStockUpdateEscape = (e) => {
    if (e.key === 'Escape' && showStockUpdateModal.value && !stockUpdateLoading.value) {
      closeStockUpdateModal()
    }
  }
  
  const setupStockUpdateKeyboardListeners = () => {
    document.addEventListener('keydown', handleStockUpdateEscape)
  }
  
  const cleanupStockUpdateKeyboardListeners = () => {
    document.removeEventListener('keydown', handleStockUpdateEscape)
  }

  // ================ UI COMPOSABLES: VIEW PRODUCT ================
  
  // Modal State for View Product
  const showViewProductModal = ref(false)
  const viewProductModalProduct = ref(null)
  
  const getCategoryName = (categoryId) => {
    const categories = {
      'noodles': 'Noodles',
      'drinks': 'Drinks',
      'toppings': 'Toppings'
    }
    return categories[categoryId] || categoryId
  }
  
  const getCategorySlug = (categoryId) => {
    return categoryId?.toLowerCase().replace(/\s+/g, '-') || 'unknown'
  }
  
  const getStockStatusClass = (productData) => {
    if (!productData) return ''
    if (productData.stock === 0) return 'badge text-bg-danger'
    if (productData.stock <= productData.low_stock_threshold) return 'badge text-bg-warning'
    return 'badge text-bg-success'
  }
  
  const getStockStatusText = (productData) => {
    if (!productData) return 'Unknown'
    if (productData.stock === 0) return 'Out of Stock'
    if (productData.stock <= productData.low_stock_threshold) return 'Low Stock'
    return 'In Stock'
  }
  
  const getStatusBadgeClass = (status) => {
    return status === 'active' ? 'badge text-bg-success' : 'badge text-bg-danger'
  }
  
  const getCategoryBadgeClass = (categoryId) => {
    const classes = {
      'noodles': 'badge text-bg-warning',
      'drinks': 'badge text-bg-primary',
      'toppings': 'badge text-bg-info'
    }
    return classes[categoryId] || 'badge text-bg-secondary'
  }
  
  const getExpiryClass = (expiryDate) => {
    if (!expiryDate) return ''
    
    const today = new Date()
    const expiry = new Date(expiryDate)
    const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
    
    if (daysUntilExpiry < 0) return 'text-danger fw-bold'
    if (daysUntilExpiry <= 7) return 'text-warning fw-semibold'
    if (daysUntilExpiry <= 30) return 'text-info fw-medium'
    return ''
  }
  
  const getDaysUntilExpiry = (expiryDate) => {
    if (!expiryDate) return ''
    
    const today = new Date()
    const expiry = new Date(expiryDate)
    const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
    
    if (daysUntilExpiry < 0) return `Expired ${Math.abs(daysUntilExpiry)} days ago`
    if (daysUntilExpiry === 0) return 'Expires today'
    if (daysUntilExpiry === 1) return 'Expires tomorrow'
    return `${daysUntilExpiry} days remaining`
  }
  
  const getProfitMargin = (productData) => {
    if (!productData || !productData.selling_price || !productData.cost_price) return '0.00'
    const margin = ((productData.selling_price - productData.cost_price) / productData.selling_price * 100)
    return margin.toFixed(2)
  }
  
  const getProfitPerUnit = (productData) => {
    if (!productData || !productData.selling_price || !productData.cost_price) return '0.00'
    const profit = productData.selling_price - productData.cost_price
    return profit.toFixed(2)
  }
  
  const formatPrice = (price) => {
    return parseFloat(price || 0).toFixed(2)
  }
  
  const formatStatus = (status) => {
    return status.charAt(0).toUpperCase() + status.slice(1).replace('-', ' ')
  }
  
  const formatDate = (dateString) => {
    if (!dateString) return 'Not set'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
  
  const formatDateTime = (dateString) => {
    if (!dateString) return 'Not available'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  const stockCardClass = computed(() => {
    if (!viewProductModalProduct.value) return ''
    if (viewProductModalProduct.value.stock === 0) return 'border-danger bg-danger-subtle'
    if (viewProductModalProduct.value.stock <= viewProductModalProduct.value.low_stock_threshold) return 'border-warning bg-warning-subtle'
    return 'border-success bg-success-subtle'
  })
  
  const thresholdCardClass = computed(() => 'border-info bg-info-subtle')
  const statusCardClass = computed(() => 'border-primary bg-primary-subtle')
  
  const canGenerateBarcode = computed(() => {
    return viewProductModalProduct.value && !viewProductModalProduct.value.barcode
  })
  
  const statusToggleText = computed(() => {
    if (!viewProductModalProduct.value) return 'Toggle Status'
    return viewProductModalProduct.value.status === 'active' ? 'Deactivate Product' : 'Activate Product'
  })
  
  const statusToggleSubtext = computed(() => {
    if (!viewProductModalProduct.value) return ''
    return viewProductModalProduct.value.status === 'active' 
      ? 'Make unavailable for sale' 
      : 'Make available for sale'
  })
  
  const openViewProductModal = (productData) => {
    viewProductModalProduct.value = productData
    showViewProductModal.value = true
  }
  
  const closeViewProductModal = () => {
    showViewProductModal.value = false
    viewProductModalProduct.value = null
  }
  
  const handleViewProductEdit = (onEdit) => {
    if (onEdit && viewProductModalProduct.value) {
      onEdit(viewProductModalProduct.value)
    }
  }
  
  const handleViewProductRestock = (onRestock) => {
    if (onRestock && viewProductModalProduct.value) {
      onRestock(viewProductModalProduct.value)
    }
  }
  
  const handleViewProductToggleStatus = (onToggleStatus) => {
    if (onToggleStatus && viewProductModalProduct.value) {
      onToggleStatus(viewProductModalProduct.value)
    }
  }
  
  const handleViewProductGenerateBarcode = (onGenerateBarcode) => {
    if (onGenerateBarcode && viewProductModalProduct.value && !viewProductModalProduct.value.barcode) {
      onGenerateBarcode(viewProductModalProduct.value)
    }
  }
  
  const handleViewProductEscape = (e) => {
    if (e.key === 'Escape' && showViewProductModal.value) {
      closeViewProductModal()
    }
  }
  
  const setupViewProductKeyboardListeners = () => {
    document.addEventListener('keydown', handleViewProductEscape)
  }
  
  const cleanupViewProductKeyboardListeners = () => {
    document.removeEventListener('keydown', handleViewProductEscape)
  }

  // ================ UI COMPOSABLES: ADDITIONAL METHODS FROM UI/USEPRODUCTS ================
  
  // Categories state
  const categories = ref([])
  
  const fetchCategories = async () => {
    try {
      const response = await categoryApiService.getAllCategories()

      if (Array.isArray(response)) {
        categories.value = response
      } else if (response.categories) {
        categories.value = response.categories
      } else {
        categories.value = []
      }
    } catch (err) {
      console.error('Error fetching categories:', err)
      categories.value = []
    }
  }
  
  const enrichProductsWithCategoryNames = async () => {
    try {
      if (categories.value.length === 0) {
        await fetchCategories()
      }

      const categoryMap = new Map(
        categories.value.map(cat => [cat._id, cat.category_name])
      )

      products.value = products.value.map(product => ({
        ...product,
        category_name: categoryMap.get(product.category_id) || 'Uncategorized'
      }))
    } catch (err) {
      console.error('Error enriching products with category names:', err)
      products.value = products.value.map(product => ({
        ...product,
        category_name: product.category_name || 'Uncategorized'
      }))
    }
  }
  
  const successMessage = ref(null)
  const filteredProductsForUI = ref([])
  const selectedProducts = ref([])
  const showAddDropdown = ref(false)
  const searchMode = ref(false)
  const showColumnFilter = ref(false)
  const currentPage = ref(1)
  const itemsPerPage = ref(10)
  const lowStockCount = ref(0)
  const expiringCount = ref(0)
  
  const visibleColumns = ref({
    sku: true,
    category: true,
    stock: true,
    costPrice: false,
    sellingPrice: true,
    status: true,
    expiryDate: false
  })
  
  const categoryFilter = ref('all')
  const stockFilter = ref('all')
  const searchFilter = ref('')
  
  const paginatedProducts = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage.value
    const end = start + itemsPerPage.value
    return filteredProductsForUI.value.slice(start, end)
  })
  
  const allSelected = computed(() => {
    return paginatedProducts.value.length > 0 && 
           selectedProducts.value.length === paginatedProducts.value.length
  })
  
  const someSelected = computed(() => {
    return selectedProducts.value.length > 0 && 
           selectedProducts.value.length < paginatedProducts.value.length
  })
  
  const fetchReportCounts = async () => {
    try {
      const lowStockData = await apiProductsService.getLowStockProducts()
      lowStockCount.value = Array.isArray(lowStockData) ? lowStockData.length : (lowStockData.count || 0)
      
      const expiringData = await apiProductsService.getExpiringProducts({ days_ahead: 30 })
      expiringCount.value = Array.isArray(expiringData) ? expiringData.length : (expiringData.count || 0)
    } catch (err) {
      console.error('Error fetching report counts:', err)
    }
  }
  
  const applyFilters = () => {
    let filtered = [...products.value]
    
    if (categoryFilter.value !== 'all') {
      filtered = filtered.filter(product => {
        return product.category_id === categoryFilter.value || 
               product.category_name?.toLowerCase() === categoryFilter.value.toLowerCase()
      })
    }
    
    if (stockFilter.value !== 'all') {
      if (stockFilter.value === 'out-of-stock') {
        filtered = filtered.filter(product => product.stock === 0)
      } else if (stockFilter.value === 'low-stock') {
        filtered = filtered.filter(product => 
          product.stock > 0 && product.stock <= product.low_stock_threshold
        )
      } else if (stockFilter.value === 'in-stock') {
        filtered = filtered.filter(product => product.stock > product.low_stock_threshold)
      }
    }
    
    if (searchFilter.value.trim()) {
      const search = searchFilter.value.toLowerCase()
      filtered = filtered.filter(product => 
        product.product_name?.toLowerCase().includes(search) ||
        product.SKU?.toLowerCase().includes(search) ||
        product._id?.toLowerCase().includes(search) ||
        product.category_name?.toLowerCase().includes(search)
      )
    }
    
    currentPage.value = 1
    selectedProducts.value = []
    filteredProductsForUI.value = filtered
  }
  
  const clearFilters = () => {
    categoryFilter.value = 'all'
    stockFilter.value = 'all'
    searchFilter.value = ''
    searchMode.value = false
    applyFilters()
  }
  
  const refreshData = async () => {
    successMessage.value = null
    await fetchProducts()
  }
  
  const selectAll = (checked) => {
    if (checked) {
      selectedProducts.value = paginatedProducts.value.map(product => product._id)
    } else {
      selectedProducts.value = []
    }
  }
  
  const deleteSelected = async () => {
    if (selectedProducts.value.length === 0) return
    
    const confirmed = confirm(`Are you sure you want to delete ${selectedProducts.value.length} product(s)?`)
    if (!confirmed) return
    
    loading.value = true
    
    try {
      for (const productId of selectedProducts.value) {
        await apiProductsService.deleteProduct(productId)
      }
      
      const message = `Successfully deleted ${selectedProducts.value.length} product(s)`
      successMessage.value = message
      selectedProducts.value = []
      await fetchProducts()
      toast.success(message)
    } catch (err) {
      console.error('Error deleting products:', err)
      error.value = `Failed to delete products: ${err.message}`
      toast.error(`Failed to delete products: ${err.message}`)
    } finally {
      loading.value = false
    }
    
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  }
  
  const toggleProductStatus = async (product) => {
    const newStatus = product.status === 'active' ? 'inactive' : 'active'
    const action = newStatus === 'active' ? 'activate' : 'deactivate'
    
    const confirmed = confirm(`Are you sure you want to ${action} "${product.product_name}"?`)
    if (!confirmed) return
    
    try {
      await apiProductsService.updateProduct(product._id, { status: newStatus })
      const message = `Product "${product.product_name}" ${action}d successfully`
      successMessage.value = message
      await fetchProducts()
      toast.success(message)
      
      setTimeout(() => {
        successMessage.value = null
      }, 3000)
    } catch (err) {
      console.error('Error updating product status:', err)
      error.value = `Failed to ${action} product: ${err.message}`
      toast.error(`Failed to ${action} product: ${err.message}`)
    }
  }
  
  const exportData = async () => {
    try {
      const blob = await apiProductsService.exportProducts({
        format: 'csv',
        filters: {
          category: categoryFilter.value !== 'all' ? categoryFilter.value : undefined,
          stock: stockFilter.value !== 'all' ? stockFilter.value : undefined,
          search: searchFilter.value || undefined
        }
      })
      
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `products_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('API export failed, falling back to client-side export:', err)
      
      const headers = ['Name', 'SKU', 'Category', 'Price', 'Cost', 'Margin', 'Stock']
      const csvContent = [
        headers.join(','),
        ...filteredProductsForUI.value.map(product => [
          `"${product.product_name}"`,
          product.SKU || '',
          getCategoryName(product.category_id),
          product.selling_price,
          product.cost_price,
          calculateMargin(product.cost_price, product.selling_price),
          product.stock
        ].join(','))
      ].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `products_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    }
  }
  
  const toggleAddDropdown = (event) => {
    if (event) event.stopPropagation()
    showAddDropdown.value = !showAddDropdown.value
  }
  
  const closeAddDropdown = () => {
    showAddDropdown.value = false
  }
  
  const toggleSearchMode = () => {
    searchMode.value = !searchMode.value
    
    if (!searchMode.value) {
      searchFilter.value = ''
      applyFilters()
    }
  }
  
  const clearSearch = () => {
    searchFilter.value = ''
    searchMode.value = false
    applyFilters()
  }
  
  const toggleColumnFilter = () => {
    showColumnFilter.value = true
  }
  
  const handleColumnChanges = (newColumnSettings) => {
    visibleColumns.value = { ...newColumnSettings }
  }
  
  const handleSingleProduct = () => {
    closeAddDropdown()
    return 'single'
  }
  
  const handleBulkAdd = () => {
    closeAddDropdown()
    // This would typically use router, but we'll return a signal
    return 'bulk'
  }
  
  const handleImport = () => {
    closeAddDropdown()
    return 'import'
  }
  
  const handlePageChange = (page) => {
    currentPage.value = page
    selectedProducts.value = []
  }
  
  const calculateMargin = (costPrice, sellingPrice) => {
    if (!costPrice || !sellingPrice) return 0
    const margin = ((sellingPrice - costPrice) / sellingPrice) * 100
    return Math.round(margin)
  }
  
  const formatExpiryDate = (expiryDate) => {
    if (!expiryDate) return 'N/A'
    try {
      const date = new Date(expiryDate)
      if (isNaN(date.getTime())) {
        return 'N/A'
      }
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
      })
    } catch (err) {
      return 'N/A'
    }
  }
  
  const getProductNameClass = (product) => {
    if (product.stock === 0) return 'text-error fw-bold'
    if (product.stock <= product.low_stock_threshold) return 'text-warning fw-semibold'
    return 'text-primary'
  }
  
  const getRowClass = (product) => {
    const classes = []
    
    if (selectedProducts.value.includes(product._id)) {
      classes.push('table-primary')
    }
    
    if (product.status === 'inactive') {
      classes.push('text-muted')
    }
    
    return classes.join(' ')
  }
  
  const getStockDisplayClass = (product) => {
    if (product.stock === 0) return 'text-error fw-bold'
    if (product.stock <= product.low_stock_threshold) return 'text-warning fw-semibold'
    return 'text-secondary'
  }
  
  const getMarginClass = (costPrice, sellingPrice) => {
    const margin = calculateMargin(costPrice, sellingPrice)
    if (margin < 10) return 'text-error'
    if (margin < 20) return 'text-warning'
    return 'text-success'
  }
  
  const getStatusText = (status) => {
    return status === 'active' ? 'Active' : 'Inactive'
  }
  
  const getExpiryDateClass = (expiryDate) => {
    if (!expiryDate) return 'text-tertiary'
    
    try {
      const expiry = new Date(expiryDate)
      const today = new Date()
      const diffDays = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) return 'text-error fw-bold'
      if (diffDays <= 7) return 'text-error'
      if (diffDays <= 30) return 'text-warning'
      return 'text-tertiary'
    } catch (err) {
      return 'text-tertiary'
    }
  }
  
  const isColumnVisible = (columnKey) => {
    return visibleColumns.value[columnKey]
  }
  
  const handleClickOutside = (event) => {
    const dropdown = document.querySelector('.dropdown')
    if (dropdown && !dropdown.contains(event.target)) {
      showAddDropdown.value = false
    }
  }
  
  const handleProductSuccess = (result) => {
    successMessage.value = result.message
    fetchProducts()
    toast.success(result.message)
    
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  }
  
  const handleStockUpdateSuccess = (result) => {
    successMessage.value = result.message
    fetchProducts()
    toast.success(result.message)
    
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  }
  
  const handleImportSuccess = (result) => {
    const message = `Import completed! ${result.totalSuccessful || 0} products imported successfully.`
    successMessage.value = message
    fetchProducts()
    toast.success(message)
    
    setTimeout(() => {
      successMessage.value = null
    }, 5000)
  }
  
  const handleImportError = (err) => {
    const message = `Import failed: ${err.message || 'An unexpected error occurred'}`
    error.value = message
    toast.error(message)
    
    setTimeout(() => {
      error.value = null
    }, 5000)
  }
  
  const initializeProductsWithUI = async () => {
    await fetchCategories()
    await fetchProducts()
    document.addEventListener('click', handleClickOutside)
  }
  
  const cleanupProductsWithUI = () => {
    document.removeEventListener('click', handleClickOutside)
  }

  return {
    // State
    products,
    currentProduct,
    deletedProducts,
    lowStockProducts,
    expiringProducts,
    filters,
    error,
    validationErrors,
    loading,
    deleteLoading,
    bulkDeleteLoading,
    exportLoading,
    stockLoading,
    importLoading,
    categoryMoveLoading,
    categories,
    successMessage,

    // Computed
    filteredProducts,
    productStats,
    productsByCategory,
    hasProducts,
    hasCurrentProduct,

    // Validation
    checkSkuExists,
    exportProductDetails,

    // CRUD Operations
    fetchProducts,
    fetchProductById,
    fetchProductBySku,
    createProduct,
    createProductWithCategory,
    updateProduct,
    deleteProduct,
    restoreProduct,

    // Bulk Operations
    bulkDeleteProducts,
    bulkCreateProducts,
    bulkCreateProductsWithCategory,

    // Export
    exportProducts,

    // Product-Category Management
    moveProductToCategory,
    bulkMoveProductsToCategory,

    // Stock Management (Batch-aware)
    updateStock,
    adjustStockForSale,
    restockProduct,
    restockWithBatch,
    bulkUpdateStock,
    getStockHistory,
    getProductWithBatches,
    getProductsWithExpirySummary,

    // Reports
    fetchLowStockProducts,
    fetchExpiringProducts,
    fetchProductsByCategory,
    fetchProductsBySubcategory,
    fetchDeletedProducts,

    // Import/Export
    importProducts,
    downloadImportTemplate,

    // Utilities
    searchProducts,
    searchProductsAdvanced,
    getProductStock,
    clearError,
    clearCurrentProduct,
    setFilters,
    resetFilters,
    initializeProducts,
    
    // UI: Add Product Modal
    showAddProductModal,
    addProductModalProduct,
    addProductModalLoading,
    addProductModalError,
    autoCalculateSellingPrice,
    hasUserEditedSellingPrice,
    hasManuallyEditedSellingPrice,
    addProductForm,
    imagePreview,
    imageFile,
    skuError,
    isValidatingSku,
    isEditMode,
    isAddProductFormValid,
    openAddProductModal,
    openEditProductModal,
    closeAddProductModal,
    submitProduct,
    initializeAddProductForm,
    validateSKU,
    generateBarcode,
    handleSellingPriceChange,
    handleImageUpload,
    removeImage,
    convertImageToBase64,
    setupAddProductKeyboardListeners,
    cleanupAddProductKeyboardListeners,
    
    // UI: Stock Update Modal
    showStockUpdateModal,
    stockUpdateProduct,
    stockUpdateLoading,
    stockUpdateError,
    stockUpdateForm,
    selectedStockReason,
    newStockPreview,
    stockReasons,
    isStockUpdateFormValid,
    operationDescription,
    openStockUpdateModal,
    closeStockUpdateModal,
    submitStockUpdate,
    initializeStockUpdateForm,
    onStockOperationChange,
    onStockReasonChange,
    calculateNewStock,
    getStockClass,
    getPreviewStockClass,
    getStockSubmitButtonClass,
    getStockSubmitButtonText,
    setupStockUpdateKeyboardListeners,
    cleanupStockUpdateKeyboardListeners,
    
    // UI: View Product Modal
    showViewProductModal,
    viewProductModalProduct,
    stockCardClass,
    thresholdCardClass,
    statusCardClass,
    canGenerateBarcode,
    statusToggleText,
    statusToggleSubtext,
    openViewProductModal,
    closeViewProductModal,
    handleViewProductEdit,
    handleViewProductRestock,
    handleViewProductToggleStatus,
    handleViewProductGenerateBarcode,
    setupViewProductKeyboardListeners,
    cleanupViewProductKeyboardListeners,
    
    // UI: Additional Methods from ui/useProducts
    filteredProductsForUI,
    selectedProducts,
    showAddDropdown,
    searchMode,
    showColumnFilter,
    currentPage,
    itemsPerPage,
    paginatedProducts,
    allSelected,
    someSelected,
    lowStockCount,
    expiringCount,
    visibleColumns,
    categoryFilter,
    stockFilter,
    searchFilter,
    fetchCategories,
    enrichProductsWithCategoryNames,
    fetchReportCounts,
    applyFilters,
    clearFilters,
    refreshData,
    selectAll,
    deleteSelected,
    toggleProductStatus,
    exportData,
    toggleAddDropdown,
    closeAddDropdown,
    toggleSearchMode,
    clearSearch,
    toggleColumnFilter,
    handleColumnChanges,
    handleSingleProduct,
    handleBulkAdd,
    handleImport,
    handlePageChange,
    calculateMargin,
    formatExpiryDate,
    getProductNameClass,
    getRowClass,
    getStockDisplayClass,
    getMarginClass,
    getStatusText,
    getExpiryDateClass,
    isColumnVisible,
    handleClickOutside,
    handleProductSuccess,
    handleStockUpdateSuccess,
    handleImportSuccess,
    handleImportError,
    initializeProductsWithUI,
    cleanupProductsWithUI,
    
    // UI: View Product Helper Methods
    getCategoryName,
    getCategorySlug,
    getStockStatusClass,
    getStockStatusText,
    getStatusBadgeClass,
    getCategoryBadgeClass,
    getExpiryClass,
    getDaysUntilExpiry,
    getProfitMargin,
    getProfitPerUnit,
    formatPrice,
    formatStatus,
    formatDate,
    formatDateTime
  }
}