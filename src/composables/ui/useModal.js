// composables/ui/useModal.js
import { ref, nextTick } from 'vue'

export function useModal() {
  const isVisible = ref(false)
  const isLoading = ref(false)
  const error = ref(null)

  const show = () => {
    isVisible.value = true
    error.value = null
    // Focus management
    nextTick(() => {
      const firstInput = document.querySelector('.modal input, .modal textarea, .modal select')
      firstInput?.focus()
    })
  }

  const hide = () => {
    isVisible.value = false
    error.value = null
    isLoading.value = false
  }

  const setLoading = (loading) => {
    isLoading.value = loading
  }

  const setError = (errorMessage) => {
    error.value = errorMessage
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    isVisible,
    isLoading,
    error,

    // Methods
    show,
    hide,
    setLoading,
    setError,
    clearError
  }
}