import { ref, computed } from 'vue'
import categoryApiService from '../../services/apiCategory.js'
import { useToast } from '../ui/useToast.js'

// Create toast instance
const toast = useToast()

// Global state for categories
const categories = ref([])
const currentCategory = ref(null)
const deletedCategories = ref([])
const subcategories = ref([])

// Loading states
const loading = ref(false)
const subcategoryLoading = ref(false)
const deleteLoading = ref(false)
const moveProductLoading = ref(false)
const bulkMoveLoading = ref(false)

// Error states
const error = ref(null)
const validationErrors = ref([])

// Filters
const filters = ref({
  status: '',
  search: '',
  include_deleted: false
})

export function useCategories() {
  // ================ COMPUTED PROPERTIES ================

  const filteredCategories = computed(() => {
    let result = categories.value

    if (filters.value.search) {
      const searchTerm = filters.value.search.toLowerCase()
      result = result.filter(category =>
        category.category_name?.toLowerCase().includes(searchTerm) ||
        category._id?.toLowerCase().includes(searchTerm) ||
        category.description?.toLowerCase().includes(searchTerm)
      )
    }

    if (filters.value.status) {
      result = result.filter(category => category.status === filters.value.status)
    }

    return result
  })

  const activeCategories = computed(() =>
    categories.value.filter(cat => cat.status === 'active' && !cat.isDeleted)
  )

  // ✅ NEW: total number of active (non-deleted) categories
  const totalActiveCategories = computed(() => activeCategories.value.length)

  const categoryStats = computed(() => ({
    total: categories.value.length,
    active: categories.value.filter(c => c.status === 'active').length,
    inactive: categories.value.filter(c => c.status === 'inactive').length,
    deleted: deletedCategories.value.length
  }))

  const categoriesWithProductCounts = computed(() =>
    categories.value.map(category => ({
      ...category,
      productCount:
        category.sub_categories?.reduce(
          (total, sub) => total + (sub.product_count || 0),
          0
        ) || 0
    }))
  )

  const hasCategories = computed(() => categories.value.length > 0)
  const hasCurrentCategory = computed(() => currentCategory.value !== null)

  // ================ CATEGORY CRUD OPERATIONS ================

  const fetchCategories = async (customFilters = {}) => {
    loading.value = true
    error.value = null

    try {
      const mergedFilters = { ...filters.value, ...customFilters }
      const response = await categoryApiService.CategoryData(mergedFilters)

      categories.value = response.categories || []
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to load categories: ${err.message}`)
      categories.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchCategoryById = async (categoryId, includeDeleted = false) => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.getCategoryById(
        categoryId,
        includeDeleted
      )
      currentCategory.value = response.category
      return response
    } catch (err) {
      error.value = err.message
      currentCategory.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  const createCategory = async categoryData => {
    loading.value = true
    error.value = null
    validationErrors.value = []

    try {
      const response = await categoryApiService.AddCategoryData(categoryData)

      // Add to local state
      categories.value.unshift(response.category)
      currentCategory.value = response.category

      toast.success(`Category "${categoryData.category_name}" created successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to create category: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateCategory = async (categoryId, categoryData) => {
    loading.value = true
    error.value = null
    validationErrors.value = []

    try {
      const response = await categoryApiService.UpdateCategoryData({
        id: categoryId,
        ...categoryData
      })

      // Update local state
      const index = categories.value.findIndex(c => c._id === categoryId)
      if (index !== -1) {
        categories.value[index] = response.category
      }

      if (currentCategory.value?._id === categoryId) {
        currentCategory.value = response.category
      }

      toast.success('Category updated successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to update category: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  const softDeleteCategory = async categoryId => {
    deleteLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.SoftDeleteCategory(categoryId)

      // Move to deleted categories
      const deletedCategory = categories.value.find(c => c._id === categoryId)
      if (deletedCategory) {
        deletedCategory.isDeleted = true
        categories.value = categories.value.filter(c => c._id !== categoryId)
        deletedCategories.value.unshift(deletedCategory)
      }

      if (currentCategory.value?._id === categoryId) {
        currentCategory.value = null
      }

      toast.success('Category deleted successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to delete category: ${err.message}`)
      throw err
    } finally {
      deleteLoading.value = false
    }
  }

  const hardDeleteCategory = async categoryId => {
    deleteLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.HardDeleteCategory(categoryId)

      // Remove from all local state
      categories.value = categories.value.filter(c => c._id !== categoryId)
      deletedCategories.value = deletedCategories.value.filter(
        c => c._id !== categoryId
      )

      if (currentCategory.value?._id === categoryId) {
        currentCategory.value = null
      }

      toast.success('Category permanently deleted')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to delete category: ${err.message}`)
      throw err
    } finally {
      deleteLoading.value = false
    }
  }

  const restoreCategory = async categoryId => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.RestoreCategory(categoryId)

      // Move back to active categories
      const restoredCategory = deletedCategories.value.find(
        c => c._id === categoryId
      )
      if (restoredCategory) {
        restoredCategory.isDeleted = false
        deletedCategories.value = deletedCategories.value.filter(
          c => c._id !== categoryId
        )
        categories.value.unshift(restoredCategory)
      }

      toast.success('Category restored successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to restore category: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ SUBCATEGORY MANAGEMENT ================

  const fetchSubcategories = async categoryId => {
    subcategoryLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.getSubcategories(categoryId)
      subcategories.value = response
      return response
    } catch (err) {
      error.value = err.message
      subcategories.value = []
      throw err
    } finally {
      subcategoryLoading.value = false
    }
  }

  const addSubcategory = async (categoryId, subcategoryData) => {
    subcategoryLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.AddSubCategoryData(
        categoryId,
        subcategoryData
      )

      // Update local category state
      const category = categories.value.find(c => c._id === categoryId)
      if (category && category.sub_categories) {
        category.sub_categories.push(subcategoryData)
      }

      // Refresh subcategories
      await fetchSubcategories(categoryId)

      toast.success(`Subcategory "${subcategoryData.name}" added successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to add subcategory: ${err.message}`)
      throw err
    } finally {
      subcategoryLoading.value = false
    }
  }

  const removeSubcategory = async (categoryId, subcategoryName) => {
    subcategoryLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.RemoveSubCategoryData(
        categoryId,
        subcategoryName
      )

      // Update local category state
      const category = categories.value.find(c => c._id === categoryId)
      if (category && category.sub_categories) {
        category.sub_categories = category.sub_categories.filter(
          sub => sub.name !== subcategoryName
        )
      }

      // Refresh subcategories
      await fetchSubcategories(categoryId)

      toast.success(`Subcategory "${subcategoryName}" removed successfully`)
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to remove subcategory: ${err.message}`)
      throw err
    } finally {
      subcategoryLoading.value = false
    }
  }

  // ================ PRODUCT-CATEGORY RELATIONSHIP MANAGEMENT ================

  const moveProductToCategory = async (
    productId,
    newCategoryId,
    newSubcategoryName = null
  ) => {
    moveProductLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.MoveProductToCategory({
        product_id: productId,
        new_category_id: newCategoryId,
        new_subcategory_name: newSubcategoryName
      })

      toast.success('Product moved to different category successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move product: ${err.message}`)
      throw err
    } finally {
      moveProductLoading.value = false
    }
  }

  const bulkMoveProductsToCategory = async (
    productIds,
    newCategoryId,
    newSubcategoryName = null
  ) => {
    bulkMoveLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.BulkMoveProductsToCategory({
        product_ids: productIds,
        new_category_id: newCategoryId,
        new_subcategory_name: newSubcategoryName
      })

      toast.success(
        `${response.moved_count || productIds.length} products moved successfully`
      )
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move products: ${err.message}`)
      throw err
    } finally {
      bulkMoveLoading.value = false
    }
  }

  const moveProductToUncategorized = async productId => {
    moveProductLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.MoveProductToUncategorized({
        product_id: productId
      })

      toast.success('Product moved to Uncategorized successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move product to Uncategorized: ${err.message}`)
      throw err
    } finally {
      moveProductLoading.value = false
    }
  }

  const bulkMoveProductsToUncategorized = async productIds => {
    bulkMoveLoading.value = true
    error.value = null

    try {
      const response = await categoryApiService.BulkMoveProductsToUncategorized({
        product_ids: productIds
      })

      toast.success(
        `${response.moved_count || productIds.length} products moved to Uncategorized`
      )
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Failed to move products to Uncategorized: ${err.message}`)
      throw err
    } finally {
      bulkMoveLoading.value = false
    }
  }

  // ================ CATEGORY DATA AND ANALYTICS ================

  const getCategoryStats = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.GetCategoryStats()
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const getCategoryDeleteInfo = async categoryId => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.GetCategoryDeleteInfo(categoryId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const getUncategorizedCategory = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.GetUncategorizedCategory()
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ PRODUCTS IN CATEGORIES ================

  const fetchProductsByCategory = async (categoryId, subcategoryName = null) => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.FindProdcategory({
        id: categoryId,
        subcategory_name: subcategoryName
      })

      // ✅ FIXED: Return the products array directly
      return response.products || response || []
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ EXPORT FUNCTIONALITY ================

  const exportCategories = async (categoriesToExport = null) => {
    loading.value = true
    error.value = null

    try {
      const exportCategories = categoriesToExport || categories.value
      const response = await categoryApiService.ExportCategoryData({
        categories: exportCategories
      })

      toast.success('Categories exported successfully')
      return response
    } catch (err) {
      error.value = err.message
      toast.error(`Export failed: ${err.message}`)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ SEARCH AND FILTERING ================

  const searchCategories = async query => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.CategoryData({
        search: query,
        ...filters.value
      })

      categories.value = response.categories || []
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // ================ UTILITY METHODS ================

  const clearError = () => {
    error.value = null
    validationErrors.value = []
  }

  const clearCurrentCategory = () => {
    currentCategory.value = null
  }

  const setFilters = newFilters => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const resetFilters = () => {
    filters.value = {
      status: '',
      search: '',
      include_deleted: false
    }
  }

  const validateCategoryData = categoryData => {
    const errors = []

    if (!categoryData.category_name?.trim()) {
      errors.push('Category name is required')
    }

    if (categoryData.sub_categories) {
      categoryData.sub_categories.forEach((sub, index) => {
        if (!sub.name?.trim()) {
          errors.push(`Subcategory ${index + 1} name is required`)
        }
      })
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  }

  // ================ INITIALIZATION ================

  const initializeCategories = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await categoryApiService.CategoryData(filters.value)
      categories.value = response.categories || []
      return response
    } catch (err) {
      error.value = err.message
      categories.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    categories,
    currentCategory,
    deletedCategories,
    subcategories,
    filters,
    error,
    validationErrors,
    loading,
    subcategoryLoading,
    deleteLoading,
    moveProductLoading,
    bulkMoveLoading,

    // Computed
    filteredCategories,
    activeCategories,
    totalActiveCategories, // ✅ Added
    categoryStats,
    categoriesWithProductCounts,
    hasCategories,
    hasCurrentCategory,

    // Category CRUD
    fetchCategories,
    fetchCategoryById,
    createCategory,
    updateCategory,
    softDeleteCategory,
    hardDeleteCategory,
    restoreCategory,

    // Subcategory Management
    fetchSubcategories,
    addSubcategory,
    removeSubcategory,

    // Product-Category Management
    moveProductToCategory,
    bulkMoveProductsToCategory,
    moveProductToUncategorized,
    bulkMoveProductsToUncategorized,

    // Analytics and Data
    getCategoryStats,
    getCategoryDeleteInfo,
    getUncategorizedCategory,
    fetchProductsByCategory,

    // Export
    exportCategories,

    // Search and Filter
    searchCategories,

    // Utilities
    clearError,
    clearCurrentCategory,
    setFilters,
    resetFilters,
    validateCategoryData,
    initializeCategories
  }
}
