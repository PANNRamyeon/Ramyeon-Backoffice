import { ref, readonly } from 'vue'

// Global state for toasts
const toasts = ref([])
let toastIdCounter = 0

// Helper function to create toast
const createToast = (options) => {
  const toast = {
    id: ++toastIdCounter,
    type: 'success',
    message: '',
    duration: 12000,
    dismissible: true,
    showProgressBar: true,
    persistent: false,
    paused: false,
    timestamp: Date.now(),
    ...options
  }
  
  return toast
}

// Auto-dismiss functionality
const setupAutoRemove = (toast) => {
  if (!toast.persistent && toast.duration > 0) {
    setTimeout(() => {
      removeToast(toast.id)
    }, toast.duration)
  }
}

// Core toast management
const addToast = (options) => {
  const toast = createToast(options)
  toasts.value.push(toast)
  
  // Setup auto-removal
  setupAutoRemove(toast)
  
  // Limit the number of toasts
  if (toasts.value.length > 5) {
    toasts.value.shift()
  }
  
  return toast.id
}

const removeToast = (id) => {
  const index = toasts.value.findIndex(toast => toast.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

const clearAllToasts = () => {
  toasts.value = []
}

const updateToast = (id, updates) => {
  const toast = toasts.value.find(toast => toast.id === id)
  if (toast) {
    Object.assign(toast, updates)
  }
}

const findToast = (id) => {
  return toasts.value.find(toast => toast.id === id)
}

// Main composable function
export function useToast() {
  
  // Convenience methods for different toast types
  const success = (message, options = {}) => {
    return addToast({
      ...options,
      type: 'success',
      message,
      duration: options.duration || 12000
    })
  }

  const error = (message, options = {}) => {
    return addToast({
      ...options,
      type: 'error',
      message,
      duration: options.duration || 12000
    })
  }

  const warning = (message, options = {}) => {
    return addToast({
      ...options,
      type: 'warning',
      message,
      duration: options.duration || 12000
    })
  }

  const info = (message, options = {}) => {
    return addToast({
      ...options,
      type: 'info',
      message,
      duration: options.duration || 12000
    })
  }

  const loading = (message, options = {}) => {
    return addToast({
      ...options,
      type: 'info',
      message,
      persistent: true,
      showProgressBar: false,
      dismissible: false
    })
  }

  // Alias methods
  const dismiss = (id) => {
    removeToast(id)
  }

  const dismissAll = () => {
    clearAllToasts()
  }

  // Promise-based toasts
  const promise = async (promiseToResolve, messages, options = {}) => {
    const defaultMessages = {
      loading: 'Loading...',
      success: 'Success!',
      error: 'Something went wrong!'
    }

    const finalMessages = { ...defaultMessages, ...messages }
    const loadingToastId = loading(finalMessages.loading, options.loading)

    try {
      const result = await promiseToResolve
      dismiss(loadingToastId)
      success(finalMessages.success, options.success)
      return result
    } catch (error) {
      dismiss(loadingToastId)
      error(finalMessages.error, options.error)
      throw error
    }
  }

  return {
    // State
    toasts: readonly(toasts),
    
    // Core methods
    addToast,
    removeToast,
    clearAllToasts,
    updateToast,
    
    // Convenience methods
    success,
    error,
    warning,
    info,
    loading,
    
    // Alias methods
    dismiss,
    dismissAll,
    
    // Advanced methods
    promise,
    
    // Utility
    findToast
  }
}