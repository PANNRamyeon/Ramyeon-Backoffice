<template>
  <div class="accounts-page">
    <!-- Page Header -->
    <div class="page-header">
      <h1 class="page-title">User Management</h1>
      <p class="page-subtitle">Manage system users and their permissions</p>
    </div>

    <!-- Action Bar -->
    <ActionBar
      entity-name="user"
      add-button-text="ADD USER"
      search-placeholder="Search users by name, email, or username..."
      :add-options="addOptions"
      :selected-items="selectedUsers"
      :selection-actions="selectionActions"
      :filters="filters"
      :search-value="searchQuery"
      :show-columns-button="false"
      :show-export-button="true"
      :exporting="exporting"
      @add-action="handleAddAction"
      @selection-action="handleSelectionAction"
      @filter-change="handleFilterChange"
      @search-input="handleSearchInput"
      @search-clear="handleSearchClear"
      @export="exportData"
    />

    <!-- Loading State -->
    <div v-if="loading && users.length === 0" class="loading-state">
      <div class="spinner-border"></div>
      <p>Loading users...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-state">
      <div class="alert alert-danger">
        <p>{{ error }}</p>
        <button class="btn btn-primary" @click="fetchUsers()">
          Try Again
        </button>
      </div>
    </div>

    <!-- Success Message -->
    <div v-if="successMessage" class="alert alert-success">
      {{ successMessage }}
    </div>

    <!-- Data Table -->
    <TableTemplate
      v-if="!loading || users.length > 0"
      :items-per-page="pagination.limit"
      :total-items="pagination.total"
      :current-page="pagination.page"
      :show-pagination="true"
      @page-changed="handlePageChange"
    >
      <template #header>
        <tr>
          <th class="checkbox-column">
            <input 
              type="checkbox" 
              class="form-check-input"
              @change="toggleSelectAll" 
              :checked="allSelected"
              :indeterminate.prop="someSelected"
            />
          </th>
          <th>ID</th>
          <th>Username</th>
          <th>Full Name</th>
          <th>Email</th>
          <th>Role</th>
          <th>Status</th>
          <th>Last Login</th>
          <th>Actions</th>
        </tr>
      </template>

      <template #body>
        <tr 
          v-for="user in users" 
          :key="user._id"
          :class="{ 'table-primary': selectedUsers.includes(user._id) }"
        >
          <td class="checkbox-column">
            <input 
              type="checkbox" 
              class="form-check-input"
              :value="user._id"
              v-model="selectedUsers"
            />
          </td>
          <td>
            <span class="badge bg-primary">{{ user._id }}</span>
          </td>
          <td>{{ user.username }}</td>
          <td>{{ user.full_name }}</td>
          <td class="text-tertiary-medium">{{ user.email }}</td>
          <td>
            <span 
              class="badge"
              :class="user.role === 'admin' ? 'bg-warning' : 'bg-info'"
            >
              {{ user.role }}
            </span>
          </td>
          <td>
            <span 
              class="badge"
              :class="user.status === 'active' ? 'bg-success' : 'bg-secondary'"
            >
              {{ user.status }}
            </span>
          </td>
          <td class="text-tertiary-medium">
            {{ formatDate(user.last_login) }}
          </td>
          <td>
            <div class="d-flex gap-1">
              <button
                class="btn btn-outline btn-sm action-btn action-btn-view"
                @click="viewUser(user)"
                title="View Details"
              >
                <Eye :size="14" />
              </button>
              <button
                class="btn btn-outline btn-sm action-btn action-btn-edit"
                @click="editUser(user)"
                title="Edit User"
              >
                <Edit :size="14" />
              </button>
              <button
                class="btn btn-outline btn-sm action-btn action-btn-delete"
                @click="confirmDeleteUser(user)"
                title="Delete User"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </td>
        </tr>
      </template>
    </TableTemplate>

    <!-- Empty State -->
    <div v-if="!loading && users.length === 0 && !error" class="empty-state">
      <div class="card">
        <div class="card-body">
          <p class="empty-message">No users found</p>
          <p class="empty-submessage">Get started by creating your first user account</p>
          <button class="btn btn-add" @click="openAddModal">
            Add First User
          </button>
        </div>
      </div>
    </div>

    <!-- Add/Edit/View User Modal -->
    <AddAccountModal
      ref="accountModal"
      @submit="handleModalSubmit"
      @close="handleModalClose"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUsers } from '@/composables/api/useUsers'
import ActionBar from '@/components/common/ActionBar.vue'
import TableTemplate from '@/components/common/TableTemplate.vue'
import AddAccountModal from '@/components/accounts/AddAccountModal.vue'

/* -------------------------------------------
   COMPOSABLES
------------------------------------------- */
const {
  users,
  loading,
  error,
  pagination,
  fetchUsers,
  createUser,
  updateUser,
  deleteUser: deleteUserService
} = useUsers()

/* -------------------------------------------
   CORE REFS
------------------------------------------- */
const accountModal = ref(null)
const selectedUsers = ref([])
const searchQuery = ref('')
const roleFilter = ref('all')
const statusFilter = ref('all')
const successMessage = ref(null)
const exporting = ref(false)

/* -------------------------------------------
   ACTION BAR CONFIG (must be above handlers)
------------------------------------------- */
const addOptions = [
  {
    key: 'single',
    icon: 'Plus',
    title: 'Add Single User',
    description: 'Create a new user account'
  }
]

const selectionActions = [
  {
    key: 'delete',
    icon: 'Trash2',
    label: 'Delete',
    buttonClass: 'btn-delete-dynamic has-items'
  }
]

/* -------------------------------------------
   FILTER CONFIGURATION
------------------------------------------- */
const filters = computed(() => [
  {
    key: 'role',
    label: 'Role',
    value: roleFilter.value,
    options: [
      { value: 'all', label: 'All Roles' },
      { value: 'admin', label: 'Admin' },
      { value: 'employee', label: 'Employee' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    value: statusFilter.value,
    options: [
      { value: 'all', label: 'All Status' },
      { value: 'active', label: 'Active' },
      { value: 'inactive', label: 'Inactive' }
    ]
  }
])

/* -------------------------------------------
   SELECTION COMPUTED
------------------------------------------- */
const allSelected = computed(() =>
  users.value.length > 0 && selectedUsers.value.length === users.value.length
)

const someSelected = computed(() =>
  selectedUsers.value.length > 0 && selectedUsers.value.length < users.value.length
)

/* -------------------------------------------
   FILTER HELPERS
------------------------------------------- */
const getFilterParams = () => {
  const params = {}

  if (roleFilter.value !== 'all') params.role = roleFilter.value
  if (statusFilter.value !== 'all') params.status = statusFilter.value
  if (searchQuery.value.trim() !== '') params.search = searchQuery.value.trim()

  return params
}

const applyFilters = async () => {
  await fetchUsers({
    page: 1,
    ...getFilterParams()
  })
}

/* -------------------------------------------
   ACTION BAR HANDLERS
------------------------------------------- */
const handleAddAction = (key) => {
  if (key === 'single') openAddModal()
}

const handleSelectionAction = (key) => {
  if (key === 'delete') deleteMultipleUsers()
}

const handleFilterChange = (filterKey, value) => {
  if (filterKey === 'role') roleFilter.value = value
  if (filterKey === 'status') statusFilter.value = value
  applyFilters()
}

const handleSearchInput = (value) => {
  searchQuery.value = value
  applyFilters()
}

const handleSearchClear = () => {
  searchQuery.value = ''
  applyFilters()
}

/* -------------------------------------------
   PAGINATION
------------------------------------------- */
const handlePageChange = (page) => {
  fetchUsers({
    page,
    ...getFilterParams()
  })
}

/* -------------------------------------------
   SELECTION
------------------------------------------- */
const toggleSelectAll = (e) => {
  if (e.target.checked) {
    selectedUsers.value = users.value.map(u => u._id)
  } else {
    selectedUsers.value = []
  }
}

/* -------------------------------------------
   MODAL METHODS
------------------------------------------- */
const openAddModal = () => accountModal.value?.show('add')

const viewUser = (user) => accountModal.value?.show('view', user)

const editUser = (user) => accountModal.value?.show('edit', user)

const handleModalSubmit = async (userData, mode) => {
  try {
    if (mode === 'edit') {
      await updateUser(userData._id, userData)
      showSuccess('User updated successfully')
    } else {
      await createUser(userData)
      showSuccess('User created successfully')
    }
    await applyFilters()
  } catch (err) {
    console.error(err)
    throw err
  }
}

/* -------------------------------------------
   DELETE METHODS
------------------------------------------- */
const deleteMultipleUsers = async () => {
  if (!confirm(`Delete ${selectedUsers.value.length} users?`)) return

  try {
    for (const id of selectedUsers.value) {
      await deleteUserService(id)
    }
    showSuccess(`Deleted ${selectedUsers.value.length} users`)
    selectedUsers.value = []
    await applyFilters()
  } catch (err) {
    error.value = err.message
  }
}

const confirmDeleteUser = async (user) => {
  if (!confirm(`Delete user "${user.username}"?`)) return

  try {
    await deleteUserService(user._id)
    showSuccess(`User "${user.username}" deleted`)
    await applyFilters()
  } catch (err) {
    error.value = err.message
  }
}

/* -------------------------------------------
   EXPORT
------------------------------------------- */
const exportData = () => {
  exporting.value = true
  try {
    const headers = ['ID', 'Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login']

    const csvContent = [
      headers.join(','),
      ...users.value.map(user => [
        user._id,
        user.username,
        user.full_name,
        user.email,
        user.role,
        user.status,
        formatDate(user.last_login)
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = `users_${new Date().toISOString().split('T')[0]}.csv`
    a.click()

    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

/* -------------------------------------------
   UTILITIES
------------------------------------------- */
const showSuccess = (msg) => {
  successMessage.value = msg
  setTimeout(() => successMessage.value = null, 3000)
}

const formatDate = (date) => {
  if (!date) return 'Never'
  return new Date(date).toLocaleString()
}

/* -------------------------------------------
   LIFECYCLE
------------------------------------------- */
onMounted(() => {
  applyFilters()
})
</script>



<style scoped>
.accounts-page {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.25rem 0;
}

.page-subtitle {
  color: var(--text-tertiary);
  margin: 0;
  font-size: 0.875rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 3rem;
  background: var(--surface-primary);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-md);
  margin-top: 1rem;
}

.spinner-border {
  width: 2rem;
  height: 2rem;
  border: 0.25em solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spinner-border 0.75s linear infinite;
}

@keyframes spinner-border {
  to { transform: rotate(360deg); }
}

.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.alert-success {
  background-color: var(--status-success-bg);
  color: var(--status-success);
  border: 1px solid var(--status-success);
}

.alert-danger {
  background-color: var(--status-error-bg);
  color: var(--status-error);
  border: 1px solid var(--status-error);
}

.empty-state .card {
  background: var(--surface-primary);
  border: 1px solid var(--border-secondary);
  border-radius: 0.75rem;
}

.empty-state .card-body {
  padding: 3rem;
}

.empty-message {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-submessage {
  color: var(--text-tertiary);
  margin-bottom: 1.5rem;
}

.checkbox-column {
  width: 40px;
  text-align: center;
}

.d-flex {
  display: flex;
}

.gap-1 {
  gap: 0.25rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.bg-primary {
  background: var(--primary-light);
  color: var(--primary-dark);
}

.badge.bg-warning {
  background: var(--status-warning-bg);
  color: var(--status-warning);
}

.badge.bg-info {
  background: var(--status-info-bg);
  color: var(--status-info);
}

.badge.bg-success {
  background: var(--status-success-bg);
  color: var(--status-success);
}

.badge.bg-secondary {
  background: var(--surface-tertiary);
  color: var(--text-tertiary);
}
</style>