<template>
  <div class="sidebar-container" :class="{ 'collapsed': isCollapsed }">
    <!-- Sidebar Header -->
    <div class="sidebar-header">
      <div class="brand-container" v-if="!isCollapsed">
        <div class="brand-logo">
          <div class="logo-circle">
            <span class="logo-text">P</span>
          </div>
        </div>
        <div class="brand-info">
          <h5 class="brand-title">PANNTECH</h5>
          <small class="brand-subtitle">POS & Inventory</small>
        </div>
      </div>
      
      <!-- Toggle Button Row in expanded mode -->
      <div class="toggle-row" v-if="!isCollapsed">
        <button 
          class="btn btn-icon-only btn-sm sidebar-toggle"
          @click="toggleSidebar"
          :title="isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'"
        >
          <Menu :size="16" />
        </button>
      </div>
      
      <!-- Collapsed mode layout -->
      <div class="collapsed-layout" v-else>
        <!-- Stacked logo and button vertically -->
        <div class="collapsed-header-row">
          <div class="logo-circle">
            <span class="logo-text">P</span>
          </div>
          <button 
            class="btn btn-icon-only btn-sm sidebar-toggle collapsed-toggle"
            @click="toggleSidebar"
            :title="isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'"
          >
            <Menu :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- User Profile Section -->
    <div class="user-profile" v-if="!isCollapsed">
      <router-link 
        to="/profile" 
        class="profile-card"
        :class="{ 'active': isActiveRoute('/profile') }"
      >
        <div class="profile-avatar">
          <User :size="20" class="text-accent" />
        </div>
        <div class="profile-info">
          <span class="profile-name">{{ userName }}</span>
          <small class="profile-role">{{ userRole }}</small>
        </div>
        <div class="nav-indicator" v-if="isActiveRoute('/profile')"></div>
      </router-link>
    </div>
    
    <!-- User Profile Section - Collapsed -->
    <div class="user-profile" v-else>
      <router-link 
        to="/profile" 
        class="profile-card profile-card-collapsed"
        :class="{ 'active': isActiveRoute('/profile') }"
        title="My Profile"
      >
        <div class="profile-avatar">
          <User :size="20" class="text-accent" />
        </div>
      </router-link>
    </div>

    <!-- Navigation Menu -->
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <!-- Dashboard -->
        <li class="nav-item">
          <router-link 
            to="/dashboard" 
            class="nav-link"
            :class="{ 'active': isActiveRoute('/dashboard') }"
          >
            <LayoutDashboard :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Dashboard</span>
            <div class="nav-indicator" v-if="isActiveRoute('/dashboard')"></div>
          </router-link>
        </li>

        <!-- Inventory Section -->
        <li class="nav-item">
          <button 
            class="nav-link nav-button"
            :class="{ 'active': showInventorySubmenu || isInventoryRoute() }"
            @click="toggleInventorySubmenu"
            @mouseenter="handleInventoryHover(true)"
            @mouseleave="handleInventoryHover(false)"
          >
            <Package :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Inventory</span>
            <ChevronDown 
              :size="14" 
              class="nav-chevron" 
              :class="{ 'rotated': showInventorySubmenu }"
              v-if="!isCollapsed"
            />
          </button>
          
          <!-- Inventory Submenu -->
          <transition name="fade-slide">
            <ul 
              class="nav-submenu"
              v-if="shouldShowInventorySubmenu"
              :class="{ 'submenu-floating': isCollapsed }"
              @mouseenter="handleInventoryHover(true)"
              @mouseleave="handleInventoryHover(false)"
              :style="collapsedSubmenuStyle"
            >
            <li class="nav-subitem">
              <router-link 
                to="/products" 
                class="nav-sublink"
                :class="{ 'active-sub': isActiveRoute('/products') }"
              >
                <Box :size="16" class="nav-subicon" />
                Products
              </router-link>
            </li>
            <li class="nav-subitem">
              <router-link 
                to="/categories" 
                class="nav-sublink"
                :class="{ 'active-sub': isActiveRoute('/categories') }"
              >
                <FolderOpen :size="16" class="nav-subicon" />
                Categories
              </router-link>
            </li>
            <li class="nav-subitem">
              <router-link 
                to="/logs" 
                class="nav-sublink"
                :class="{ 'active-sub': isActiveRoute('/logs') }"
              >
                <FileText :size="16" class="nav-subicon" />
                Logs
              </router-link>
            </li>
            </ul>
          </transition>
        </li>

        <!-- Suppliers -->
        <li class="nav-item">
          <router-link 
            to="/suppliers" 
            class="nav-link"
            :class="{ 'active': isActiveRoute('/suppliers') }"
          >
            <Truck :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Suppliers</span>
            <div class="nav-indicator" v-if="isActiveRoute('/suppliers')"></div>
          </router-link>
        </li>

        <!-- Accounts -->
        <li class="nav-item">
          <router-link 
            to="/accounts" 
            class="nav-link"
            :class="{ 'active': isActiveRoute('/accounts') }"
          >
            <Users :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Accounts</span>
            <div class="nav-indicator" v-if="isActiveRoute('/accounts')"></div>
          </router-link>
        </li>

        <!-- Promotions -->
        <li class="nav-item">
          <router-link 
            to="/promotions" 
            class="nav-link"
            :class="{ 'active': isActiveRoute('/promotions') }"
          >
            <Tag :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Promotions</span>
            <div class="nav-indicator" v-if="isActiveRoute('/promotions')"></div>
          </router-link>
        </li>

        <!-- Reports Section -->
        <li class="nav-item">
          <button 
            class="nav-link nav-button"
            :class="{ 'active': showReportsSubmenu || isReportsRoute() }"
            @click="toggleReportsSubmenu"
            @mouseenter="handleReportsHover(true)"
            @mouseleave="handleReportsHover(false)"
          >
            <BarChart3 :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Reports</span>
            <ChevronDown 
              :size="14" 
              class="nav-chevron" 
              :class="{ 'rotated': showReportsSubmenu }"
              v-if="!isCollapsed"
            />
          </button>
          
          <!-- Reports Submenu -->
          <transition name="fade-slide">
            <ul 
              class="nav-submenu" 
              v-if="shouldShowReportsSubmenu"
              :class="{ 'submenu-floating': isCollapsed }"
              @mouseenter="handleReportsHover(true)"
              @mouseleave="handleReportsHover(false)"
              :style="collapsedSubmenuStyle"
            >
            <li class="nav-subitem">
              <router-link 
                to="/salesbyitem" 
                class="nav-sublink"
                :class="{ 'active-sub': isActiveRoute('/salesbyitem') }"
              >
                <TrendingUp :size="16" class="nav-subicon" />
                Sales By Items
              </router-link>
            </li>
            <li class="nav-subitem">
              <router-link 
                to="/salesbycategory" 
                class="nav-sublink"
                :class="{ 'active-sub': isActiveRoute('/salesbycategory') }"
              >
                <PieChart :size="16" class="nav-subicon" />
                Sales By Categories
              </router-link>
            </li>
            </ul>
          </transition>
        </li>

        <!-- Customers -->
        <li class="nav-item">
          <router-link 
            to="/customers" 
            class="nav-link"
            :class="{ 'active': isActiveRoute('/customers') }"
          >
            <UserCheck :size="18" class="nav-icon" />
            <span class="nav-text" v-if="!isCollapsed">Customers</span>
            <div class="nav-indicator" v-if="isActiveRoute('/customers')"></div>
          </router-link>
        </li>
      </ul>
    </nav>

    <!-- Sidebar Footer -->
    <div class="sidebar-footer">
      <button 
        class="btn btn-delete btn-md w-100"
        @click="handleLogout"
        :disabled="isLoggingOut"
        v-if="!isCollapsed"
      >
        <div v-if="isLoggingOut" class="loading-spinner"></div>
        <LogOut :size="16" v-else />
        {{ isLoggingOut ? 'Logging out...' : 'Logout' }}
      </button>
      <button 
        class="btn btn-delete btn-icon-only btn-md"
        @click="handleLogout"
        :disabled="isLoggingOut"
        v-else
        title="Logout"
      >
        <div v-if="isLoggingOut" class="loading-spinner"></div>
        <LogOut :size="16" v-else />
      </button>
    </div>
  </div>
</template>

<script>
import apiService from '../services/api.js'
import { useAuth } from '@/composables/auth/useAuth.js'
import { 
  LayoutDashboard,
  Package,
  Truck,
  Users,
  Tag,
  BarChart3,
  UserCheck,
  User,
  Settings,
  Menu,
  X,
  ChevronDown,
  TrendingUp,
  PieChart,
  LogOut,
  Box,
  FolderOpen,
  FileText
} from 'lucide-vue-next'

const inventoryRoutePrefixes = ['/inventory', '/products', '/categories', '/logs']
const reportsRoutePrefixes = ['/salesbyitem', '/salesbycategory', '/reports']

export default {
  name: 'ModernSidebar',
  components: {
    LayoutDashboard,
    Package,
    Truck,
    Users,
    Tag,
    BarChart3,
    UserCheck,
    User,
    Settings,
    Menu,
    X,
    ChevronDown,
    TrendingUp,
    PieChart,
    LogOut,
    Box,
    FolderOpen,
    FileText
  },
  setup() {
    const { user } = useAuth()
    return { user }
  },
  data() {
    return {
      isCollapsed: false,
      showInventorySubmenu: false,
      showReportsSubmenu: false,
      inventoryHover: false,
      reportsHover: false,
      isLoggingOut: false
    }
  },
  computed: {
    userRole() {
      if (this.user) {
        const userData = this.user.user_data || this.user
        return userData?.role || 'Administrator'
      }
      return 'Administrator'
    },
    userName() {
      if (this.user) {
        const userData = this.user.user_data || this.user
        return userData?.full_name || userData?.name || 'My Profile'
      }
      return 'My Profile'
    },
    shouldShowInventorySubmenu() {
      if (this.isCollapsed) {
        return this.inventoryHover
      }
      return this.showInventorySubmenu
    },
    shouldShowReportsSubmenu() {
      if (this.isCollapsed) {
        return this.reportsHover
      }
      return this.showReportsSubmenu
    },
    collapsedSubmenuStyle() {
      if (!this.isCollapsed) {
        return {}
      }
      return {
        position: 'absolute',
        left: '70px',
        top: '0'
      }
    }
  },
  methods: {
    toggleSidebar() {
      this.isCollapsed = !this.isCollapsed
      // Emit event to parent component
      this.$emit('sidebar-toggled', this.isCollapsed)
    },
    
    toggleInventorySubmenu() {
      if (this.isCollapsed) return
      this.showInventorySubmenu = !this.showInventorySubmenu
    },
    
    toggleReportsSubmenu() {
      if (this.isCollapsed) return
      this.showReportsSubmenu = !this.showReportsSubmenu
    },
    
    isActiveRoute(route) {
      return this.$route.path.startsWith(route)
    },

    isInventoryRoute() {
      return inventoryRoutePrefixes.some(prefix => this.$route.path.startsWith(prefix))
    },

    isReportsRoute() {
      return reportsRoutePrefixes.some(prefix => this.$route.path.startsWith(prefix))
    },

    handleInventoryHover(state) {
      if (this.isCollapsed) {
        this.inventoryHover = state
      }
    },

    handleReportsHover(state) {
      if (this.isCollapsed) {
        this.reportsHover = state
      }
    },

    syncSubmenusWithRoute() {
      this.showInventorySubmenu = this.isInventoryRoute()
      this.showReportsSubmenu = this.isReportsRoute()
    },
    
    async handleLogout() {
      const confirmed = confirm('Are you sure you want to logout?')
      if (confirmed) {
        this.isLoggingOut = true
        
        try {
          await this.callLogoutAPI()
        } catch (error) {
          console.error('Logout API error:', error)
          // Continue with local logout even if API fails
        } finally {
          this.performLocalLogout()
        }
      }
    },
    
    async callLogoutAPI() {
      const token = this.getStoredToken()

      if (!token) {
        console.warn('No token found for logout')
        return
      }

      try {
        // ✅ Use the API service (same pattern as login)
        const result = await apiService.logout()
        return result
      } catch (error) {
        console.error('API service logout error:', error)
        throw error
      }
    },
    
    getStoredToken() {
      // Try different possible token storage keys (reordered to match login)
      const possibleKeys = [
        'authToken',        // Login.vue uses this
        'access_token',
        'auth_token',
        'token',
        'accessToken',
        'jwt_token',
        'bearer_token',
        'user_token'
      ]

      for (const key of possibleKeys) {
        const token = localStorage.getItem(key) || sessionStorage.getItem(key)
        if (token) {
          return token
        }
      }

      return null
    },
    
    performLocalLogout() {
      // Clear ALL localStorage and sessionStorage to be absolutely sure

      // Method 1: Clear specific auth keys
      const authKeys = [
        'access_token', 'refresh_token', 'auth_token', 'token',
        'accessToken', 'refreshToken', 'authToken', 'userToken',
        'jwt_token', 'bearer_token', 'user_token',
        'user_data', 'user_info', 'user', 'userData', 'userInfo',
        'isAuthenticated', 'isLoggedIn', 'authState'
      ]

      authKeys.forEach(key => {
        localStorage.removeItem(key)
        sessionStorage.removeItem(key)
      })

      // Method 2: Nuclear option - clear everything (comment out if too aggressive)
      // localStorage.clear()
      // sessionStorage.clear()

      // Clear any global state if using Vuex/Pinia
      if (this.$store && this.$store.dispatch) {
        try {
          this.$store.dispatch('auth/logout')
          this.$store.dispatch('auth/clearAuth')
          this.$store.dispatch('user/logout')
        } catch (e) {
          // No auth store found or dispatch failed
        }
      }

      // Reset component state
      this.isLoggingOut = false

      // Use Vue router for smooth navigation
      this.$router.push('/login').catch(err => {
        // Handle navigation failures (e.g., already on login page)
      })
    },
    
    // Helper method to get CSRF token if needed
    getCsrfToken() {
      // Get CSRF token from meta tag or cookie
      const metaToken = document.querySelector('meta[name="csrf-token"]')
      if (metaToken) {
        return metaToken.getAttribute('content')
      }
      
      // Alternative: get from cookie
      const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
      
      return cookieValue ? cookieValue.split('=')[1] : null
    }
  },
  
  mounted() {
    // Load collapsed state from localStorage
    const savedState = localStorage.getItem('sidebar-collapsed')
    if (savedState !== null) {
      this.isCollapsed = JSON.parse(savedState)
      // Emit initial state to parent
      this.$emit('sidebar-toggled', this.isCollapsed)
    }
    this.syncSubmenusWithRoute()
  },
  
  watch: {
    isCollapsed(newValue) {
      // Save collapsed state to localStorage
      localStorage.setItem('sidebar-collapsed', JSON.stringify(newValue))
    },
    '$route.path': {
      immediate: true,
      handler() {
        this.syncSubmenusWithRoute()
      }
    }
  }
}
</script>

<style scoped>
/* ==========================================================================
   SIDEBAR CONTAINER - SEMANTIC THEME SYSTEM
   ========================================================================== */

.sidebar-container {
  width: 280px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 9999;
  transition: width 0.3s ease, background-color 0.3s ease, border-color 0.3s ease;
  background-color: var(--surface-primary);
  border-right: 1px solid var(--border-primary);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.sidebar-container.collapsed {
  width: 80px;
}

/* ==========================================================================
   SIDEBAR HEADER - SEMANTIC STYLING
   ========================================================================== */

.sidebar-header {
  height: 100px; /* Match main layout header height */
  padding: 1.5rem 1rem;
  flex-shrink: 0;
  background-color: var(--surface-primary);
  border-bottom: 1px solid var(--border-primary);
  transition: background-color 0.3s ease, border-color 0.3s ease;
  display: flex;
  align-items: center;
}

.brand-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  justify-content: center;
  position: relative;
}

.brand-logo {
  position: absolute;
  left: 1rem;
}

/* Collapsed mode layout */
.collapsed-layout {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.toggle-row {
  display: flex;
  justify-content: flex-end;
}

.collapsed-header-row {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 100%;
  gap: 0.5rem;
}

.collapsed-toggle {
  margin: 0;
}

.logo-circle {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
}

.logo-text {
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--text-inverse);
}

.brand-title {
  font-weight: 700;
  font-size: 1.1rem;
  margin: 0;
  color: var(--text-primary);
  transition: color 0.3s ease;
}

.brand-subtitle {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  transition: color 0.3s ease;
}

.sidebar-toggle {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.sidebar-toggle:hover {
  background-color: var(--state-hover);
  border-color: var(--border-accent);
  color: var(--text-accent);
}

/* ==========================================================================
   USER PROFILE - SEMANTIC STYLING
   ========================================================================== */

.user-profile {
  padding: 1rem;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-primary);
  transition: border-color 0.3s ease;
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-primary);
  transition: all 0.3s ease;
  text-decoration: none;
  cursor: pointer;
  position: relative;
}

.profile-card:hover {
  background-color: var(--state-hover);
  transform: translateX(2px);
  border-color: var(--border-accent);
}

.profile-card.active {
  color: var(--text-inverse);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  background: linear-gradient(135deg, var(--secondary), var(--secondary-dark));
  border-color: var(--secondary-dark);
}

.profile-card-collapsed {
  justify-content: center;
  padding: 0.75rem;
}

.profile-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--border-accent);
  background-color: var(--surface-primary);
  transition: all 0.3s ease;
}

.profile-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
  transition: color 0.3s ease;
}

.profile-role {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  transition: color 0.3s ease;
}

.profile-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.profile-settings {
  background-color: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-tertiary);
  transition: all 0.3s ease;
}

.profile-settings:hover {
  background-color: var(--state-hover);
  border-color: var(--border-accent);
  color: var(--text-accent);
}

/* ==========================================================================
   NAVIGATION - SEMANTIC STYLING
   ========================================================================== */

.sidebar-nav {
  flex: 1;
  padding: 1rem 0;
  overflow-y: auto;
  overflow-x: visible;
}
.sidebar-container.collapsed .sidebar-nav {
  overflow: visible;
}


.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin: 0.25rem 0.75rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  position: relative;
  border: 1px solid transparent;
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.nav-button {
  background: none;
  border: 1px solid transparent;
  width: 100%;
  text-align: left;
  cursor: pointer;
}

.nav-link:hover {
  transform: translateX(2px);
  background-color: var(--state-hover);
  color: var(--text-accent);
  border-color: var(--border-accent);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.nav-link.active {
  color: var(--text-inverse);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  background: linear-gradient(135deg, var(--secondary), var(--secondary-dark));
  border-color: var(--secondary-dark);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-text {
  flex: 1;
  white-space: nowrap;
}

.nav-chevron {
  transition: transform 0.2s ease;
}

.nav-chevron.rotated {
  transform: rotate(180deg);
}

.nav-indicator {
  position: absolute;
  right: -1px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 24px;
  border-radius: 2px 0 0 2px;
  background-color: var(--text-inverse);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

/* ==========================================================================
   SUBMENU - SEMANTIC STYLING
   ========================================================================== */

.nav-submenu {
  list-style: none;
  padding: 0.5rem 0 0;
  margin: 0;
  margin-left: 2.5rem;
}

.nav-subitem {
  margin: 0.125rem 0;
}

.nav-sublink {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  text-decoration: none;
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  color: var(--text-tertiary);
  transition: all 0.3s ease;
}

.nav-sublink:hover {
  background-color: var(--state-hover);
  color: var(--text-accent);
}

.nav-sublink.active-sub {
  background-color: var(--surface-secondary);
  color: var(--text-primary);
  font-weight: 600;
  border: 1px solid var(--border-accent);
}

.nav-subicon {
  flex-shrink: 0;
}

/* ==========================================================================
   SIDEBAR FOOTER - SEMANTIC STYLING
   ========================================================================== */

.sidebar-footer {
  padding: 1rem;
  flex-shrink: 0;
  background-color: var(--surface-primary);
  border-top: 1px solid var(--border-primary);
  transition: all 0.3s ease;
}

/* ==========================================================================
   LOADING SPINNER
   ========================================================================== */

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ==========================================================================
   BUTTON STATES
   ========================================================================== */

.btn:disabled {
  background-color: var(--state-disabled);
  opacity: 0.6;
  cursor: not-allowed;
}

.btn:disabled:hover {
  transform: none;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

/* ==========================================================================
   COLLAPSED STATE ADJUSTMENTS
   ========================================================================== */

.sidebar-container.collapsed .nav-link {
  justify-content: center;
  padding: 0.75rem;
}

.sidebar-container.collapsed .nav-item {
  margin: 0.25rem 0.5rem;
}

/* ==========================================================================
   ENHANCED INTERACTIONS
   ========================================================================== */

.sidebar-container .btn {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.sidebar-container .btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* ==========================================================================
   RESPONSIVE DESIGN
   ========================================================================== */

.submenu-floating {
  position: absolute;
  left: 36px;
  top: 0;
  background-color: var(--surface-primary);
  border: 1px solid var(--border-primary);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border-radius: 0.75rem;
  padding: 0.75rem;
  z-index: 10000;
  min-width: 180px;
}

.sidebar-container.collapsed .nav-item {
  position: relative;
}

.sidebar-container.collapsed .submenu-floating {
  display: block;
}

.sidebar-container.collapsed .nav-submenu {
  display: none;
}

.sidebar-container.collapsed .nav-submenu.submenu-floating {
  display: block;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(5px);
}
/* ==========================================================================
   SCROLLBAR STYLING - SEMANTIC
   ========================================================================== */

.sidebar-nav::-webkit-scrollbar {
  width: 6px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: var(--surface-tertiary);
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}
</style>