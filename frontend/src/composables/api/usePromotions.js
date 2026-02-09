// composables/promotions/usePromotions.js
import { ref, computed } from 'vue'
import promotionApiService from '@/services/apiPromotions'
import { useToast } from '@/composables/ui/useToast'

export function usePromotions() {
  const { success: showSuccess, error: showError } = useToast()
  
  // =============================
  // STATE
  // =============================
  const promotions = ref([])
  const loading = ref(false)
  const error = ref(null)
  const selectedPromotions = ref([])

  const pagination = ref({
    current_page: 1,
    total_pages: 1,
    total_items: 0,
    items_per_page: 20
  })

  const filters = ref({
    discountType: 'all',
    status: 'all'
  })

  const searchQuery = ref('')

  // =============================
  // FETCH ACTIVE PROMOS (store use)
  // =============================
  const fetchActivePromotions = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await promotionApiService.getAllPromotions()

      if (response.success && response.promotions) {
        const now = new Date()
        promotions.value = response.promotions.filter(promo => {
          const start = new Date(promo.start_date)
          const end = new Date(promo.end_date)
          return (
            promo.status === 'active' &&
            now >= start &&
            now <= end
          )
        })
      } else {
        promotions.value = []
        console.warn("⚠️ No promotions found in response")
      }

      return promotions.value
    } catch (err) {
      console.error("❌ Error fetching promotions:", err)
      error.value = err.message
      promotions.value = []
      showError("Failed to load promotions")
      return []
    } finally {
      loading.value = false
    }
  }

  // =============================
  // ADMIN PROMOTION FETCH (WITH FILTERS)
  // =============================
  const fetchPromotions = async () => {
    try {
      loading.value = true
      error.value = null

      const params = {
        page: pagination.value.current_page,
        limit: pagination.value.items_per_page
      }

      // Discount type
      if (filters.value.discountType !== 'all') {
        params.type = filters.value.discountType
      }

      // Status
      if (filters.value.status !== 'all') {
        params.status = filters.value.status
      }

      // Target Type
      if (filters.value.targetType !== 'all') {
        params.target_type = filters.value.targetType
      }

      // Search
      if (searchQuery.value.trim()) {
        params.search = searchQuery.value.trim()
      }

      const response = await promotionApiService.getAllPromotions(params)

      if (response.success) {
        promotions.value = response.promotions || []
        pagination.value = response.pagination || pagination.value
      } else {
        error.value = response.message || "Failed to load promotions"
        showError(error.value)
      }

    } catch (err) {
      console.error("❌ Error fetching promotions:", err)
      error.value = err.message
      showError("Failed to load promotions")
    } finally {
      loading.value = false
    }
  }


  // =============================
  // CRUD OPERATIONS
  // =============================
  const deletePromotion = async (promotionId) => {
    return await promotionApiService.deletePromotion(promotionId)
  }

  const deleteMultiplePromotions = async (promotionIds) => {
    return await promotionApiService.deleteMultiplePromotions(promotionIds)
  }

  const activatePromotion = async (promotionId) => {
    return await promotionApiService.activatePromotion(promotionId)
  }

  const deactivatePromotion = async (promotionId) => {
    return await promotionApiService.deactivatePromotion(promotionId)
  }

  // =============================
  // FILTERS + SEARCH MANAGEMENT
  // =============================
  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.current_page = 1
  }

  const setSearchQuery = (query) => {
    searchQuery.value = query
    pagination.value.current_page = 1
  }

  const setPage = (page) => {
    pagination.value.current_page = page
  }

  const clearSelection = () => {
    selectedPromotions.value = []
  }

  // =============================
  // CART USE FUNCTIONS (unchanged)
  // =============================
  const getApplicablePromotion = (product) => {
    if (!product || !promotions.value.length) return null
    
    const now = new Date()
    
    return promotions.value.find(promo => {
      const start = new Date(promo.start_date)
      const end = new Date(promo.end_date)

      if (promo.status !== 'active' || now < start || now > end) return false

      if (promo.target_type === 'all') return true

      if (promo.target_type === 'categories')
        return promo.target_ids.includes(product.category_id)

      return false
    }) || null
  }

  const calculateDiscountedPrice = (originalPrice, promotion) => {
    if (!promotion || !originalPrice) return originalPrice
    
    if (promotion.discount_type === 'percentage')
      return originalPrice * (1 - promotion.discount_value / 100)

    if (promotion.discount_type === 'fixed_amount')
      return Math.max(0, originalPrice - promotion.discount_value)

    return originalPrice
  }

  const formatDiscount = (promotion) => {
    if (!promotion) return ''

    if (promotion.discount_type === 'percentage')
      return `${promotion.discount_value}% OFF`

    if (promotion.discount_type === 'fixed_amount')
      return `₱${promotion.discount_value} OFF`

    if (promotion.discount_type === 'buy_x_get_y')
      return 'BOGO'

    return ''
  }

  // =============================
  // COMPUTED
  // =============================
  const hasSelectedPromotions = computed(
    () => selectedPromotions.value.length > 0
  )

  return {
    promotions,
    loading,
    error,
    pagination,
    filters,
    searchQuery,
    selectedPromotions,

    hasSelectedPromotions,

    fetchPromotions,
    deletePromotion,
    deleteMultiplePromotions,
    activatePromotion,
    deactivatePromotion,
    setFilters,
    setSearchQuery,
    setPage,
    clearSelection,

    fetchActivePromotions,
    getApplicablePromotion,
    calculateDiscountedPrice,
    formatDiscount
  }
}
