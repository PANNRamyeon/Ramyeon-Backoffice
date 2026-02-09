<template>
  <div class="app-layout">
    <!-- Sidebar Component -->
    <Sidebar 
      @menu-changed="handleMenuChange"
      @show-profile="handleShowProfile"
      @logout="handleLogout"
      @sidebar-toggled="handleSidebarToggle"
    />
    
   <!-- Main Content Area -->
    <main class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <!-- Header Bar -->
      <header class="content-header">
        <div class="header-content">
          <h1>{{ currentPageTitle }}</h1>
          
          <!-- Header Right Section with Notifications -->
          <div class="header-right">
            <!-- Notification Bell -->
            <NotificationBell />
          </div>
        </div>
      </header>

      <!-- Page Content - This will now show the routed component -->
      <div class="page-content">
        <router-view />
      </div>
    </main>

    <!-- Dark Mode Toggle Button -->
    <DarkModeToggle />

    <!-- Profile Modal (if needed) -->
    <div v-if="showProfileModal" class="modal-overlay" @click="closeProfileModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>My Profile</h2>
          <button class="modal-close-btn" @click="closeProfileModal">
            <X :size="20" />
          </button>
        </div>
        <div class="profile-info">
          <div class="profile-field">
            <label>User:</label>
            <span>{{ userInfo.full_name || 'N/A' }}</span>
          </div>
          <div class="profile-field">
            <label>Email:</label>
            <span>{{ userInfo.email || 'N/A' }}</span>
          </div>
          <div class="profile-field">
            <label>Role:</label>
            <span>{{ userInfo.role || 'N/A' }}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-cancel btn-sm" @click="closeProfileModal">
            Close
          </button>
          <button class="btn btn-edit btn-sm">
            Edit Profile
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Container - Add this for global toast notifications -->
    <ToastContainer />
  </div>
</template>

<script>
import { useToast } from '../composables/ui/useToast.js'
import { useAuth } from '@/composables/auth/useAuth.js'
import Sidebar from './Sidebar.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import DarkModeToggle from '@/components/common/DarkModeToggle.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'

export default {
  name: 'MainLayout',
  components: {
    Sidebar,
    NotificationBell,
    DarkModeToggle,
    ToastContainer
  },
  setup() {
    // Use the auth composable
    const { logout } = useAuth()
    
    // Make toast available globally in this layout if needed
    const { success, error, warning, info } = useToast()
    
    return {
      authLogout: logout,
      toast: { success, error, warning, info }
    }
  },
  data() {
    return {
      sidebarCollapsed: false,
      showProfileModal: false
    }
  },
  computed: {
    currentPageTitle() {
      if (this.$route.meta?.title) {
        return this.$route.meta.title
      }

      const path = this.$route.path

      if (path.startsWith('/products/') && path !== '/products/bulk') {
        return 'Product Details'
      }

      if (path.startsWith('/suppliers/') && path !== '/suppliers/orders') {
        return 'Supplier Details'
      }

      const fallbackTitles = {
        '/dashboard': 'Dashboard',
        '/accounts': 'User Accounts',
        '/customers': 'Customers',
        '/products': 'Products',
        '/products/bulk': 'Add Products (Bulk)',
        '/categories': 'Categories',
        '/categorydetails': 'Category Details',
        '/logs': 'System Logs',
        '/suppliers': 'Suppliers',
        '/promotions': 'Promotions',
        '/salesbyitem': 'Sales By Item',
        '/salesbycategory': 'Sales By Category',
        '/uncategorized': 'Uncategorized Products',
        '/allNotifications': 'All Notifications',
        '/profile': 'User Profile'
      }

      return fallbackTitles[path] || 'Dashboard'
    },
    userInfo() {
      // Try both possible storage keys for backward compatibility
      let userData = localStorage.getItem('user') || localStorage.getItem('userData')
      return userData ? JSON.parse(userData) : {}
    }
  },
  methods: {
    handleMenuChange(menu) {
      this.$router.push(`/${menu}`)
    },
    handleShowProfile() {
      this.showProfileModal = true
    },
    closeProfileModal() {
      this.showProfileModal = false
    },
    handleSidebarToggle(collapsed) {
      this.sidebarCollapsed = collapsed
    },
    async handleLogout() {
      const logoutToastId = this.toast.loading('Logging out...')
      
      try {
        // Use the auth composable logout method
        await this.authLogout()
        
        this.toast.dismiss(logoutToastId)
        this.toast.success('Successfully logged out', { duration: 2000 })
        
        // Small delay before redirect
        setTimeout(() => {
          this.$router.push('/login')
        }, 1500)
        
      } catch (error) {
        console.error('Logout error:', error)
        this.toast.dismiss(logoutToastId)
        this.toast.warning('Logged out with connection issues', { duration: 3000 })
        
        // Still redirect even if logout API failed
        setTimeout(() => {
          this.$router.push('/login')
        }, 1500)
      }
    }
  },
  mounted() {
    // Load sidebar state from localStorage
    const savedState = localStorage.getItem('sidebar-collapsed')
    if (savedState !== null) {
      this.sidebarCollapsed = JSON.parse(savedState)
    }
    
    // Show welcome toast (optional)
    const userData = this.userInfo
    if (userData.full_name || userData.name) {
      this.toast.success(`Welcome back, ${userData.full_name || userData.name}!`, {
        duration: 3000
      })
    }
  }
}
</script>

<style scoped>
/* ==========================================================================
   APP LAYOUT - SEMANTIC THEME SYSTEM
   ========================================================================== */

.app-layout {
  min-height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  position: relative; /* Added for toast positioning */
}

/* ==========================================================================
   MAIN CONTENT AREA - SEMANTIC STYLING
   ========================================================================== */

.main-content {
  margin-left: 280px; /* Default sidebar width */
  transition: margin-left 0.3s ease;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-width: 0;
}

.main-content.sidebar-collapsed {
  margin-left: 80px; /* Collapsed sidebar width */
}

/* ==========================================================================
   CONTENT HEADER - SEMANTIC STYLING
   ========================================================================== */

.content-header {
  height: 100px; /* Match sidebar header height */
  padding: 0 2.5rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--border-primary);
  @apply header-theme transition-theme;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.content-header h1 {
  font-size: 1.875rem;
  font-weight: 600;
  margin: 0;
  flex: 1;
  @apply text-primary transition-theme;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* ==========================================================================
   PAGE CONTENT - SEMANTIC STYLING
   ========================================================================== */

.page-content {
  flex: 1;
  padding: 2.5rem;
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
  min-width: 0;
  @apply page-container transition-theme;
}

/* ==========================================================================
   MODAL STYLES - SEMANTIC STYLING
   ========================================================================== */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
  @apply modal-overlay-theme transition-theme;
}

.modal-content {
  border-radius: 16px;
  max-width: 480px;
  width: 90%;
  transform: scale(1);
  opacity: 1;
  animation: modalSlideIn 0.3s ease-out;
  @apply modal-theme shadow-2xl transition-theme;
}

@keyframes modalSlideIn {
  0% {
    opacity: 0;
    transform: scale(0.95) translateY(-20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Modal Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 1.5rem 0;
  margin-bottom: 1.5rem;
  @apply border-bottom-theme;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  @apply text-primary transition-theme;
}

.modal-close-btn {
  background: none;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  @apply border-theme text-tertiary transition-theme;
}

.modal-close-btn:hover {
  @apply surface-tertiary border-accent text-secondary;
}

/* Profile Info */
.profile-info {
  padding: 0 1.5rem 1.5rem;
}

.profile-field {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  @apply border-bottom-theme transition-theme;
}

.profile-field:last-child {
  border-bottom: none;
}

.profile-field label {
  font-weight: 600;
  font-size: 0.875rem;
  @apply text-primary transition-theme;
}

.profile-field span {
  font-size: 0.875rem;
  @apply text-secondary transition-theme;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-radius: 0 0 16px 16px;
  @apply border-top-theme surface-secondary transition-theme;
}

/* ==========================================================================
   ENHANCED INTERACTIONS
   ========================================================================== */

/* Profile field hover effect */
.profile-field:hover {
  margin: 0 -0.5rem;
  padding: 0.75rem 0.5rem;
  border-radius: 8px;
  @apply surface-tertiary;
}

/* Modal content elevation on hover */
.modal-content:hover {
  @apply shadow-2xl;
  box-shadow: 
    0 32px 64px -12px var(--shadow-2xl),
    0 0 0 1px var(--border-primary);
}

/* Header border line effect */
.content-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background-color: var(--border-primary);
}

/* ==========================================================================
   RESPONSIVE DESIGN
   ========================================================================== */

@media (max-width: 1024px) {
  .page-content {
    padding: 2rem;
  }
  
  .content-header {
    padding: 0 2rem;
  }
  
  .header-right {
    gap: 0.75rem;
  }
  
  .modal-content {
    max-width: 420px;
  }
}

@media (max-width: 768px) {
  .main-content {
    margin-left: 0;
  }
  
  .main-content.sidebar-collapsed {
    margin-left: 0;
  }
  
  .page-content {
    padding: 1.5rem;
  }
  
  .content-header {
    padding: 0 1.5rem;
    height: 80px;
  }
  
  .content-header h1 {
    font-size: 1.5rem;
  }
  
  .header-right {
    gap: 0.5rem;
  }
  
  .modal-content {
    max-width: 90%;
    margin: 1rem;
  }
  
  .modal-header,
  .profile-info,
  .modal-footer {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}

@media (max-width: 480px) {
  .page-content {
    padding: 1rem;
  }
  
  .content-header {
    padding: 0 1rem;
    height: 70px;
  }
  
  .content-header h1 {
    font-size: 1.25rem;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .modal-footer .btn {
    width: 100%;
    justify-content: center;
  }
}

/* ==========================================================================
   ACCESSIBILITY & REDUCED MOTION
   ========================================================================== */

/* Enhanced focus styles */
.modal-close-btn:focus-visible {
  @apply focus-ring-theme;
}

/* Smooth transitions for reduced motion users */
@media (prefers-reduced-motion: reduce) {
  .app-layout,
  .content-header,
  .content-header h1,
  .page-content,
  .modal-content,
  .modal-header h2,
  .profile-field,
  .modal-footer,
  .modal-close-btn {
    transition: none !important;
    animation: none !important;
  }
  
  .modal-content {
    transform: none !important;
  }
}

/* ==========================================================================
   ENHANCED VISUAL EFFECTS
   ========================================================================== */

/* Page content subtle gradient background */
.page-content {
  background: 
    linear-gradient(
      180deg, 
      var(--surface-secondary) 0%, 
      var(--surface-secondary) 100%
    );
}

/* Modal backdrop blur enhancement */
@supports (backdrop-filter: blur(8px)) {
  .modal-overlay {
    backdrop-filter: blur(8px);
  }
}

/* Button elevation effects */
.modal-footer .btn {
  @apply shadow-sm transition-all-theme;
}

.modal-footer .btn:hover {
  transform: translateY(-1px);
  @apply shadow-md;
}

/* Header content enhancement */
.header-content {
  position: relative;
}

.header-content::before {
  content: '';
  position: absolute;
  left: -2.5rem;
  right: -2.5rem;
  top: -1rem;
  bottom: -1rem;
  background: linear-gradient(
    135deg,
    var(--surface-primary) 0%,
    var(--surface-secondary) 100%
  );
  border-radius: 0 0 16px 16px;
  z-index: -1;
  opacity: 0.5;
}
</style>