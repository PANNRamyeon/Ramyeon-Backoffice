import { ref } from 'vue'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const ADMIN = `${API_BASE}/admin`

function authHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function buildParams(params) {
  const out = {}
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') out[k] = v
  }
  return out
}

// ─── Sales Summary ────────────────────────────────────────────────────────────

export function useSalesSummary() {
  const summary = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchSummary({ startDate, endDate, frequency } = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/sales-summary/`, {
        headers: authHeaders(),
        params: buildParams({ start_date: startDate, end_date: endDate, frequency }),
      })
      summary.value = data
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load sales summary.'
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, error, fetchSummary }
}

// ─── Sales by Item ────────────────────────────────────────────────────────────

export function useSalesByItem() {
  const items = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchSalesByItem({ startDate, endDate, frequency, includeVoided = false } = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/sales-by-item/`, {
        headers: authHeaders(),
        params: buildParams({
          start_date: startDate,
          end_date: endDate,
          frequency,
          include_voided: includeVoided,
        }),
      })
      items.value = Array.isArray(data) ? data : []
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load sales by item.'
    } finally {
      loading.value = false
    }
  }

  return { items, loading, error, fetchSalesByItem }
}

// ─── Top Items ────────────────────────────────────────────────────────────────

export function useTopItems() {
  const topItems = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchTopItems({ startDate, endDate, frequency, limit = 5 } = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/top-items/`, {
        headers: authHeaders(),
        params: buildParams({ start_date: startDate, end_date: endDate, frequency, limit }),
      })
      topItems.value = Array.isArray(data) ? data : []
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load top items.'
    } finally {
      loading.value = false
    }
  }

  return { topItems, loading, error, fetchTopItems }
}

// ─── Sales by Category ────────────────────────────────────────────────────────

export function useSalesByCategory() {
  const categories = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchSalesByCategory({
    startDate,
    endDate,
    frequency,
    includeVoided = false,
    includeTrends = false,
  } = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/sales-by-category/`, {
        headers: authHeaders(),
        params: buildParams({
          start_date: startDate,
          end_date: endDate,
          frequency,
          include_voided: includeVoided,
          include_trends: includeTrends,
        }),
      })
      categories.value = Array.isArray(data) ? data : []
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load sales by category.'
    } finally {
      loading.value = false
    }
  }

  return { categories, loading, error, fetchSalesByCategory }
}

// ─── Top Categories ───────────────────────────────────────────────────────────

export function useTopCategories() {
  const topCategories = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchTopCategories({ startDate, endDate, frequency, limit = 5 } = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/top-categories/`, {
        headers: authHeaders(),
        params: buildParams({ start_date: startDate, end_date: endDate, frequency, limit }),
      })
      topCategories.value = Array.isArray(data) ? data : []
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load top categories.'
    } finally {
      loading.value = false
    }
  }

  return { topCategories, loading, error, fetchTopCategories }
}

// ─── Sales by Period (chart data) ─────────────────────────────────────────────

export function useSalesByPeriod() {
  const periodData = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchSalesByPeriod({ startDate, endDate, periodType = 'daily' } = {}) {
    if (!startDate || !endDate) {
      error.value = 'start_date and end_date are required.'
      return
    }
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(`${ADMIN}/reports/sales-by-period/`, {
        headers: authHeaders(),
        params: { start_date: startDate, end_date: endDate, period_type: periodType },
      })
      periodData.value = data
    } catch (e) {
      error.value = e.response?.data?.error || 'Failed to load period data.'
    } finally {
      loading.value = false
    }
  }

  return { periodData, loading, error, fetchSalesByPeriod }
}

// ─── Category Performance Detail ──────────────────────────────────────────────

export function useCategoryPerformance() {
  const categoryDetail = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchCategoryPerformance(categoryId, { startDate, endDate } = {}) {
    if (!categoryId) return
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.get(
        `${ADMIN}/reports/category-performance/${categoryId}/`,
        {
          headers: authHeaders(),
          params: buildParams({ start_date: startDate, end_date: endDate }),
        },
      )
      categoryDetail.value = data
    } catch (e) {
      if (e.response?.status === 404) {
        categoryDetail.value = null
        error.value = 'No sales data for this category in the selected period.'
      } else {
        error.value = e.response?.data?.error || 'Failed to load category performance.'
      }
    } finally {
      loading.value = false
    }
  }

  return { categoryDetail, loading, error, fetchCategoryPerformance }
}
