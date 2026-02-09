<template>
  <div class="supplier-details-page">
    <!-- Header Section -->
    <div class="d-flex justify-content-between align-items-center mb-4 page-header">
      <div class="d-flex align-items-center">
        <button 
          class="btn btn-outline-secondary me-3"
          @click="goBack"
        >
          <ArrowLeft :size="16" class="me-1" />
          Back to Suppliers
        </button>
        <div>
          <h1 class="h2 fw-semibold text-primary-dark mb-0">Supplier Details</h1>
          <p class="page-subtitle mb-0">View and manage supplier information</p>
        </div>
      </div>
      <div class="header-actions d-flex gap-2" v-if="!loading && supplier">
        <button class="btn btn-primary" @click="editSupplier">
          <Edit :size="16" class="me-1" />
          Edit Supplier
        </button>
        <button class="btn btn-primary new-order-btn" @click="createOrder">
          <ShoppingCart :size="16" class="me-1" />
          New Order
        </button>
        <button class="btn btn-success receive-stock-btn" @click="openReceiveStockModal">
          <Package :size="16" class="me-1" />
          Receive Stock
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 loading-text">Loading supplier details...</p>
    </div>

    <!-- Quick Stats Card - Moved to Top -->
    <div v-if="!loading && !error && supplier" class="card stats-card mb-4">
      <div class="card-header">
        <h5 class="card-title mb-0">
          <BarChart3 :size="18" class="me-2" />
          Quick Statistics
        </h5>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number stat-primary">{{ supplier.purchaseOrders || 0 }}</div>
            <div class="stat-label">Total Orders</div>
          </div>
          <div class="stat-item clickable-stat" @click="openActiveOrdersModal">
            <div class="stat-number stat-warning">{{ getActiveOrders() }}</div>
            <div class="stat-label">Active Orders</div>
          </div>
          <div class="stat-item">
            <div class="stat-number stat-success">₱{{ formatCurrency(getTotalSpent()) }}</div>
            <div class="stat-label">Total Spent</div>
          </div>
          <div class="stat-item">
            <div class="stat-number stat-info">{{ getDaysActive() }}</div>
            <div class="stat-label">Days Active</div>
          </div>
        </div>
        
        <!-- Performance Rating -->
        <div class="mt-3 pt-3 performance-rating-divider">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="rating-label">Performance Rating</small>
            <div class="rating-tooltip-wrapper position-relative d-inline-block">
              <small class="rating-value" :class="{ 'cursor-help': getPerformanceRating() !== 'N/A' }">
                {{ getPerformanceRating() }}/5.0
                <Info v-if="getPerformanceRating() !== 'N/A'" :size="12" class="ms-1 opacity-75" />
              </small>
              <!-- Tooltip -->
              <div v-if="getPerformanceRating() !== 'N/A'" class="rating-tooltip">
                <div class="tooltip-header">
                  <strong>Rating Breakdown</strong>
                </div>
                <div class="tooltip-content">
                  <div v-for="factor in getRatingBreakdown()" :key="factor.name" class="tooltip-factor">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                      <span class="factor-name">{{ factor.name }}</span>
                      <span class="factor-weight">({{ factor.weight }}%)</span>
                    </div>
                    <div class="d-flex align-items-center">
                      <div class="factor-score-bar" style="flex: 1; height: 6px; background: var(--surface-tertiary); border-radius: 3px; margin-right: 0.5rem;">
                        <div 
                          class="factor-score-fill" 
                          :style="{ 
                            width: factor.score + '%',
                            backgroundColor: factor.score >= 70 ? '#22c55e' : factor.score >= 50 ? '#3b82f6' : factor.score >= 30 ? '#f59e0b' : '#ef4444'
                          }">
                        </div>
                      </div>
                      <span class="factor-score-value">{{ factor.score.toFixed(1) }}%</span>
                    </div>
                  </div>
                  <div class="tooltip-divider"></div>
                  <div class="tooltip-total">
                    <div class="d-flex justify-content-between align-items-center">
                      <strong>Final Rating:</strong>
                      <strong>{{ getPerformanceRating() }}/5.0</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="progress" style="height: 6px;">
            <div 
              class="progress-bar" 
              :class="getPerformanceRatingClass()"
              :style="{ width: (getPerformanceRatingPercentage() + '%') }">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Supplier Details Content -->
    <div v-if="!loading && !error && supplier" class="row">
      <!-- Left Column - Supplier Info Card with Notes -->
      <div class="col-lg-4">
        <!-- Main Info Card with Integrated Notes -->
        <div class="card supplier-info-card mb-4">
          <div class="card-header bg-primary text-white">
            <div class="d-flex align-items-center">
              <div class="supplier-logo me-3">
                <Building :size="32" />
              </div>
              <div class="flex-grow-1">
                <h4 class="card-title mb-1">{{ supplier.name }}</h4>
                <span :class="['badge', 'status-badge', getStatusBadgeClass(supplier.status)]">
                  {{ formatStatus(supplier.status) }}
                </span>
              </div>
              <div class="dropdown" ref="supplierDropdownRef">
                <button 
                  class="btn btn-link text-white p-0" 
                  type="button" 
                  @click="toggleSupplierDropdown"
                  :class="{ 'active': showSupplierDropdown }"
                  style="transition: opacity 0.2s;"
                  :style="{ opacity: showSupplierDropdown ? '1' : '0.8' }"
                >
                  <MoreVertical :size="20" />
                </button>
                <ul class="dropdown-menu dropdown-menu-modern" :class="{ 'show': showSupplierDropdown }" style="right: 0; left: auto; margin-top: 0.5rem;">
                  <li><a class="dropdown-item" href="#" @click.prevent="handleEditSupplier">
                    <Edit :size="16" class="me-2" />
                    Edit Supplier
                  </a></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item" href="#" @click.prevent="handleToggleFavorite">
                    <Star :size="16" class="me-2" :class="{ 'text-warning': supplier.isFavorite }" />
                    {{ supplier.isFavorite ? 'Remove from Favorites' : 'Add to Favorites' }}
                  </a></li>
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item text-danger" href="#" @click.prevent="handleDeleteSupplier">
                    <Trash2 :size="16" class="me-2" />
                    Delete Supplier
                  </a></li>
                </ul>
              </div>
            </div>
          </div>
          <div class="card-body">
            <!-- Contact Information -->
            <div class="section-header">
              <h6 class="fw-bold section-title mb-3">
                <User :size="16" class="me-2" />
                Contact Information
              </h6>
            </div>
            
            <div class="info-item">
              <label>
                <User :size="16" class="me-2" />
                Contact Person:
              </label>
              <span>{{ supplier.contactPerson || 'Not specified' }}</span>
            </div>
            <div class="info-item">
              <label>
                <Phone :size="16" class="me-2" />
                Phone Number:
              </label>
              <span>
                {{ supplier.phone || 'Not provided' }}
                <button v-if="supplier.phone" class="btn btn-link p-0 ms-2" @click="callSupplier" title="Call">
                  <PhoneCall :size="14" />
                </button>
              </span>
            </div>
            <div class="info-item">
              <label>
                <Mail :size="16" class="me-2" />
                Email Address:
              </label>
              <span>
                {{ supplier.email || 'Not provided' }}
                <button v-if="supplier.email" class="btn btn-link p-0 ms-2" @click="emailSupplier" title="Send Email">
                  <Send :size="14" />
                </button>
              </span>
            </div>
            <div class="info-item">
              <label>
                <MapPin :size="16" class="me-2" />
                Address:
              </label>
              <span class="address-text">
                {{ supplier.address || 'Not specified' }}
                <button v-if="supplier.address" class="btn btn-link p-0 ms-2" @click="openMaps" title="View on Map">
                  <Navigation :size="14" />
                </button>
              </span>
            </div>

            <!-- Business Information -->
            <div class="section-divider"></div>
            <div class="section-header">
              <h6 class="fw-bold section-title mb-3">
                <Building :size="16" class="me-2" />
                Business Information
              </h6>
            </div>

            <div class="info-item">
              <label>
                <Tag :size="16" class="me-2" />
                Supplier Type:
              </label>
              <span>{{ getSupplierTypeLabel(supplier.type) }}</span>
            </div>
            <div class="info-item">
              <label>
                <Calendar :size="16" class="me-2" />
                Member Since:
              </label>
              <span>{{ formatDate(supplier.createdAt) }}</span>
            </div>
            <div class="info-item">
              <label>
                <Clock :size="16" class="me-2" />
                Last Updated:
              </label>
              <span>{{ formatDate(supplier.updatedAt) }}</span>
            </div>

            <!-- Additional Notes Section - Integrated -->
            <div class="section-divider"></div>
            <div class="section-header">
              <div class="d-flex justify-content-between align-items-center">
                <h6 class="fw-bold section-title mb-0">
                  <FileText :size="16" class="me-2" />
                  Additional Notes
                </h6>
                <button class="btn btn-outline-secondary btn-sm" @click="toggleNotesEdit">
                  <Edit :size="14" class="me-1" />
                  {{ editingNotes ? 'Save' : 'Edit' }}
                </button>
              </div>
            </div>

            <div class="mt-3">
              <div v-if="!editingNotes" class="notes-content">
                {{ supplier.notes || 'No additional notes available' }}
              </div>
              <div v-else>
                <textarea 
                  class="form-control" 
                  v-model="editableNotes" 
                  rows="3"
                  placeholder="Add notes about this supplier..."
                ></textarea>
                <div class="mt-2">
                  <button class="btn btn-primary btn-sm me-2" @click="saveNotes">Save</button>
                  <button class="btn btn-secondary btn-sm" @click="cancelNotesEdit">Cancel</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column - Orders and Activity -->
      <div class="col-lg-8">
        <!-- Orders Section -->
        <div class="card orders-card mb-4">
          <div class="card-header">
            <div class="d-flex justify-content-between align-items-center">
              <h5 class="card-title mb-0">
                <Package :size="18" class="me-2" />
                Order History
                <span class="badge bg-secondary ms-2">{{ filteredOrders.length }}</span>
              </h5>
              <div class="d-flex gap-2 align-items-center" v-if="orders.length > 0">
                <select class="form-select form-select-sm" v-model="orderStatusFilter" @change="filterOrders">
                  <option value="all">All Orders</option>
                  <option value="pending delivery">Pending Delivery</option>
                  <option value="received">Received</option>
                  <option value="partially received">Partially Received</option>
                  <option value="depleted">Depleted</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <div class="dropdown" ref="sortDropdownRef">
                  <button 
                    class="btn btn-outline-secondary btn-sm dropdown-toggle" 
                    type="button" 
                    @click="toggleSortDropdown"
                    :class="{ 'active': showSortDropdown }"
                  >
                    <Filter :size="14" />
                  </button>
                  <ul class="dropdown-menu" :class="{ 'show': showSortDropdown }">
                    <li><a class="dropdown-item" href="#" @click.prevent="handleSort('date')">Sort by Date</a></li>
                    <li><a class="dropdown-item" href="#" @click.prevent="handleSort('amount')">Sort by Amount</a></li>
                    <li><a class="dropdown-item" href="#" @click.prevent="handleSort('status')">Sort by Status</a></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <div class="card-body p-0">
            <div class="table-responsive" v-if="orders.length > 0">
              <table class="table table-hover orders-table mb-0">
                <thead class="table-light">
                  <tr>
                    <th>
                      <input type="checkbox" class="form-check-input" v-model="selectAllOrders" @change="toggleSelectAllOrders">
                    </th>
                    <th>Order ID</th>
                    <th>Order Date</th>
                    <th>Items</th>
                    <th>Total Cost</th>
                    <th>Expected Date</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="order in filteredOrders" :key="order.id" :class="{ 'table-warning': isOverdue(order) }">
                    <td>
                      <input type="checkbox" class="form-check-input" :value="order.id" v-model="selectedOrders">
                    </td>
                    <td class="order-id">
                      <div class="d-flex align-items-center">
                        {{ order.id }}
                        <AlertTriangle v-if="isOverdue(order)" :size="14" class="text-warning ms-1" title="Overdue" />
                      </div>
                    </td>
                    <td>{{ formatDate(order.date) }}</td>
                    <td>
                      <div>
                        {{ order.items?.length || 0 }} item(s)
                        <br>
                        <small class="order-detail-text">{{ order.quantity }} total quantity</small>
                        <br>
                        <small class="order-detail-text">{{ order.description || 'Various items' }}</small>
                      </div>
                    </td>
                    <td class="amount fw-bold">₱{{ formatCurrency(order.total) }}</td>
                    <td>
                      <div>
                        {{ formatDate(order.expectedDate) }}
                        <br>
                        <small :class="['order-meta-text', { 'text-danger': isOverdue(order) }]">
                          {{ getTimeRemaining(order.expectedDate) }}
                        </small>
                      </div>
                    </td>
                    <td>
                      <span :class="['badge', 'order-status', getOrderStatusClass(order.status)]">
                        {{ order.status }}
                      </span>
                    </td>
                    <td>
                      <div class="action-buttons">
                        <button 
                          class="btn btn-outline-primary btn-sm" 
                          @click="viewReceipt(order)" 
                          title="View Order Details"
                        >
                          <Eye :size="14" />
                        </button>
                        <button 
                          class="btn btn-outline-warning btn-sm" 
                          @click="editBatchDetails(order)" 
                          title="Edit Order Details"
                          :disabled="order.status === 'Received' || order.status === 'Depleted' || order.status === 'Cancelled' || cancelingOrderId === order.id"
                        >
                          <Edit :size="14" />
                        </button>
                        <button 
                          class="btn btn-outline-danger btn-sm"
                          @click="promptCancelOrder(order)"
                          title="Cancel Order"
                          :disabled="order.status === 'Cancelled' || order.status === 'Received' || order.status === 'Depleted' || cancelingOrderId === order.id"
                        >
                          <span v-if="cancelingOrderId === order.id" class="spinner-border spinner-border-sm"></span>
                          <XCircle v-else :size="14" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <!-- Empty State -->
            <div v-if="orders.length === 0" class="text-center empty-state py-5">
              <Package :size="48" class="empty-state-icon mb-3" />
              <div>
                <h6 class="empty-state-text">No orders found</h6>
                <p class="mb-3">No orders have been placed with this supplier yet.</p>
                <button class="btn btn-primary btn-sm" @click="openCreateOrderModal">
                  <Plus :size="16" class="me-1" />
                  New Order
                </button>
              </div>
            </div>
            
            <!-- Bulk Actions Bar -->
            <div v-if="selectedOrders.length > 0" class="alert alert-info mx-3 mb-3 d-flex justify-content-between align-items-center">
              <span>{{ selectedOrders.length }} order(s) selected</span>
              <div class="btn-group btn-group-sm">
              <!--  <button class="btn btn-outline-primary" @click="bulkExportOrders">Export Selected</button>
                <button class="btn btn-outline-warning" @click="bulkUpdateStatus">Update Status</button> -->
                <button class="btn btn-outline-danger" @click="bulkDeleteOrders">Delete Selected</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Activity Timeline -->
        <div class="card activity-card">
          <div class="card-header">
            <h5 class="card-title mb-0">
              <Activity :size="18" class="me-2" />
              Recent Activity
            </h5>
          </div>
          <div class="card-body">
            <div class="timeline" v-if="recentActivity.length > 0">
              <div v-for="activity in recentActivity" :key="activity.id" class="timeline-item">
                <div class="timeline-marker" :class="getActivityMarkerClass(activity.type)">
                  <component :is="getActivityIcon(activity.type)" :size="14" />
                </div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <strong>{{ activity.title }}</strong>
                    <small class="activity-time ms-2">{{ formatTimeAgo(activity.date) }}</small>
                  </div>
                  <p class="mb-1 activity-description">{{ activity.description }}</p>
                  <small class="activity-user">by {{ activity.user }}</small>
                </div>
              </div>
            </div>
            
            <!-- Empty Timeline State -->
            <div v-if="recentActivity.length === 0" class="text-center py-4">
              <Clock :size="32" class="empty-state-icon mb-2" />
              <p class="empty-state-text">No recent activity</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Show message if no supplier found -->
    <div v-if="!loading && !error && !supplier" class="alert alert-warning text-center">
      <h5>Supplier Not Found</h5>
      <p>No supplier found with ID: {{ supplierId }}</p>
      <button class="btn btn-primary" @click="goBack">Go Back to Suppliers</button>
    </div>

    <!-- Create Order Modal -->
    <CreateOrderModal
      v-if="showCreateOrderModal && supplier"
      :show="showCreateOrderModal"
      :supplier="supplier"
      @close="closeCreateOrderModal"
      @saved="handleOrderSave"
    />

    <!-- Receive Stock Modal (Shows ALL pending batches for bulk receiving) -->
    <ReceiveStockModal
      v-if="showReceiveStockModal && supplier"
      :show="showReceiveStockModal"
      :supplier="supplier"
      @close="closeReceiveStockModal"
      @received="handleStockReceived"
    />

    <!-- Batch Details Modal (View only) -->
    <BatchDetailsModal
      v-if="showBatchDetailsModal"
      :show="showBatchDetailsModal"
      :receipt="selectedReceiptForView"
      @close="closeBatchDetailsModal"
    />

    <!-- Edit Batch Details Modal -->
    <EditBatchDetailsModal
      v-if="showEditBatchDetailsModal && supplier"
      :show="showEditBatchDetailsModal"
      :receipt="selectedReceiptForEdit"
      :supplier="supplier"
      @close="closeEditBatchDetailsModal"
      @saved="handleBatchDetailsUpdated"
    />

    <!-- Active Orders Modal -->
    <ActiveOrdersModal
      v-if="showActiveOrdersModal && supplier"
      :show="showActiveOrdersModal"
      :orders="getActiveOrdersForModal()"
      :supplier="supplier"
      :loading="false"
      @close="closeActiveOrdersModal"
    />

    <!-- Order Details Modal -->
    <OrderDetailsModal
      v-if="selectedOrderForView"
      :show="showOrderDetailsModal"
      :order="selectedOrderForView"
      :can-edit="selectedOrderForView.status !== 'Received' && selectedOrderForView.status !== 'Cancelled'"
      :initial-mode="orderModalMode"
      @close="closeOrderDetailsModal"
      @save="handleOrderUpdate"
      @edit-mode-changed="handleOrderEditModeChanged"
    />

    <!-- Edit Supplier Modal -->
    <Teleport to="body">
      <div v-if="showEditModal" class="modal-overlay" @click="handleEditModalOverlayClick">
        <div class="modal-content modern-modal" @click.stop>
          <div class="modal-header edit-supplier-header">
            <div class="d-flex align-items-center">
              <div class="modal-icon me-3">
                <Edit :size="24" />
              </div>
              <div>
                <h4 class="modal-title mb-1">Edit Supplier</h4>
                <p class="modal-subtitle mb-0 small">Update supplier information</p>
              </div>
            </div>
            <button type="button" class="btn-close btn-close-custom" @click="closeEditModal"></button>
          </div>
          <div class="modal-body edit-supplier-body">
            <form @submit.prevent="saveSupplier">
              <div class="row g-3">
                <!-- Basic Information Section -->
                <div class="col-md-6">
                  <div class="form-group">
                    <label for="supplierName" class="form-label modern-label required">
                      <Building :size="16" class="me-2" />
                      Company Name
                    </label>
                    <input 
                      type="text" 
                      class="form-control modern-input" 
                      id="supplierName"
                      v-model="editForm.name"
                      placeholder="Enter company name"
                      required
                    >
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="contactPerson" class="form-label modern-label">
                      <User :size="16" class="me-2" />
                      Contact Person
                    </label>
                    <input 
                      type="text" 
                      class="form-control modern-input"
                      id="contactPerson"
                      v-model="editForm.contactPerson"
                      placeholder="Enter contact person name"
                    >
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="email" class="form-label modern-label">
                      <Mail :size="16" class="me-2" />
                      Email Address
                    </label>
                    <input 
                      type="email" 
                      class="form-control modern-input"
                      id="email"
                      v-model="editForm.email"
                      placeholder="company@example.com"
                    >
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="phone" class="form-label modern-label">
                      <Phone :size="16" class="me-2" />
                      Phone Number
                    </label>
                    <input 
                      type="tel" 
                      class="form-control modern-input"
                      id="phone"
                      v-model="editForm.phone"
                      placeholder="Enter phone number"
                    >
                  </div>
                </div>

                <!-- Divider -->
                <div class="col-12">
                  <hr class="form-divider">
                </div>

                <!-- Additional Information Section -->
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="type" class="form-label modern-label">
                      <Tag :size="16" class="me-2" />
                      Supplier Type
                    </label>
                    <select class="form-select modern-input" id="type" v-model="editForm.type">
                      <option value="">Select type</option>
                      <option value="food">Food & Beverages</option>
                      <option value="packaging">Packaging Materials</option>
                      <option value="equipment">Equipment & Tools</option>
                      <option value="services">Services</option>
                      <option value="raw_materials">Raw Materials</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="status" class="form-label modern-label">
                      <Activity :size="16" class="me-2" />
                      Status
                    </label>
                    <select class="form-select modern-input" id="status" v-model="editForm.status">
                      <option value="active">Active</option>
                      <option value="pending">Pending</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="form-group">
                    <label for="phone" class="form-label modern-label">
                      <Phone :size="16" class="me-2" />
                      Phone Number
                    </label>
                    <input 
                      type="tel" 
                      class="form-control modern-input"
                      id="phone"
                      v-model="editForm.phone"
                      placeholder="Enter phone number"
                    >
                  </div>
                </div>

                <div class="col-12">
                  <div class="form-group">
                    <label for="address" class="form-label modern-label">
                      <MapPin :size="16" class="me-2" />
                      Address
                    </label>
                    <textarea 
                      class="form-control modern-input" 
                      id="address"
                      v-model="editForm.address"
                      rows="3"
                      placeholder="Enter supplier address"
                    ></textarea>
                  </div>
                </div>
                <div class="col-12">
                  <div class="form-group">
                    <label for="notes" class="form-label modern-label">
                      <FileText :size="16" class="me-2" />
                      Notes
                    </label>
                    <textarea 
                      class="form-control modern-input" 
                      id="notes"
                      v-model="editForm.notes"
                      rows="3"
                      placeholder="Additional notes about this supplier"
                    ></textarea>
                  </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer edit-supplier-footer">
            <button type="button" class="btn btn-outline-secondary btn-cancel" @click="closeEditModal">Cancel</button>
            <button type="button" class="btn btn-primary btn-update" @click="saveSupplier" :disabled="saving">
              <div v-if="saving" class="spinner-border spinner-border-sm me-2"></div>
              <span v-if="!saving">Update Supplier</span>
              <span v-else>Updating...</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDeleteModal" class="modal-overlay" @click="handleDeleteModalOverlayClick">
        <div class="modal-content modern-modal" @click.stop>
          <div class="modal-header edit-supplier-header">
            <div class="d-flex align-items-center">
              <div class="modal-icon me-3" style="background: linear-gradient(135deg, #dc3545, #c82333);">
                <AlertTriangle :size="24" />
              </div>
              <div>
                <h4 class="modal-title mb-1 text-danger">Delete Supplier</h4>
                <p class="modal-subtitle mb-0 small">Confirm deletion</p>
              </div>
            </div>
            <button type="button" class="btn-close btn-close-custom" @click="showDeleteModal = false"></button>
          </div>
          <div class="modal-body edit-supplier-body">
            <p>Are you sure you want to delete <strong>{{ supplier?.name }}</strong>?</p>
            <div class="alert alert-warning">
              <strong>Warning:</strong> This action cannot be undone. All associated purchase orders and history will be preserved but this supplier will be removed from your system.
            </div>
          </div>
          <div class="modal-footer edit-supplier-footer">
            <button type="button" class="btn btn-outline-secondary btn-cancel" @click="showDeleteModal = false">Cancel</button>
            <button type="button" class="btn btn-danger btn-delete" @click="confirmDeleteSupplier" :disabled="deleting">
              <div v-if="deleting" class="spinner-border spinner-border-sm me-2"></div>
              <span v-if="!deleting">Delete Supplier</span>
              <span v-else>Deleting...</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { 
  ArrowLeft,
  Edit,
  Plus,
  Building,
  User,
  Phone,
  Mail,
  MapPin,
  Tag,
  Calendar,
  Clock,
  BarChart3,
  ShoppingCart,
  MoreVertical,
  Star,
  PhoneCall,
  Send,
  Navigation,
  FileText,
  Trash2,
  Package,
  Eye,
  Filter,
  AlertTriangle,
  Activity,
  CreditCard,
  Info,
  XCircle
} from 'lucide-vue-next'
import CreateOrderModal from '@/components/suppliers/CreateOrderModal.vue'
import ReceiveStockModal from '@/components/suppliers/ReceiveStockModal.vue'
import BatchDetailsModal from '@/components/suppliers/BatchDetailsModal.vue'
import EditBatchDetailsModal from '@/components/suppliers/EditBatchDetailsModal.vue'
import OrderDetailsModal from '@/components/suppliers/OrderDetailsModal.vue'
import ActiveOrdersModal from '@/components/suppliers/ActiveOrdersModal.vue'
import { useToast } from '@/composables/ui/useToast'
import { useAuth } from '@/composables/auth/useAuth'
import { useProducts } from '@/composables/api/useProducts'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default {
  name: 'SupplierDetails',
  components: {
    ArrowLeft,
    Edit,
    Plus,
    Building,
    User,
    Phone,
    Mail,
    MapPin,
    Tag,
    Calendar,
    Clock,
    BarChart3,
    ShoppingCart,
    MoreVertical,
    Star,
    PhoneCall,
    Send,
    Navigation,
    FileText,
    Trash2,
    Package,
    Eye,
    Filter,
    AlertTriangle,
    Activity,
    CreditCard,
    Info,
    XCircle,
    CreateOrderModal,
    ReceiveStockModal,
    BatchDetailsModal,
    EditBatchDetailsModal,
    OrderDetailsModal,
    ActiveOrdersModal
  },
  props: {
    supplierId: {
      type: [String, Number],
      required: true
    }
  },
  setup() {
    const { user } = useAuth()
    const { success, error: showError } = useToast()
    const { fetchProductById } = useProducts()
    
    return {
      user,
      success,
      showError,
      fetchProductById
    }
  },
  data() {
    return {
      supplier: null,
      orders: [],
      filteredOrders: [],
      recentActivity: [],
      loading: false,
      error: null,
      saving: false,
      deleting: false,
      orderStatusFilter: 'all',
      selectedOrders: [],
      selectAllOrders: false,
      cancelingOrderId: null,

      showCreateOrderModal: false,
      showReceiveStockModal: false,
      showBatchDetailsModal: false,
      showEditBatchDetailsModal: false,
      showActiveOrdersModal: false,
      selectedReceiptForView: null,
      selectedReceiptForEdit: null,
      showOrderDetailsModal: false,
      selectedOrderForView: null,
      orderModalMode: 'view',
      
      showEditModal: false,
      showDeleteModal: false,
      showSortDropdown: false,
      sortDropdownRef: null,
      showSupplierDropdown: false,
      supplierDropdownRef: null,
      editForm: {
        name: '',
        contactPerson: '',
        email: '',
        phone: '',
        address: '',
        type: '',
        status: 'active',
        notes: ''
      },
      
      editingNotes: false,
      editableNotes: ''
    }
  },
  async mounted() {
    await this.fetchSupplierDetails()
    
    // Add click outside listeners for dropdowns
    document.addEventListener('click', this.handleClickOutside)
  },
  
  beforeUnmount() {
    // Clean up click outside listeners
    document.removeEventListener('click', this.handleClickOutside)
  },
  watch: {
    supplierId: {
      handler(newId, oldId) {
        this.fetchSupplierDetails()
      },
      immediate: false
    }
  },
  methods: {
    async fetchSupplierDetails() {
      this.loading = true
      this.error = null
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        
        // ===== STEP 1: Fetch Supplier Info =====
        const supplierResponse = await axios.get(
          `${API_BASE_URL}/suppliers/${this.supplierId}/`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        const backendSupplier = supplierResponse.data
        
        // ===== STEP 2: Fetch Batches for this Supplier =====
        let batchesList = []
        try {
          const batchesResponse = await axios.get(
            `${API_BASE_URL}/batches/by-supplier/${this.supplierId}/`,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          )
          
          // Handle different response formats
          const rawBatches = batchesResponse.data.batches || batchesResponse.data || []
          
          // Ensure it's always an array
          if (Array.isArray(rawBatches)) {
            batchesList = rawBatches
          } else if (rawBatches.data && Array.isArray(rawBatches.data)) {
            batchesList = rawBatches.data
          } else {
            console.warn('⚠️ Batches response is not an array:', rawBatches)
            batchesList = []
          }
          
        } catch (batchesError) {
          console.error('❌ Error fetching batches:', batchesError)
          if (batchesError.response?.status === 404) {
            console.warn('⚠️ Batches endpoint returned 404 - batches will be empty')
          }
          batchesList = []
        }
        
        // ===== STEP 3: Map Supplier Data =====
        this.supplier = {
          id: backendSupplier._id,
          name: backendSupplier.supplier_name,
          contactPerson: backendSupplier.contact_person || '',
          email: backendSupplier.email || '',
          phone: backendSupplier.phone_number || '',
          address: backendSupplier.address || '',
          purchaseOrders: 0, // Will be set after grouping batches into orders
          status: backendSupplier.isDeleted ? 'inactive' : 'active',
          type: backendSupplier.type || 'food',
          rating: null, // Will be calculated based on performance metrics
          isFavorite: false,
          notes: backendSupplier.notes || '',
          createdAt: backendSupplier.created_at,
          updatedAt: backendSupplier.updated_at
        }
        
        // ===== STEP 4: Group Batches by Date to Create "Receipts" =====
        // Safety check
        if (!Array.isArray(batchesList)) {
          console.error('❌ batchesList is not an array:', batchesList)
          batchesList = []
        }
        
        // If no batches, set empty orders
        if (batchesList.length === 0) {
          this.orders = []
          this.filteredOrders = []
          this.editableNotes = this.supplier.notes
          this.recentActivity = [
            {
              id: 1,
              type: 'supplier_updated',
              title: 'Supplier Information Updated',
              description: 'Contact details updated',
              user: 'Admin User',
              date: backendSupplier.updated_at
            }
          ]
          
          return
        }
        
        // Group batches by receipt/order identifier to prevent unrelated orders from merging
        const getBatchGroupKey = (batch) => {
          const notes = batch?.notes || ''
          const receiptMatch = notes.match(/Receipt:\s*([^\|]+)/i)
          if (receiptMatch) {
            return `receipt:${receiptMatch[1].trim()}`
          }
          if (batch?.batch_number) {
            return `batch:${batch.batch_number}`
          }
          if (batch?.reference_number) {
            return `reference:${batch.reference_number}`
          }
          return `id:${batch?._id || 'unknown'}`
        }

        const batchesByReceipt = {}
        batchesList.forEach(batch => {
          const key = getBatchGroupKey(batch)
          if (!batchesByReceipt[key]) {
            batchesByReceipt[key] = []
          }
          batchesByReceipt[key].push(batch)
        })
        
        // ===== STEP 4.5: Enrich batches with product details for complete category info =====
        const enrichedBatchesByReceipt = {}
        for (const [groupKey, batches] of Object.entries(batchesByReceipt)) {
          enrichedBatchesByReceipt[groupKey] = await Promise.all(
            batches.map(async (batch) => {
              try {
                // Always fetch product details to get category info (don't rely on batch fields)
                if (batch.product_id) {
                  const productResponse = await this.fetchProductById(batch.product_id)
                  const product = productResponse.data
                  
                  if (product) {
                    return {
                      ...batch,
                      // Get product name and category info from product, not from batch
                      product_name: product.product_name || product.name || 'Unknown Product',
                      category_id: product.category_id || '',
                      category_name: product.category_name || '',
                      subcategory_name: product.subcategory_name || ''
                    }
                  }
                }
                
                return batch
              } catch (err) {
                console.warn(`Failed to fetch product details for batch ${batch._id}:`, err)
                return batch
              }
            })
          )
        }
        
        // Convert grouped batches to "orders" format
        this.orders = Object.values(enrichedBatchesByReceipt).map((batches) => {
          const totalCost = batches.reduce((sum, b) => sum + ((b.cost_price || 0) * (b.quantity_received || 0)), 0)
          const totalQuantity = batches.reduce((sum, b) => sum + (b.quantity_received || 0), 0)
          
          const firstBatch = batches[0]
          const createdDate = firstBatch?.created_at ? firstBatch.created_at.split('T')[0] : new Date().toISOString().split('T')[0]

          let receiptId = `SR-${createdDate.replace(/-/g, '')}`
          const firstBatchNotes = batches[0].notes || ''
          const receiptMatch = firstBatchNotes.match(/Receipt:\s*([^\|]+)/)
          if (receiptMatch) {
            receiptId = receiptMatch[1].trim()
          }
          
          // Get expected_delivery_date and date_received from first batch
          const expectedDate = firstBatch.expected_delivery_date ? 
            (typeof firstBatch.expected_delivery_date === 'string' ? firstBatch.expected_delivery_date.split('T')[0] : new Date(firstBatch.expected_delivery_date).toISOString().split('T')[0]) : 
            createdDate
          const receivedDate = firstBatch.date_received ? 
            (typeof firstBatch.date_received === 'string' ? firstBatch.date_received.split('T')[0] : new Date(firstBatch.date_received).toISOString().split('T')[0]) : 
            null
          
          return {
            id: receiptId,
            date: firstBatch.created_at ? firstBatch.created_at.split('T')[0] : createdDate, // Order date (when PO was created)
            quantity: totalQuantity,
            total: totalCost,
            expectedDate: expectedDate, // Expected delivery date
            receivedDate: receivedDate, // Actual received date (null for pending)
            status: this.getReceiptStatus(batches),
            description: `Order with ${batches.length} item(s)`,
            notes: firstBatchNotes,
            priority: 'normal',
            subtotal: totalCost,
            tax: 0,
            shippingCost: 0,
            taxRate: 0,
            items: batches.map(batch => ({
            name: batch.product_name || batch.name || 'Unknown Product',
              quantity: batch.quantity_received,
              unit: 'pcs',
              unitPrice: batch.cost_price || 0,
              totalPrice: (batch.cost_price || 0) * (batch.quantity_received || 0),
              notes: batch.notes || '',
              productId: batch.product_id,
              product_name: batch.product_name || batch.name || 'Unknown Product', // Add product_name for ActiveOrdersModal
              batchNumber: batch.batch_number,  // ✅ Pass batch number for activation
              batchId: batch._id,  // ✅ Pass batch ID 
              expiryDate: batch.expiry_date,
              quantityRemaining: batch.quantity_remaining,
              // ✅ Enhanced category info from product details
              categoryId: batch.category_id || '',
              categoryName: batch.category_name || '',
              subcategoryName: batch.subcategory_name || ''
            })),
            orderHistory: [{
              id: batches[0].created_at,
              type: 'stock_received',
              title: 'Stock Received',
              description: `Received ${batches.length} batch(es) containing ${totalQuantity} units`,
              user: 'System',
              date: batches[0].created_at
            }]
          }
        }).sort((a, b) => new Date(b.date) - new Date(a.date))
        
        // Update total orders count after grouping
        this.supplier.purchaseOrders = this.orders.length
        
        this.filteredOrders = [...this.orders]
        this.editableNotes = this.supplier.notes
        
        this.recentActivity = [
          {
            id: 1,
            type: 'supplier_updated',
            title: 'Supplier Information Updated',
            description: 'Contact details updated',
            user: 'Admin User',
            date: backendSupplier.updated_at
          }
        ]
        
        
      } catch (error) {
        console.error('Error fetching supplier details:', error)
        
        if (error.response?.status === 404) {
          this.error = `Supplier with ID ${this.supplierId} not found`
          this.showError(`Supplier with ID ${this.supplierId} not found`)
        } else {
          this.error = error.response?.data?.error || `Failed to load supplier details: ${error.message}`
          this.showError(this.error)
        }
      } finally {
        this.loading = false
      }
    },

    getReceiptStatus(batches) {
       if (!batches || batches.length === 0) return 'Unknown'
       
       const allCancelled = batches.every(b => b.status === 'cancelled')
       const allPending = batches.every(b => b.status === 'pending')
       const allActive = batches.every(b => b.status === 'active')
       const allInactive = batches.every(b => b.status === 'inactive')
       const hasPending = batches.some(b => b.status === 'pending')
       const hasCancelled = batches.some(b => b.status === 'cancelled')
       
       if (allCancelled) return 'Cancelled'
       if (allPending) return 'Pending Delivery'
       if (allActive) return 'Received'
       if (allInactive) return 'Depleted'
       if (hasCancelled) return 'Mixed Status'
       if (hasPending) return 'Partially Received'
       
       return 'Mixed Status'
     },

    openReceiveStockModal() {
      // Open the "Receive Stock" modal that shows ALL pending batches
      this.showReceiveStockModal = true
    },

    closeReceiveStockModal() {
      this.showReceiveStockModal = false
    },

    openActiveOrdersModal() {
      // Open the "Active Orders" modal that shows pending orders for this supplier
      this.showActiveOrdersModal = true
    },

    closeActiveOrdersModal() {
      this.showActiveOrdersModal = false
    },
    
    async handleStockReceived(results) {
      
      if (results.successful?.length > 0) {
        this.success(`Successfully received ${results.successful.length} batch(es)`)
      }
      
      if (results.failed?.length > 0) {
        this.showError(`Failed to receive ${results.failed.length} batch(es)`)
      }
      
      // Refresh supplier details to show updated batches
      await this.fetchSupplierDetails()
    },


    createOrder() {
      this.openCreateOrderModal()
    },

    openCreateOrderModal() {
      this.showCreateOrderModal = true
    },

    closeCreateOrderModal() {
      this.showCreateOrderModal = false
    },

    async handleOrderSave(result) {
      
      const { successful, failed } = result.results
      
      if (successful.length > 0) {
        this.success(`Successfully created ${successful.length} pending order(s)`)
      }
      
      if (failed.length > 0) {
        this.showError(`Failed to create ${failed.length} order(s)`)
      }
      
      // Refresh supplier details to show new batches
      await this.fetchSupplierDetails()
    },

    canReceiveOrder(order) {
      return order.status === 'Pending' || order.status === 'Active'
    },


    viewReceipt(receipt) {
      this.selectedReceiptForView = receipt
      this.showBatchDetailsModal = true
    },
    
    closeBatchDetailsModal() {
      this.showBatchDetailsModal = false
      this.selectedReceiptForView = null
    },

    editBatchDetails(receipt) {
      this.selectedReceiptForEdit = receipt
      this.showEditBatchDetailsModal = true
    },
    
    closeEditBatchDetailsModal() {
      this.showEditBatchDetailsModal = false
      this.selectedReceiptForEdit = null
    },

    async handleBatchDetailsUpdated(updatedReceipt) {
       this.success('Purchase order updated successfully')
       
       // Refresh supplier details to show updated batches
       await this.fetchSupplierDetails()
     },

    goBack() {
      this.$router.push({ name: 'Suppliers' })
    },


    callSupplier() {
      if (this.supplier?.phone) {
        window.open(`tel:${this.supplier.phone}`)
        this.success(`Calling ${this.supplier.name}...`)
      } else {
        this.showError('No phone number available for this supplier')
      }
    },

    emailSupplier() {
      if (this.supplier?.email) {
        window.open(`mailto:${this.supplier.email}`)
        this.success(`Opening email to ${this.supplier.name}...`)
      } else {
        this.showError('No email address available for this supplier')
      }
    },

    openMaps() {
      if (this.supplier?.address) {
        const encodedAddress = encodeURIComponent(this.supplier.address)
        window.open(`https://maps.google.com/maps?q=${encodedAddress}`, '_blank')
        this.success('Opening location in Google Maps...')
      } else {
        this.showError('No address available for this supplier')
      }
    },

    editSupplier() {
      this.editForm = {
        name: this.supplier.name || '',
        contactPerson: this.supplier.contactPerson || '',
        email: this.supplier.email || '',
        phone: this.supplier.phone || '',
        address: this.supplier.address || '',
        type: this.supplier.type || '',
        status: this.supplier.status || 'active',
        notes: this.supplier.notes || ''
      }
      this.showEditModal = true
    },

    handleEditModalOverlayClick() {
      if (!this.saving) {
        this.closeEditModal()
      }
    },

    handleDeleteModalOverlayClick() {
      if (!this.deleting) {
        this.showDeleteModal = false
      }
    },

    closeEditModal() {
      this.showEditModal = false
      this.editForm = {
        name: '',
        contactPerson: '',
        email: '',
        phone: '',
        address: '',
        type: '',
        status: 'active',
        notes: ''
      }
    },

    async saveSupplier() {
      this.saving = true
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        
        const backendData = {
          supplier_name: this.editForm.name,
          contact_person: this.editForm.contactPerson,
          email: this.editForm.email,
          phone_number: this.editForm.phone,
          address: this.editForm.address,
          type: this.editForm.type,
          notes: this.editForm.notes
        }
        
        const response = await axios.put(
          `${API_BASE_URL}/suppliers/${this.supplier.id}/`,
          backendData,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        const updated = response.data
        this.supplier = {
          id: updated._id,
          name: updated.supplier_name,
          contactPerson: updated.contact_person || '',
          email: updated.email || '',
          phone: updated.phone_number || '',
          address: updated.address || '',
          purchaseOrders: updated.purchase_orders?.length || 0,
          status: updated.isDeleted ? 'inactive' : 'active',
          type: updated.type || 'food',
          rating: this.supplier.rating,
          isFavorite: this.supplier.isFavorite,
          notes: updated.notes || '',
          createdAt: updated.created_at,
          updatedAt: updated.updated_at
        }
        
        this.closeEditModal()
        
        // Show success toast instead of setting successMessage
        this.success(`${this.supplier.name} has been updated successfully!`)
        
      } catch (error) {
        console.error('Error updating supplier:', error)
        const errorMessage = error.response?.data?.error || `Failed to update supplier: ${error.message}`
        
        // Show error toast instead of setting error
        this.showError(errorMessage)
        
      } finally {
        this.saving = false
      }
    },


    async toggleFavorite() {
      const previousFavoriteState = this.supplier.isFavorite
      this.supplier.isFavorite = !this.supplier.isFavorite
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        
        await axios.put(
          `${API_BASE_URL}/suppliers/${this.supplier.id}/`,
          {
            isFavorite: this.supplier.isFavorite
          },
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        // Show success toast
        this.success(`${this.supplier.name} ${this.supplier.isFavorite ? 'added to' : 'removed from'} favorites`)
      } catch (error) {
        // Revert on error
        this.supplier.isFavorite = previousFavoriteState
        console.error('Error updating favorite status:', error)
        const errorMessage = error.response?.data?.error || `Failed to update favorite status: ${error.message}`
        this.showError(errorMessage)
      }
    },

    deleteSupplier() {
      this.showDeleteModal = true
    },

    async confirmDeleteSupplier() {
      this.deleting = true
      
      try {
        const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
        
        await axios.delete(
          `${API_BASE_URL}/suppliers/${this.supplier.id}/`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        this.showDeleteModal = false
        
        // Show success toast (soft delete)
        this.success(`${this.supplier.name} has been deleted successfully (soft delete)`)
        
        setTimeout(() => {
          this.goBack()
        }, 1500)
        
      } catch (error) {
        console.error('Error deleting supplier:', error)
        const errorMessage = error.response?.data?.error || `Failed to delete supplier: ${error.message}`
        
        // Show error toast instead of setting error
        this.showError(errorMessage)
        
      } finally {
        this.deleting = false
      }
    },

    filterOrders() {
      if (this.orderStatusFilter === 'all') {
        this.filteredOrders = [...this.orders]
      } else {
        this.filteredOrders = this.orders.filter(order => 
          order.status.toLowerCase() === this.orderStatusFilter.toLowerCase()
        )
      }
    },

    toggleSortDropdown(event) {
      if (event) {
        event.stopPropagation()
      }
      this.showSortDropdown = !this.showSortDropdown
    },

    closeSortDropdown() {
      this.showSortDropdown = false
    },

    handleClickOutside(event) {
      if (this.$refs.sortDropdownRef && !this.$refs.sortDropdownRef.contains(event.target)) {
        this.closeSortDropdown()
      }
      if (this.$refs.supplierDropdownRef && !this.$refs.supplierDropdownRef.contains(event.target)) {
        this.closeSupplierDropdown()
      }
    },

    toggleSupplierDropdown(event) {
      if (event) {
        event.stopPropagation()
      }
      this.showSupplierDropdown = !this.showSupplierDropdown
    },

    closeSupplierDropdown() {
      this.showSupplierDropdown = false
    },

    handleEditSupplier(event) {
      event.preventDefault()
      this.editSupplier()
      this.closeSupplierDropdown()
    },

    handleToggleFavorite(event) {
      event.preventDefault()
      this.toggleFavorite()
      this.closeSupplierDropdown()
    },

    handleDeleteSupplier(event) {
      event.preventDefault()
      this.deleteSupplier()
      this.closeSupplierDropdown()
    },

    handleSort(criteria) {
      this.sortOrders(criteria)
      this.closeSortDropdown()
    },

    sortOrders(criteria) {
      this.filteredOrders.sort((a, b) => {
        switch (criteria) {
          case 'date':
            return new Date(b.date) - new Date(a.date)
          case 'amount':
            return b.total - a.total
          case 'status':
            return a.status.localeCompare(b.status)
          default:
            return 0
        }
      })
      
      // Show toast for feedback
      this.success(`Orders sorted by ${criteria}`)
    },

    toggleSelectAllOrders() {
      if (this.selectAllOrders) {
        this.selectedOrders = this.filteredOrders.map(order => order.id)
      } else {
        this.selectedOrders = []
      }
    },

    isOverdue(order) {
      const expectedDate = new Date(order.expectedDate)
      const today = new Date()
      return expectedDate < today && (order.status === 'Pending' || order.status === 'Active')
    },

    getTimeRemaining(dateString) {
      const expectedDate = new Date(dateString)
      const today = new Date()
      const diffTime = expectedDate - today
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays < 0) {
        return `${Math.abs(diffDays)} days overdue`
      } else if (diffDays === 0) {
        return 'Due today'
      } else if (diffDays === 1) {
        return 'Due tomorrow'
      } else {
        return `${diffDays} days remaining`
      }
    },

    formatTimeAgo(dateString) {
      const date = new Date(dateString)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
      const diffHours = Math.floor(diffTime / (1000 * 60 * 60))
      const diffMinutes = Math.floor(diffTime / (1000 * 60))

      if (diffDays > 0) {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
      } else if (diffHours > 0) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
      } else if (diffMinutes > 0) {
        return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`
      } else {
        return 'Just now'
      }
    },

    getActivityIcon(type) {
      const icons = {
        order_created: Plus,
        order_received: Package,
        supplier_updated: Edit,
        payment_processed: CreditCard
      }
      return icons[type] || Activity
    },

    getActivityMarkerClass(type) {
      const classes = {
        order_created: 'bg-primary',
        order_received: 'bg-success',
        supplier_updated: 'bg-info',
        payment_processed: 'bg-warning'
      }
      return classes[type] || 'bg-secondary'
    },

    viewOrder(order) {
      
      this.selectedOrderForView = order
      this.orderModalMode = 'view'
      this.showOrderDetailsModal = true
    },

    editOrder(order) {
      this.selectedOrderForView = order
      this.orderModalMode = 'edit'
      this.showOrderDetailsModal = true
    },

    closeOrderDetailsModal() {
      this.showOrderDetailsModal = false
      this.selectedOrderForView = null
      this.orderModalMode = 'view'
    },

    deleteOrder(order) {
      if (confirm(`Are you sure you want to delete order ${order.id}?`)) {
        this.orders = this.orders.filter(o => o.id !== order.id)
        this.filterOrders()
        
        // Show success toast instead of setting successMessage
        this.success(`Order ${order.id} deleted successfully`)
      }
    },

    duplicateOrder(order) {
      this.showError(`Duplicate order ${order.id} feature coming soon!`)
    },

    trackOrder(order) {
      this.showError(`Track order ${order.id} feature coming soon!`)
    },

    handleOrderUpdate(updatedOrder) {
      const index = this.orders.findIndex(o => o.id === updatedOrder.id)
      if (index !== -1) {
        this.orders[index] = updatedOrder
        this.filterOrders()
        
        // Show success toast instead of setting successMessage
        this.success(`Order ${updatedOrder.id} updated successfully`)
      }
      
      this.closeOrderDetailsModal()
    },

    handleOrderEditModeChanged(isEditMode) {
      // Edit mode changed
    },

    bulkExportOrders() {
      this.showError(`Export ${this.selectedOrders.length} selected orders feature coming soon!`)
    },

    bulkUpdateStatus() {
      this.showError(`Update status for ${this.selectedOrders.length} selected orders feature coming soon!`)
    },

    bulkDeleteOrders() {
      if (confirm(`Are you sure you want to delete ${this.selectedOrders.length} selected orders?`)) {
        this.orders = this.orders.filter(o => !this.selectedOrders.includes(o.id))
        this.selectedOrders = []
        this.selectAllOrders = false
        this.filterOrders()
        
        // Show success toast instead of setting successMessage
        this.success('Selected orders deleted successfully')
      }
    },

    toggleNotesEdit() {
      if (this.editingNotes) {
        this.saveNotes()
      } else {
        this.editingNotes = true
      }
    },

    saveNotes() {
      this.supplier.notes = this.editableNotes
      this.editingNotes = false
      
      // Show success toast instead of setting successMessage
      this.success('Notes updated successfully')
    },

    cancelNotesEdit() {
      this.editableNotes = this.supplier.notes
      this.editingNotes = false
    },

    getOrderStatusClass(status) {
      const classes = {
        'Received': 'bg-success',
        'Pending Delivery': 'bg-warning',
        'Partially Received': 'bg-info',
        'Pending': 'bg-warning',
        'Partial': 'bg-info',
        'Cancelled': 'bg-danger',
        'Active': 'bg-primary',
        'Depleted': 'bg-secondary'
      }
      return classes[status] || 'bg-secondary'
    },

    getSupplierTypeLabel(type) {
      const labels = {
        'food': 'Food & Beverages',
        'packaging': 'Packaging Materials',
        'equipment': 'Equipment & Tools',
        'services': 'Services',
        'raw_materials': 'Raw Materials',
        'other': 'Other'
      }
      return labels[type] || 'Not specified'
    },

    getActiveOrders() {
      // Count orders that are currently pending (not yet received)
      return this.orders.filter(order => 
        order.status === 'Pending Delivery' || order.status === 'Partially Received'
      ).length
    },

    getActiveOrdersForModal() {
      
      // Filter for pending orders (both Pending Delivery and Partially Received)
      const activeOrders = this.orders.filter(order => {
        const isActive = order.status === 'Pending Delivery' || order.status === 'Partially Received'
        return isActive
      })
      
      
      // Transform the orders to match the format expected by ActiveOrdersModal
      const transformedOrders = activeOrders.map(order => {
        
        return {
          id: order.id,
          supplier: this.supplier.name,
          supplierId: this.supplier.id,
          supplierEmail: this.supplier.email || 'N/A',
          orderDate: order.date, // Map date to orderDate
          expectedDelivery: order.expectedDate, // Map expectedDate to expectedDelivery
          deliveredDate: order.receivedDate, // Map receivedDate to deliveredDate
          totalAmount: order.total, // Map total to totalAmount
          status: order.status,
          items: order.items.map(item => {
            return {
              name: item.name || item.product_name || item.productId || 'Unknown Product',
              product_name: item.name || item.product_name || 'Unknown Product',
              product_id: item.productId,
              quantity: item.quantity,
              unitPrice: item.unitPrice,
              totalPrice: item.totalPrice,
              batchNumber: item.batchNumber,
              batchId: item.batchId,
              expiryDate: item.expiryDate,
              quantityRemaining: item.quantityRemaining
            }
          }),
          description: order.description,
          notes: order.notes
        }
      })
      
      return transformedOrders
    },

    getTotalSpent() {
      return this.orders
        .filter(order => order.status === 'Received')
        .reduce((total, order) => total + order.total, 0)
    },

    getDaysActive() {
      if (!this.supplier?.createdAt) return 0
      const createdDate = new Date(this.supplier.createdAt)
      const today = new Date()
      const diffTime = Math.abs(today - createdDate)
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    },

    getPerformanceRating() {
      // Calculate performance rating based on multiple factors
      if (!this.orders || this.orders.length === 0) {
        return 'N/A'
      }

      const receivedOrders = this.orders.filter(order => 
        order.status === 'Received' && order.expectedDate && order.receivedDate
      )

      // If no completed orders, return a baseline rating
      if (receivedOrders.length === 0) {
        const pendingOrders = this.orders.filter(order => 
          order.status === 'Pending Delivery' || order.status === 'Partially Received'
        )
        // New supplier with only pending orders gets neutral rating
        return pendingOrders.length > 0 ? '3.0' : 'N/A'
      }

      // Factor 1: On-time Delivery Rate (40% weight)
      let onTimeDeliveryRate = 0
      let onTimeCount = 0

      receivedOrders.forEach(order => {
        const expectedDate = new Date(order.expectedDate)
        const receivedDate = new Date(order.receivedDate)
        const diffDays = Math.ceil((receivedDate - expectedDate) / (1000 * 60 * 60 * 24))

        if (diffDays <= 0) {
          // On time or early (early is also good)
          onTimeCount++
        } else if (diffDays <= 3) {
          // Slightly late (1-3 days) - partial credit
          onTimeCount += 0.7
        }
        // Late more than 3 days gets 0 credit (onTimeCount stays the same)
      })

      onTimeDeliveryRate = receivedOrders.length > 0 
        ? (onTimeCount / receivedOrders.length) * 100 
        : 0

      // Factor 2: Order Frequency/Activity (25% weight)
      // More orders = better (capped at reasonable max)
      const daysActive = this.getDaysActive() || 1
      const ordersPerMonth = (this.orders.length / (daysActive / 30))
      const frequencyScore = Math.min(ordersPerMonth / 2, 1) * 100 // Normalize to 0-100

      // Factor 3: Value Contribution (20% weight)
      // Higher total spent = better (normalized based on average)
      // Use only receivedOrders with dates (same as Top Performers calculation)
      const totalSpent = receivedOrders.reduce((sum, o) => sum + o.total, 0)
      const avgOrderValue = receivedOrders.length > 0 ? totalSpent / receivedOrders.length : 0
      // Assuming ₱10,000+ per order is good, scale accordingly
      const valueScore = Math.min((avgOrderValue / 10000) * 100, 100)

      // Factor 4: Consistency (15% weight)
      // Regular ordering pattern = better
      const orderDates = this.orders
        .filter(o => o.date)
        .map(o => new Date(o.date))
        .sort((a, b) => a - b)
      
      let consistencyScore = 50 // Default neutral
      if (orderDates.length >= 3) {
        // Calculate time between orders
        const intervals = []
        for (let i = 1; i < orderDates.length; i++) {
          const diffDays = (orderDates[i] - orderDates[i-1]) / (1000 * 60 * 60 * 24)
          intervals.push(diffDays)
        }
        
        if (intervals.length > 0) {
          // Lower variance = more consistent
          const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
          const variance = intervals.reduce((sum, interval) => {
            return sum + Math.pow(interval - avgInterval, 2)
          }, 0) / intervals.length
          const stdDev = Math.sqrt(variance)
          
          // Lower standard deviation = higher consistency score
          // Normalize: if stdDev is 0, score is 100; if stdDev is > avgInterval, score approaches 0
          consistencyScore = Math.max(0, Math.min(100, 100 - (stdDev / avgInterval) * 100))
        }
      }

      // Calculate weighted average
      const weightedRating = (
        (onTimeDeliveryRate * 0.40) +
        (frequencyScore * 0.25) +
        (valueScore * 0.20) +
        (consistencyScore * 0.15)
      ) / 100 * 5 // Convert to 0-5 scale

      // Round to 1 decimal place and ensure it's between 0 and 5
      return Math.max(0, Math.min(5, Math.round(weightedRating * 10) / 10)).toFixed(1)
    },

    getPerformanceRatingPercentage() {
      const rating = this.getPerformanceRating()
      if (rating === 'N/A') return 0
      return (parseFloat(rating) / 5) * 100
    },

    getPerformanceRatingClass() {
      const rating = this.getPerformanceRating()
      if (rating === 'N/A') return 'bg-secondary'
      
      const numRating = parseFloat(rating)
      if (numRating >= 4.0) return 'bg-success'
      if (numRating >= 3.0) return 'bg-info'
      if (numRating >= 2.0) return 'bg-warning'
      return 'bg-danger'
    },

    getRatingBreakdown() {
      // Calculate all factors and return breakdown
      if (!this.orders || this.orders.length === 0) {
        return []
      }

      const receivedOrders = this.orders.filter(order => 
        order.status === 'Received' && order.expectedDate && order.receivedDate
      )

      if (receivedOrders.length === 0) {
        return []
      }

      // Factor 1: On-time Delivery Rate (40% weight)
      let onTimeCount = 0
      receivedOrders.forEach(order => {
        const expectedDate = new Date(order.expectedDate)
        const receivedDate = new Date(order.receivedDate)
        const diffDays = Math.ceil((receivedDate - expectedDate) / (1000 * 60 * 60 * 24))

        if (diffDays <= 0) {
          onTimeCount++
        } else if (diffDays <= 3) {
          onTimeCount += 0.7
        }
      })
      const onTimeDeliveryRate = receivedOrders.length > 0 
        ? (onTimeCount / receivedOrders.length) * 100 
        : 0

      // Factor 2: Order Frequency/Activity (25% weight)
      const daysActive = this.getDaysActive() || 1
      const ordersPerMonth = (this.orders.length / (daysActive / 30))
      const frequencyScore = Math.min(ordersPerMonth / 2, 1) * 100

      // Factor 3: Value Contribution (20% weight)
      const totalSpent = receivedOrders.reduce((sum, o) => sum + o.total, 0)
      const avgOrderValue = receivedOrders.length > 0 ? totalSpent / receivedOrders.length : 0
      const valueScore = Math.min((avgOrderValue / 10000) * 100, 100)

      // Factor 4: Consistency (15% weight)
      const orderDates = this.orders
        .filter(o => o.date)
        .map(o => new Date(o.date))
        .sort((a, b) => a - b)
      
      let consistencyScore = 50 // Default neutral
      if (orderDates.length >= 3) {
        const intervals = []
        for (let i = 1; i < orderDates.length; i++) {
          const diffDays = (orderDates[i] - orderDates[i-1]) / (1000 * 60 * 60 * 24)
          intervals.push(diffDays)
        }
        
        if (intervals.length > 0) {
          const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
          const variance = intervals.reduce((sum, interval) => {
            return sum + Math.pow(interval - avgInterval, 2)
          }, 0) / intervals.length
          const stdDev = Math.sqrt(variance)
          
          consistencyScore = Math.max(0, Math.min(100, 100 - (stdDev / avgInterval) * 100))
        }
      }

      return [
        {
          name: 'On-time Delivery',
          weight: 40,
          score: Math.round(onTimeDeliveryRate * 10) / 10
        },
        {
          name: 'Order Frequency',
          weight: 25,
          score: Math.round(frequencyScore * 10) / 10
        },
        {
          name: 'Value Contribution',
          weight: 20,
          score: Math.round(valueScore * 10) / 10
        },
        {
          name: 'Consistency',
          weight: 15,
          score: Math.round(consistencyScore * 10) / 10
        }
      ]
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0)
    },

    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },

    getStatusBadgeClass(status) {
      const classes = {
        active: 'bg-success',
        inactive: 'bg-danger',
        pending: 'bg-warning'
      }
      return classes[status] || 'bg-secondary'
    },

    formatStatus(status) {
      return status.charAt(0).toUpperCase() + status.slice(1)
    },

    async promptCancelOrder(order) {
      if (!order) {
        return
      }

      if (order.status === 'Received' || order.status === 'Depleted') {
        this.showError('Completed orders cannot be cancelled.')
        return
      }

      if (order.status === 'Cancelled') {
        this.showError(`Order ${order.id} has already been cancelled.`)
        return
      }

      const confirmed = window.confirm(`Cancel order ${order.id}? This will mark the order as cancelled and cannot be undone.`)
      if (!confirmed) {
        return
      }

      await this.performOrderCancellation(order)
    },

    async performOrderCancellation(order) {
      if (!order) {
        return
      }

      const batchIds = Array.isArray(order.items)
        ? order.items.map(item => item.batchId).filter(Boolean)
        : []

      if (batchIds.length === 0) {
        this.showError('Cannot cancel this order because no batch information was found.')
        return
      }

      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('authToken') || sessionStorage.getItem('authToken')

      if (!token) {
        this.showError('Authentication token not found. Please sign in again.')
        return
      }

      this.cancelingOrderId = order.id

      try {
        await Promise.all(batchIds.map(batchId =>
          axios.put(
            `${API_BASE_URL}/batches/${batchId}/`,
            { status: 'cancelled' },
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          )
        ))

        const applyStatusUpdate = (list) => {
          if (!Array.isArray(list)) {
            return
          }
          const match = list.find(o => o.id === order.id)
          if (match) {
            match.status = 'Cancelled'
            if (Array.isArray(match.items)) {
              match.items.forEach(item => {
                item.status = 'cancelled'
              })
            }
          }
        }

        applyStatusUpdate(this.orders)
        applyStatusUpdate(this.filteredOrders)

        order.status = 'Cancelled'
        if (Array.isArray(order.items)) {
          order.items.forEach(item => {
            item.status = 'cancelled'
          })
        }

        if (this.selectedOrderForView && this.selectedOrderForView.id === order.id) {
          this.selectedOrderForView.status = 'Cancelled'
        }

        this.selectedOrders = this.selectedOrders.filter(id => id !== order.id)
        this.selectAllOrders = false

        this.filterOrders()
        this.success(`Order ${order.id} has been cancelled`)
      } catch (error) {
        console.error('Error cancelling order:', error)
        const message = error.response?.data?.error || 'Failed to cancel the order. Please try again.'
        this.showError(message)
      } finally {
        this.cancelingOrderId = null
      }
    },
  }
}
</script>

<style scoped>
@import '@/assets/styles/colors.css';

.supplier-details-page {
  background-color: var(--surface-secondary);
  min-height: 100vh;
  padding: 1.5rem;
}

.page-header {
  background-color: var(--surface-elevated);
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-secondary);
  margin-bottom: 1.5rem;
}

.header-actions {
  flex-wrap: wrap;
  gap: 0.5rem;
}

.new-order-btn,
.receive-stock-btn {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  transition: all 0.2s ease;
}

.new-order-btn {
  border-color: var(--primary);
  color: var(--text-primary);
}

.new-order-btn:hover {
  background-color: var(--state-hover);
  border-color: var(--border-accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.receive-stock-btn {
  border-color: var(--success);
  color: var(--text-primary);
}

.receive-stock-btn:hover {
  background-color: var(--state-hover);
  border-color: var(--success-dark-mode);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.dropdown-menu-modern {
  border-radius: 12px;
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--border-primary);
  background-color: var(--surface-elevated);
  padding: 0.75rem 0;
  min-width: 280px;
}

.dropdown-menu-modern .dropdown-item {
  padding: 0.75rem 1.25rem;
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.dropdown-menu-modern .dropdown-item:hover {
  background-color: var(--state-hover);
  color: var(--text-accent);
  transform: translateX(2px);
}

.dropdown-menu-modern .dropdown-item.disabled {
  color: var(--text-disabled);
  cursor: not-allowed;
  opacity: 0.6;
}

/* Fix for sort dropdown in Order History */
.dropdown {
  position: relative;
}

.dropdown-menu {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  min-width: 160px;
  padding: 0.5rem 0;
  margin: 0.125rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
  text-align: left;
  list-style: none;
  background-color: var(--surface-elevated);
  background-clip: padding-box;
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  box-shadow: var(--shadow-lg);
}

.dropdown-menu.show {
  display: block !important;
}

/* Supplier dropdown specific styling */
.dropdown-menu-modern {
  border-radius: 12px !important;
  box-shadow: var(--shadow-xl) !important;
  border: 1px solid var(--border-primary) !important;
  padding: 0.5rem 0 !important;
  min-width: 220px !important;
  margin-top: 0.5rem !important;
  background-color: var(--surface-elevated) !important;
}

.dropdown-menu-modern .dropdown-item {
  padding: 0.75rem 1.25rem !important;
  display: flex !important;
  align-items: center !important;
  color: var(--text-secondary) !important;
  transition: all 0.2s ease !important;
  font-size: 0.9rem !important;
  text-decoration: none !important;
}

.dropdown-menu-modern .dropdown-item:hover {
  background-color: var(--state-hover) !important;
  color: var(--text-accent) !important;
}

.dropdown-menu-modern .dropdown-item.text-danger {
  color: var(--error) !important;
}

.dropdown-menu-modern .dropdown-item.text-danger:hover {
  background-color: rgba(220, 53, 69, 0.1) !important;
  color: var(--error) !important;
}

.dropdown-menu-modern .dropdown-divider {
  margin: 0.5rem 0 !important;
  border-top: 1px solid var(--neutral-light) !important;
  opacity: 0.5 !important;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 0.5rem 1rem;
  clear: both;
  font-weight: 400;
  color: #212529;
  text-align: inherit;
  text-decoration: none;
  white-space: nowrap;
  background-color: transparent;
  border: 0;
  cursor: pointer;
  transition: background-color 0.15s ease-in-out;
}

.dropdown-item:hover,
.dropdown-item:focus {
  color: var(--text-primary);
  background-color: var(--state-hover);
}

.btn.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: white;
}

.supplier-info-card {
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  overflow: hidden;
  background-color: var(--surface-primary);
}

.supplier-logo {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.status-badge {
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
}

.section-header {
  margin-bottom: 1rem;
}

.section-divider {
  height: 1px;
  background-color: var(--border-primary);
  margin: 1.5rem 0;
}

.info-item {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.info-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
  padding-bottom: 0;
}

.info-item label {
  font-weight: 500;
  color: var(--text-tertiary);
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
}

.info-item span {
  color: var(--text-secondary);
  font-weight: 500;
  display: flex;
  align-items: center;
}

.stats-card {
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  background-color: var(--surface-primary);
}

.orders-card, .activity-card, .notes-card {
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  background-color: var(--surface-primary);
}

.orders-table {
  font-size: 0.9rem;
}

.orders-table th {
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-primary);
}

.orders-table td {
  vertical-align: middle;
  border-top: 1px solid var(--border-primary);
  color: var(--text-secondary);
}

.order-id {
  font-family: 'Monaco', 'Menlo', monospace;
  font-weight: 600;
  color: var(--primary);
}

.amount {
  text-align: right;
}

.order-status {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.dark-theme .order-status.bg-warning {
  color: #111827; /* near-black for contrast */
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  margin-bottom: 1.5rem;
  position: relative;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 30px;
  bottom: -24px;
  width: 2px;
  background-color: var(--neutral-medium);
}

.timeline-marker {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 1rem;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.timeline-content {
  flex-grow: 1;
}

.timeline-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
}

.notes-content {
  color: var(--text-secondary);
  line-height: 1.6;
  background-color: var(--surface-tertiary);
  padding: 0.75rem;
  border-radius: 8px;
  font-style: italic;
  border: 1px solid var(--border-primary);
}

.modern-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

/* Edit Supplier Modal Header */
.edit-supplier-header {
  padding: 1.5rem 1.75rem 1rem 1.75rem !important;
  background: linear-gradient(135deg, var(--surface-tertiary), var(--surface-secondary));
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-dark);
  box-shadow: 0 2px 8px rgba(115, 146, 226, 0.2);
}

.btn-close-custom {
  opacity: 0.7;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.btn-close-custom:hover {
  opacity: 1;
  transform: scale(1.05);
}

.dark-theme .btn-close-custom {
  filter: invert(1);
}

.modal-title {
  color: var(--text-primary);
  font-weight: 600;
  margin: 0;
  font-size: 1.5rem;
}

/* Edit Supplier Modal Body */
.edit-supplier-body {
  padding: 1.5rem 1.75rem 1.25rem 1.75rem !important;
  background-color: var(--surface-elevated);
  max-height: calc(90vh - 200px);
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1rem;
}

.modern-label {
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  font-size: 0.9rem;
  letter-spacing: 0.01em;
}

.modern-input {
  border: 1px solid var(--input-border);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  background-color: var(--input-bg);
  color: var(--input-text);
  height: auto;
}

.modern-input:hover:not(:focus) {
  border-color: var(--border-accent);
  background-color: var(--surface-tertiary);
}

.modern-input:focus {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.2rem rgba(160, 123, 227, 0.15);
  background-color: var(--input-bg);
  outline: none;
}

.form-select.modern-input {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23343a40' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M2 5l6 6 6-6'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 16px 12px;
  padding-right: 40px;
}

textarea.modern-input {
  resize: vertical;
  min-height: 80px;
}

.form-divider {
  margin: 1rem 0;
  border: none;
  border-top: 1px solid var(--border-primary);
  opacity: 0.5;
}

/* Edit Supplier Modal Footer */
.edit-supplier-footer {
  padding: 1.25rem 1.75rem 1.75rem 1.75rem !important;
  background-color: var(--surface-tertiary);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-cancel {
  border: 2px solid var(--border-primary);
  color: var(--text-secondary);
  border-radius: 8px;
  font-weight: 500;
  padding: 10px 24px;
  transition: all 0.2s ease;
  background-color: transparent;
}

.btn-cancel:hover {
  background-color: var(--state-hover);
  border-color: var(--border-primary);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn-update {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border: none;
  border-radius: 8px;
  font-weight: 500;
  padding: 10px 24px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(115, 146, 226, 0.25);
}

.btn-update:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(115, 146, 226, 0.35);
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
}

.btn-update:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-delete {
  background: linear-gradient(135deg, #dc3545, #c82333);
  border: none;
  border-radius: 8px;
  font-weight: 500;
  padding: 10px 24px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(220, 53, 69, 0.25);
  color: white;
}

.btn-delete:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.35);
  background: linear-gradient(135deg, #c82333, #dc3545);
}

.btn-delete:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.form-label.required::after {
  content: '*';
  color: var(--error);
  margin-left: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background-color: var(--surface-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.stat-primary {
  color: var(--primary);
}

.dark-theme .stat-primary {
  color: var(--primary-dark-mode);
}

.stat-warning {
  color: #f59e0b;
}

.dark-theme .stat-warning {
  color: #fbbf24;
}

.stat-success {
  color: #22c55e;
}

.dark-theme .stat-success {
  color: var(--success-dark-mode);
}

.stat-info {
  color: #3b82f6;
}

.dark-theme .stat-info {
  color: var(--info-dark-mode-light);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.clickable-stat {
  cursor: pointer;
  transition: all 0.2s ease;
}

.clickable-stat:hover {
  background-color: var(--state-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.text-primary-dark {
  color: var(--primary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

/* Dark mode text classes */
.page-subtitle {
  color: var(--text-secondary);
}

.loading-text {
  color: var(--text-secondary);
}

.rating-label {
  color: var(--text-primary);
  font-weight: 500;
}

.rating-value {
  color: var(--text-primary);
  font-weight: 600;
}

.performance-rating-divider {
  border-top: 1px solid var(--border-primary);
}

.factor-weight {
  color: var(--text-tertiary);
}

.section-title {
  color: var(--text-primary);
}

.order-detail-text {
  color: var(--text-secondary);
}

.order-meta-text {
  color: var(--text-secondary);
}

.empty-state {
  color: var(--text-secondary);
}

.empty-state-icon {
  color: var(--text-tertiary);
  opacity: 0.6;
}

.empty-state-text {
  color: var(--text-secondary);
}

.activity-time {
  color: var(--text-tertiary);
}

.activity-description {
  color: var(--text-secondary);
}

.activity-user {
  color: var(--text-tertiary);
}

.modal-subtitle {
  color: var(--text-secondary);
}

/* Button links in info sections */
.info-item .btn-link {
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color 0.2s ease;
}

.info-item .btn-link:hover {
  color: var(--text-accent);
}

.address-text {
  color: var(--text-secondary);
}

/* Responsive adjustments */
@media (max-width: 992px) {
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .header-actions {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .dropdown-menu-modern {
    width: 100%;
    min-width: unset;
  }
  
  .supplier-details-page {
    padding: 1rem;
  }
}

@media (max-width: 576px) {
  .page-header {
    padding: 1rem;
  }
  
  .section-divider {
    margin: 1rem 0;
  }
}

/* Modal Overlay (for Edit Supplier Modal) */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background-color: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  z-index: 9999 !important;
  animation: fadeIn 0.3s ease;
  backdrop-filter: blur(4px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Modal Content (for Edit Supplier Modal) */
.modal-content {
  position: relative !important;
  max-width: 720px;
  width: 95%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
  z-index: 10000 !important;
  background-color: var(--surface-elevated);
  border-radius: 16px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-2xl);
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Responsive Modal Styles for Edit Supplier */
@media (max-width: 768px) {
  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
    width: calc(100% - 2rem);
  }

  .edit-supplier-header {
    padding: 1.25rem 1.5rem 0.75rem 1.5rem !important;
  }

  .edit-supplier-header h4 {
    font-size: 1.25rem;
  }

  .edit-supplier-body {
    padding: 1.25rem 1.5rem 1rem 1.5rem !important;
  }

  .edit-supplier-footer {
    padding: 1rem 1.5rem 1.25rem 1.5rem !important;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  /* Stack columns on mobile */
  .row > [class*="col-md-"] {
    width: 100%;
    flex: 0 0 100%;
    max-width: 100%;
  }

  .form-divider {
    margin: 0.75rem 0;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
    width: calc(100% - 1rem);
    border-radius: 8px;
  }

  .edit-supplier-header {
    padding: 0.9rem 1rem 0.65rem 1rem !important;
  }

  .edit-supplier-header h4 {
    font-size: 1.1rem;
  }

  .edit-supplier-body {
    padding: 0.9rem 1rem 0.75rem 1rem !important;
  }

  .edit-supplier-footer {
    padding: 0.75rem 1rem 0.9rem 1rem !important;
    flex-direction: column;
    gap: 0.75rem !important;
  }

  .edit-supplier-footer .btn {
    width: 100%;
  }

  .modal-icon {
    width: 40px !important;
    height: 40px !important;
  }

  .form-group {
    margin-bottom: 0.9rem;
  }

  .modern-input {
    padding: 10px 12px;
    font-size: 0.85rem;
  }
}

/* Custom Scrollbar for modals */
.modal-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--neutral-light);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--neutral-medium);
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

/* Prevent body scroll when modal is open */
body:has(.modal-overlay) {
  overflow: hidden !important;
}

/* Rating Tooltip Styles */
.rating-tooltip-wrapper {
  cursor: help;
}

.rating-value {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.cursor-help {
  cursor: help;
}

.rating-tooltip {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 0.5rem;
  background-color: var(--surface-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  box-shadow: var(--shadow-xl);
  padding: 0;
  min-width: 300px;
  max-width: 400px;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transform: translateY(5px);
  transition: all 0.2s ease;
  pointer-events: none;
}

.rating-tooltip-wrapper:hover .rating-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
  pointer-events: auto;
}

.tooltip-header {
  padding: 0.75rem 1rem;
  background-color: var(--surface-tertiary);
  border-bottom: 1px solid var(--border-primary);
  border-radius: 8px 8px 0 0;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.tooltip-content {
  padding: 1rem;
}

.tooltip-factor {
  margin-bottom: 0.75rem;
}

.tooltip-factor:last-of-type {
  margin-bottom: 0;
}

.factor-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.factor-weight {
  font-size: 0.75rem;
}

.factor-score-bar {
  position: relative;
  overflow: hidden;
  background-color: var(--surface-tertiary);
}

.factor-score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.factor-score-value {
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 45px;
  text-align: right;
  color: var(--text-secondary);
}

.tooltip-divider {
  height: 1px;
  background-color: var(--border-primary);
  margin: 0.75rem 0;
}

.tooltip-total {
  padding-top: 0.5rem;
  font-size: 0.875rem;
}

/* Responsive adjustments for tooltip */
@media (max-width: 576px) {
  .rating-tooltip {
    right: auto;
    left: 0;
    min-width: 280px;
    max-width: 90vw;
  }
}
</style>