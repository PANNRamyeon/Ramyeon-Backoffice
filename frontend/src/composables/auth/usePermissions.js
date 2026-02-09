// composables/auth/usePermissions.js
import { computed } from 'vue'
import { useAuth } from './useAuth.js'

export function usePermissions() {
  const { user, isAuthenticated } = useAuth()

  // Role checks
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEmployee = computed(() => user.value?.role === 'employee' || user.value?.role === 'cashier')
  const isManager = computed(() => user.value?.role === 'manager' || isAdmin.value)

  // Permission checks for specific actions
  const canManageUsers = computed(() => isAdmin.value)
  const canManageInventory = computed(() => isAdmin.value || isManager.value)
  const canViewReports = computed(() => isAdmin.value || isManager.value)
  const canProcessSales = computed(() => isAuthenticated.value) // All authenticated users
  const canManageSuppliers = computed(() => isAdmin.value || isManager.value)
  const canManagePromotions = computed(() => isAdmin.value || isManager.value)
  const canViewCustomers = computed(() => isAuthenticated.value)
  const canManageCategories = computed(() => isAdmin.value || isManager.value)
  const canViewLogs = computed(() => isAdmin.value)

  // Resource-level permissions
  const canEdit = (resourceType) => {
    switch (resourceType) {
      case 'products':
        return canManageInventory.value
      case 'users':
        return canManageUsers.value
      case 'suppliers':
        return canManageSuppliers.value
      case 'promotions':
        return canManagePromotions.value
      case 'categories':
        return canManageCategories.value
      default:
        return false
    }
  }

  const canDelete = (resourceType) => {
    // More restrictive - usually admin only
    switch (resourceType) {
      case 'products':
      case 'users':
      case 'suppliers':
      case 'promotions':
      case 'categories':
        return isAdmin.value
      default:
        return false
    }
  }

  const canView = (resourceType) => {
    switch (resourceType) {
      case 'dashboard':
        return isAuthenticated.value
      case 'products':
      case 'customers':
        return isAuthenticated.value
      case 'reports':
        return canViewReports.value
      case 'users':
        return canManageUsers.value
      case 'suppliers':
        return canManageSuppliers.value
      case 'logs':
        return canViewLogs.value
      default:
        return false
    }
  }

  // Helper to check multiple permissions
  const hasAnyPermission = (...permissions) => {
    return permissions.some(permission => permission.value)
  }

  const hasAllPermissions = (...permissions) => {
    return permissions.every(permission => permission.value)
  }

  return {
    // Role checks
    isAdmin,
    isEmployee,
    isManager,
    
    // Action permissions
    canManageUsers,
    canManageInventory,
    canViewReports,
    canProcessSales,
    canManageSuppliers,
    canManagePromotions,
    canViewCustomers,
    canManageCategories,
    canViewLogs,
    
    // Resource methods
    canEdit,
    canDelete,
    canView,
    
    // Helper methods
    hasAnyPermission,
    hasAllPermissions
  }
}