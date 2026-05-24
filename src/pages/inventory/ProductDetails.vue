<template>
  <div class="d-flex flex-column surface-secondary" style="min-height: 100%;">
    <!-- Loading State -->
    <div v-if="loading && !currentProduct" class="d-flex align-items-center justify-content-center flex-grow-1 py-5">
      <div class="text-center">
        <div class="spinner-border text-accent" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 text-tertiary-medium">Loading product details...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error && !currentProduct" class="d-flex align-items-center justify-content-center flex-grow-1 py-5">
      <div class="text-center">
        <div class="mb-4 text-error" style="font-size: 3rem;">✕</div>
        <h2 class="fs-4 fw-bold mb-2 text-error">Error Loading Product</h2>
        <p class="text-tertiary-medium">{{ error }}</p>
        <button @click="initializeData" class="mt-4 btn btn-save">Try Again</button>
      </div>
    </div>

    <!-- Product Not Found State -->
    <div v-else-if="!currentProduct || !currentProduct.product_id" class="d-flex align-items-center justify-content-center flex-grow-1 py-5">
      <div class="text-center">
        <Package :size="64" class="mb-4 text-tertiary-medium" />
        <h2 class="fs-4 fw-bold mb-2 text-primary">Product Not Found</h2>
        <p class="text-tertiary-medium">The product with ID "{{ id }}" could not be found.</p>
        <button @click="router.push('/products')" class="mt-4 btn btn-save">Back to Products</button>
      </div>
    </div>

    <!-- Product Content -->
    <div v-else-if="currentProduct.product_id" class="d-flex flex-column flex-grow-1 overflow-hidden">
      <!-- Success Message -->
      <div v-if="successMessage" class="mx-4 mt-3 status-success rounded">
        {{ successMessage }}
      </div>

      <!-- Header -->
      <header class="surface-primary px-4 py-3 border-bottom-theme">
        <nav class="breadcrumb-nav">
          <router-link to="/products" class="breadcrumb-link">Inventory</router-link>
          <ChevronRight :size="12" class="breadcrumb-icon" />
          <router-link to="/products" class="breadcrumb-link">Products</router-link>
          <ChevronRight :size="12" class="breadcrumb-icon" />
          <span class="breadcrumb-current">Product Details</span>
        </nav>

        <div class="product-header">
          <div class="w-100">
            <h1 class="product-title text-primary">{{ currentProduct.product_name }}</h1>
            <div class="description-and-buttons">
              <p class="product-description text-tertiary-medium mb-0">
                {{ currentProduct.description || 'No description available.' }}
              </p>
              <div class="button-group">
                <button @click="handleDelete" class="btn btn-delete btn-sm">Delete</button>
                <button @click="handleEdit" class="btn btn-edit btn-sm">Edit</button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Tab Navigation -->
      <div class="surface-primary px-4">
        <nav class="d-flex border-bottom-theme">
          <button
            v-for="tab in tabs"
            :key="tab"
            @click="setActiveTab(tab)"
            class="tab-button"
            :class="{ 'tab-active': activeTab === tab }"
          >
            {{ tab }}
          </button>
        </nav>
      </div>

      <!-- Content Area -->
      <div class="flex-grow-1 overflow-auto p-4 surface-secondary">
        <ProductOverview
          v-if="activeTab === 'Overview'"
          :key="`overview-${id}`"
          :product-id="id"
          ref="overviewRef"
          @adjust-stock="handleStockAdjustment"
          @change-image="handleEdit"
          @reorder="handleReorder"
          @view-history="() => setActiveTab('Purchases')"
        />

        <ProductPurchases
          v-else-if="activeTab === 'Purchases' && hasVisitedTab('Purchases')"
          :key="`purchases-${id}`"
          :product-id="id"
          :product="currentProduct"
        />

        <ProductAdjustments
          v-else-if="activeTab === 'Adjustments' && hasVisitedTab('Adjustments')"
          :key="`adjustments-${id}`"
          :product-id="id"
        />
      </div>
    </div>

    <!-- Modals -->
    <AddProductModal
      ref="addProductModal"
      :categories="activeCategories"
      @success="handleModalSuccess"
    />

    <StockUpdateModal
      ref="stockUpdateModal"
      @success="handleModalSuccess"
    />

    <DeleteConfirmationModal ref="confirmModal" @confirm="handleConfirm" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight, Package } from 'lucide-vue-next'
import { useProducts } from '@/composables/api/useProducts'
import { useCategories } from '@/composables/api/useCategories'
import AddProductModal from '@/components/products/AddProductModal.vue'
import StockUpdateModal from '@/components/products/StockUpdateModal.vue'
import DeleteConfirmationModal from '@/components/common/DeleteConfirmationModal.vue'
import ProductOverview from '@/components/products/ProductOverview.vue'
import ProductPurchases from '@/components/products/ProductPurchases.vue'
import ProductAdjustments from '@/components/products/ProductAdjustments.vue'

const props = defineProps({
  id: { type: String, required: true }
})

const router = useRouter()

const addProductModal = ref(null)
const stockUpdateModal = ref(null)
const overviewRef = ref(null)
const confirmModal = ref(null)
const pendingAction = ref(null)

const openConfirm = (options, action) => {
  pendingAction.value = action
  confirmModal.value?.openModal(options)
}

const handleConfirm = async () => {
  await pendingAction.value?.()
  pendingAction.value = null
  confirmModal.value?.closeModal()
}

const { currentProduct, loading, error, fetchProductById, deleteProduct } = useProducts()
const { activeCategories, initializeCategories } = useCategories()

const activeTab = ref('Overview')
const tabs = ['Overview', 'Purchases', 'Adjustments']
const successMessage = ref('')
const isInitialized = ref(false)
const visitedTabs = ref(new Set(['Overview']))

const hasVisitedTab = (tab) => visitedTabs.value.has(tab)

const setActiveTab = (tab) => {
  activeTab.value = tab
  visitedTabs.value.add(tab)
}

const handleEdit = () => {
  if (currentProduct.value?.product_id) {
    addProductModal.value?.openEdit?.(currentProduct.value)
  }
}

const handleStockAdjustment = () => {
  if (currentProduct.value?.product_id) {
    stockUpdateModal.value?.openStock?.(currentProduct.value)
  }
}

const handleReorder = () => {
  // TODO: implement reorder
}

const handleDelete = () => {
  if (!currentProduct.value?.product_name) return
  openConfirm({
    title: 'Delete Product',
    message: `Are you sure you want to delete <strong>${currentProduct.value.product_name}</strong>? This action cannot be undone.`,
    confirmText: 'Delete',
    confirmClass: 'btn-delete'
  }, async () => {
    try {
      await deleteProduct(currentProduct.value.product_id)
      router.push('/products')
    } catch (err) {
      console.error('Error deleting product:', err)
    }
  })
}


const handleModalSuccess = async (result) => {
  if (result?.message) {
    successMessage.value = result.message
    setTimeout(() => { successMessage.value = '' }, 3000)
  }
  try {
    await fetchProductById(props.id)
    overviewRef.value?.loadProductData?.()
  } catch (err) {
    console.error('Failed to refresh product after modal:', err)
  }
}

const initializeData = async () => {
  if (isInitialized.value) return
  try {
    await Promise.all([initializeCategories(), fetchProductById(props.id)])
    isInitialized.value = true
  } catch (err) {
    console.error('Failed to initialize data:', err)
    isInitialized.value = false
  }
}

onMounted(() => {
  initializeData()
})
</script>

<style scoped>
.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
}

.breadcrumb-link {
  color: var(--text-accent);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.breadcrumb-link:hover {
  opacity: 0.8;
}

.breadcrumb-current {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.breadcrumb-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.product-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.description-and-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 20px;
}

.product-description {
  font-size: 0.875rem;
  flex: 1;
}

.button-group {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.tab-button {
  border: none;
  background: transparent;
  padding: 1rem 0;
  margin-right: 2rem;
  border-bottom: 2px solid transparent;
  color: var(--text-tertiary);
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.tab-button:hover {
  color: var(--text-accent);
}

.tab-button.tab-active {
  color: var(--text-accent);
  border-bottom-color: var(--border-accent);
  font-weight: 600;
}

@media (max-width: 768px) {
  .description-and-buttons {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .button-group {
    width: 100%;
    justify-content: flex-start;
  }

  .tab-button {
    margin-right: 1rem;
    font-size: 0.8rem;
  }
}
</style>
