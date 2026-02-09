<template>
  <div class="flex h-screen surface-secondary">
    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Loading State -->
      <div v-if="loading && !currentProduct" class="flex items-center justify-center h-full">
        <div class="text-center">
          <div class="spinner-border text-accent" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-3 text-tertiary-medium">Loading product details...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error && !currentProduct" class="flex items-center justify-center h-full">
        <div class="text-center">
          <div class="text-6xl mb-4">❌</div>
          <h2 class="text-2xl font-bold mb-2 text-error">Error Loading Product</h2>
          <p class="text-tertiary-medium">{{ error }}</p>
          <button 
            @click="initializeData" 
            class="mt-4 btn btn-submit"
          >
            Try Again
          </button>
        </div>
      </div>

      <!-- Product Not Found State -->
      <div v-else-if="!currentProduct || !currentProduct._id" class="flex items-center justify-center h-full">
        <div class="text-center">
          <div class="text-6xl mb-4">📦</div>
          <h2 class="text-2xl font-bold mb-2 text-primary">Product Not Found</h2>
          <p class="text-tertiary-medium">The product with ID "{{ id }}" could not be found.</p>
          <button 
            @click="router.push('/products')" 
            class="mt-4 btn btn-submit"
          >
            Back to Products
          </button>
        </div>
      </div>

      <!-- Product Content - Only show when we have a valid product -->
      <div v-else-if="currentProduct._id" class="h-full">
        <!-- Success Message -->
        <div v-if="successMessage" class="mx-6 mt-4 status-success rounded-md">
          {{ successMessage }}
        </div>

        <!-- Header -->
        <header class="surface-primary px-6 py-3 border-bottom-theme">
          <!-- Breadcrumb Navigation -->
          <nav class="breadcrumb-nav">
            <router-link to="/products" class="breadcrumb-link">Inventory</router-link>
            <ChevronRight :size="12" class="breadcrumb-icon" />
            <router-link to="/products" class="breadcrumb-link">Products</router-link>
            <ChevronRight :size="12" class="breadcrumb-icon" />
            <span class="breadcrumb-current">Product Details</span>
          </nav>

          <!-- Product Header -->
          <div class="product-header">
            <div class="product-info">
              <h1 class="product-title text-primary">{{ currentProduct.product_name || 'Product Name' }}</h1>
              <div class="description-and-buttons">
                <p class="product-description text-tertiary-medium">{{ currentProduct.description || 'Product description not available.' }}</p>
                <div class="button-group">
                  <button @click="handleDelete" class="btn btn-delete btn-sm">Delete</button>
                  <button @click="handleEdit" class="btn btn-edit btn-sm">Edit</button>
                  <button @click="handleExport" class="btn btn-export btn-sm">Export</button>
                </div>
              </div>
            </div>
          </div>
        </header>

        <!-- Tab Navigation -->
        <div class="surface-primary px-6">
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
        <div class="flex-1 overflow-auto p-6 surface-secondary">
          <!-- Overview Tab - Only render when active -->
          <ProductOverview 
            v-if="activeTab === 'Overview'"
            :key="`overview-${id}`"
            :product-id="id"
            ref="overviewRef"
            @adjust-stock="handleStockAdjustment"
            @change-image="handleImageUpload"
            @reorder="handleReorder"
            @view-history="() => setActiveTab('Purchases')"
          />

          <!-- Purchases Tab - Only render when active and has been visited -->
          <ProductPurchases 
            v-else-if="activeTab === 'Purchases' && hasVisitedTab('Purchases')"
            :key="`purchases-${id}`"
            :product-id="id" 
            :product="currentProduct" 
          />

          <!-- Adjustments Tab - Only render when active and has been visited -->
          <ProductAdjustments 
            v-else-if="activeTab === 'Adjustments' && hasVisitedTab('Adjustments')"
            :key="`adjustments-${id}`"
            :product-id="id" 
          />
        </div>
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
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import { useProducts } from '@/composables/api/useProducts'
import { useCategories } from '@/composables/api/useCategories'
import AddProductModal from '@/components/products/AddProductModal.vue'
import StockUpdateModal from '@/components/products/StockUpdateModal.vue'
import ProductOverview from '@/components/products/ProductOverview.vue'
import ProductPurchases from '@/components/products/ProductPurchases.vue'
import ProductAdjustments from '@/components/products/ProductAdjustments.vue'

export default {
  name: 'ProductDetails',
  components: {
    ChevronRight,
    AddProductModal,
    StockUpdateModal,
    ProductOverview,
    ProductPurchases,
    ProductAdjustments 
  },
  props: {
    id: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const router = useRouter()
    
    // Template refs
    const addProductModal = ref(null)
    const stockUpdateModal = ref(null)
    
    // Use composables
    const {
      currentProduct,
      loading,
      error,
      fetchProductById,
      deleteProduct,
      exportProducts,
      exportProductDetails
    } = useProducts()

    const {
      activeCategories,
      initializeCategories
    } = useCategories()

    // Local state
    const activeTab = ref('Overview')
    const tabs = ['Overview', 'Purchases', 'Adjustments']
    const successMessage = ref('')
    const isInitialized = ref(false)
    const visitedTabs = ref(new Set(['Overview'])) // Track which tabs have been visited
    const overviewRef = ref(null)

    // Check if a tab has been visited
    const hasVisitedTab = (tab) => {
      return visitedTabs.value.has(tab)
    }

    // Methods
    const handleEdit = () => {
      if (currentProduct.value && currentProduct.value._id) {
        addProductModal.value?.openEdit?.(currentProduct.value)
      }
    }

    const handleStockAdjustment = () => {
      if (currentProduct.value && currentProduct.value._id) {
        stockUpdateModal.value?.openStock?.(currentProduct.value)
      }
    }

    const handleImageUpload = () => {
      if (currentProduct.value && currentProduct.value._id) {
        addProductModal.value?.openEdit?.(currentProduct.value)
      }
    }

    const handleReorder = () => {
      // TODO: Implement reorder logic
    }

    const handleDelete = async () => {
      if (!currentProduct.value || !currentProduct.value.product_name) {
        return
      }
      
      const confirmed = confirm(`Are you sure you want to delete "${currentProduct.value.product_name}"?`)
      if (confirmed) {
        try {
          await deleteProduct(currentProduct.value._id)
          router.push('/products')
        } catch (err) {
          console.error('❌ Error deleting product:', err)
        }
      }
    }

    const handleExport = async () => {
      if (!currentProduct.value || !currentProduct.value._id) {
        console.warn('⚠️ No product loaded for export');
        return;
      }

      try {
        await exportProductDetails(currentProduct.value._id);
      } catch (err) {
        console.error('❌ Error exporting product details:', err);
      }
    }


   const handleModalSuccess = async (result) => {
    if (result?.message) {
      successMessage.value = result.message
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    }
    
    try {
      // Optional: still refresh the product data
      await fetchProductById(props.id)
    } catch (err) {
      console.error('❌ Failed to refresh product after modal:', err)
    }

    // 🔥 Hard refresh the current route (page-level refresh)
    router.go(0)
  }



    const setActiveTab = (tab) => {
      activeTab.value = tab
      
      // Mark this tab as visited for lazy loading
      visitedTabs.value.add(tab)
    }

    const initializeData = async () => {
      // Prevent multiple initialization
      if (isInitialized.value) {
        return
      }
      
      try {
        // Only fetch product and categories here
        // Let child components fetch their own batch data
        await Promise.all([
          initializeCategories(),
          fetchProductById(props.id)
        ])
        
        isInitialized.value = true
      } catch (err) {
        console.error('❌ Failed to initialize data:', err)
        isInitialized.value = false // Allow retry
      }
    }

    onMounted(() => {
      initializeData()
    })

    return {
      // State
      loading,
      error,
      successMessage,
      currentProduct,
      activeTab,
      tabs,
      router,
      activeCategories,
      
      // Template refs
      addProductModal,
      stockUpdateModal,
      overviewRef,
      // Methods
      setActiveTab,
      hasVisitedTab,
      handleDelete,
      handleEdit,
      handleStockAdjustment,
      handleImageUpload,
      handleReorder,
      handleExport,
      handleModalSuccess,
      initializeData
    }
  }
}
</script>
  
<style scoped>
/* Breadcrumb Navigation Styles */
.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  line-height: 1;
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

/* Product Header Styles */
.product-header {
  width: 100%;
}

.product-info {
  width: 100%;
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
  margin: 0;
  flex: 1;
}

/* Button Group Styles */
.button-group {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

/* Tab Styles */
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

/* Responsive Design */
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