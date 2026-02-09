<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content modern-modal order-details-modal" @click.stop>
        <div class="modal-header border-0 pb-0">
          <div class="d-flex align-items-center flex-grow-1">
            <div class="modal-icon me-3">
              <component :is="isEditMode ? Edit : Eye" :size="24" />
            </div>
            <div class="flex-grow-1">
              <h4 class="modal-title mb-1">
                {{ isEditMode ? 'Edit Order' : 'Order Details' }}
              </h4>
              <p class="text-muted mb-0 small">
                {{ isEditMode ? 'Modify order information' : 'View order information' }}
              </p>
            </div>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button 
              v-if="!isEditMode && canEdit" 
              type="button" 
              class="btn btn-primary btn-sm"
              @click="toggleEditMode"
            >
              <Edit :size="16" class="me-1" />
              Edit Order
            </button>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
        </div>
        
        <div class="modal-body pt-4">
          <!-- Order Header Info -->
          <div class="row mb-4">
            <div class="col-md-6">
              <div class="info-card">
                <h6 class="info-card-title">
                  <FileText :size="16" class="me-2" />
                  Order Information
                </h6>
                <div class="info-item">
                  <label>Order ID:</label>
                  <span class="order-id-text">{{ order.id }}</span>
                </div>
                <div class="info-item">
                  <label>Order Date:</label>
                  <span>{{ formatDate(order.date) }}</span>
                </div>
                <div class="info-item">
                  <label>Expected Date:</label>
                  <div v-if="!isEditMode">
                    <span>{{ formatDate(order.expectedDate) }}</span>
                    <br>
                    <small :class="['text-muted', { 'text-danger': isOverdue(order) }]">
                      {{ getTimeRemaining(order.expectedDate) }}
                    </small>
                  </div>
                  <input 
                    v-else
                    type="date" 
                    class="form-control form-control-sm"
                    v-model="editForm.expectedDate"
                  >
                </div>
                <div class="info-item mb-0">
                  <label>Status:</label>
                  <div v-if="!isEditMode">
                    <span :class="['badge', 'order-status', getOrderStatusClass(order.status)]">
                      {{ order.status }}
                    </span>
                  </div>
                  <select v-else class="form-select form-select-sm" v-model="editForm.status">
                    <option value="Pending">Pending</option>
                    <option value="Active">Active</option>
                    <option value="Received">Received</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>
                </div>
              </div>
            </div>
            
            <div class="col-md-6">
              <div class="info-card">
                <h6 class="info-card-title">
                  <DollarSign :size="16" class="me-2" />
                  Financial Summary
                </h6>
                <div class="info-item">
                  <label>Total Items:</label>
                  <span>{{ displayItemCount }} item(s)</span>
                </div>
                <div class="info-item">
                  <label>Total Quantity:</label>
                  <span>{{ displayTotalQuantity }}</span>
                </div>
                <div class="info-item">
                  <label>Subtotal:</label>
                  <span class="text-muted">₱{{ formatCurrency(order.subtotal || 0) }}</span>
                </div>
                <div class="info-item">
                  <label>Tax ({{ order.taxRate || 12 }}%):</label>
                  <span class="text-muted">₱{{ formatCurrency(order.tax || 0) }}</span>
                </div>
                <div class="info-item">
                  <label>Shipping:</label>
                  <div v-if="!isEditMode">
                    <span class="text-muted">₱{{ formatCurrency(order.shippingCost || 0) }}</span>
                  </div>
                  <div v-else class="input-group input-group-sm">
                    <span class="input-group-text">₱</span>
                    <input 
                      type="number" 
                      class="form-control"
                      v-model.number="editForm.shippingCost"
                      min="0"
                      step="0.01"
                    >
                  </div>
                </div>
                <div class="info-item mb-0">
                  <label>Total Cost:</label>
                  <span class="amount-text">₱{{ formatCurrency(order.total) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Order Items (if available) -->
          <div v-if="orderItems && orderItems.length > 0" class="info-card mb-4">
            <h6 class="info-card-title">
              <List :size="16" class="me-2" />
              Order Items
              <span class="badge bg-secondary ms-2">{{ orderItems.length }}</span>
            </h6>
            <div class="table-responsive">
              <table class="table table-sm items-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item Name / Description</th>
                    <th>Quantity</th>
                    <th>Unit</th>
                    <th>Unit Price</th>
                    <th>Total Price</th>
                    <th v-if="!isEditMode">Notes</th>
                    <th v-if="isEditMode">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in orderItems" :key="`item-${index}`">
                    <td>{{ index + 1 }}</td>
                    <td>
                      <input 
                        v-if="isEditMode"
                        type="text" 
                        class="form-control form-control-sm"
                        v-model="item.name"
                        placeholder="Enter item name or description"
                      >
                      <span v-else class="fw-medium">{{ item.name }}</span>
                    </td>
                    <td>
                      <input 
                        v-if="isEditMode"
                        type="number" 
                        class="form-control form-control-sm"
                        v-model.number="item.quantity"
                        min="1"
                        @input="calculateItemTotal(item)"
                        style="width: 80px;"
                      >
                      <span v-else class="fw-bold">{{ item.quantity }}</span>
                    </td>
                    <td>
                      <select 
                        v-if="isEditMode"
                        class="form-select form-select-sm"
                        v-model="item.unit"
                        style="width: 80px;"
                      >
                        <option value="pcs">pcs</option>
                        <option value="kg">kg</option>
                        <option value="lbs">lbs</option>
                        <option value="box">box</option>
                        <option value="pack">pack</option>
                        <option value="bottle">bottle</option>
                        <option value="can">can</option>
                      </select>
                      <span v-else class="text-muted">{{ item.unit || 'pcs' }}</span>
                    </td>
                    <td>
                      <div v-if="isEditMode" class="input-group input-group-sm" style="width: 120px;">
                        <span class="input-group-text">₱</span>
                        <input 
                          type="number" 
                          class="form-control"
                          v-model.number="item.unitPrice"
                          min="0"
                          step="0.01"
                          @input="calculateItemTotal(item)"
                        >
                      </div>
                      <span v-else>₱{{ formatCurrency(item.unitPrice) }}</span>
                    </td>
                    <td>
                      <span class="fw-bold text-success">₱{{ formatCurrency(item.totalPrice) }}</span>
                    </td>
                    <td v-if="!isEditMode">
                      <small class="text-muted">{{ item.notes || '-' }}</small>
                    </td>
                    <td v-if="isEditMode">
                      <div class="d-flex gap-1">
                        <input 
                          type="text" 
                          class="form-control form-control-sm"
                          v-model="item.notes"
                          placeholder="Notes"
                          style="width: 100px;"
                        >
                        <button 
                          type="button" 
                          class="btn btn-outline-danger btn-sm"
                          @click="removeItem(index)"
                          :disabled="orderItems.length <= 1"
                          title="Remove Item"
                        >
                          <Trash2 :size="12" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
                <tfoot v-if="orderItems.length > 1">
                  <tr class="table-light">
                    <td colspan="2" class="fw-bold">Total</td>
                    <td class="fw-bold">{{ displayTotalQuantity }}</td>
                    <td></td>
                    <td></td>
                    <td class="fw-bold text-success">₱{{ formatCurrency(displayTotalAmount) }}</td>
                    <td v-if="!isEditMode"></td>
                    <td v-if="isEditMode"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <!-- Show message if no items -->
          <div v-else class="info-card mb-4">
            <h6 class="info-card-title">
              <List :size="16" class="me-2" />
              Order Items
            </h6>
            <div class="text-center py-4 text-muted">
              <Package :size="48" class="mb-2 opacity-50" />
              <p class="mb-0">
                {{ itemsReady ? 'No items found for this order' : 'Loading items...' }}
              </p>
            </div>
          </div>

          <!-- Order Description -->
          <div class="info-card mb-4">
            <h6 class="info-card-title">
              <Package :size="16" class="me-2" />
              Order Description
            </h6>
            <div v-if="!isEditMode" class="description-content">
              {{ order.description || 'No description provided' }}
            </div>
            <textarea 
              v-else
              class="form-control"
              v-model="editForm.description"
              rows="3"
              placeholder="Enter order description..."
            ></textarea>
          </div>

          <!-- Order Notes -->
          <div class="info-card mb-4">
            <h6 class="info-card-title">
              <MessageSquare :size="16" class="me-2" />
              Order Notes
            </h6>
            <div v-if="!isEditMode" class="notes-content">
              {{ order.notes || 'No notes available' }}
            </div>
            <textarea 
              v-else
              class="form-control"
              v-model="editForm.notes"
              rows="3"
              placeholder="Add notes about this order..."
            ></textarea>
          </div>

          <!-- Order Timeline/History -->
          <div v-if="orderHistory && orderHistory.length > 0" class="info-card">
            <h6 class="info-card-title">
              <Clock :size="16" class="me-2" />
              Order History
            </h6>
            <div class="timeline">
              <div v-for="event in orderHistory" :key="event.id" class="timeline-item">
                <div class="timeline-marker" :class="getEventMarkerClass(event.type)">
                  <component :is="getEventIcon(event.type)" :size="12" />
                </div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <strong>{{ event.title }}</strong>
                    <small class="text-muted ms-auto">{{ formatTimeAgo(event.date) }}</small>
                  </div>
                  <p class="mb-1 text-muted">{{ event.description }}</p>
                  <small class="text-muted">by {{ event.user }}</small>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer border-0 pt-4">
          <div class="d-flex justify-content-between w-100">
            <div>
              <button 
                v-if="!isEditMode" 
                type="button" 
                class="btn btn-outline-primary"
                @click="printOrder"
              >
                <Printer :size="16" class="me-1" />
                Print
              </button>
            </div>
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-secondary" @click="handleCancel">
                {{ isEditMode ? 'Cancel' : 'Close' }}
              </button>
              <button 
                v-if="isEditMode" 
                type="button" 
                class="btn btn-primary" 
                @click="saveOrder"
                :disabled="saving || !isFormValid"
              >
                <div v-if="saving" class="spinner-border spinner-border-sm me-2"></div>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import {
  Eye,
  Edit,
  FileText,
  DollarSign,
  Package,
  List,
  MessageSquare,
  Clock,
  Plus,
  Trash2,
  Printer,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity
} from 'lucide-vue-next'

export default {
  name: 'OrderDetailsModal',
  components: {
    Eye,
    Edit,
    FileText,
    DollarSign,
    Package,
    List,
    MessageSquare,
    Clock,
    Plus,
    Trash2,
    Printer,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Activity
  },
  props: {
    show: {
      type: Boolean,
      default: false
    },
    order: {
      type: Object,
      required: true
    },
    canEdit: {
      type: Boolean,
      default: true
    },
    initialMode: {
      type: String,
      default: 'view',
      validator: value => ['view', 'edit'].includes(value)
    }
  },
  emits: ['close', 'save', 'edit-mode-changed'],
  data() {
    return {
      isEditMode: false,
      saving: false,
      Edit,
      Eye,
      editForm: {
        expectedDate: '',
        status: '',
        quantity: 0,
        total: 0,
        description: '',
        notes: ''
      },
      editableItems: [],
      orderItems: [],
      orderHistory: [],
      // Force reactive updates
      itemsReady: false
    }
  },
  computed: {
    displayItemCount() {
      // Direct access without itemsReady check
      return this.orderItems?.length || 0
    },
    
    displayTotalQuantity() {
      if (!this.orderItems || this.orderItems.length === 0) return 0
      return this.orderItems.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0)
    },
    
    displayTotalAmount() {
      if (!this.orderItems || this.orderItems.length === 0) return 0
      return this.orderItems.reduce((sum, item) => sum + (Number(item.totalPrice) || 0), 0)
    },
    
    isFormValid() {
      return this.editForm.quantity > 0 && 
            this.editForm.total > 0 && 
            this.editForm.expectedDate && 
            this.editForm.status
    }
  },
  watch: {
    show: {
      handler(newVal) {
        try {
          if (newVal) {
            this.initializeModal()
          }
        } catch (error) {
          console.error('Error in show watcher:', error)
        }
      },
      immediate: true
    },
    
    order: {
      handler(newOrder, oldOrder) {
        try {
          if (this.show && newOrder) {
            this.initializeModal()
          }
        } catch (error) {
          console.error('Error in order watcher:', error)
        }
      },
      deep: true,
      immediate: false  // Changed to false to prevent double initialization
    },
    
    initialMode: {
      handler(newMode) {
        try {
          if (this.show) {
            this.isEditMode = newMode === 'edit'
            this.$emit('edit-mode-changed', this.isEditMode)
          }
        } catch (error) {
          console.error('Error in initialMode watcher:', error)
        }
      },
      immediate: true
    }
  },
  methods: {
    initializeModal() {
      this.isEditMode = this.initialMode === 'edit'
      this.resetEditForm()
      this.loadOrderData()
      this.$emit('edit-mode-changed', this.isEditMode)
    },

    handleOverlayClick(event) {
      if (event.target === event.currentTarget && !this.saving) {
        if (this.isEditMode) {
          this.isEditMode = false
          this.resetEditForm()
          this.editableItems = [...this.orderItems]
          this.$emit('edit-mode-changed', this.isEditMode)
        }
        this.closeModal()
      }
    },

    resetEditForm() {
      const formatDateForInput = (dateString) => {
        if (!dateString) return ''
        const date = new Date(dateString)
        return date.toISOString().split('T')[0]
      }

      this.editForm = {
        expectedDate: formatDateForInput(this.order.expectedDate),
        status: this.order.status || 'Pending',
        quantity: this.order.quantity || 0,
        total: this.order.total || 0,
        description: this.order.description || '',
        notes: this.order.notes || '',
        priority: this.order.priority || 'normal',
        subtotal: this.order.subtotal || 0,
        tax: this.order.tax || 0,
        shippingCost: this.order.shippingCost || 0
      }
    },

    safeNumber(value, defaultValue = 0) {
      const num = Number(value)
      return isNaN(num) ? defaultValue : num
    },

    loadOrderData() {
      try {
        // Reset state
        this.itemsReady = false
        
        // Validate order object
        if (!this.order) {
          console.warn('No order object provided')
          this.orderItems = []
          this.editableItems = []
          this.itemsReady = true
          return
        }
        
        // Process items with better error handling
        if (this.order.items && Array.isArray(this.order.items) && this.order.items.length > 0) {
          // Create new arrays with proper reactivity
          const processedItems = this.order.items.map((item, index) => {
            const processedItem = {
              name: item?.name || item?.product_name || `Item ${index + 1}`,
              quantity: Number(item?.quantity) || 0,
              unit: item?.unit || 'pcs',
              unitPrice: Number(item?.unitPrice || item?.unit_price) || 0,
              notes: item?.notes || '',
              productId: item?.productId || item?.product_id || `temp-${index}`,
              totalPrice: 0
            }
            
            // Calculate total price
            processedItem.totalPrice = processedItem.quantity * processedItem.unitPrice
            
            return processedItem
          })
          
          // Assign new arrays directly (Vue 3 handles reactivity automatically)
          this.orderItems = [...processedItems]
          this.editableItems = JSON.parse(JSON.stringify(processedItems))
        } else {
          this.orderItems = []
          this.editableItems = []
        }
        
        // Load order history safely
        try {
          this.orderHistory = this.order?.orderHistory || []
        } catch (historyError) {
          console.error('Error loading order history:', historyError)
          this.orderHistory = []
        }
        
        // Signal that items are ready
        this.itemsReady = true

        // Force update in Vue 3
        this.$nextTick(() => {
          // Force re-render if needed
          this.$forceUpdate()
        })
        
      } catch (error) {
        console.error('Critical error in loadOrderData:', error)
        this.itemsReady = true
        this.orderItems = []
        this.editableItems = []
        this.orderHistory = []
      }
    },

    toggleEditMode() {
      this.isEditMode = !this.isEditMode
      if (this.isEditMode) {
        this.resetEditForm()
        this.editableItems = [...this.orderItems]
      }
      this.$emit('edit-mode-changed', this.isEditMode)
    },

    handleCancel() {
      if (this.isEditMode) {
        this.isEditMode = false
        this.resetEditForm()
        this.editableItems = [...this.orderItems]
      } else {
        this.closeModal()
      }
    },

    closeModal() {
      this.isEditMode = false
      this.$emit('close')
    },

    async saveOrder() {
      this.saving = true
      
      try {
        const subtotal = this.getTotalAmount()
        const tax = subtotal * 0.12
        const shipping = this.editForm.shippingCost || 0
        const total = subtotal + tax + shipping

        const updatedOrder = {
          ...this.order,
          ...this.editForm,
          quantity: this.getTotalQuantity(),
          subtotal: subtotal,
          tax: tax,
          total: total,
          items: this.editableItems.map(item => ({
            name: item.name,
            quantity: item.quantity,
            unit: item.unit,
            unitPrice: item.unitPrice,
            totalPrice: item.totalPrice,
            notes: item.notes
          }))
        }

        this.$emit('save', updatedOrder)
        this.isEditMode = false
        
      } catch (error) {
        console.error('Error saving order:', error)
        alert('Failed to save order. Please try again.')
      } finally {
        this.saving = false
      }
    },

    addNewItem() {
      this.editableItems.push({
        name: '',
        quantity: 1,
        unit: 'pcs',
        unitPrice: 0,
        totalPrice: 0,
        notes: ''
      })
    },

    removeItem(index) {
      if (this.editableItems.length > 1) {
        this.editableItems.splice(index, 1)
        this.updateFormTotals()
      }
    },

    calculateItemTotal(item) {
      item.totalPrice = (item.quantity || 0) * (item.unitPrice || 0)
      this.updateFormTotals()
    },

    updateFormTotals() {
      this.editForm.quantity = this.getTotalQuantity()
      this.editForm.total = this.getTotalAmount()
    },

    getTotalQuantity() {
      return this.displayTotalQuantity
    },

    getTotalAmount() {
      return this.displayTotalAmount
    },

    printOrder() {
      window.print()
    },

    // Utility methods
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },

    formatTimeAgo(dateString) {
      const date = new Date(dateString)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
      const diffHours = Math.floor(diffTime / (1000 * 60 * 60))

      if (diffDays > 0) {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
      } else if (diffHours > 0) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
      } else {
        return 'Just now'
      }
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0)
    },

    getCostPerItem() {
      return this.isEditMode 
        ? (this.editForm.total || 0) / (this.editForm.quantity || 1)
        : (this.order.total || 0) / (this.order.quantity || 1)
    },

    isOverdue(order) {
      const expectedDate = new Date(order.expectedDate)
      const today = new Date()
      return expectedDate < today && (order.status === 'Pending' || order.status === 'Active')
    },

    getTimeRemaining(dateString) {
      const expectedDate = new Date(dateString)
      const today = new Date()
      const diffTime = expectedDate - today
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) {
        return `${Math.abs(diffDays)} days overdue`
      } else if (diffDays === 0) {
        return 'Due today'
      } else if (diffDays === 1) {
        return 'Due tomorrow'
      } else {
        return `${diffDays} days remaining`
      }
    },

    getOrderStatusClass(status) {
      const classes = {
        'Received': 'bg-success',
        'Pending': 'bg-warning',
        'Cancelled': 'bg-danger',
        'Active': 'bg-primary'
      }
      return classes[status] || 'bg-secondary'
    },

    getEventIcon(type) {
      const icons = {
        created: Plus,
        updated: Edit,
        cancelled: XCircle,
        received: CheckCircle
      }
      return icons[type] || Activity
    },

    getEventMarkerClass(type) {
      const classes = {
        created: 'bg-primary',
        updated: 'bg-info',
        cancelled: 'bg-danger',
        received: 'bg-success'
      }
      return classes[type] || 'bg-secondary'
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.modern-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background-color: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  z-index: 9999 !important;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.3s ease;
}

.order-details-modal {
  width: min(1100px, 95vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 10000 !important;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-dark);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2rem 2rem 1rem 2rem;
  border-bottom: 1px solid var(--neutral);
  background-color: var(--surface-tertiary);
  flex-shrink: 0;
}

.modal-body {
  padding: 1.5rem 2rem 2rem 2rem;
  overflow-y: auto;
  background-color: var(--surface-elevated);
  flex: 1;
  max-height: calc(90vh - 220px);
}

.modal-footer {
  padding: 1.5rem 2rem 2rem 2rem;
  background-color: var(--surface-tertiary);
  border-top: 1px solid var(--neutral);
  flex-shrink: 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-header .d-flex.align-items-center.flex-grow-1 {
  min-width: 0;
}

.modal-header .d-flex.align-items-center.gap-2 {
  flex-shrink: 0;
  margin-left: auto;
}

.modal-header .btn {
  white-space: nowrap;
}

.modal-header .btn-close {
  padding: 0.5rem;
  margin-left: 0.5rem;
}

.info-card {
  background: var(--neutral-light);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.info-card:last-child {
  margin-bottom: 0;
}

.info-card-title {
  color: var(--tertiary-dark);
  font-weight: 600;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--neutral);
  padding-bottom: 0.5rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--neutral);
}

.info-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}

.info-item label {
  font-weight: 500;
  color: var(--tertiary-medium);
  font-size: 0.875rem;
  margin-bottom: 0;
  flex-shrink: 0;
  width: 120px;
}

.info-item span, .info-item div {
  color: var(--tertiary-dark);
  font-weight: 500;
  text-align: right;
  flex-grow: 1;
}

.order-id-text {
  font-family: 'Monaco', 'Menlo', monospace;
  color: var(--primary) !important;
  font-weight: 600;
}

.amount-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--success) !important;
}

.description-content, .notes-content {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--neutral);
  min-height: 60px;
  color: var(--tertiary-dark);
  line-height: 1.6;
}

.items-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.875rem;
}

.items-table th {
  background: var(--primary-light);
  color: var(--primary-dark);
  font-weight: 600;
  border: none;
  padding: 0.75rem 0.5rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.items-table td {
  padding: 0.75rem 0.5rem;
  border-top: 1px solid var(--neutral);
  vertical-align: middle;
}

.items-table tbody tr:hover {
  background-color: var(--neutral-light);
}

.items-table tfoot tr {
  border-top: 2px solid var(--primary);
}

.items-table tfoot td {
  font-weight: 600;
  background-color: var(--neutral-light);
}

/* Form controls in table */
.items-table .form-control-sm,
.items-table .form-select-sm {
  font-size: 0.75rem;
}

.items-table .input-group-sm .input-group-text {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  margin-bottom: 1.5rem;
  position: relative;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 30px;
  bottom: -24px;
  width: 2px;
  background-color: var(--neutral-medium);
}

.timeline-marker {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 1rem;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.timeline-content {
  flex-grow: 1;
}

.timeline-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.order-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

/* Form controls in edit mode */
.form-control:focus,
.form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-item label {
    width: auto;
    margin-bottom: 0.25rem;
  }
  
  .info-item span, .info-item div {
    text-align: left;
  }
}
</style>