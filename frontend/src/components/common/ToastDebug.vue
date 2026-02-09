<template>
  <div class="toast-debug-container">
    <div class="card">
      <div class="card-header">
        <h4>🧪 Toast Notification Debug</h4>
        <p class="text-muted mb-0">Test if the toast system is working properly</p>
      </div>
      <div class="card-body">
        <!-- Basic Tests -->
        <div class="mb-4">
          <h5>Basic Toast Types</h5>
          <div class="d-flex flex-wrap gap-2 mb-3">
            <button class="btn btn-success btn-sm" @click="testSuccess">
              ✅ Test Success
            </button>
            <button class="btn btn-danger btn-sm" @click="testError">
              ❌ Test Error
            </button>
            <button class="btn btn-warning btn-sm" @click="testWarning">
              ⚠️ Test Warning
            </button>
            <button class="btn btn-info btn-sm" @click="testInfo">
              ℹ️ Test Info
            </button>
          </div>
        </div>

        <!-- Product Addition Test -->
        <div class="mb-4">
          <h5>Product Addition Simulation</h5>
          <div class="d-flex flex-wrap gap-2 mb-3">
            <button class="btn btn-primary btn-sm" @click="testProductAdded">
              📦 Simulate "Item added"
            </button>
            <button class="btn btn-secondary btn-sm" @click="testProductUpdate">
              📝 Simulate Product Update
            </button>
            <button class="btn btn-outline-danger btn-sm" @click="testProductError">
              💥 Simulate Add Error
            </button>
          </div>
        </div>

        <!-- Advanced Tests -->
        <div class="mb-4">
          <h5>Advanced Features</h5>
          <div class="d-flex flex-wrap gap-2 mb-3">
            <button class="btn btn-outline-primary btn-sm" @click="testLoading">
              🔄 Test Loading Toast
            </button>
            <button class="btn btn-outline-secondary btn-sm" @click="testPersistent">
              📌 Test Persistent Toast
            </button>
            <button class="btn btn-outline-warning btn-sm" @click="testMultiple">
              📚 Test Multiple Toasts
            </button>
            <button class="btn btn-outline-danger btn-sm" @click="clearAll">
              🗑️ Clear All Toasts
            </button>
          </div>
        </div>

        <!-- Debug Information -->
        <div class="debug-info">
          <h5>Debug Information</h5>
          <div class="alert alert-info">
            <small>
              <strong>Toast State:</strong> {{ toastCount }} active toast(s)<br>
              <strong>Composable Available:</strong> {{ composableAvailable ? '✅ Yes' : '❌ No' }}<br>
              <strong>Toast Container Present:</strong> {{ containerPresent ? '✅ Yes' : '❌ No' }}<br>
              <strong>Last Action:</strong> {{ lastAction || 'None' }}
            </small>
          </div>
        </div>

        <!-- Console Log Test -->
        <div class="mb-3">
          <h5>Manual Test</h5>
          <div class="alert alert-secondary">
            <small>
              <strong>Manual Test Instructions:</strong><br>
              1. Click "Console Log Test" button<br>
              2. Review the popup for toast debug info<br>
              3. Verify there are no error alerts
            </small>
          </div>
          <button class="btn btn-outline-info btn-sm" @click="consoleTest">
            🖥️ Console Log Test
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useToast } from '@/composables/ui/useToast.js'

export default {
  name: 'ToastDebug',
  setup() {
    // Test if composable is available
    let toast = null
    let composableAvailable = false
    
    try {
      toast = useToast()
      composableAvailable = true
    } catch (error) {
      console.error('❌ Error loading toast composable:', error)
      composableAvailable = false
    }

    return {
      toast,
      composableAvailable
    }
  },
  data() {
    return {
      lastAction: null,
      toastCount: 0
    }
  },
  computed: {
    containerPresent() {
      // Check if toast container exists in DOM
      return !!document.querySelector('.toast-container')
    }
  },
  mounted() {
    this.updateToastCount()
    
    // Set up interval to update toast count
    setInterval(() => {
      this.updateToastCount()
    }, 1000)
  },
  methods: {
    updateToastCount() {
      if (this.toast && this.toast.toasts) {
        this.toastCount = this.toast.toasts.length
      }
    },
    
    testSuccess() {
      this.lastAction = 'Success Toast'
      
      if (this.toast && this.toast.success) {
        this.toast.success('✅ Success test completed!')
      } else {
        console.error('❌ Toast success method not available')
        alert('Toast success method not available - check console')
      }
    },
    
    testError() {
      this.lastAction = 'Error Toast'
      
      if (this.toast && this.toast.error) {
        this.toast.error('❌ Error test completed!')
      } else {
        console.error('❌ Toast error method not available')
        alert('Toast error method not available - check console')
      }
    },
    
    testWarning() {
      this.lastAction = 'Warning Toast'
      
      if (this.toast && this.toast.warning) {
        this.toast.warning('⚠️ Warning test completed!')
      } else {
        console.error('❌ Toast warning method not available')
        alert('Toast warning method not available - check console')
      }
    },
    
    testInfo() {
      this.lastAction = 'Info Toast'
      
      if (this.toast && this.toast.info) {
        this.toast.info('ℹ️ Info test completed!')
      } else {
        console.error('❌ Toast info method not available')
        alert('Toast info method not available - check console')
      }
    },
    
    testProductAdded() {
      this.lastAction = 'Product Added'
      
      if (this.toast && this.toast.success) {
        // Exact same call as in your Products.vue
        this.toast.success('Item added')
      } else {
        console.error('❌ Cannot simulate product addition - toast not available')
        alert('Cannot simulate product addition - check console')
      }
    },
    
    testProductUpdate() {
      this.lastAction = 'Product Updated'
      
      if (this.toast && this.toast.success) {
        this.toast.success('Product "Test Product" updated successfully')
      } else {
        console.error('❌ Cannot simulate product update')
        alert('Cannot simulate product update - check console')
      }
    },
    
    testProductError() {
      this.lastAction = 'Product Error'
      
      if (this.toast && this.toast.error) {
        this.toast.error('Failed to add product: Validation error')
      } else {
        console.error('❌ Cannot simulate product error')
        alert('Cannot simulate product error - check console')
      }
    },
    
    testLoading() {
      this.lastAction = 'Loading Toast'
      
      if (this.toast && this.toast.loading) {
        const loadingId = this.toast.loading('Loading products...')
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
          if (this.toast.dismiss) {
            this.toast.dismiss(loadingId)
            this.toast.success('Loading completed!')
          }
        }, 3000)
      } else {
        console.error('❌ Toast loading method not available')
        alert('Toast loading method not available - check console')
      }
    },
    
    testPersistent() {
      this.lastAction = 'Persistent Toast'
      
      if (this.toast && this.toast.warning) {
        this.toast.warning('This toast will not auto-dismiss - click the X to close', {
          persistent: true
        })
      } else {
        console.error('❌ Cannot create persistent toast')
        alert('Cannot create persistent toast - check console')
      }
    },
    
    testMultiple() {
      this.lastAction = 'Multiple Toasts'
      
      if (this.toast) {
        this.toast.success('First toast')
        setTimeout(() => this.toast.info('Second toast'), 500)
        setTimeout(() => this.toast.warning('Third toast'), 1000)
        setTimeout(() => this.toast.error('Fourth toast'), 1500)
      } else {
        console.error('❌ Cannot create multiple toasts')
        alert('Cannot create multiple toasts - check console')
      }
    },
    
    clearAll() {
      this.lastAction = 'Clear All'
      
      if (this.toast && this.toast.dismissAll) {
        this.toast.dismissAll()
      } else {
        console.error('❌ Toast dismissAll method not available')
        alert('Toast dismissAll method not available - check console')
      }
    },
    
    consoleTest() {
      // Display relevant toast debug info in an alert for easy viewing
      alert(`Toast Debug Info:
      
Composable: ${this.composableAvailable ? 'Available' : 'Not Available'}
Container: ${this.containerPresent ? 'Present' : 'Missing'}
Active Toasts: ${this.toastCount}
Methods Available: ${this.toast ? Object.keys(this.toast).join(', ') : 'None'}`)
    }
  }
}
</script>

<style scoped>
.toast-debug-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1rem;
}

.card {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border-radius: 0.5rem;
  overflow: hidden;
}

.card-header {
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-bottom: 1px solid #dee2e6;
}

.card-header h4 {
  margin: 0 0 0.5rem 0;
  color: #495057;
}

.card-body {
  padding: 1.5rem;
}

.debug-info {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #dee2e6;
}

.alert {
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
}

.alert-info {
  background-color: #cce7ff;
  border-color: #99d3ff;
  color: #0066cc;
}

.alert-secondary {
  background-color: #f8f9fa;
  border-color: #dee2e6;
  color: #6c757d;
}

h5 {
  color: #495057;
  margin-bottom: 1rem;
  font-weight: 600;
}

.btn {
  margin-bottom: 0.5rem;
}

@media (max-width: 768px) {
  .toast-debug-container {
    margin: 1rem;
    padding: 0.5rem;
  }
  
  .card-header,
  .card-body {
    padding: 1rem;
  }
  
  .d-flex.gap-2 {
    gap: 0.5rem !important;
  }
}
</style>