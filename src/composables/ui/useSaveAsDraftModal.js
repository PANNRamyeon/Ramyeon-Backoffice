// composables/ui/useSaveAsDraftModal.js
import { ref, computed } from 'vue'

/**
 * Composable for managing Save as Draft Modal functionality
 * Works with the SaveAsDraftModal component in components/common
 */
export function useSaveAsDraftModal() {
  // Modal state
  const modalRef = ref(null)
  const isLoading = ref(false)
  const isVisible = ref(false)
  
  // Modal configuration
  const modalConfig = ref({
    modalId: 'saveDraftModal',
    title: 'Unsaved Changes',
    subtitle: 'You have unsaved work',
    message: 'You have unsaved changes that will be lost if you leave this page. Would you like to save your progress as a draft?',
    dataSummary: null,
    showDraftNameInput: true,
    defaultDraftName: `Draft ${new Date().toLocaleDateString()}`,
    saveText: 'Save as Draft',
    savingText: 'Saving...',
    cancelText: 'Cancel',
    discardText: 'Discard Changes'
  })
  
  // Draft data
  const currentDraftData = ref(null)
  const savedDrafts = ref([])
  
  // Computed properties
  const hasUnsavedChanges = computed(() => {
    return currentDraftData.value !== null
  })

  const shouldShowDraftContent = computed(() => {
    return currentDraftData.value !== null && !isVisible.value
  })
  
  /**
   * Show the modal with optional configuration
   * @param {Object} config - Modal configuration options
   * @param {Object} draftData - Data to be saved as draft
   */
  const showModal = (config = {}, draftData = null) => {
    // Merge provided config with defaults
    modalConfig.value = {
      ...modalConfig.value,
      ...config
    }
    
    // Set current draft data
    currentDraftData.value = draftData
    
    // Set visible flag
    isVisible.value = true
  }

  /**
   * Hide the modal
   */
  const hideModal = () => {
    isVisible.value = false
  }

  /**
   * Handle saving draft
   * @param {Object} draftInfo - Information about the draft (name, id, timestamp)
   * @returns {Promise} - Resolves when draft is saved
   */
  const handleSaveDraft = async (draftInfo) => {
    isLoading.value = true
    
    try {
      const draftToSave = {
        ...draftInfo,
        data: currentDraftData.value,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
      
      // Add to saved drafts
      savedDrafts.value.push(draftToSave)
      
      // Store in localStorage (since we can't use browser storage APIs in artifacts)
      // In a real app, this would be an API call or proper storage
      if (typeof localStorage !== 'undefined') {
        const existingDrafts = JSON.parse(localStorage.getItem('savedDrafts') || '[]')
        existingDrafts.push(draftToSave)
        localStorage.setItem('savedDrafts', JSON.stringify(existingDrafts))
      }
      
      // Clear current draft data
      currentDraftData.value = null
      
      // Hide modal
      hideModal()
      
      return draftToSave
    } catch (error) {
      console.error('Error saving draft:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Handle discarding changes
   */
  const handleDiscard = () => {
    currentDraftData.value = null
    hideModal()
  }
  
  /**
   * Handle canceling (keep changes, close modal)
   */
  const handleCancel = () => {
    hideModal()
  }
  
  /**
   * Load a saved draft
   * @param {string} draftId - ID of the draft to load
   * @returns {Object|null} - Draft data or null if not found
   */
  const loadDraft = (draftId) => {
    const draft = savedDrafts.value.find(d => d.id === draftId)
    if (draft) {
      currentDraftData.value = draft.data
      return draft
    }
    return null
  }
  
  /**
   * Delete a saved draft
   * @param {string} draftId - ID of the draft to delete
   */
  const deleteDraft = (draftId) => {
    savedDrafts.value = savedDrafts.value.filter(d => d.id !== draftId)
    
    // Update localStorage
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('savedDrafts', JSON.stringify(savedDrafts.value))
    }
  }
  
  /**
   * Load saved drafts from storage
   */
  const loadSavedDrafts = () => {
    if (typeof localStorage !== 'undefined') {
      const drafts = JSON.parse(localStorage.getItem('savedDrafts') || '[]')
      savedDrafts.value = drafts
    }
  }
  
  /**
   * Create a data summary for display in the modal
   * @param {Object} data - The data to summarize
   * @returns {Object} - Summary object for display
   */
  const createDataSummary = (data) => {
    if (!data) return null
    
    const summary = {}
    
    // Example summary logic - customize based on your data structure
    if (data.products && Array.isArray(data.products)) {
      summary['Products'] = `${data.products.length} items`
    }
    
    if (data.totalProducts) {
      summary['Total Products'] = `${data.totalProducts} items`
    }
    
    if (data.validProducts !== undefined) {
      summary['Valid Products'] = `${data.validProducts} items`
    }
    
    if (data.invalidProducts !== undefined && data.invalidProducts > 0) {
      summary['Invalid Products'] = `${data.invalidProducts} items`
    }
    
    if (data.totalValue || data.total) {
      const total = data.totalValue || data.total
      summary['Total Value'] = typeof total === 'number' 
        ? `₱${total.toLocaleString('en-PH')}` 
        : total
    }
    
    if (data.customer) {
      summary['Customer'] = data.customer.name || data.customer
    }
    
    if (data.orderType) {
      summary['Order Type'] = data.orderType
    }
    
    return Object.keys(summary).length > 0 ? summary : null
  }
  
  /**
   * Check if there are unsaved changes before navigation
   * @param {Function} beforeUnload - Optional custom beforeunload handler
   */
  const setupBeforeUnloadHandler = (beforeUnload = null) => {
    const handleBeforeUnload = (event) => {
      if (hasUnsavedChanges.value) {
        if (beforeUnload) {
          return beforeUnload(event)
        }
        event.preventDefault()
        event.returnValue = ''
        return ''
      }
    }
    
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', handleBeforeUnload)
      
      // Return cleanup function
      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload)
      }
    }
  }
  
  // Initialize by loading saved drafts
  loadSavedDrafts()
  
  return {
    // State
    modalRef,
    isLoading,
    isVisible,
    modalConfig,
    currentDraftData,
    savedDrafts,
    
    // Computed
    hasUnsavedChanges,
    shouldShowDraftContent,
    
    // Methods
    showModal,
    hideModal,
    handleSaveDraft,
    handleDiscard,
    handleCancel,
    loadDraft,
    deleteDraft,
    loadSavedDrafts,
    createDataSummary,
    setupBeforeUnloadHandler
  }
}