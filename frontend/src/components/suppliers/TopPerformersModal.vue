<template>
  <div class="modal fade" :class="{ show: show }" :style="{ display: show ? 'block' : 'none' }" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content surface-card border-theme">
        <div class="modal-header surface-secondary border-theme">
          <h5 class="modal-title">
            <TrendingUp :size="20" class="me-2 text-accent" />
            <span class="text-primary">Top Performing Suppliers</span>
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        <div class="modal-body surface-card">
          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-accent" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
          
          <div v-else-if="suppliers.length === 0" class="text-center py-4">
            <TrendingUp :size="48" class="text-tertiary-medium mb-3" />
            <p class="text-tertiary-medium">No top performers found</p>
          </div>
          
          <div v-else class="row g-3">
            <div v-for="(supplier, index) in suppliers" :key="supplier.id" class="col-12">
              <div :class="['supplier-card surface-card border-theme', index === 0 ? 'supplier-card--highlight' : '']">
                <div class="card-body p-4">
                  <div class="d-flex align-items-center mb-3">
                    <div class="rank-badge surface-secondary border-theme me-3">
                      <span class="fw-bold text-primary">#{{ index + 1 }}</span>
                    </div>
                    <div class="flex-grow-1">
                      <h6 class="mb-1 fw-bold text-primary">{{ supplier.name }}</h6>
                      <p class="text-tertiary-medium mb-0">{{ supplier.email }}</p>
                    </div>
                    <div class="text-end">
                      <div class="d-flex align-items-center mb-1">
                        <Star :size="16" class="text-warning me-1" :fill="supplier.rating !== 'N/A' ? 'currentColor' : 'none'" />
                        <span class="fw-bold text-primary">{{ supplier.rating }}</span>
                      </div>
                      <small class="text-tertiary-medium">{{ supplier.onTimeDelivery }}% on-time</small>
                    </div>
                  </div>
                  
                  <div class="row g-3 mb-3">
                    <div class="col-6 col-md-3">
                      <div class="stat-card surface-tertiary border-theme text-center">
                        <div class="stat-value text-accent">{{ supplier.totalOrders }}</div>
                        <small class="text-tertiary-medium">Total Orders</small>
                      </div>
                    </div>
                    <div class="col-6 col-md-3">
                      <div class="stat-card surface-tertiary border-theme text-center">
                        <div class="stat-value text-accent">₱{{ formatCurrency(supplier.totalValue) }}</div>
                        <small class="text-tertiary-medium">Total Value</small>
                      </div>
                    </div>
                    <div class="col-6 col-md-3">
                      <div class="stat-card surface-tertiary border-theme text-center">
                        <div class="stat-value text-accent">₱{{ formatCurrency(supplier.averageOrderValue, 2) }}</div>
                        <small class="text-tertiary-medium">Avg Order</small>
                      </div>
                    </div>
                    <div class="col-6 col-md-3">
                      <div class="stat-card surface-tertiary border-theme text-center">
                        <div class="stat-value text-primary">{{ formatDate(supplier.lastOrder) }}</div>
                        <small class="text-tertiary-medium">Last Order</small>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <small class="text-tertiary-medium">Top Products:</small>
                    <div class="mt-2 d-flex flex-wrap gap-2">
                      <span
                        v-for="(product, pIndex) in supplier.topProducts"
                        :key="pIndex"
                        class="product-pill surface-tertiary border-theme text-primary"
                      >
                        {{ getProductDisplayName(product) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer surface-secondary border-theme">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Backdrop -->
  <div v-if="show" class="modal-backdrop fade show" @click="$emit('close')"></div>
</template>

<script>
import { TrendingUp, Star } from 'lucide-vue-next'

export default {
  name: 'TopPerformersModal',
  components: {
    TrendingUp,
    Star
  },
  props: {
    show: {
      type: Boolean,
      default: false
    },
    suppliers: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  methods: {
    formatDate(dateString) {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      })
    },

    formatCurrency(amount, decimals = 0) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }).format(amount || 0)
    },

    getProductDisplayName(product) {
      // Product is already the name from batches, but handle edge cases
      // If it looks like an ID (starts with PROD-), try to extract name
      if (product && product.startsWith && product.startsWith('PROD-')) {
        // This means we got an ID instead of name - should not happen with enrichment
        // But keep as fallback
        return product
      }
      // Return the product name as-is (already enriched from batches)
      return product || 'Unknown Product'
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.text-tertiary-medium {
  color: var(--text-tertiary, var(--tertiary-medium)) !important;
}

.modal {
  align-items: center;
  justify-content: center;
}

.modal-backdrop.show {
  opacity: 0.6;
  background-color: rgba(0, 0, 0, 0.6);
  position: fixed;
  inset: 0;
  z-index: 1040;
}

.modal-content {
  border-radius: 1rem;
  border: 1px solid var(--border-primary);
  box-shadow: none;
}

.modal-header,
.modal-footer {
  border-color: var(--border-primary);
  padding: 1.5rem;
}

.modal-footer {
  justify-content: flex-end;
}

.supplier-card {
  border-radius: 1rem;
  border: 1px solid var(--border-primary);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  box-shadow: none;
}

.supplier-card--highlight {
  border-color: var(--accent);
}

.supplier-card:hover {
  transform: translateY(-2px);
  box-shadow: none;
  border-color: var(--accent);
}

.rank-badge {
  width: 48px;
  height: 48px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-primary);
  box-shadow: none;
}

.stat-card {
  border-radius: 0.75rem;
  padding: 0.85rem;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.product-pill {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
  display: inline-flex;
  align-items: center;
  border-width: 1px;
  gap: 0.35rem;
}

.card-body {
  padding: 1.5rem;
}
</style>