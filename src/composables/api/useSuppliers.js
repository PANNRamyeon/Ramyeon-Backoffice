import { ref, reactive, computed } from 'vue'
import { api } from '@/services/api.js'
import { useToast } from '@/composables/ui/useToast'

// Module-level shared state
const suppliers = ref([])
const loading = ref(false)
const error = ref(null)
const successMessage = ref(null)

// Module-level order history state
const ordersHistoryLoading = ref(false)
const ordersHistoryError = ref(null)
const allHistoryOrders = ref([])
const ordersHistoryFilters = ref({ status: 'all', supplier: 'all', dateRange: 'all', search: '' })

export function useSuppliers() {
  const { success: showSuccess, error: showError } = useToast()

  // ─── Filters ────────────────────────────────────────────────────────────────
  const filters = reactive({ search: '', type: 'all', status: 'all', order: 'all' })

  const filteredSuppliers = computed(() => {
    let result = suppliers.value
    if (filters.search) {
      const s = filters.search.toLowerCase()
      result = result.filter(sup =>
        sup.supplier_name?.toLowerCase().includes(s) ||
        sup.email?.toLowerCase().includes(s) ||
        sup.contact_person?.toLowerCase().includes(s)
      )
    }
    if (filters.type && filters.type !== 'all') {
      result = result.filter(sup => sup.type === filters.type)
    }
    return result
  })

  const applyFilters = () => {}
  const clearFilters = () => {
    filters.search = ''
    filters.type = 'all'
    filters.status = 'all'
    filters.order = 'all'
  }

  // ─── CRUD ───────────────────────────────────────────────────────────────────
  const fetchSuppliers = async () => {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/suppliers/')
      suppliers.value = response.data.suppliers || []
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to load suppliers'
      showError(error.value)
    } finally {
      loading.value = false
    }
  }

  const createSupplier = async (data) => {
    try {
      const response = await api.post('/suppliers/', data)
      suppliers.value.unshift(response.data)
      showSuccess(`${data.supplier_name} added successfully`)
      return { success: true, data: response.data }
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to create supplier'
      showError(msg)
      return { success: false, error: msg }
    }
  }

  const updateSupplier = async (supplierId, data) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}/`, data)
      const index = suppliers.value.findIndex(s => s.supplier_id === supplierId)
      if (index !== -1) suppliers.value[index] = response.data
      showSuccess('Supplier updated successfully')
      return { success: true, data: response.data }
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to update supplier'
      showError(msg)
      return { success: false, error: msg }
    }
  }

  const deleteSupplier = async (supplier) => {
    try {
      await api.delete(`/suppliers/${supplier.supplier_id}/`)
      suppliers.value = suppliers.value.filter(s => s.supplier_id !== supplier.supplier_id)
      showSuccess(`${supplier.supplier_name} deleted`)
      return { success: true }
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to delete supplier'
      showError(msg)
      return { success: false, error: msg }
    }
  }

  const toggleFavorite = async (supplier) => {
    try {
      const newFav = !supplier.isFavorite
      await api.put(`/suppliers/${supplier.supplier_id}/`, { isFavorite: newFav })
      const index = suppliers.value.findIndex(s => s.supplier_id === supplier.supplier_id)
      if (index !== -1) suppliers.value[index].isFavorite = newFav
      return { success: true }
    } catch (err) {
      return { success: false, error: 'Failed to update favorite' }
    }
  }

  const refreshData = async () => {
    await fetchSuppliers()
  }

  // ─── Bulk Selection ──────────────────────────────────────────────────────────
  const selectedSuppliers = ref([])

  const deleteSelected = async () => {
    if (!selectedSuppliers.value.length) return
    loading.value = true
    try {
      for (const id of selectedSuppliers.value) {
        await api.delete(`/suppliers/${id}/`)
      }
      suppliers.value = suppliers.value.filter(s => !selectedSuppliers.value.includes(s.supplier_id))
      selectedSuppliers.value = []
      showSuccess('Selected suppliers deleted')
    } catch (err) {
      showError('Some suppliers could not be deleted')
    } finally {
      loading.value = false
    }
  }

  // ─── Add / Edit Form ────────────────────────────────────────────────────────
  const showAddModal = ref(false)
  const isEditMode = ref(false)
  const editingSupplierId = ref(null)
  const formLoading = ref(false)
  const addAnotherAfterSave = ref(false)
  const formErrors = ref({})

  const formData = reactive({
    supplier_name: '',
    contact_person: '',
    email: '',
    phone_number: '',
    type: '',
    address: '',
    notes: '',
    isFavorite: false,
    lead_time_days: '',
    payment_terms: '',
    delivery_method: ''
  })

  const isFormValid = computed(() => !!formData.supplier_name.trim())

  const resetForm = () => {
    Object.assign(formData, {
      supplier_name: '',
      contact_person: '',
      email: '',
      phone_number: '',
      type: '',
      address: '',
      notes: '',
      isFavorite: false,
      lead_time_days: '',
      payment_terms: '',
      delivery_method: ''
    })
    formErrors.value = {}
    editingSupplierId.value = null
  }

  const showAddSupplierModal = () => {
    resetForm()
    isEditMode.value = false
    showAddModal.value = true
  }

  const editSupplier = (supplier) => {
    resetForm()
    Object.assign(formData, {
      supplier_name: supplier.supplier_name || '',
      contact_person: supplier.contact_person || '',
      email: supplier.email || '',
      phone_number: supplier.phone_number || '',
      type: supplier.type || '',
      address: supplier.address || '',
      notes: supplier.notes || '',
      isFavorite: supplier.isFavorite || false,
      lead_time_days: supplier.lead_time_days || '',
      payment_terms: supplier.payment_terms || '',
      delivery_method: supplier.delivery_method || ''
    })
    editingSupplierId.value = supplier.supplier_id
    isEditMode.value = true
    showAddModal.value = true
  }

  const closeAddModal = () => {
    showAddModal.value = false
    resetForm()
  }

  const clearFormError = (field) => {
    if (formErrors.value[field]) delete formErrors.value[field]
  }

  const saveSupplier = async () => {
    formErrors.value = {}
    if (!formData.supplier_name.trim()) {
      formErrors.value.supplier_name = 'Supplier name is required'
      return { success: false }
    }

    formLoading.value = true
    try {
      let result
      if (isEditMode.value) {
        result = await updateSupplier(editingSupplierId.value, { ...formData })
      } else {
        result = await createSupplier({ ...formData })
      }

      if (result.success) {
        if (!addAnotherAfterSave.value) {
          closeAddModal()
        } else {
          resetForm()
        }
      }
      return result
    } finally {
      formLoading.value = false
    }
  }

  // ─── Reports (simplified) ───────────────────────────────────────────────────
  const showActiveOrdersModal = ref(false)
  const showTopPerformersModal = ref(false)
  const reportsLoading = ref(false)

  const reportsActiveOrdersCount = computed(() => 0)
  const reportsTopPerformersCount = computed(() => suppliers.value.filter(s => s.isFavorite).length)
  const activeOrders = computed(() => [])
  const topPerformers = computed(() => suppliers.value.filter(s => s.isFavorite))

  const openActiveOrdersModal = () => { showActiveOrdersModal.value = true }
  const closeActiveOrdersModal = () => { showActiveOrdersModal.value = false }
  const openTopPerformersModal = () => { showTopPerformersModal.value = true }
  const closeTopPerformersModal = () => { showTopPerformersModal.value = false }
  const refreshReports = async () => {}

  // ─── Export ─────────────────────────────────────────────────────────────────
  const showExportModal = ref(false)
  const selectedExportFormat = ref('csv')
  const exportOptions = reactive({ includeDeleted: false })

  const openExportModal = () => { showExportModal.value = true }
  const closeExportModal = () => { showExportModal.value = false }

  const handleExport = (suppliersData) => {
    try {
      const data = suppliersData || suppliers.value
      const headers = ['ID', 'Name', 'Contact Person', 'Email', 'Phone', 'Type', 'Address', 'Notes']
      const rows = data.map(s => [
        s.supplier_id || '',
        s.supplier_name || '',
        s.contact_person || '',
        s.email || '',
        s.phone_number || '',
        s.type || '',
        s.address || '',
        s.notes || ''
      ])
      const csv = [headers, ...rows]
        .map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
        .join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `suppliers_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      URL.revokeObjectURL(url)
      closeExportModal()
      return { success: true, message: 'Exported successfully' }
    } catch (err) {
      return { success: false, error: 'Export failed' }
    }
  }

  // ─── Bulk Add Modal ──────────────────────────────────────────────────────────
  const showBulkModal = ref(false)
  const openBulkModal = () => { showBulkModal.value = true }
  const closeBulkModal = () => { showBulkModal.value = false }
  const handleBulkSave = (newSuppliers) => {
    suppliers.value.push(...newSuppliers)
    closeBulkModal()
    return { success: true, message: `${newSuppliers.length} suppliers added` }
  }

  // ─── Import Modal ────────────────────────────────────────────────────────────
  const showImportModal = ref(false)
  const openImportModal = () => { showImportModal.value = true }
  const closeImportModal = () => { showImportModal.value = false }
  const handleImportSave = (importedSuppliers) => {
    suppliers.value.push(...importedSuppliers)
    closeImportModal()
    return { success: true, message: `${importedSuppliers.length} suppliers imported` }
  }

  // ─── Create Order Modal ──────────────────────────────────────────────────────
  const showCreateOrderModal = ref(false)
  const selectedSupplier = ref(null)

  const openCreateOrderModal = (supplier) => {
    selectedSupplier.value = supplier
    showCreateOrderModal.value = true
  }
  const closeCreateOrderModal = () => {
    showCreateOrderModal.value = false
    selectedSupplier.value = null
  }
  const handleOrderSave = async () => {
    return { success: true, message: 'Order created' }
  }
  const handleViewAllOrders = () => ({ name: 'OrdersHistory' })

  // ─── Order History ───────────────────────────────────────────────────────────
  const ordersHistoryFilteredOrders = computed(() => {
    let result = allHistoryOrders.value
    const f = ordersHistoryFilters.value
    if (f.search) {
      const s = f.search.toLowerCase()
      result = result.filter(o =>
        (o.id || '').toLowerCase().includes(s) ||
        (o.supplier || '').toLowerCase().includes(s)
      )
    }
    if (f.status !== 'all') result = result.filter(o => o.status === f.status)
    if (f.supplier !== 'all') result = result.filter(o => o.supplier_id === f.supplier)
    if (f.dateRange !== 'all') {
      const now = new Date()
      result = result.filter(o => {
        const d = new Date(o.orderDate)
        if (f.dateRange === 'today') return d.toDateString() === now.toDateString()
        if (f.dateRange === 'week') { const w = new Date(now); w.setDate(w.getDate() - 7); return d >= w }
        if (f.dateRange === 'month') return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
        if (f.dateRange === 'quarter') return Math.floor(d.getMonth() / 3) === Math.floor(now.getMonth() / 3) && d.getFullYear() === now.getFullYear()
        return true
      })
    }
    return result
  })

  const ordersHistorySupplierOptions = computed(() => {
    const seen = new Set()
    return allHistoryOrders.value.reduce((opts, o) => {
      if (o.supplier_id && !seen.has(o.supplier_id)) {
        seen.add(o.supplier_id)
        opts.push({ value: o.supplier_id, label: o.supplier || o.supplier_id })
      }
      return opts
    }, [])
  })

  const fetchOrders = async () => {
    ordersHistoryLoading.value = true
    ordersHistoryError.value = null
    try {
      // Ensure suppliers list is loaded first
      if (!suppliers.value.length) {
        const suppResp = await api.get('/suppliers/')
        suppliers.value = suppResp.data.suppliers || []
      }

      // Fetch shipments per-supplier (uses the same endpoint that works in SupplierDetails)
      const results = await Promise.all(
        suppliers.value.map(async (supplier) => {
          try {
            const resp = await api.get(`/shipments/supplier/${supplier.supplier_id}/`, {
              params: { limit: 100 }
            })
            return (resp.data?.data || []).map(s => ({
              ...s,
              supplier_name: supplier.supplier_name || s.supplier_id
            }))
          } catch {
            return []
          }
        })
      )

      const statusMap = {
        pending: 'pending', received: 'delivered', inspected: 'delivered',
        approved: 'delivered', quality_issue: 'delivered', cancelled: 'cancelled'
      }
      allHistoryOrders.value = results
        .flat()
        .map(s => ({
          id: s.shipment_id,
          supplier: s.supplier_name || s.supplier_id || 'Unknown',
          supplier_id: s.supplier_id,
          supplierEmail: '',
          status: statusMap[s.status] || 'pending',
          orderDate: s.shipment_date,
          expectedDelivery: s.expected_delivery_date || s.shipment_date,
          totalAmount: s.freight_cost || 0,
          items: [],
          batchNumber: s.batch_number,
          invoiceNumber: s.invoice_number,
          notes: s.notes
        }))
        .sort((a, b) => new Date(b.orderDate) - new Date(a.orderDate))
    } catch (err) {
      ordersHistoryError.value = err.response?.data?.error || 'Failed to load order history'
      showError(ordersHistoryError.value)
    } finally {
      ordersHistoryLoading.value = false
    }
  }

  const applyOrdersFilters = () => {}

  const exportOrdersData = () => {
    try {
      const data = ordersHistoryFilteredOrders.value
      const headers = ['Order ID', 'Supplier', 'Status', 'Order Date', 'Expected Delivery', 'Amount']
      const rows = data.map(o => [
        o.id || '', o.supplier || '', o.status || '',
        o.orderDate || '', o.expectedDelivery || '', o.totalAmount || 0
      ])
      const csv = [headers, ...rows]
        .map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
        .join('\n')
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `orders_history_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      URL.revokeObjectURL(url)
      return { success: true }
    } catch {
      return { success: false }
    }
  }

  return {
    // State
    suppliers,
    loading,
    error,
    successMessage,
    selectedSuppliers,
    filters,

    // Computed
    filteredSuppliers,

    // CRUD
    fetchSuppliers,
    createSupplier,
    updateSupplier,
    deleteSupplier,
    toggleFavorite,
    deleteSelected,
    refreshData,

    // Form
    showAddModal,
    isEditMode,
    formData,
    formErrors,
    formLoading,
    isFormValid,
    addAnotherAfterSave,
    showAddSupplierModal,
    editSupplier,
    closeAddModal,
    clearFormError,
    saveSupplier,

    // Reports
    showActiveOrdersModal,
    showTopPerformersModal,
    reportsLoading,
    reportsActiveOrdersCount,
    reportsTopPerformersCount,
    activeOrders,
    topPerformers,
    openActiveOrdersModal,
    closeActiveOrdersModal,
    openTopPerformersModal,
    closeTopPerformersModal,
    refreshReports,

    // Filters
    applyFilters,
    clearFilters,

    // Export
    showExportModal,
    selectedExportFormat,
    exportOptions,
    openExportModal,
    closeExportModal,
    handleExport,

    // Bulk
    showBulkModal,
    openBulkModal,
    closeBulkModal,
    handleBulkSave,

    // Import
    showImportModal,
    openImportModal,
    closeImportModal,
    handleImportSave,

    // Create Order
    showCreateOrderModal,
    selectedSupplier,
    openCreateOrderModal,
    closeCreateOrderModal,
    handleOrderSave,
    handleViewAllOrders,

    // Order History
    ordersHistoryLoading,
    ordersHistoryError,
    ordersHistoryFilters,
    ordersHistoryFilteredOrders,
    ordersHistorySupplierOptions,
    fetchOrders,
    applyOrdersFilters,
    exportOrdersData
  }
}
