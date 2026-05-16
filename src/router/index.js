import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

import Login from '../pages/Login.vue'
import ForgotPassword from '../pages/ForgotPassword.vue'
import ResetPassword from '../pages/ResetPassword.vue'
import MainLayout from '../layouts/MainLayout.vue'

import Dashboard from '../pages/Dashboard.vue'
import Accounts from '../pages/Accounts.vue'
import Customers from '../pages/Customers.vue'
import Products from '@/pages/inventory/Products.vue'
import ProductBulkEntry from '@/pages/inventory/ProductBulkEntry.vue'
import ProductDetails from '@/pages/inventory/ProductDetails.vue'
import Categories from '@/pages/inventory/Categories.vue'
import CategoryDetails from '@/pages/inventory/CategoryDetails.vue'
import Promotions from '@/pages/Promotions.vue'
import SalesByItem from '@/pages/reports/SalesByItem.vue'
import SalesByCategory from '@/pages/reports/SalesByCategory.vue'
import UncategorizedProducts from '@/components/categories/UncategorizedProducts.vue'
import Logs from '@/pages/Logs.vue'
import AllNotifications from '@/pages/notifications/AllNotifications.vue'
import TesterPage from '@/pages/TesterPage.vue'
import Suppliers from '@/pages/suppliers/Suppliers.vue'
import SupplierDetails from '@/pages/suppliers/SupplierDetails.vue'
import OrdersHistory from '@/pages/suppliers/OrdersHistory.vue'

// Debug components (only for development)
import ToastDebug from '@/pages/ToastDebug.vue'

// Simple token check for immediate evaluation
function hasValidToken() {
  const token = localStorage.getItem('access_token')
  return !!token
}

// Auth guard function
function requireAuth(to, from, next) {
  const token = localStorage.getItem('access_token')
  if (token) {
    next()
  } else {
    next('/login')
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login,
    },
    {
      path: '/forgot-password',
      name: 'ForgotPassword',
      component: ForgotPassword,
      meta: {
        title: 'Forgot Password'
      }
    },
    {
      path: '/reset-password',
      name: 'ResetPassword',
      component: ResetPassword,
      meta: {
        title: 'Reset Password'
      }
    },
    // Protected routes that use the main layout
    {
      path: '/',
      component: MainLayout,
      beforeEnter: requireAuth,
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: Dashboard,
          meta: {
            title: 'Dashboard'
          }
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('../pages/Profile.vue'),
          meta: {
            title: 'My Profile'
          }
        },
        {
          path: 'accounts',
          name: 'Accounts',
          component: Accounts,
          meta: {
            title: 'User Accounts'
          }
        },
        {
          path: 'customers',
          name: 'Customers',
          component: Customers,
          meta: {
            title: 'Customers'
          }
        },
        // Inventory routes
        {
          path: 'products',
          name: 'Products',
          component: Products,
          meta: {
            title: 'Products'
          }
        },
        {
          path: 'products/bulk',
          name: 'ProductBulkEntry',
          component: ProductBulkEntry,
          meta: {
            title: 'Bulk Product Entry'
          }
        },
        {
          path: 'products/:id',
          name: 'ProductDetails',
          component: ProductDetails,
          props: true,
          meta: {
            title: 'Product Details'
          }
        },
        {
          path: 'categories',
          name: 'Categories',
          component: Categories,
          meta: {
            title: 'Categories'
          }
        },
        {
          path: 'category/:id',
          name: 'Category Details',
          component: CategoryDetails,
          props: true,
          meta: {
            title: 'Category Details'
          }
        },
        // Suppliers routes
        {
          path: 'suppliers',
          name: 'Suppliers',
          component: Suppliers,
          meta: {
            title: 'Suppliers'
          }
        },
        {
          path: 'suppliers/orders',
          name: 'OrdersHistory',
          component: OrdersHistory,
          meta: {
            title: 'Purchase Orders History',
            breadcrumb: [
              { name: 'Dashboard', path: '/dashboard' },
              { name: 'Suppliers', path: '/suppliers' },
              { name: 'Orders History', path: null }
            ]
          }
        },
        {
          path: 'suppliers/:supplierId',
          name: 'SupplierDetails',
          component: SupplierDetails,
          props: true,
          meta: {
            title: 'Supplier Details',
            breadcrumb: [
              { name: 'Dashboard', path: '/dashboard' },
              { name: 'Suppliers', path: '/suppliers' },
              { name: 'Details', path: null }
            ]
          }
        },
        // Reports
        {
          path: 'salesbyitem',
          name: 'SalesByItem',
          component: SalesByItem,
          meta: {
            title: 'Sales by Item'
          }
        },
        {
          path: 'salesbycategory',
          name: 'SalesByCategory',
          component: SalesByCategory,
          meta: {
            title: 'Sales by Category'
          }
        },
        // Other routes
        {
          path: 'promotions',
          name: 'Promotions',
          component: Promotions,
          meta: {
            title: 'Promotions'
          }
        },
        {
          path: 'logs',
          name: 'Logs',
          component: Logs,
          meta: {
            title: 'System Logs'
          }
        },
        {
          path: 'uncategorized',
          name: 'UncategorizedProducts',
          component: UncategorizedProducts,
          meta: {
            title: 'Uncategorized Products'
          }
        },
        {
          path: 'allNotifications',
          name: 'AllNotifications',
          component: AllNotifications,
          meta: {
            title: 'All Notifications'
          }
        },
        {
          path: 'home',
          name: 'home',
          component: HomeView,
          meta: {
            title: 'Home'
          }
        },
        {
          path: 'about',
          name: 'about',
          component: () => import('../views/AboutView.vue'),
          meta: {
            title: 'About'
          }
        },
        // Development/Testing routes (protected)
        {
          path: 'tester',
          name: 'TesterPage',
          component: TesterPage,
          meta: {
            title: 'Customer CRUD Tester',
            isDevelopmentOnly: true
          }
        },
        {
          path: 'debug/toast',
          name: 'ToastDebug',
          component: ToastDebug,
          meta: {
            title: 'Toast Debug',
            isDevelopmentOnly: true
          }
        }
      ]
    },
    // Catch all route - redirect to login
    {
      path: '/:pathMatch(.*)*',
      redirect: '/login'
    }
  ]
})

// Global navigation guard
router.beforeEach((to, from, next) => {
  // Set page title
  if (to.meta?.title) {
    document.title = `${to.meta.title} - PANN POS`
  } else {
    document.title = 'PANN POS'
  }

  // Handle development-only routes in production
  if (to.meta?.isDevelopmentOnly && import.meta.env.PROD) {
    next('/dashboard')
    return
  }

  next()
})

// Handle navigation errors
router.onError((error) => {
  console.error('Router error:', error)
})

export default router