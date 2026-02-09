import { ref, computed, reactive, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { useToast } from '@/composables/ui/useToast'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Shared axios instance with auth token
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token =
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token') ||
    localStorage.getItem('authToken') ||
    sessionStorage.getItem('authToken')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function useSuppliers() {
  const { success: showSuccess, error: showError } = useToast()

  // Core state
  const suppliers = ref([])
  const allBatches = ref([])
  const loading = ref(false)
  const error = ref(null)
  const successMessage = ref(null)
  const selectedSuppliers = ref([])
  const pagination = ref({
    current_page: 1,
    per_page: 50,
    total_count: 0,
    total_pages: 1
  })

  // Filters
  const filters = reactive({
    type: 'all',
    status: 'all',
    order: 'all',
    search: ''
  })

  // Report data (from main suppliers composable)
  const reportData = reactive({
    activeOrdersCount: 0,
    topSuppliersCount: 0
  })

  // ---------- Helpers reused across modules ----------
  const getReceiptStatus = (batches) => {
    if (!batches || batches.length === 0) return 'Unknown'
    const allPending = batches.every(b => b.status === 'pending')
    const allActive = batches.every(b => b.status === 'active')
    const allInactive = batches.every(b => b.status === 'inactive')
    const hasPending = batches.some(b => b.status === 'pending')
    if (allPending) return 'Pending Delivery'
    if (allActive) return 'Received'
    if (allInactive) return 'Depleted'
    if (hasPending) return 'Partially Received'
    return 'Mixed Status'
  }

  const calculatePurchaseOrdersCount = (batches) => {
    if (!batches || !Array.isArray(batches) || batches.length === 0) return 0
    const batchesByDate = {}
    batches.forEach(batch => {
      let dateKey
      if (batch.date_received) {
        dateKey = typeof batch.date_received === 'string'
          ? batch.date_received.split('T')[0]
          : new Date(batch.date_received).toISOString().split('T')[0]
      } else if (batch.expected_delivery_date) {
        dateKey = typeof batch.expected_delivery_date === 'string'
          ? batch.expected_delivery_date.split('T')[0]
          : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
      } else {
        dateKey = batch.created_at.split('T')[0]
      }
      if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
      batchesByDate[dateKey].push(batch)
    })
    return Object.keys(batchesByDate).length
  }

  const getActiveOrdersCount = (batches) => {
    if (!batches || batches.length === 0) return 0
    const batchesByDate = {}
    batches.forEach(batch => {
      let dateKey
      if (batch.date_received) {
        dateKey = typeof batch.date_received === 'string'
          ? batch.date_received.split('T')[0]
          : new Date(batch.date_received).toISOString().split('T')[0]
      } else if (batch.expected_delivery_date) {
        dateKey = typeof batch.expected_delivery_date === 'string'
          ? batch.expected_delivery_date.split('T')[0]
          : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
      } else {
        dateKey = batch.created_at.split('T')[0]
      }
      if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
      batchesByDate[dateKey].push(batch)
    })
    const orders = Object.entries(batchesByDate).map(([, grouped]) => ({
      status: getReceiptStatus(grouped)
    }))
    return orders.filter(o =>
      o.status === 'Pending Delivery' || o.status === 'Partially Received'
    ).length
  }

  const getTotalSpent = (batches) => {
    if (!batches || batches.length === 0) return 0
    const batchesByDate = {}
    batches.forEach(batch => {
      let dateKey
      if (batch.date_received) {
        dateKey = typeof batch.date_received === 'string'
          ? batch.date_received.split('T')[0]
          : new Date(batch.date_received).toISOString().split('T')[0]
      } else if (batch.expected_delivery_date) {
        dateKey = typeof batch.expected_delivery_date === 'string'
          ? batch.expected_delivery_date.split('T')[0]
          : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
      } else {
        dateKey = batch.created_at.split('T')[0]
      }
      if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
      batchesByDate[dateKey].push(batch)
    })
    const orders = Object.entries(batchesByDate).map(([, grouped]) => ({
      status: getReceiptStatus(grouped),
      total: grouped.reduce(
        (sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)),
        0
      )
    }))
    return orders
      .filter(order => order.status === 'Received')
      .reduce((total, order) => total + order.total, 0)
  }

  const getDaysActive = (createdAt) => {
    if (!createdAt) return 0
    const createdDate = new Date(createdAt)
    const today = new Date()
    const diffTime = Math.abs(today - createdDate)
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  }

  // ---------- Core Suppliers list ----------
  const transformSupplier = (backendSupplier, batchesCount = 0, supplierBatches = []) => {
    const activeOrders = getActiveOrdersCount(supplierBatches)
    const totalSpent = getTotalSpent(supplierBatches)
    const daysActive = getDaysActive(backendSupplier.created_at)
    return {
      id: backendSupplier._id,
      name: backendSupplier.supplier_name,
      email: backendSupplier.email || '',
      phone: backendSupplier.phone_number || '',
      address: backendSupplier.address || '',
      contactPerson: backendSupplier.contact_person || '',
      purchaseOrders: batchesCount,
      activeOrders,
      totalSpent,
      daysActive,
      status: backendSupplier.isDeleted ? 'inactive' : 'active',
      type: backendSupplier.type || 'food',
      isFavorite: backendSupplier.isFavorite || false,
      createdAt: backendSupplier.created_at,
      updatedAt: backendSupplier.updated_at,
      raw: backendSupplier
    }
  }

  const filteredSuppliers = computed(() => {
    let filtered = [...suppliers.value]
    if (filters.type !== 'all') filtered = filtered.filter(s => s.type === filters.type)
    if (filters.status !== 'all') filtered = filtered.filter(s => s.status === filters.status)
    if (filters.order !== 'all') {
      if (filters.order === 'high') filtered = filtered.filter(s => s.purchaseOrders >= 10)
      else if (filters.order === 'medium')
        filtered = filtered.filter(s => s.purchaseOrders >= 5 && s.purchaseOrders < 10)
      else if (filters.order === 'low')
        filtered = filtered.filter(s => s.purchaseOrders >= 1 && s.purchaseOrders < 5)
      else if (filters.order === 'none')
        filtered = filtered.filter(s => s.purchaseOrders === 0)
    }
    if (filters.search.trim()) {
      const search = filters.search.toLowerCase()
      filtered = filtered.filter(s =>
        s.name?.toLowerCase().includes(search) ||
        s.email?.toLowerCase().includes(search) ||
        s.phone?.includes(search) ||
        s.contactPerson?.toLowerCase().includes(search)
      )
    }
    filtered.sort((a, b) => {
      if (a.isFavorite && !b.isFavorite) return -1
      if (!a.isFavorite && b.isFavorite) return 1
      return (a.name || '').localeCompare(b.name || '')
    })
    return filtered
  })

  const fetchSuppliers = async (page = 1) => {
    loading.value = true
    error.value = null
    try {
      const params = { page, per_page: pagination.value.per_page }
      if (filters.search.trim()) params.search = filters.search.trim()

      const response = await api.get('/suppliers/', { params })
      const backendSuppliers = response.data.suppliers

      let fetchedBatches = []
      try {
        const batchesResponse = await api.get('/batches/', { params: { per_page: 1000 } })
        if (batchesResponse.data?.success && Array.isArray(batchesResponse.data.data)) {
          fetchedBatches = batchesResponse.data.data
        } else if (Array.isArray(batchesResponse.data)) {
          fetchedBatches = batchesResponse.data
        } else if (Array.isArray(batchesResponse.data?.batches)) {
          fetchedBatches = batchesResponse.data.batches
        }
      } catch (batchesError) {
        console.warn('Failed to fetch batches:', batchesError)
      }

      // Build products map (best-effort)
      let productsMap = {}
      try {
        let allProducts = []
        let currentPage = 1
        let hasMore = true
        const perPage = 1000
        while (hasMore) {
          const productsResponse = await api.get('/products/', { params: { page: currentPage, per_page: perPage } })
          const payload = productsResponse.data?.products || productsResponse.data?.data || productsResponse.data
          if (Array.isArray(payload)) {
            allProducts = allProducts.concat(payload)
            const paginationInfo = productsResponse.data?.pagination
            hasMore = paginationInfo ? currentPage < paginationInfo.total_pages : payload.length === perPage
            currentPage++
          } else {
            hasMore = false
          }
        }
        allProducts.forEach(product => {
          const productId = product._id || product.id
          if (!productId) return
          productsMap[productId] = {
            name: product.product_name || product.name || 'Unknown Product',
            categoryId: product.category_id || '',
            categoryName: product.category_name || '',
            subcategoryName: product.subcategory_name || ''
          }
        })
      } catch (productsError) {
        console.error('[useSuppliers] Failed to fetch products for enrichment:', productsError)
      }

      // Enrich batches
      const batchesWithMissingNames = []
      fetchedBatches = fetchedBatches.map(batch => {
        const productId = batch.product_id
        const productInfo = productId ? productsMap[productId] : null
        let productName = batch.product_name || batch.name
        if (!productName && productInfo) productName = productInfo.name
        if (!productName && productId) {
          productName = 'Unknown Product'
          batchesWithMissingNames.push({ batch_id: batch._id, product_id: productId })
        }
        if (!productName) productName = 'Unknown Product'
        return {
          ...batch,
          product_name: productName,
          name: productName,
          category_id: batch.category_id || productInfo?.categoryId || '',
          category_name: batch.category_name || productInfo?.categoryName || '',
          subcategory_name: batch.subcategory_name || productInfo?.subcategoryName || ''
        }
      })
      if (batchesWithMissingNames.length > 0) {
        console.warn(`[useSuppliers] ${batchesWithMissingNames.length} batches missing product names`)
      }

      allBatches.value = fetchedBatches
      const batchesBySupplier = {}
      fetchedBatches.forEach(batch => {
        const supplierId = batch.supplier_id
        if (supplierId) {
          if (!batchesBySupplier[supplierId]) batchesBySupplier[supplierId] = []
          batchesBySupplier[supplierId].push(batch)
        }
      })

      suppliers.value = backendSuppliers.map(backendSupplier => {
        const supplierBatches = batchesBySupplier[backendSupplier._id] || []
        const purchaseOrdersCount = calculatePurchaseOrdersCount(supplierBatches)
        return transformSupplier(backendSupplier, purchaseOrdersCount, supplierBatches)
      })
      pagination.value = response.data.pagination
      updateReportData()
    } catch (err) {
      console.error('Error fetching suppliers:', err)
      if (err.response) {
        error.value = err.response.data.error || `Failed to load suppliers: ${err.response.statusText}`
      } else if (err.request) {
        error.value = 'Cannot connect to server. Please check your connection.'
      } else {
        error.value = `Failed to load suppliers: ${err.message}`
      }
    } finally {
      loading.value = false
    }
  }

  const addSupplier = async (supplierData) => {
    loading.value = true
    error.value = null
    try {
      const backendData = {
        supplier_name: supplierData.name,
        email: supplierData.email,
        phone_number: supplierData.phone,
        address: supplierData.address,
        contact_person: supplierData.contactPerson,
        type: supplierData.type || 'food'
      }
      const response = await api.post('/suppliers/', backendData)
      const newSupplier = transformSupplier(response.data, 0, [])
      suppliers.value.unshift(newSupplier)
      const message = `Supplier "${newSupplier.name}" added successfully`
      successMessage.value = message
      setTimeout(() => { successMessage.value = null }, 3000)
      showSuccess(message)
      return { success: true, supplier: newSupplier }
    } catch (err) {
      console.error('Error adding supplier:', err)
      const errorMessage = err.response?.data?.error || 'Failed to add supplier'
      error.value = errorMessage
      showError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  const updateSupplier = async (supplierId, supplierData) => {
    loading.value = true
    error.value = null
    try {
      const backendData = {
        supplier_name: supplierData.name,
        email: supplierData.email,
        phone_number: supplierData.phone,
        address: supplierData.address,
        contact_person: supplierData.contactPerson,
        type: supplierData.type
      }
      const response = await api.put(`/suppliers/${supplierId}/`, backendData)
      const updatedSupplier = transformSupplier(response.data, 0, [])
      const index = suppliers.value.findIndex(s => s.id === supplierId)
      if (index !== -1) suppliers.value[index] = updatedSupplier
      const message = `Supplier "${updatedSupplier.name}" updated successfully`
      successMessage.value = message
      setTimeout(() => { successMessage.value = null }, 3000)
      showSuccess(message)
      return { success: true, supplier: updatedSupplier }
    } catch (err) {
      console.error('Error updating supplier:', err)
      const errorMessage = err.response?.data?.error || 'Failed to update supplier'
      error.value = errorMessage
      showError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  const toggleFavorite = async (supplier) => {
    const previous = supplier.isFavorite
    supplier.isFavorite = !supplier.isFavorite
    try {
      await api.put(`/suppliers/${supplier.id}/`, { isFavorite: supplier.isFavorite })
      const idx = suppliers.value.findIndex(s => s.id === supplier.id)
      if (idx !== -1) suppliers.value[idx].isFavorite = supplier.isFavorite
      return { success: true }
    } catch (err) {
      supplier.isFavorite = previous
      console.error('Error updating favorite status:', err)
      const errorMessage = err.response?.data?.error || 'Failed to update favorite status'
      error.value = errorMessage
      return { success: false, error: errorMessage }
    }
  }

  const deleteSupplier = async (supplier) => {
    const confirmed = confirm(`Are you sure you want to delete "${supplier.name}"?`)
    if (!confirmed) return { success: false, cancelled: true }
    loading.value = true
    error.value = null
    try {
      await api.delete(`/suppliers/${supplier.id}/`)
      suppliers.value = suppliers.value.filter(s => s.id !== supplier.id)
      const message = `Supplier "${supplier.name}" deleted successfully`
      successMessage.value = message
      setTimeout(() => { successMessage.value = null }, 3000)
      showSuccess(message)
      return { success: true }
    } catch (err) {
      console.error('Error deleting supplier:', err)
      const errorMessage = err.response?.data?.error || 'Failed to delete supplier'
      error.value = errorMessage
      showError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  const deleteSelected = async () => {
    if (selectedSuppliers.value.length === 0) return
    const confirmed = confirm(`Are you sure you want to delete ${selectedSuppliers.value.length} supplier(s)?`)
    if (!confirmed) return
    loading.value = true
    error.value = null
    try {
      const deletePromises = selectedSuppliers.value.map(id => api.delete(`/suppliers/${id}/`))
      await Promise.all(deletePromises)
      suppliers.value = suppliers.value.filter(s => !selectedSuppliers.value.includes(s.id))
      const count = selectedSuppliers.value.length
      selectedSuppliers.value = []
      const message = `Successfully deleted ${count} supplier(s)`
      successMessage.value = message
      setTimeout(() => { successMessage.value = null }, 3000)
      showSuccess(message)
      return { success: true }
    } catch (err) {
      console.error('Error deleting suppliers:', err)
      const errorMessage = err.response?.data?.error || 'Failed to delete some suppliers'
      error.value = errorMessage
      showError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      loading.value = false
    }
  }

  const updateReportData = () => {
    reportData.activeOrdersCount = suppliers.value.filter(
      s => s.purchaseOrders > 0 && s.status === 'active'
    ).length
    reportData.topSuppliersCount = suppliers.value.filter(
      s => s.purchaseOrders >= 10
    ).length
  }

  const clearFilters = () => {
    filters.type = 'all'
    filters.status = 'all'
    filters.order = 'all'
    filters.search = ''
  }

  const applyFilters = () => {
    updateReportData()
  }

  const refreshData = async () => {
    try {
      successMessage.value = null
      error.value = null
      await fetchSuppliers(pagination.value?.current_page || 1)
    } catch (err) {
      console.error('Error refreshing data:', err)
      error.value = err.message || 'Failed to refresh data'
    }
  }

  // Utilities
  const getStatusBadgeClass = (status) => {
    const classes = { active: 'text-bg-success', inactive: 'text-bg-danger', pending: 'text-bg-warning' }
    return classes[status] || 'text-bg-secondary'
  }

  const formatStatus = (status) => status.charAt(0).toUpperCase() + status.slice(1)

  const getShortAddress = (address) => {
    if (!address) return 'No address'
    return address.length > 50 ? `${address.substring(0, 50)}...` : address
  }

  // ---------- Bulk Suppliers Modal ----------
  const showBulkModal = ref(false)
  const openBulkModal = () => { showBulkModal.value = true }
  const closeBulkModal = () => { showBulkModal.value = false }
  const handleBulkSave = (newSuppliers, existingSuppliers) => {
    newSuppliers.forEach(supplier => existingSuppliers.push(supplier))
    closeBulkModal()
    return {
      success: true,
      message: `Successfully added ${newSuppliers.length} supplier(s)`,
      count: newSuppliers.length
    }
  }

  // ---------- Create Order Modal ----------
  const showCreateOrderModal = ref(false)
  const selectedSupplierForOrder = ref(null)
  const orderLoading = ref(false)
  const orderError = ref(null)

  const openCreateOrderModal = (supplier) => {
    selectedSupplierForOrder.value = supplier
    showCreateOrderModal.value = true
  }
  const closeCreateOrderModal = () => {
    showCreateOrderModal.value = false
    selectedSupplierForOrder.value = null
    orderError.value = null
  }
  const handleOrderSave = async (orderData) => {
    orderLoading.value = true
    orderError.value = null
    try {
      if (!selectedSupplierForOrder.value?.id) throw new Error('No supplier selected')
      const supplierName = selectedSupplierForOrder.value.name
      const supplierId = selectedSupplierForOrder.value.id
      const backendOrderData = {
        order_id: orderData.id || orderData.orderId,
        status: orderData.status || 'pending',
        order_date: orderData.orderDate || new Date().toISOString(),
        expected_delivery_date: orderData.expectedDate,
        priority: orderData.priority || 'normal',
        description: orderData.description || '',
        notes: orderData.notes || '',
        shipping_cost: orderData.shippingCost || 0,
        tax_rate: 12,
        subtotal: orderData.subtotal,
        tax_amount: orderData.tax,
        total_cost: orderData.total,
        items: orderData.items.map((item, index) => ({
          product_id: item.productId || `TEMP-${Date.now()}-${index}`,
          product_name: item.name,
          quantity: item.quantity,
          unit: item.unit || 'pcs',
          unit_price: item.unitPrice || 0,
          notes: item.notes || ''
        }))
      }
      const response = await api.post(`/suppliers/${supplierId}/orders/`, backendOrderData)
      closeCreateOrderModal()
      return {
        success: true,
        message: `Purchase order ${orderData.id} created successfully for ${supplierName}`,
        orderId: orderData.id,
        total: orderData.total,
        data: response.data
      }
    } catch (err) {
      console.error('Error creating order:', err)
      let errorMessage = 'Failed to create purchase order'
      if (err.response?.data?.error) errorMessage = err.response.data.error
      else if (err.message) errorMessage = err.message
      orderError.value = errorMessage
      return { success: false, error: errorMessage }
    } finally {
      orderLoading.value = false
    }
  }

  // ---------- Dropdown helper ----------
  const showDropdown = ref(false)
  const dropdownRef = ref(null)
  const toggleDropdown = (event) => {
    event?.stopPropagation()
    showDropdown.value = !showDropdown.value
  }
  const closeDropdown = () => { showDropdown.value = false }
  const handleDropdownClickOutside = (event) => {
    if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
      showDropdown.value = false
    }
  }
  onMounted(() => {
    document.addEventListener('click', handleDropdownClickOutside)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('click', handleDropdownClickOutside)
  })

  // ---------- Export Modal ----------
  const showExportModal = ref(false)
  const selectedExportFormat = ref('')
  const exportOptions = reactive({ includeInactive: false, includeDetails: true })
  const openExportModal = () => { showExportModal.value = true }
  const closeExportModal = () => {
    showExportModal.value = false
    selectedExportFormat.value = ''
  }
  const handleExport = (suppliersList) => {
    if (!selectedExportFormat.value) return
    try {
      const exportData = exportOptions.includeInactive
        ? suppliersList
        : suppliersList.filter(s => s.status === 'active')
      const headers = ['Name', 'Email', 'Phone', 'Address', 'Status', 'Purchase Orders', 'Type']
      const csvContent = [
        headers.join(','),
        ...exportData.map(supplier => [
          `"${supplier.name}"`,
          supplier.email || '',
          supplier.phone || '',
          `"${supplier.address || ''}"`,
          supplier.status,
          supplier.purchaseOrders,
          supplier.type || ''
        ].join(','))
      ].join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `suppliers_${new Date().toISOString().split('T')[0]}.${selectedExportFormat.value}`
      a.click()
      window.URL.revokeObjectURL(url)
      closeExportModal()
      return { success: true, message: `Suppliers exported successfully as ${selectedExportFormat.value.toUpperCase()}` }
    } catch (err) {
      console.error('Error exporting suppliers:', err)
      return { success: false, error: `Failed to export suppliers: ${err.message}` }
    }
  }

  // ---------- Import Suppliers Modal ----------
  const showImportModal = ref(false)
  const openImportModal = () => { showImportModal.value = true }
  const closeImportModal = () => { showImportModal.value = false }
  const handleImportSave = (importedSuppliers, existingSuppliers) => {
    importedSuppliers.forEach(supplier => existingSuppliers.push(supplier))
    closeImportModal()
    return {
      success: true,
      message: `Successfully imported ${importedSuppliers.length} supplier(s) from file`,
      count: importedSuppliers.length
    }
  }

  // ---------- Orders History (from useOrdersHistory) ----------
  const ordersHistoryLoading = ref(false)
  const ordersHistoryError = ref(null)
  const ordersHistorySuppliers = ref([])
  const ordersHistoryFilters = ref({
    status: 'all',
    supplier: 'all',
    dateRange: 'all',
    search: ''
  })

  const ordersHistoryAllOrders = computed(() => {
    const orders = []
    ordersHistorySuppliers.value.forEach(supplier => {
      const supplierBatches = supplier.batches || []
      if (supplierBatches.length > 0) {
        const batchesByDate = {}
        supplierBatches.forEach(batch => {
          let dateKey
          if (batch.date_received) {
            dateKey = typeof batch.date_received === 'string'
              ? batch.date_received.split('T')[0]
              : new Date(batch.date_received).toISOString().split('T')[0]
          } else if (batch.expected_delivery_date) {
            dateKey = typeof batch.expected_delivery_date === 'string'
              ? batch.expected_delivery_date.split('T')[0]
              : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
          } else {
            dateKey = batch.created_at.split('T')[0]
          }
          if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
          batchesByDate[dateKey].push(batch)
        })
        Object.entries(batchesByDate).forEach(([date, batches]) => {
          const totalCost = batches.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0)
          const orderStatus = getReceiptStatus(batches)
          let receiptId = `SR-${date.replace(/-/g, '')}`
          const firstBatchNotes = batches[0].notes || ''
          const receiptMatch = firstBatchNotes.match(/Receipt:\s*([^\|]+)/)
          if (receiptMatch) receiptId = receiptMatch[1].trim()
          const firstBatch = batches[0]
          const expectedDate = firstBatch.expected_delivery_date
            ? (typeof firstBatch.expected_delivery_date === 'string'
              ? firstBatch.expected_delivery_date.split('T')[0]
              : new Date(firstBatch.expected_delivery_date).toISOString().split('T')[0])
            : date
          const receivedDate = firstBatch.date_received
            ? (typeof firstBatch.date_received === 'string'
              ? firstBatch.date_received.split('T')[0]
              : new Date(firstBatch.date_received).toISOString().split('T')[0])
            : null
          orders.push({
            id: receiptId,
            supplier: supplier.supplier_name,
            supplierEmail: supplier.email || 'N/A',
            supplierId: supplier._id,
            orderDate: firstBatch.created_at ? firstBatch.created_at.split('T')[0] : date,
            expectedDelivery: expectedDate,
            deliveredDate: receivedDate,
            totalAmount: totalCost,
            status: orderStatus,
            items: batches.map(batch => ({
              name: batch.product_name || batch.name || 'Unknown Product',
              product_name: batch.product_name || 'Unknown Product',
              product_id: batch.product_id,
              quantity: batch.quantity_received,
              unitPrice: batch.cost_price || 0,
              totalPrice: (batch.cost_price || 0) * (batch.quantity_received || 0),
              batchNumber: batch.batch_number,
              batchId: batch._id,
              expiryDate: batch.expiry_date,
              quantityRemaining: batch.quantity_remaining
            })),
            description: `Stock receipt with ${batches.length} item(s)`,
            notes: firstBatchNotes
          })
        })
      }
    })
    return orders.sort((a, b) => new Date(b.orderDate) - new Date(a.orderDate))
  })

  const ordersHistorySupplierOptions = computed(() => {
    const uniqueNames = new Set()
    const options = []
    ordersHistorySuppliers.value.forEach(supplier => {
      const name = supplier.supplier_name || supplier.name
      if (name && !uniqueNames.has(name)) {
        uniqueNames.add(name)
        options.push({ value: name, label: name, email: supplier.email || '' })
      }
    })
    return options.sort((a, b) => a.label.localeCompare(b.label))
  })

  const ordersHistoryFilteredOrders = computed(() => {
    let filtered = [...ordersHistoryAllOrders.value]
    if (ordersHistoryFilters.value.status !== 'all') {
      const statusMap = {
        pending_delivery: 'Pending Delivery',
        partially_received: 'Partially Received',
        received: 'Received',
        depleted: 'Depleted',
        mixed_status: 'Mixed Status'
      }
      const targetStatus = statusMap[ordersHistoryFilters.value.status]
      if (targetStatus) filtered = filtered.filter(order => order.status === targetStatus)
    }
    if (ordersHistoryFilters.value.supplier !== 'all') {
      filtered = filtered.filter(order => order.supplier === ordersHistoryFilters.value.supplier)
    }
    if (ordersHistoryFilters.value.dateRange !== 'all') {
      const now = new Date()
      const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      let startDate
      switch (ordersHistoryFilters.value.dateRange) {
        case 'today': startDate = startOfDay; break
        case 'week': startDate = new Date(startOfDay.getTime() - 7 * 24 * 60 * 60 * 1000); break
        case 'month': startDate = new Date(startOfDay.getFullYear(), startOfDay.getMonth(), 1); break
        case 'quarter':
          const quarter = Math.floor(startOfDay.getMonth() / 3)
          startDate = new Date(startOfDay.getFullYear(), quarter * 3, 1)
          break
      }
      if (startDate) filtered = filtered.filter(order => new Date(order.orderDate) >= startDate)
    }
    if (ordersHistoryFilters.value.search.trim()) {
      const search = ordersHistoryFilters.value.search.toLowerCase()
      filtered = filtered.filter(order =>
        order.id.toLowerCase().includes(search) ||
        order.supplier.toLowerCase().includes(search) ||
        order.supplierEmail.toLowerCase().includes(search) ||
        order.items?.some(item => item.name.toLowerCase().includes(search))
      )
    }
    return filtered
  })

  const ordersHistoryTotalOrders = computed(() => ordersHistoryAllOrders.value.length)
  const ordersHistoryActiveOrdersCount = computed(() =>
    ordersHistoryAllOrders.value.filter(order =>
      ['Pending Delivery', 'Partially Received'].includes(order.status)
    ).length
  )
  const ordersHistoryDeliveredOrdersCount = computed(() =>
    ordersHistoryAllOrders.value.filter(order => order.status === 'Received').length
  )
  const ordersHistoryCancelledOrdersCount = computed(() =>
    ordersHistoryAllOrders.value.filter(order => order.status === 'Depleted').length
  )
  const ordersHistoryTotalOrderValue = computed(() =>
    ordersHistoryAllOrders.value.reduce((sum, order) => sum + order.totalAmount, 0)
  )
  const ordersHistoryAverageOrderValue = computed(() => {
    if (ordersHistoryAllOrders.value.length === 0) return 0
    return Math.round(ordersHistoryTotalOrderValue.value / ordersHistoryAllOrders.value.length)
  })

  const fetchOrders = async () => {
    ordersHistoryLoading.value = true
    ordersHistoryError.value = null
    try {
      const response = await api.get('/suppliers/', { params: { per_page: 1000 } })
      const backendSuppliers = response.data.suppliers
      let allBatchesForOrders = []
      try {
        const batchesResponse = await api.get('/batches/', { params: { per_page: 1000 } })
        if (batchesResponse.data?.success && Array.isArray(batchesResponse.data.data)) {
          allBatchesForOrders = batchesResponse.data.data
        } else if (Array.isArray(batchesResponse.data)) {
          allBatchesForOrders = batchesResponse.data
        } else if (Array.isArray(batchesResponse.data?.batches)) {
          allBatchesForOrders = batchesResponse.data.batches
        }
      } catch (batchesError) {
        console.warn('Failed to fetch batches for orders history:', batchesError)
        allBatchesForOrders = []
      }
      const batchesBySupplier = {}
      allBatchesForOrders.forEach(batch => {
        const supplierId = batch.supplier_id
        if (supplierId) {
          if (!batchesBySupplier[supplierId]) batchesBySupplier[supplierId] = []
          batchesBySupplier[supplierId].push(batch)
        }
      })
      ordersHistorySuppliers.value = backendSuppliers.map(supplier => ({
        ...supplier,
        batches: batchesBySupplier[supplier._id] || []
      }))
    } catch (err) {
      ordersHistoryError.value = err.response?.data?.error || 'Failed to fetch orders history'
      console.error('Error fetching orders history:', err)
    } finally {
      ordersHistoryLoading.value = false
    }
  }

  const applyOrdersFilters = () => {}
  const clearOrdersFilters = () => {
    ordersHistoryFilters.value = {
      status: 'all',
      supplier: 'all',
      dateRange: 'all',
      search: ''
    }
  }

  const exportOrdersData = (format = 'csv') => {
    const exportData = ordersHistoryFilteredOrders.value.map(order => ({
      'Order ID': order.id,
      'Supplier': order.supplier,
      'Supplier Email': order.supplierEmail,
      'Status': order.status,
      'Order Date': order.orderDate,
      'Expected Delivery': order.expectedDelivery,
      'Total Amount': order.totalAmount,
      'Items Count': order.items?.length || 0
    }))
    if (format === 'csv') {
      const headers = Object.keys(exportData[0] || {}).join(',')
      const rows = exportData.map(row => Object.values(row).join(','))
      const csvContent = [headers, ...rows].join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `orders_history_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    }
    return exportData
  }

  // ---------- Supplier Form ----------
  const showAddModal = ref(false)
  const isEditMode = ref(false)
  const formLoading = ref(false)
  const selectedSupplierForm = ref(null)
  const addAnotherAfterSave = ref(false)
  const formData = reactive({
    name: '',
    contactPerson: '',
    email: '',
    phone: '',
    address: '',
    type: '',
    status: 'active',
    notes: ''
  })
  const formErrors = ref({})
  const isFormValid = computed(() => formData.name.trim() !== '' && Object.keys(formErrors.value).length === 0)

  const resetForm = () => {
    formData.name = ''
    formData.contactPerson = ''
    formData.email = ''
    formData.phone = ''
    formData.address = ''
    formData.type = ''
    formData.status = 'active'
    formData.notes = ''
    formErrors.value = {}
    addAnotherAfterSave.value = false
  }

  const showAddSupplierModal = () => {
    isEditMode.value = false
    selectedSupplierForm.value = null
    resetForm()
    showAddModal.value = true
  }

  const editSupplierForm = (supplier) => {
    isEditMode.value = true
    selectedSupplierForm.value = supplier
    formData.name = supplier.name || ''
    formData.contactPerson = supplier.contactPerson || ''
    formData.email = supplier.email || ''
    formData.phone = supplier.phone || ''
    formData.address = supplier.address || ''
    formData.type = supplier.type || ''
    formData.status = supplier.status || 'active'
    formData.notes = supplier.notes || ''
    formErrors.value = {}
    addAnotherAfterSave.value = false
    showAddModal.value = true
  }

  const closeAddModal = () => {
    showAddModal.value = false
    isEditMode.value = false
    selectedSupplierForm.value = null
    resetForm()
  }

  const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  const isValidPhone = (phone) => /^[\d\s\+\-\(\)]+$/.test(phone) && phone.replace(/\D/g, '').length >= 10

  const validateForm = () => {
    const errors = {}
    if (!formData.name.trim()) errors.name = 'Supplier name is required'
    else if (formData.name.trim().length < 2) errors.name = 'Supplier name must be at least 2 characters'
    if (formData.email && !isValidEmail(formData.email)) errors.email = 'Please enter a valid email address'
    if (formData.phone && !isValidPhone(formData.phone)) errors.phone = 'Please enter a valid phone number'
    formErrors.value = errors
    return Object.keys(errors).length === 0
  }

  const clearFormError = (field) => {
    if (formErrors.value[field]) delete formErrors.value[field]
  }

  const saveSupplier = async () => {
    if (!validateForm()) {
      showError('Please correct the form errors before submitting')
      return { success: false, error: 'Please fix form errors' }
    }
    formLoading.value = true
    try {
      const backendData = {
        supplier_name: formData.name,
        contact_person: formData.contactPerson,
        email: formData.email,
        phone_number: formData.phone,
        address: formData.address,
        type: formData.type,
        notes: formData.notes
      }
      let response
      let message
      if (isEditMode.value && selectedSupplierForm.value) {
        response = await api.put(`/suppliers/${selectedSupplierForm.value.id}/`, backendData)
        message = `${formData.name} has been updated successfully`
        const updatedSupplier = transformSupplier(response.data, selectedSupplierForm.value.purchaseOrders || 0, [])
        const index = suppliers.value.findIndex(s => s.id === selectedSupplierForm.value.id)
        if (index !== -1) suppliers.value[index] = updatedSupplier
      } else {
        response = await api.post('/suppliers/', backendData)
        message = `${formData.name} has been added as a new supplier`
        const newSupplier = transformSupplier(response.data, 0, [])
        suppliers.value.unshift(newSupplier)
      }
      updateReportData()
      showSuccess(message)
      if (!isEditMode.value && addAnotherAfterSave.value) {
        resetForm()
      } else {
        setTimeout(() => { closeAddModal() }, 100)
      }
      return { success: true, message }
    } catch (err) {
      console.error('Error saving supplier:', err)
      let errorMessage = 'Failed to save supplier'
      if (err.response?.data?.error) errorMessage = err.response.data.error
      else if (err.response?.statusText) errorMessage = `Failed to save supplier: ${err.response.statusText}`
      else if (err.message) errorMessage = err.message
      showError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      formLoading.value = false
    }
  }

  // ---------- Supplier Reports ----------
  const reportsLoading = ref(false)
  const reportsError = ref(null)
  const showActiveOrdersModal = ref(false)
  const showTopPerformersModal = ref(false)
  const reportsSuppliers = ref([])

  const activeOrders = computed(() => {
    const orders = []
    reportsSuppliers.value.forEach(supplier => {
      const supplierBatches = supplier.batches || []
      if (supplierBatches.length > 0) {
        const batchesByDate = {}
        supplierBatches.forEach(batch => {
          let dateKey
          if (batch.date_received) {
            dateKey = typeof batch.date_received === 'string'
              ? batch.date_received.split('T')[0]
              : new Date(batch.date_received).toISOString().split('T')[0]
          } else if (batch.expected_delivery_date) {
            dateKey = typeof batch.expected_delivery_date === 'string'
              ? batch.expected_delivery_date.split('T')[0]
              : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
          } else {
            dateKey = batch.created_at.split('T')[0]
          }
          if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
          batchesByDate[dateKey].push(batch)
        })
        Object.entries(batchesByDate).forEach(([date, batches]) => {
          const totalCost = batches.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0)
          const orderStatus = getReceiptStatus(batches)
          if (orderStatus === 'Pending Delivery' || orderStatus === 'Partially Received') {
            let receiptId = `SR-${date.replace(/-/g, '')}`
            const firstBatchNotes = batches[0].notes || ''
            const receiptMatch = firstBatchNotes.match(/Receipt:\s*([^\|]+)/)
            if (receiptMatch) receiptId = receiptMatch[1].trim()
            orders.push({
              id: receiptId,
              supplier: supplier.supplier_name,
              supplierId: supplier._id,
              supplierEmail: supplier.email || 'N/A',
              orderDate: batches[0].created_at ? batches[0].created_at.split('T')[0] : date,
              expectedDelivery: batches[0].expected_delivery_date
                ? (typeof batches[0].expected_delivery_date === 'string'
                  ? batches[0].expected_delivery_date.split('T')[0]
                  : new Date(batches[0].expected_delivery_date).toISOString().split('T')[0])
                : date,
              deliveredDate: batches[0].date_received
                ? (typeof batches[0].date_received === 'string'
                  ? batches[0].date_received.split('T')[0]
                  : new Date(batches[0].date_received).toISOString().split('T')[0])
                : null,
              totalAmount: totalCost,
              status: orderStatus,
              items: batches.map(batch => ({
                name: batch.product_name || batch.name || 'Unknown Product',
                product_name: batch.product_name || batch.name || 'Unknown Product',
                product_id: batch.product_id,
                quantity: batch.quantity_received,
                unitPrice: batch.cost_price || 0,
                totalPrice: (batch.cost_price || 0) * (batch.quantity_received || 0),
                batchNumber: batch.batch_number,
                batchId: batch._id,
                expiryDate: batch.expiry_date,
                quantityRemaining: batch.quantity_remaining
              })),
              description: `Stock receipt with ${batches.length} item(s)`,
              notes: firstBatchNotes
            })
          }
        })
      }
    })
    return orders.sort((a, b) => new Date(b.orderDate) - new Date(a.orderDate))
  })

  const calculatePerformanceRating = (supplierBatches, supplierCreatedAt) => {
    if (!supplierBatches || supplierBatches.length === 0) return null
    const batchesByDate = {}
    supplierBatches.forEach(batch => {
      let dateKey
      if (batch.date_received) {
        dateKey = typeof batch.date_received === 'string'
          ? batch.date_received.split('T')[0]
          : new Date(batch.date_received).toISOString().split('T')[0]
      } else if (batch.expected_delivery_date) {
        dateKey = typeof batch.expected_delivery_date === 'string'
          ? batch.expected_delivery_date.split('T')[0]
          : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
      } else {
        dateKey = batch.created_at.split('T')[0]
      }
      if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
      batchesByDate[dateKey].push(batch)
    })
    const orders = Object.entries(batchesByDate).map(([date, batches]) => {
      const firstBatch = batches[0]
      const expectedDate = firstBatch.expected_delivery_date
        ? (typeof firstBatch.expected_delivery_date === 'string'
          ? firstBatch.expected_delivery_date.split('T')[0]
          : new Date(firstBatch.expected_delivery_date).toISOString().split('T')[0])
        : date
      const receivedDate = firstBatch.date_received
        ? (typeof firstBatch.date_received === 'string'
          ? firstBatch.date_received.split('T')[0]
          : new Date(firstBatch.date_received).toISOString().split('T')[0])
        : null
      const status = getReceiptStatus(batches)
      return {
        date,
        expectedDate,
        receivedDate,
        status,
        total: batches.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0),
        batches
      }
    })
    const receivedOrders = orders.filter(order => order.status === 'Received' && order.expectedDate && order.receivedDate)
    if (receivedOrders.length === 0) return null
    let onTimeCount = 0
    receivedOrders.forEach(order => {
      const expectedDate = new Date(order.expectedDate)
      const receivedDate = new Date(order.receivedDate)
      const diffDays = Math.ceil((receivedDate - expectedDate) / (1000 * 60 * 60 * 24))
      if (diffDays <= 0) onTimeCount++
      else if (diffDays <= 3) onTimeCount += 0.7
    })
    const onTimeDeliveryRate = receivedOrders.length > 0 ? (onTimeCount / receivedOrders.length) * 100 : 0
    const daysActiveVal = supplierCreatedAt ? (() => {
      const createdDate = new Date(supplierCreatedAt)
      const today = new Date()
      const diffTime = Math.abs(today - createdDate)
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) || 1
    })() : 1
    const ordersPerMonth = (orders.length / (daysActiveVal / 30))
    const frequencyScore = Math.min(ordersPerMonth / 2, 1) * 100
    const totalSpent = receivedOrders.reduce((sum, o) => sum + o.total, 0)
    const avgOrderValue = receivedOrders.length > 0 ? totalSpent / receivedOrders.length : 0
    const valueScore = Math.min((avgOrderValue / 10000) * 100, 100)
    const orderDates = orders.filter(o => o.date).map(o => new Date(o.date)).sort((a, b) => a - b)
    let consistencyScore = 50
    if (orderDates.length >= 3) {
      const intervals = []
      for (let i = 1; i < orderDates.length; i++) {
        const diffDays = (orderDates[i] - orderDates[i - 1]) / (1000 * 60 * 60 * 24)
        intervals.push(diffDays)
      }
      if (intervals.length > 0) {
        const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
        const variance = intervals.reduce((sum, interval) => sum + Math.pow(interval - avgInterval, 2), 0) / intervals.length
        const stdDev = Math.sqrt(variance)
        consistencyScore = Math.max(0, Math.min(100, 100 - (stdDev / avgInterval) * 100))
      }
    }
    const weightedRating = (
      (onTimeDeliveryRate * 0.40) +
      (frequencyScore * 0.25) +
      (valueScore * 0.20) +
      (consistencyScore * 0.15)
    ) / 100 * 5
    return Math.max(0, Math.min(5, Math.round(weightedRating * 10) / 10))
  }

  const calculateOnTimeDelivery = (supplierBatches) => {
    const batchesByDate = {}
    supplierBatches.forEach(batch => {
      let dateKey
      if (batch.date_received) {
        dateKey = typeof batch.date_received === 'string'
          ? batch.date_received.split('T')[0]
          : new Date(batch.date_received).toISOString().split('T')[0]
      } else if (batch.expected_delivery_date) {
        dateKey = typeof batch.expected_delivery_date === 'string'
          ? batch.expected_delivery_date.split('T')[0]
          : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
      } else {
        return
      }
      if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
      batchesByDate[dateKey].push(batch)
    })
    const receivedOrders = Object.entries(batchesByDate)
      .map(([, batches]) => {
        const firstBatch = batches[0]
        return {
          expectedDate: firstBatch.expected_delivery_date
            ? (typeof firstBatch.expected_delivery_date === 'string'
              ? firstBatch.expected_delivery_date.split('T')[0]
              : new Date(firstBatch.expected_delivery_date).toISOString().split('T')[0])
            : null,
          receivedDate: firstBatch.date_received
            ? (typeof firstBatch.date_received === 'string'
              ? firstBatch.date_received.split('T')[0]
              : new Date(firstBatch.date_received).toISOString().split('T')[0])
            : null
        }
      })
      .filter(order => order.expectedDate && order.receivedDate)
    if (receivedOrders.length === 0) return 0
    let onTimeCount = 0
    receivedOrders.forEach(order => {
      const expectedDate = new Date(order.expectedDate)
      const receivedDate = new Date(order.receivedDate)
      const diffDays = Math.ceil((receivedDate - expectedDate) / (1000 * 60 * 60 * 24))
      if (diffDays <= 0) onTimeCount++
      else if (diffDays <= 3) onTimeCount += 0.7
    })
    return Math.round((onTimeCount / receivedOrders.length) * 100)
  }

  const topPerformers = computed(() => {
    return reportsSuppliers.value
      .filter(supplier => !supplier.isDeleted && supplier.batches && supplier.batches.length > 0)
      .map(supplier => {
        const supplierBatches = supplier.batches || []
        const batchesByDate = {}
        supplierBatches.forEach(batch => {
          let dateKey
          if (batch.date_received) {
            dateKey = typeof batch.date_received === 'string'
              ? batch.date_received.split('T')[0]
              : new Date(batch.date_received).toISOString().split('T')[0]
          } else if (batch.expected_delivery_date) {
            dateKey = typeof batch.expected_delivery_date === 'string'
              ? batch.expected_delivery_date.split('T')[0]
              : new Date(batch.expected_delivery_date).toISOString().split('T')[0]
          } else {
            dateKey = batch.created_at?.split('T')[0] || new Date().toISOString().split('T')[0]
          }
          if (!batchesByDate[dateKey]) batchesByDate[dateKey] = []
          batchesByDate[dateKey].push(batch)
        })
        const orders = Object.entries(batchesByDate).map(([date, batches]) => {
          const status = getReceiptStatus(batches)
          return {
            date,
            status,
            total: batches.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0),
            batches
          }
        })
        const receivedOrders = orders.filter(o => o.status === 'Received')
        const totalValue = receivedOrders.reduce((sum, o) => sum + o.total, 0)
        const avgOrderValue = receivedOrders.length > 0 ? totalValue / receivedOrders.length : 0
        const sortedOrders = [...orders].sort((a, b) => new Date(b.date) - new Date(a.date))
        const lastOrderDate = sortedOrders[0]?.date || supplier.created_at
        const productCounts = {}
        supplierBatches.forEach(batch => {
          const productName = batch.product_name || batch.name || 'Unknown Product'
          productCounts[productName] = (productCounts[productName] || 0) + (batch.quantity_received || 0)
        })
        const topProducts = Object.entries(productCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([name]) => name)
        const rating = calculatePerformanceRating(supplierBatches, supplier.created_at)
        const onTimeDelivery = calculateOnTimeDelivery(supplierBatches)
        return {
          id: supplier._id,
          name: supplier.supplier_name,
          email: supplier.email || 'N/A',
          rating: rating !== null ? rating.toFixed(1) : 'N/A',
          totalOrders: orders.length,
          completedOrders: receivedOrders.length,
          totalValue,
          averageOrderValue: avgOrderValue,
          lastOrder: lastOrderDate,
          onTimeDelivery,
          topProducts: topProducts.length > 0 ? topProducts : ['No products yet'],
          performanceScore: rating !== null ? rating : 0
        }
      })
      .filter(s => s.completedOrders >= 3)
      .sort((a, b) => {
        const aScore = a.performanceScore * 0.6 + Math.min(a.totalValue / 100000, 5) * 0.4
        const bScore = b.performanceScore * 0.6 + Math.min(b.totalValue / 100000, 5) * 0.4
        return bScore - aScore
      })
      .slice(0, 10)
  })

  const reportsActiveOrdersCount = computed(() => activeOrders.value.length)
  const reportsTopPerformersCount = computed(() => topPerformers.value.length)
  const reportDataComputed = computed(() => ({
    activeOrdersCount: reportsActiveOrdersCount.value,
    topSuppliersCount: reportsTopPerformersCount.value,
    totalOrderValue: activeOrders.value.reduce((sum, order) => sum + order.totalAmount, 0),
    pendingOrdersCount: activeOrders.value.filter(order => order.status === 'pending').length,
    averageOrderValue: reportsActiveOrdersCount.value > 0
      ? Math.round(activeOrders.value.reduce((sum, order) => sum + order.totalAmount, 0) / reportsActiveOrdersCount.value)
      : 0
  }))

  const fetchAllSuppliersForReports = async () => {
    reportsLoading.value = true
    reportsError.value = null
    try {
      const response = await api.get('/suppliers/', { params: { per_page: 1000 } })
      const backendSuppliers = response.data.suppliers
      let allBatchesForReports = []
      try {
        const batchesResponse = await api.get('/batches/', { params: { per_page: 1000 } })
        if (batchesResponse.data?.success && Array.isArray(batchesResponse.data.data)) {
          allBatchesForReports = batchesResponse.data.data
        } else if (Array.isArray(batchesResponse.data)) {
          allBatchesForReports = batchesResponse.data
        } else if (Array.isArray(batchesResponse.data?.batches)) {
          allBatchesForReports = batchesResponse.data.batches
        } else {
          allBatchesForReports = []
        }
      } catch (batchesError) {
        console.warn('Failed to fetch batches for reports:', batchesError)
        allBatchesForReports = []
      }
      const batchesBySupplier = {}
      allBatchesForReports.forEach(batch => {
        const supplierId = batch.supplier_id
        if (supplierId) {
          if (!batchesBySupplier[supplierId]) batchesBySupplier[supplierId] = []
          batchesBySupplier[supplierId].push(batch)
        }
      })
      const uniqueProductIds = [...new Set(allBatchesForReports
        .filter(b => b.product_id && !b.product_name)
        .map(b => b.product_id)
      )]
      const productNamesMap = {}
      if (uniqueProductIds.length > 0) {
        await Promise.all(uniqueProductIds.map(async (productId) => {
          try {
            const productResponse = await api.get(`/products/${productId}/`, { params: { include_deleted: 'true' } })
            const product = productResponse.data?.data || productResponse.data
            if (product) {
              productNamesMap[productId] = product.product_name || product.name || productId
            }
          } catch (err) {
            console.warn(`[SupplierReports] Failed to fetch product name for ${productId}:`, err)
          }
        }))
      }
      const enrichedBatchesBySupplier = {}
      const batchesWithMissingNames = []
      Object.entries(batchesBySupplier).forEach(([supplierId, batches]) => {
        enrichedBatchesBySupplier[supplierId] = batches.map(batch => {
          let productName = batch.product_name || batch.name
          if (!productName && batch.product_id) productName = productNamesMap[batch.product_id]
          if (!productName) {
            productName = 'Unknown Product'
            if (batch.product_id) {
              batchesWithMissingNames.push({ batch_id: batch._id, product_id: batch.product_id })
            }
          }
          return { ...batch, product_name: productName, name: productName }
        })
      })
      if (batchesWithMissingNames.length > 0) {
        console.warn(`[SupplierReports] ${batchesWithMissingNames.length} batches have missing product names`)
      }
      reportsSuppliers.value = backendSuppliers.map(supplier => ({
        ...supplier,
        batches: enrichedBatchesBySupplier[supplier._id] || []
      }))
    } catch (err) {
      reportsError.value = err.response?.data?.error || 'Failed to fetch supplier reports'
      console.error('Error fetching suppliers for reports:', err)
    } finally {
      reportsLoading.value = false
    }
  }

  const openActiveOrdersModal = () => { showActiveOrdersModal.value = true }
  const closeActiveOrdersModal = () => { showActiveOrdersModal.value = false }
  const openTopPerformersModal = () => { showTopPerformersModal.value = true }
  const closeTopPerformersModal = () => { showTopPerformersModal.value = false }
  const refreshReports = async () => { await fetchAllSuppliersForReports() }
  const handleViewAllOrders = () => ({ name: 'OrdersHistory' })

  // ---------- Return everything ----------
  return {
    // Core state
    suppliers,
    allBatches,
    loading,
    error,
    successMessage,
    selectedSuppliers,
    pagination,
    filters,
    reportData,

    // Computed core
    filteredSuppliers,

    // Core methods
    fetchSuppliers,
    addSupplier,
    updateSupplier,
    toggleFavorite,
    deleteSupplier,
    deleteSelected,
    updateReportData,
    clearFilters,
    applyFilters,
    refreshData,
    getStatusBadgeClass,
    formatStatus,
    getShortAddress,
    getActiveOrdersForModal: null, // placeholder not used in UI

    // Bulk suppliers modal
    showBulkModal,
    openBulkModal,
    closeBulkModal,
    handleBulkSave,

    // Create order modal
    showCreateOrderModal,
    selectedSupplierForOrder,
    orderLoading,
    orderError,
    openCreateOrderModal,
    closeCreateOrderModal,
    handleOrderSave,

    // Dropdown
    showDropdown,
    dropdownRef,
    toggleDropdown,
    closeDropdown,

    // Export
    showExportModal,
    selectedExportFormat,
    exportOptions,
    openExportModal,
    closeExportModal,
    handleExport,

    // Import
    showImportModal,
    openImportModal,
    closeImportModal,
    handleImportSave,

    // Orders history
    ordersHistoryLoading,
    ordersHistoryError,
    ordersHistorySuppliers,
    ordersHistoryFilters,
    ordersHistoryAllOrders,
    ordersHistorySupplierOptions,
    ordersHistoryFilteredOrders,
    ordersHistoryTotalOrders,
    ordersHistoryActiveOrdersCount,
    ordersHistoryDeliveredOrdersCount,
    ordersHistoryCancelledOrdersCount,
    ordersHistoryTotalOrderValue,
    ordersHistoryAverageOrderValue,
    fetchOrders,
    applyOrdersFilters,
    clearOrdersFilters,
    exportOrdersData,

    // Supplier form
    showAddModal,
    isEditMode,
    formLoading,
    selectedSupplierForm,
    addAnotherAfterSave,
    formData,
    formErrors,
    isFormValid,
    showAddSupplierModal,
    editSupplier: editSupplierForm,
    closeAddModal,
    resetForm,
    validateForm,
    clearFormError,
    saveSupplier,

    // Supplier reports
    reportsLoading,
    reportsError,
    showActiveOrdersModal,
    showTopPerformersModal,
    activeOrders,
    topPerformers,
    reportsActiveOrdersCount,
    reportsTopPerformersCount,
    reportDataComputed,
    openActiveOrdersModal,
    closeActiveOrdersModal,
    openTopPerformersModal,
    closeTopPerformersModal,
    refreshReports,
    handleViewAllOrders
  }
}

