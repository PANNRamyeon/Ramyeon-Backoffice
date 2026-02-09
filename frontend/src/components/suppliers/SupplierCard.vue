<template>
  <div class="card h-100 supplier-card" :class="{ 'card-selected': isSelected }">
    <div class="card-body d-flex flex-column">
      <!-- Supplier Header with Checkbox -->
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div class="d-flex align-items-center">
          <input 
            type="checkbox" 
            class="form-check-input me-3"
            :value="supplier.id"
            :checked="isSelected"
            @change="$emit('toggle-select', supplier.id)"
          />
          <div class="supplier-icon me-3">
            <i class="bi bi-building"></i>
          </div>
          <h5 class="card-title mb-0 supplier-name">
            {{ supplier.name }}
            <button
              @click.stop="$emit('toggle-favorite', supplier)"
              class="btn btn-link p-0 ms-2 favorite-toggle"
              type="button"
              :title="supplier.isFavorite ? 'Remove from favorites' : 'Add to favorites'"
            >
              <Star 
                :size="18" 
                class="favorite-star" 
                :class="{ 'favorite-filled': supplier.isFavorite }"
                :fill="supplier.isFavorite ? 'currentColor' : 'none'"
                :stroke-width="supplier.isFavorite ? 2 : 2.5"
              />
            </button>
          </h5>
        </div>
        <div class="dropdown">
          <button 
            class="btn btn-link p-0 dropdown-toggle-btn"
            type="button"
            :id="`dropdownMenuButton${supplier.id}`"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            <i class="bi bi-three-dots-vertical"></i>
          </button>
          <ul class="dropdown-menu" :aria-labelledby="`dropdownMenuButton${supplier.id}`">
            <li>
              <a class="dropdown-item" href="#" @click.prevent="$emit('edit', supplier)">
                <i class="bi bi-pencil me-2"></i>Edit
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="#" @click.prevent="$emit('view', supplier)">
                <i class="bi bi-eye me-2"></i>View Details
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="#" @click.prevent="$emit('create-order', supplier)">
                <i class="bi bi-plus me-2"></i>New Order
              </a>
            </li>
            <li><hr class="dropdown-divider"></li>
            <li>
              <a class="dropdown-item text-danger" href="#" @click.prevent="$emit('delete', supplier)">
                <i class="bi bi-trash me-2"></i>Delete
              </a>
            </li>
          </ul>
        </div>
      </div>

      <!-- Supplier Info -->
      <div class="mb-3">
        <div class="supplier-contact mb-2">
          <i class="bi bi-envelope contact-icon me-2"></i>
          <span class="contact-text">{{ supplier.email || 'No email' }}</span>
        </div>
        <div class="supplier-contact mb-2">
          <i class="bi bi-telephone contact-icon me-2"></i>
          <span class="contact-text">{{ supplier.phone || 'No phone' }}</span>
        </div>
        <div class="supplier-contact">
          <i class="bi bi-geo-alt contact-icon me-2"></i>
          <span class="contact-text">{{ getShortAddress(supplier.address) }}</span>
        </div>
      </div>

      <!-- Purchase Orders Info -->
      <div class="mb-3 mt-auto">
        <p class="purchase-orders-label mb-2">Purchase Orders</p>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="purchase-orders-count">{{ supplier.purchaseOrders }}</span>
          <span :class="['badge', 'rounded-pill', getStatusBadgeClass(supplier.status)]">
            {{ formatStatus(supplier.status) }}
          </span>
        </div>
        
        <!-- Additional Stats -->
        <div class="supplier-stats">
          <div class="stat-row">
            <span class="stat-label">Active Orders:</span>
            <span class="stat-value text-warning">{{ supplier.activeOrders || 0 }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Total Spent:</span>
            <span class="stat-value text-success">₱{{ formatCurrency(supplier.totalSpent || 0) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Days Active:</span>
            <span class="stat-value text-info">{{ supplier.daysActive || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="d-flex gap-2 mt-2">
        <button 
          class="btn btn-outline-primary btn-sm flex-fill"
          @click="$emit('view', supplier)"
        >
          <i class="bi bi-eye me-1"></i>
          View
        </button>
        <button 
          class="btn btn-outline-success btn-sm flex-fill"
          @click="$emit('create-order', supplier)"
        >
          <i class="bi bi-plus me-1"></i>
          Order
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { Star } from 'lucide-vue-next'

export default {
  name: 'SupplierCard',
  components: {
    Star
  },
  emits: ['toggle-select', 'toggle-favorite', 'edit', 'view', 'create-order', 'delete'],
  props: {
    supplier: {
      type: Object,
      required: true
    },
    isSelected: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    getStatusBadgeClass(status) {
      const classes = {
        active: 'text-bg-success',
        inactive: 'text-bg-danger',
        pending: 'text-bg-warning'
      }
      return classes[status] || 'text-bg-secondary'
    },

    formatStatus(status) {
      return status.charAt(0).toUpperCase() + status.slice(1)
    },

    getShortAddress(address) {
      if (!address) return 'No address'
      return address.length > 50 ? address.substring(0, 50) + '...' : address
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0)
    }
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';
/* Supplier card styling */
.supplier-card {
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  transition: all 0.3s ease;
  background-color: var(--surface-primary);
}

.supplier-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--border-accent);
}

.supplier-card.card-selected {
  border-color: var(--border-accent);
  background-color: var(--state-selected);
}

.supplier-icon {
  width: 40px;
  height: 40px;
  background-color: var(--surface-tertiary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-accent);
}

.supplier-name {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
}

.favorite-toggle {
  line-height: 1;
  display: inline-flex;
  align-items: center;
  transition: transform 0.2s ease;
}

.favorite-toggle:hover {
  transform: scale(1.1);
}

.favorite-toggle:focus {
  outline: none;
  box-shadow: none;
}

.favorite-star {
  color: #ffc107;
  flex-shrink: 0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.favorite-star:not(.favorite-filled) {
  color: #9e9e9e;
  opacity: 1;
  stroke-width: 2;
}

.favorite-star.favorite-filled {
  color: #ffc107;
}

.favorite-star:hover {
  transform: scale(1.15);
}

.supplier-contact {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.contact-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.contact-text {
  color: var(--text-secondary);
}

.dropdown-toggle-btn {
  color: var(--text-tertiary);
  transition: color 0.2s ease;
}

.dropdown-toggle-btn:hover {
  color: var(--text-secondary);
}

.purchase-orders-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.purchase-orders-count {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-accent);
}

/* Supplier Stats Styling */
.supplier-stats {
  background-color: var(--surface-secondary);
  border-radius: 8px;
  padding: 0.75rem;
  border: 1px solid var(--border-primary);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.stat-row:last-child {
  margin-bottom: 0;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  font-size: 0.875rem;
  font-weight: 600;
}
</style>