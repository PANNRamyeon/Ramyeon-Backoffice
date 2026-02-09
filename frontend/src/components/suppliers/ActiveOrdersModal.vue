<template>
  <div class="modal fade" :class="{ show: show }" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <Package :size="20" class="me-2 text-warning" />
            {{ modalTitle }}
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        <div class="modal-body">
          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2 text-muted">Loading active orders...</p>
          </div>
          
          <div v-else-if="processedOrders.length === 0" class="text-center py-4">
            <Package :size="48" class="text-tertiary-medium mb-3" />
            <p class="text-tertiary-medium">No active orders found</p>
            <small class="text-muted">There are currently no pending purchase orders</small>
          </div>
          
          <div v-else class="row g-3">
            <div v-for="order in processedOrders" :key="order.id" class="col-12">
              <div class="card border-start border-warning border-3">
                <div class="card-body">
                  <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                      <h6 class="mb-1 fw-bold">{{ order.id }}</h6>
                      <p class="text-tertiary-medium mb-1">{{ order.supplier }}</p>
                      <small class="text-tertiary-medium">Ordered: {{ formatDate(order.orderDate) }}</small>
                    </div>
                    <div class="text-end">
                      <h5 class="mb-1 text-warning fw-bold">₱{{ formatCurrency(order.totalAmount) }}</h5>
                      <span :class="getStatusBadgeClass(order.status)" class="badge">
                        {{ getStatusText(order.status) }}
                      </span>
                    </div>
                  </div>
                  
                  <div class="mb-3">
                    <small class="text-tertiary-medium">Expected Delivery:</small>
                    <div class="fw-semibold">{{ formatDate(order.expectedDelivery) }}</div>
                  </div>
                  
                  <div class="border-top pt-2">
                    <small class="text-tertiary-medium">Items ({{ order.items?.length || 0 }}):</small>
                    <div class="mt-1">
                      <div v-for="(item, index) in order.items" :key="index" class="d-flex justify-content-between small">
                        <div>
                          <div class="fw-medium">{{ getProductName(item) }}</div>
                          <small class="text-muted">{{ getProductId(item) }}</small>
                        </div>
                        <div class="text-end">
                          <div>{{ item.quantity }}x</div>
                          <div class="fw-medium">₱{{ formatCurrency(item.quantity * item.unitPrice) }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">Close</button>
          <button type="button" class="btn btn-warning" @click="handleViewAllOrders">View All Orders</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Backdrop -->
  <div v-if="show" class="modal-backdrop fade show" @click="$emit('close')"></div>
</template>

<script>
import { Package } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

export default {
  name: 'ActiveOrdersModal',
  components: {
    Package
  },
  props: {
    show: {
      type: Boolean,
      default: false
    },
    orders: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    supplier: {
      type: Object,
      default: null
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const router = useRouter()

    const handleViewAllOrders = () => {
      emit('close')
      router.push({ name: 'OrdersHistory' })
    }

    return {
      handleViewAllOrders
    }
  },
  computed: {
    modalTitle() {
      if (this.supplier) {
        return `Active Orders - ${this.supplier.name}`
      }
      return 'Active Purchase Orders'
    },

    processedOrders() {
      if (!this.orders || this.orders.length === 0) {
        return []
      }

      // Filter orders based on supplier if provided
      let filtered = this.orders
      if (this.supplier) {
        filtered = this.orders.filter(order => 
          order.supplierId === this.supplier.id || 
          order.supplier === this.supplier.name ||
          order.supplierId === this.supplier.id
        )
      }
      
      // Process each order to ensure consistent data structure
      return filtered.map(order => ({
        ...order,
        items: (order.items || []).map(item => ({
          ...item,
          // Ensure we have consistent product name and ID fields
          productName: this.getProductName(item),
          productId: this.getProductId(item)
        }))
      }))
    }
  },
  methods: {
    getProductName(item) {
      // Try multiple possible fields for product name
      return item.name || 
             item.product_name || 
             item.productName || 
             'Unknown Product'
    },

    getProductId(item) {
      // Try multiple possible fields for product ID
      return item.productId || 
             item.product_id || 
             item.id || 
             'N/A'
    },

    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      })
    },

    formatCurrency(amount) {
      if (!amount || isNaN(amount)) return '0.00'
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount)
    },

    getStatusBadgeClass(status) {
      const statusClasses = {
        'Pending Delivery': 'bg-warning text-dark',
        'Partially Received': 'bg-info text-white',
        'Received': 'bg-success text-white',
        'Depleted': 'bg-secondary text-white',
        'Mixed Status': 'bg-primary text-white'
      }
      return statusClasses[status] || 'bg-secondary text-white'
    },

    getStatusText(status) {
      return status || 'Unknown'
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

/* Modal styling */
.modal-backdrop.show {
  opacity: 0.5;
  background-color: rgba(0, 0, 0, 0.5);
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1040;
  pointer-events: auto;
}

.modal-backdrop:not(.show) {
  display: none !important;
  pointer-events: none;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
}

.modal.show {
  display: flex !important;
  z-index: 1055;
}

.modal:not(.show) {
  display: none !important;
  pointer-events: none;
}

.modal.show .modal-dialog {
  transform: none;
  margin: 0;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-dialog {
  position: relative;
  width: auto;
  max-width: 800px;
  margin: 0 auto;
}

.modal-content {
  border-radius: 0.75rem;
  border: none;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-body {
  overflow-y: auto;
  max-height: calc(90vh - 140px);
}

.modal-header {
  border-bottom: 1px solid var(--neutral-light);
  padding: 1.5rem;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  max-height: calc(90vh - 140px);
}

.modal-footer {
  border-top: 1px solid var(--neutral-light);
  padding: 1rem 1.5rem;
}
</style>