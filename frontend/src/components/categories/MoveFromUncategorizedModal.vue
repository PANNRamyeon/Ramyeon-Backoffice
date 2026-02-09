<template>
  <div
    class="modal fade move-products-modal"
    id="moveFromUncategorizedModal"
    tabindex="-1"
    aria-hidden="true"
    ref="modal"
  >
    <div class="modal-dialog modal-xxl modal-dialog-scrollable modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <div>
            <h5 class="modal-title d-flex align-items-center gap-2 mb-1">
              <Package :size="18" />
              Move Products from Uncategorized
            </h5>
            <small class="text-tertiary">
              Target: <strong>{{ targetCategoryName || 'Selected Category' }}</strong>
            </small>
          </div>
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="closeModal"
          ></button>
        </div>

        <div class="modal-body">
          <div v-if="error" class="alert alert-danger d-flex align-items-start gap-2">
            <AlertTriangle :size="16" class="flex-shrink-0" />
            <div>
              <strong>Unable to load products.</strong>
              <div>{{ error }}</div>
            </div>
          </div>

          <div class="d-flex flex-wrap gap-2 align-items-center mb-3">
            <div class="search-field flex-grow-1">
              <div class="input-group input-group-sm">
                <span class="input-group-text">
                  <Search :size="14" />
                </span>
                <input
                  v-model="searchTerm"
                  type="text"
                  class="form-control"
                  placeholder="Search uncategorized products..."
                />
                <button
                  v-if="searchTerm"
                  class="btn btn-outline-secondary"
                  type="button"
                  @click="searchTerm = ''"
                >
                  <X :size="14" />
                </button>
              </div>
            </div>

            <div class="subcategory-select">
              <label class="form-label text-tertiary mb-1 small">Assign to subcategory</label>
              <select
                class="form-select form-select-sm"
                v-model="targetSubcategory"
              >
                <option value="">None (keep at category level)</option>
                <option
                  v-for="sub in normalizedSubcategories"
                  :key="sub.name"
                  :value="sub.name"
                >
                  {{ sub.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="d-flex flex-wrap gap-3 mb-3 text-tertiary small">
            <div class="stat-chip">
              Total in view: <strong>{{ filteredProducts.length }}</strong>
            </div>
            <div class="stat-chip">
              Selected: <strong>{{ selectedProducts.length }}</strong>
            </div>
            <div class="stat-chip" v-if="uncategorizedCategoryName">
              Source: <strong>{{ uncategorizedCategoryName }}</strong>
            </div>
          </div>

          <div
            v-if="loading"
            class="text-center py-4"
          >
            <div class="spinner-border text-accent" role="status">
              <span class="visually-hidden">Loading uncategorized products...</span>
            </div>
            <p class="mt-2 text-tertiary">Loading uncategorized products...</p>
          </div>

          <div
            v-else-if="filteredProducts.length === 0"
            class="text-center py-5 surface-tertiary rounded border border-dashed"
          >
            <Package :size="40" class="text-tertiary mb-2" />
            <p class="mb-1">No products available to move.</p>
            <small class="text-tertiary">
              {{ searchTerm ? 'Try adjusting your search.' : 'Uncategorized category is empty.' }}
            </small>
          </div>

          <div v-else class="table-responsive move-products-table">
            <table class="table table-sm align-middle mb-0">
              <thead>
                <tr>
                  <th style="width: 36px;">
                    <input
                      type="checkbox"
                      class="form-check-input"
                      :checked="areAllVisibleSelected"
                      :indeterminate.prop="isIndeterminate"
                      @change="toggleSelectAll"
                    />
                  </th>
                  <th style="width: 120px;">Product ID</th>
                  <th>Product Name</th>
                  <th style="width: 110px;" class="text-center">Stock</th>
                  <th style="width: 110px;" class="text-end">Price</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in filteredProducts" :key="product._id">
                  <td>
                    <input
                      type="checkbox"
                      class="form-check-input"
                      :value="product._id"
                      v-model="selectedProducts"
                    />
                  </td>
                  <td>
                    <code class="code-pill">{{ product._id }}</code>
                  </td>
                  <td>
                    <div class="fw-semibold text-primary">{{ product.product_name }}</div>
                    <small class="text-tertiary">
                      SKU: {{ product.SKU || 'N/A' }}
                    </small>
                  </td>
                  <td class="text-center">
                    <span :class="getStockClass(product.total_stock)">
                      {{ product.total_stock ?? 0 }}
                    </span>
                  </td>
                  <td class="text-end">
                    ₱{{ formatPrice(product.selling_price) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer justify-content-between flex-wrap gap-2">
          <div class="text-tertiary small">
            <strong>Tip:</strong> Select multiple rows to move them in one action.
          </div>
          <div class="d-flex gap-2">
            <button
              type="button"
              class="btn btn-outline-secondary btn-sm"
              @click="closeModal"
              :disabled="moveLoading"
            >
              Cancel
            </button>
            <button
              type="button"
              class="btn btn-add btn-sm btn-with-icon-sm"
              :disabled="!selectedProducts.length || moveLoading"
              @click="moveSelectedProducts"
            >
              <div
                v-if="moveLoading"
                class="spinner-border spinner-border-sm me-2"
                role="status"
              >
                <span class="visually-hidden">Moving...</span>
              </div>
              <MoveRight v-else :size="14" />
              {{ moveLoading ? 'Moving...' : `Move ${selectedProducts.length || ''}` }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { AlertTriangle, MoveRight, Package, Search, X } from 'lucide-vue-next'
import { useProducts } from '@/composables/api/useProducts'
import { useToast } from '@/composables/ui/useToast'
import categoryApiService from '@/services/apiCategory'

export default {
  name: 'MoveFromUncategorizedModal',
  components: {
    AlertTriangle,
    MoveRight,
    Package,
    Search,
    X
  },
  props: {
    targetCategoryId: {
      type: String,
      required: true
    },
    targetCategoryName: {
      type: String,
      default: ''
    },
    subcategories: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      modalInstance: null,
      loading: false,
      moveLoading: false,
      error: null,
      products: [],
      searchTerm: '',
      selectedProducts: [],
      targetSubcategory: '',
      uncategorizedCategoryId: null,
      uncategorizedCategoryName: '',
      productsComposable: useProducts(),
      toast: useToast()
    }
  },
  computed: {
    normalizedSubcategories() {
      return (this.subcategories || []).filter(sub => sub?.name)
    },
    filteredProducts() {
      if (!this.searchTerm) {
        return this.products
      }

      const term = this.searchTerm.trim().toLowerCase()
      return this.products.filter(product => {
        return (
          product.product_name?.toLowerCase().includes(term) ||
          product._id?.toLowerCase().includes(term) ||
          product.SKU?.toLowerCase().includes(term)
        )
      })
    },
    areAllVisibleSelected() {
      if (!this.filteredProducts.length) return false
      return this.filteredProducts.every(product => this.selectedProducts.includes(product._id))
    },
    isIndeterminate() {
      const selectedOnPage = this.filteredProducts.filter(product =>
        this.selectedProducts.includes(product._id)
      )
      return selectedOnPage.length > 0 && selectedOnPage.length < this.filteredProducts.length
    }
  },
  mounted() {
    if (typeof window !== 'undefined' && window.bootstrap) {
      this.modalInstance = new window.bootstrap.Modal(this.$refs.modal, {
        backdrop: 'static',
        keyboard: true
      })
    }
  },
  methods: {
    async openModal() {
      if (!this.targetCategoryId) {
        this.error = 'Target category information is missing.'
        return
      }

      this.resetSelections()

      await this.loadUncategorizedProducts()

      if (this.modalInstance) {
        this.modalInstance.show()
      }
    },
    closeModal() {
      if (this.modalInstance) {
        this.modalInstance.hide()
      }
    },
    resetSelections() {
      this.searchTerm = ''
      this.selectedProducts = []
      this.targetSubcategory = ''
      this.error = null
    },
    async loadUncategorizedProducts() {
      this.loading = true
      this.error = null

      try {
        const response = await categoryApiService.GetUncategorizedCategory()
        const uncategorized = response?.uncategorized_category

        if (!uncategorized?._id) {
          throw new Error('Unable to find the Uncategorized category.')
        }

        this.uncategorizedCategoryId = uncategorized._id
        this.uncategorizedCategoryName = uncategorized.category_name || 'Uncategorized'

        const productsResponse = await categoryApiService.FindProdcategory({
          id: this.uncategorizedCategoryId
        })

        if (Array.isArray(productsResponse)) {
          this.products = productsResponse
        } else if (Array.isArray(productsResponse?.products)) {
          this.products = productsResponse.products
        } else {
          this.products = []
        }
      } catch (error) {
        console.error('Failed to load uncategorized products:', error)
        this.error = error.message || 'Failed to load uncategorized products.'
        this.products = []
      } finally {
        this.loading = false
      }
    },
    toggleSelectAll(event) {
      if (event.target.checked) {
        this.selectedProducts = this.filteredProducts.map(product => product._id)
      } else {
        this.selectedProducts = []
      }
    },
    getStockClass(stock) {
      if (stock === 0) return 'text-error fw-semibold'
      if (stock <= 10) return 'text-warning fw-semibold'
      return 'text-success fw-semibold'
    },
    formatPrice(price) {
      return parseFloat(price || 0).toFixed(2)
    },
    async moveSelectedProducts() {
      if (!this.selectedProducts.length || !this.targetCategoryId) return

      this.moveLoading = true

      try {
        await this.productsComposable.bulkMoveProductsToCategory(
          this.selectedProducts,
          this.targetCategoryId,
          this.targetSubcategory || null
        )

        this.products = this.products.filter(
          product => !this.selectedProducts.includes(product._id)
        )
        this.selectedProducts = []

        this.toast.success('Products moved successfully.')
        this.$emit('products-moved')
        this.closeModal()
      } catch (error) {
        console.error('Failed to move products:', error)
        this.toast.error(error.message || 'Failed to move products.')
      } finally {
        this.moveLoading = false
      }
    }
  }
}
</script>

<style scoped>
.move-products-table table {
  border: 1px solid var(--border-secondary);
  border-radius: 0.5rem;
  overflow: hidden;
}

.move-products-table thead {
  background-color: var(--surface-tertiary);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.code-pill {
  display: inline-block;
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  background-color: var(--surface-tertiary);
  font-size: 0.75rem;
}

.stat-chip {
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background-color: var(--surface-tertiary);
  border: 1px dashed var(--border-secondary);
}

.subcategory-select {
  min-width: 220px;
}

.search-field .input-group-text {
  background: var(--surface-secondary);
}

.move-products-modal .modal-dialog {
  margin: 1.25rem auto;
  width: calc(100% - 320px);
  max-width: 1400px;
}

.move-products-modal.show {
  display: flex !important;
  justify-content: center;
  align-items: center;
  padding-left: 280px;
}

@media (max-width: 1200px) {
  .move-products-modal.show {
    padding-left: 0;
  }
  .move-products-modal .modal-dialog {
    width: 95%;
    max-width: 1000px;
  }
}
</style>

