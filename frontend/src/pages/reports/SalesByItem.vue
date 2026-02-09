<template>
  <div class="SBI-page">
    <!-- ========================================== -->
    <!-- TOP SECTION: Analytics & Chart -->
    <!-- ========================================== -->
    <div class="TopContainer">
      <!-- Left: Top Five Items List -->
      <div class="LC-SBI">
        <div class="LCL1">
          <h1>Top Five Items</h1>
          <h3>Net Sales</h3>
        </div>
         
        <!-- Loading state for top items -->
        <div v-if="loadingTopItems" class="loading-state-small">
          <div class="spinner-border-sm"></div>
          <p>Loading top items...</p>
        </div>
        
        <!-- Top items list -->
        <ul v-else-if="topItems && topItems.length > 0" class="LCL2">
          <li
            v-for="(item, index) in topItems"
            :key="index"
            class="list-item"
          >
            <span class="item-name">
              {{ item.name }}
            </span>
            <span class="item-price">
              {{ item.price }}
            </span>
          </li>
        </ul>
        
        <!-- Empty state for top items -->
        <div v-else class="empty-state-small">
          <p>No top items data available</p>
          <button @click="loadAllData" class="btn btn-sm btn-primary">
            Retry Loading
          </button>
        </div>
      </div>
      
      <div class="divider"></div>
      
      <!-- Right: Sales Chart -->
      <div class="RC-SBI">
        <div class="chart-header">
          <h1>Sales Chart</h1>
          <select
            v-model="selectedFrequency"
            @change="onFrequencyChange"
            class="frequency-dropdown"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <div class="chart-container">
          <div v-if="loadingChart" class="chart-loading">
            <div class="spinner-border text-primary"></div>
            <p>Loading chart data...</p>
          </div>
          <BarChart
            v-else
            :chartData="chartData"
            :selectedFrequency="selectedFrequency"
          />
        </div>
      </div>
    </div>
    
    <!-- ========================================== -->
    <!-- BOTTOM SECTION: Sales by Item Table -->
    <!-- ========================================== -->
    <div class="BottomContainer">
      <!-- Header with Action Buttons -->
      <div class="transaction-header">
        <div class="header-left">
          <h1>Sales by Item</h1>
          <div class="date-range-info" v-if="currentDateRange">
            <i class="bi bi-calendar3"></i>
            {{ dateRangeDisplay }}
          </div>
        </div>

        <div class="header-actions">
          <!-- Auto-refresh status and controls -->
          <div class="auto-refresh-status">
            <i
              class="bi bi-arrow-repeat text-success"
              :class="{ 'spinning': salesByItemLoading }"
            ></i>
            <span class="status-text">
              <span v-if="autoRefreshEnabled">
                Updates in {{ countdown }}s
              </span>
              <span v-else>Auto-refresh disabled</span>
            </span>
            
            <!-- Toggle button -->
            <button 
              class="btn btn-sm"
              :class="autoRefreshEnabled ? 'btn-outline-secondary' : 'btn-outline-success'"
              @click="toggleAutoRefresh"
            >
              {{ autoRefreshEnabled ? 'Disable' : 'Enable' }}
            </button>
          </div>
          
          <!-- Connection health indicator -->
          <div
            class="connection-indicator"
            :class="getConnectionStatus()"
          >
            <i :class="getConnectionIcon()"></i>
            <span class="connection-text">{{ getConnectionText() }}</span>
          </div>
          
          <!-- Emergency Refresh - Only show if error or connection lost -->
          <button 
            v-if="error || connectionLost" 
            class="btn btn-warning" 
            @click="emergencyReconnect"
            :disabled="salesByItemLoading"
          >
            <i
              class="bi bi-arrow-clockwise"
              :class="{ 'spinning': salesByItemLoading }"
            ></i>
            {{ salesByItemLoading ? 'Reconnecting...' : 'Reconnect' }}
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="salesByItemLoading" class="loading-state">
        <div class="spinner-border text-primary"></div>
        <p>Loading sales data...</p>
      </div>
      
      <!-- Sales by Item Table -->
      <div v-else class="table-container">
        <table class="table table-striped">
          <thead>
            <tr>
              <th scope="col">Product ID</th>
              <th scope="col">Product Name</th>
              <th scope="col">Category</th>
              <th scope="col" style="text-align: center;">Stock</th>
              <th scope="col" style="text-align: center;">Items Sold</th>
              <th scope="col">Total Sales</th>
              <th scope="col">Unit Price</th>
              <th scope="col" style="text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody class="table-group-divider">
            <tr v-for="item in salesByItemRows" :key="item.id">
              <td class="id-column" :title="item.id">
                {{ item.id }}
              </td>
              <td class="product-column">
                <span :title="item.product">
                  {{
                    item.product.length > 30
                      ? item.product.substring(0, 30) + '...'
                      : item.product
                  }}
                </span>
              </td>
              <td class="category-column">
                <span class="badge badge-secondary">
                  {{ item.category }}
                </span>
              </td>
              <td class="stock-column">
                <span
                  :class="{
                    'low-stock': item.stock < 10,
                    'critical-stock': item.stock < 5
                  }"
                >
                  {{ item.stock }} {{ item.unit }}
                </span>
              </td>
              <td class="sold-column">
                {{ item.items_sold }}
              </td>
              <td class="sales-column">
                <span class="total-amount">
                  {{ formatCurrency(item.total_sales) }}
                </span>
              </td>
              <td class="price-column">
                {{ formatCurrency(item.selling_price) }}
              </td>
              <td class="actions-column">
                <div class="action-buttons">
                  <button 
                    class="btn btn-outline-primary btn-sm" 
                    @click="viewProductDetails(item)"
                    title="View Product Details"
                  >
                    <Eye />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- Empty State -->
        <div
          v-if="salesByItemRows.length === 0 && !salesByItemLoading"
          class="empty-state"
        >
          <i
            class="bi bi-receipt"
            style="font-size: 3rem; color: var(--text-tertiary, #6b7280);"
          ></i>
          <p>No sales data found for the selected time period</p>
          <button class="btn btn-primary" @click="loadAllData">
            <i class="bi bi-arrow-clockwise"></i> Refresh Data
          </button>
        </div>
        
        <!-- Pagination for Sales by Item Table -->
        <div
          v-if="showSalesByItemPagination"
          class="pagination-container"
        >
          <div class="pagination-header">
            <div class="pagination-info-right">
              <span class="pagination-text">
                Showing
                {{
                  ((salesByItemPagination.current_page - 1) *
                    salesByItemPagination.page_size) + 1
                }} 
                to
                {{
                  Math.min(
                    salesByItemPagination.current_page *
                      salesByItemPagination.page_size,
                    salesByItemPagination.total_records
                  )
                }} 
                of {{ salesByItemPagination.total_records }} products
              </span>
              
              <div class="page-size-selector">
                <label for="salesPageSize">Per page:</label>
                <select 
                  id="salesPageSize"
                  :value="salesByItemPagination.page_size" 
                  @change="changeSalesByItemPageSize(Number($event.target.value))"
                  :disabled="salesByItemLoading"
                  class="form-select form-select-sm"
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
            </div>
          </div>

          <nav aria-label="Sales by item pagination">
            <ul class="pagination pagination-sm justify-content-center">
              <li
                class="page-item"
                :class="{ disabled: !salesByItemPagination.has_prev || salesByItemLoading }"
              >
                <button 
                  class="page-link" 
                  @click="goToSalesByItemPage(salesByItemPagination.current_page - 1)"
                  :disabled="!salesByItemPagination.has_prev || salesByItemLoading"
                  aria-label="Previous page"
                >
                  <i class="bi bi-chevron-left">‹</i>
                </button>
              </li>

              <li 
                v-for="page in getSalesByItemVisiblePages" 
                :key="page"
                class="page-item" 
                :class="{ active: page === salesByItemPagination.current_page }"
              >
                <button 
                  class="page-link" 
                  @click="goToSalesByItemPage(page)"
                  :disabled="salesByItemLoading"
                >
                  {{ page }}
                </button>
              </li>

              <li
                class="page-item"
                :class="{ disabled: !salesByItemPagination.has_next || salesByItemLoading }"
              >
                <button 
                  class="page-link" 
                  @click="goToSalesByItemPage(salesByItemPagination.current_page + 1)"
                  :disabled="!salesByItemPagination.has_next || salesByItemLoading"
                  aria-label="Next page"
                >
                  <i class="bi bi-chevron-right">›</i>
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>

    <!-- Product Details Modal -->
    <div
      v-if="showProductModal"
      class="modal-overlay"
      @click="closeProductModal"
    >
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Product Details</h2>
          <button class="modal-close" @click="closeProductModal">
            &times;
          </button>
        </div>
        
        <div class="modal-body">
          <div class="product-details" v-if="selectedProductData">
            <div class="detail-section">
              <h4>Product Information</h4>
              <div class="detail-row">
                <strong>Product ID:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.id }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Product Name:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.name }}
                </span>
              </div>
              <div class="detail-row">
                <strong>SKU:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.sku }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Category:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.category }}
                </span>
              </div>
            </div>

            <div class="detail-section">
              <h4>Inventory & Sales</h4>
              <div class="detail-row">
                <strong>Stock:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.stock }} {{ selectedProductData.unit }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Items Sold:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.items_sold }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Unit Price:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.selling_price }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Total Sales:</strong> 
                <span class="detail-value total-highlight">
                  {{ selectedProductData.total_sales }}
                </span>
              </div>
              <div class="detail-row">
                <strong>Taxable:</strong> 
                <span class="detail-value">
                  {{ selectedProductData.is_taxable }}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeProductModal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import BarChart from '@/components/BarChart.vue';
import salesDisplayService from '@/services/apiSalesByItem';

export default {
  name: 'SalesByItem',
  components: {
    BarChart
  },
  
  data() {
    return {
      // Loading states
      loadingTopItems: false,
      loadingChart: false,
      
      // Sales by Item data
      salesByItemRows: [],
      allSalesByItemRows: [],
      salesByItemLoading: false,
      salesByItemError: null,
      
      // Sales by Item Pagination
      salesByItemPagination: {
        current_page: 1,
        page_size: 10,
        total_records: 0,
        total_pages: 0,
        has_next: false,
        has_prev: false
      },
      
      // Product Details Modal
      showProductModal: false,
      selectedProductData: null,
      
      // Chart and analytics
      selectedFrequency: 'monthly',
      currentDateRange: null,
      topItems: [],
      chartData: {
        labels: ['Loading...'],
        datasets: [{
          label: 'Sales Amount',
          data: [0],
          backgroundColor: ['#e5e7eb'],
          borderColor: ['#d1d5db'],
          borderWidth: 1
        }]
      },

      autoRefreshEnabled: true,
      autoRefreshInterval: 30000,
      autoRefreshTimer: null,
      countdown: 30,
      countdownTimer: null,
      
      // Connection health tracking
      connectionLost: false,
      consecutiveErrors: 0,
      lastSuccessfulLoad: null,
      error: null,
    };
  },
  
  computed: {
    showSalesByItemPagination() {
      return this.salesByItemPagination.total_pages > 1;
    },
    
    getSalesByItemVisiblePages() {
      const current = this.salesByItemPagination.current_page;
      const total = this.salesByItemPagination.total_pages;
      const delta = 2;
      
      if (total <= 7) {
        return Array.from({ length: total }, (_, i) => i + 1);
      }
      
      let start = Math.max(1, current - delta);
      let end = Math.min(total, current + delta);
      
      if (current <= delta + 1) {
        end = Math.min(total, 2 * delta + 2);
      }
      if (current >= total - delta) {
        start = Math.max(1, total - 2 * delta - 1);
      }
      
      const pages = [];
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      
      return pages;
    },

    dateRangeDisplay() {
      if (!this.currentDateRange) return 'Select date range';
      const start = new Date(this.currentDateRange.start_date);
      const end = new Date(this.currentDateRange.end_date);
      const opts = { year: 'numeric', month: 'short', day: 'numeric' };
      return `${start.toLocaleDateString('en-US', opts)} - ${end.toLocaleDateString('en-US', opts)}`;
    }
  },
  
  async mounted() {
    await this.loadAllData();
    
    if (this.autoRefreshEnabled) {
      this.startAutoRefresh();
    }
  },

  beforeUnmount() {
    this.stopAutoRefresh();
  },
  
  methods: {
    // ================================================================
    // CORE DATA LOADING METHODS
    // ================================================================
    
    async loadAllData() {
      try {
        await Promise.all([
          this.getTopItems(),
          this.getTopChartItems(),
          this.loadSalesByItemTable()
        ]);
      } catch (error) {
        console.error('Error loading all data:', error);
      }
    },

    async getTopItems() {
      try {
        this.loadingTopItems = true;
        
        const dateRange = this.calculateDateRange(this.selectedFrequency);
        
        const response = await salesDisplayService.getSalesByItem(
          dateRange.start_date, 
          dateRange.end_date
        );

        let items = [];
        
        if (Array.isArray(response)) {
          items = response;
        } else if (response?.data && Array.isArray(response.data)) {
          items = response.data;
        }

        if (items && items.length > 0) {
          const sortedItems = items
            .sort((a, b) => (b.total_sales || 0) - (a.total_sales || 0))
            .slice(0, 5);

          this.topItems = sortedItems.map((item) => ({
            name: item.product_name || 'Unknown Product',
            price: this.formatCurrency(item.total_sales || 0)
          }));
        } else {
          this.topItems = [
            { name: 'No data available', price: '₱0.00' }
          ];
        }
        
        this.connectionLost = false;
        this.consecutiveErrors = 0;
        this.lastSuccessfulLoad = Date.now();
        this.error = null;
        
      } catch (error) {
        console.error("❌ Error loading top items:", error);
        
        this.consecutiveErrors++;
        this.error = `Failed to load top items: ${error.message}`;

        if (this.consecutiveErrors >= 3) {
          this.connectionLost = true;
        }

        this.topItems = [{ name: 'Error loading data', price: '₱0.00' }];
      } finally {
        this.loadingTopItems = false;
      }
    },

    async getTopChartItems() {
      try {
        this.loadingChart = true;
        const dateRange = this.calculateDateRange(this.selectedFrequency);
        
        const response = await salesDisplayService.getSalesByItem(
          dateRange.start_date, 
          dateRange.end_date
        );

        let items = [];
        
        if (Array.isArray(response)) {
          items = response;
        } else if (response?.data && Array.isArray(response.data)) {
          items = response.data;
        }

        if (items && items.length > 0) {
          const sortedItems = items
            .sort((a, b) => (b.total_sales || 0) - (a.total_sales || 0))
            .slice(0, 10);

          const chartItems = sortedItems.map(item => ({
            item_name: item.product_name || 'Unknown Product',
            total_amount: item.total_sales || 0
          }));

          this.updateChartData(chartItems);

          this.connectionLost = false;
          this.consecutiveErrors = 0;
          this.lastSuccessfulLoad = Date.now();
          this.error = null;

        } else {
          this.setDefaultChartData();
        }
        
      } catch (error) {
        console.error("❌ Error in getTopChartItems:", error);
        
        this.consecutiveErrors++;
        this.error = `Failed to load chart data: ${error.message}`;

        if (this.consecutiveErrors >= 3) {
          this.connectionLost = true;
        }

        this.setDefaultChartData();
      } finally {
        this.loadingChart = false;
      }
    },

    async loadSalesByItemTable() {
      try {
        this.salesByItemLoading = true;
        this.salesByItemError = null;
        
        const dateRange = this.calculateDateRange(this.selectedFrequency);
        this.currentDateRange = dateRange;
        
        if (!this.validateDateRange(dateRange.start_date, dateRange.end_date)) {
          this.salesByItemError = 'Invalid date range: start date cannot be after end date';
          this.allSalesByItemRows = [];
          this.salesByItemRows = [];
          return;
        }
        
        const response = await salesDisplayService.getSalesByItem(
          dateRange.start_date, 
          dateRange.end_date,
          false
        );

        let data = [];
        
        if (Array.isArray(response)) {
          data = response;
        } else if (response?.data && Array.isArray(response.data)) {
          data = response.data;
        } else if (response?.results && Array.isArray(response.results)) {
          data = response.results;
        } else {
          console.warn('⚠️ Unexpected API response format:', response);
          data = [];
        }

        this.allSalesByItemRows = data
          .filter(item => item && typeof item === 'object')
          .sort((a, b) => {
            const salesA = parseFloat(a.total_sales) || 0;
            const salesB = parseFloat(b.total_sales) || 0;
            return salesB - salesA;
          })
          .map(item => ({
            id: item.product_id || item.id || 'N/A',
            product: item.product_name || item.name || item.product || 'Unknown Product',
            category: item.category_name || item.category || 'Uncategorized',
            stock: parseInt(item.stock) || 0,
            items_sold: parseInt(item.items_sold) || 0,
            total_sales: parseFloat(item.total_sales) || 0,
            selling_price: parseFloat(item.selling_price) || 0,
            unit: item.unit || 'unit',
            sku: item.sku || 'N/A',
            is_taxable: Boolean(item.is_taxable)
          }));

        this.salesByItemPagination.current_page = 1;
        this.updateSalesByItemPageData();

        this.connectionLost = false;
        this.consecutiveErrors = 0;
        this.lastSuccessfulLoad = Date.now();
        this.error = null;

      } catch (error) {
        console.error('❌ loadSalesByItemTable error:', error);
        
        this.consecutiveErrors++;
        this.salesByItemError = this.getErrorMessage(error);

        if (this.consecutiveErrors >= 3) {
          this.connectionLost = true;
        }

        this.allSalesByItemRows = [];
        this.salesByItemRows = [];
        this.salesByItemPagination.current_page = 1;
        this.updateSalesByItemPageData();
        
      } finally {
        this.salesByItemLoading = false;
      }
    },

    // ================================================================
    // DATE FILTERING METHODS - FIXED
    // ================================================================
    
    calculateDateRange(frequency) {
      const now = new Date();
      const end_date = this.formatDateForAPI(now);
      let start_date;
      
      switch (frequency) {
        case 'daily':
          // Last 30 days
          const dailyDate = new Date(now);
          dailyDate.setDate(dailyDate.getDate() - 30);
          start_date = this.formatDateForAPI(dailyDate);
          break;
        case 'weekly':
          // Last 12 weeks
          const weeklyDate = new Date(now);
          weeklyDate.setDate(weeklyDate.getDate() - (12 * 7));
          start_date = this.formatDateForAPI(weeklyDate);
          break;
        case 'monthly':
          // Last 12 months
          const monthlyDate = new Date(now);
          monthlyDate.setMonth(monthlyDate.getMonth() - 12);
          start_date = this.formatDateForAPI(monthlyDate);
          break;
        case 'yearly':
          // Last 3 years
          const yearlyDate = new Date(now);
          yearlyDate.setFullYear(yearlyDate.getFullYear() - 3);
          start_date = this.formatDateForAPI(yearlyDate);
          break;
        default:
          // Default to last 30 days
          const defaultDate = new Date(now);
          defaultDate.setDate(defaultDate.getDate() - 30);
          start_date = this.formatDateForAPI(defaultDate);
      }
      
      return { start_date, end_date };
    },

    formatDateForAPI(date) {
      if (!(date instanceof Date)) {
        date = new Date(date);
      }
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },

    validateDateRange(startDate, endDate) {
      if (!startDate || !endDate) return true;
      
      const start = new Date(startDate);
      const end = new Date(endDate);
      
      return start <= end;
    },

    getErrorMessage(error) {
      if (error.response?.status === 400) {
        return 'Invalid date range or parameters. Please try a different time period.';
      } else if (error.response?.status === 404) {
        return 'Sales data not found for the selected period.';
      } else if (error.response?.status === 500) {
        return 'Server error. Please try again later.';
      } else if (error.message?.includes('Network Error') || error.message?.includes('Failed to fetch')) {
        return 'Network connection failed. Please check your internet connection.';
      } else {
        return error.message || 'Failed to load sales data. Please try again.';
      }
    },

    // ================================================================
    // CHART METHODS - FIXED
    // ================================================================
    
    updateChartData(items) {
      const colors = this.generateChartColors(items.length);
      
      this.chartData = {
        labels: items.map(item => {
          const name = item.item_name || 'Unknown Item';
          return name.length > 20 ? name.substring(0, 20) + '...' : name;
        }),
        datasets: [{
          label: `Sales Amount (${this.selectedFrequency})`,
          data: items.map(item => item.total_amount || 0),
          backgroundColor: colors.background,
          borderColor: colors.border,
          borderWidth: 1
        }]
      };
    },

    generateChartColors(count) {
      const baseColors = [
        '#ef4444', '#3b82f6', '#eab308', '#22c55e', '#8b5cf6',
        '#f59e0b', '#10b981', '#6366f1', '#f97316', '#84cc16'
      ];
      
      const borderColors = [
        '#dc2626', '#2563eb', '#ca8a04', '#16a34a', '#7c3aed',
        '#d97706', '#059669', '#4f46e5', '#ea580c', '#65a30d'
      ];
      
      const background = [];
      const border = [];
      
      for (let i = 0; i < count; i++) {
        background.push(baseColors[i % baseColors.length]);
        border.push(borderColors[i % borderColors.length]);
      }
      
      return { background, border };
    },

    setDefaultChartData() {
      this.chartData = {
        labels: ['No Data Available'],
        datasets: [{
          label: 'Sales Amount',
          data: [0],
          backgroundColor: ['#e5e7eb'],
          borderColor: ['#d1d5db'],
          borderWidth: 1
        }]
      };
    },

    async onFrequencyChange() {
      if (this.showProductModal) {
        return;
      }

      await this.loadAllData();
    },

    // ================================================================
    // PAGINATION METHODS
    // ================================================================
    
    updateSalesByItemPageData() {
      const startIndex = (this.salesByItemPagination.current_page - 1) * this.salesByItemPagination.page_size;
      const endIndex = startIndex + this.salesByItemPagination.page_size;
      
      this.salesByItemRows = this.allSalesByItemRows.slice(startIndex, endIndex);
      
      this.salesByItemPagination.total_records = this.allSalesByItemRows.length;
      this.salesByItemPagination.total_pages = Math.ceil(this.allSalesByItemRows.length / this.salesByItemPagination.page_size);
      this.salesByItemPagination.has_prev = this.salesByItemPagination.current_page > 1;
      this.salesByItemPagination.has_next = this.salesByItemPagination.current_page < this.salesByItemPagination.total_pages;
    },
    
    goToSalesByItemPage(page) {
      if (this.showProductModal) {
        return;
      }
      
      if (page >= 1 && page <= this.salesByItemPagination.total_pages) {
        this.salesByItemPagination.current_page = page;
        this.updateSalesByItemPageData();
      }
    },

    changeSalesByItemPageSize(newPageSize) {
      if (this.showProductModal) {
        return;
      }
      
      this.salesByItemPagination.page_size = newPageSize;
      this.salesByItemPagination.current_page = 1;
      this.updateSalesByItemPageData();
    },

    // ================================================================
    // MODAL METHODS
    // ================================================================
    
    viewProductDetails(product) {
      try {
        this.selectedProductData = {
          id: product.id,
          name: product.product,
          category: product.category,
          stock: product.stock,
          unit: product.unit,
          items_sold: product.items_sold,
          total_sales: this.formatCurrency(product.total_sales),
          selling_price: this.formatCurrency(product.selling_price),
          sku: product.sku || 'N/A',
          is_taxable: product.is_taxable ? 'Yes' : 'No'
        };
        
        this.showProductModal = true;
      } catch (error) {
        console.error('Error in viewProductDetails:', error);
        this.showError('Failed to display product details');
      }
    },

    closeProductModal() {
      this.showProductModal = false;
      this.selectedProductData = null;
    },

    // ================================================================
    // FORMATTING METHODS
    // ================================================================
    
    formatCurrency(amount) {
      let numericAmount = amount;
      
      if (typeof amount === 'string') {
        numericAmount = parseFloat(amount);
      }
      
      if (typeof numericAmount !== 'number' || isNaN(numericAmount)) {
        numericAmount = 0;
      }
      
      return `₱${numericAmount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })}`;
    },

    // ================================================================
    // UTILITY METHODS
    // ================================================================
    
    showSuccess(message) {
      alert(message);
    },

    showError(message) {
      console.error('Error:', message);
      alert(message);
    },

    async refreshData() {
      if (this.showProductModal) {
        return;
      }

      try {
        this.error = null;
        await this.loadAllData();
        this.connectionLost = false;
        this.consecutiveErrors = 0;
        this.lastSuccessfulLoad = Date.now();
      } catch (error) {
        console.error('Error refreshing data:', error);
        this.consecutiveErrors++;
        this.error = `Failed to refresh data: ${error.message}`;

        if (this.consecutiveErrors >= 3) {
          this.connectionLost = true;
        }
      }
    },

    toggleAutoRefresh() {
      if (this.autoRefreshEnabled) {
        this.autoRefreshEnabled = false
        this.stopAutoRefresh()
      } else {
        this.autoRefreshEnabled = true
        this.startAutoRefresh()
      }
    },
    
    startAutoRefresh() {
      this.stopAutoRefresh()
      
      this.countdown = this.autoRefreshInterval / 1000
      this.countdownTimer = setInterval(() => {
        this.countdown--
        if (this.countdown <= 0) {
          this.countdown = this.autoRefreshInterval / 1000
        }
      }, 1000)
      
      this.autoRefreshTimer = setInterval(() => {
        this.refreshData()
      }, this.autoRefreshInterval)
    },

    stopAutoRefresh() {
      if (this.autoRefreshTimer) {
        clearInterval(this.autoRefreshTimer)
        this.autoRefreshTimer = null
      }

      if (this.countdownTimer) {
        clearInterval(this.countdownTimer)
        this.countdownTimer = null
      }
    },

    async emergencyReconnect() {
      this.consecutiveErrors = 0
      this.connectionLost = false
      this.error = null
      await this.refreshData()

      if (!this.autoRefreshEnabled) {
        this.autoRefreshEnabled = true
        this.startAutoRefresh()
      }
    },

    getConnectionStatus() {
      if (this.connectionLost) return 'connection-lost'
      if (this.consecutiveErrors > 0) return 'connection-unstable'
      if (this.lastSuccessfulLoad && (Date.now() - this.lastSuccessfulLoad < 60000)) return 'connection-good'
      return 'connection-unknown'
    },

    getConnectionIcon() {
      switch (this.getConnectionStatus()) {
        case 'connection-good': return 'bi bi-wifi text-success'
        case 'connection-unstable': return 'bi bi-wifi-1 text-warning'
        case 'connection-lost': return 'bi bi-wifi-off text-danger'
        default: return 'bi bi-wifi text-muted'
      }
    },

    getConnectionText() {
      switch (this.getConnectionStatus()) {
        case 'connection-good': return 'Connected'
        case 'connection-unstable': return 'Unstable'
        case 'connection-lost': return 'Connection Lost'
        default: return 'Connecting...'
      }
    }
  }
}
</script>

<style scoped>
/* ====================================================================== */
/* MAIN LAYOUT */
/* ====================================================================== */
.SBI-page {
  padding: 0;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.TopContainer {
  width: 100%;
  height: 400px;
  display: grid;
  grid-template-columns: 1fr 2px 1fr;
  gap: 20px;
  align-items: start;
  margin-top: 20px;
}

.divider {
  width: 2px;
  height: 100%;
  background-color: var(--border-primary);
  justify-self: center;
}

/* ====================================================================== */
/* TOP ITEMS SECTION */
/* ====================================================================== */
.LCL1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.LCL1 h1,
.LCL1 h3 {
  margin: 0;
}

.LCL1 h3 {
  color: var(--text-secondary);
  font-size: 20px;
}

.LCL1 h1 {
  color: var(--text-primary);
  font-size: 30px;
  font-weight: bold;
}

.LC-SBI h1 {
  font-weight: bold;
}

.LCL2 {
  list-style-type: none;
  padding-left: 0;
  margin-top: 10px;
}

.LCL2 li {
  color: var(--text-primary);
  height: 30px;
  margin-bottom: 20px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 8px;
  height: 30px;
  padding: 0 10px;
}

.item-name {
  font-weight: 600;
  font-size: 25px;
  flex: 1;
  color: var(--text-primary);
}

.item-price {
  font-weight: bold;
  white-space: nowrap;
  font-size: 15px;
  color: var(--success, #16a34a);
}

/* ====================================================================== */
/* CHART SECTION */
/* ====================================================================== */
.RC-SBI {
  color: var(--text-primary);
}

.RC-SBI h1 {
  font-weight: bold;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h1 {
  font-size: 30px;
}

.frequency-dropdown {
  padding: 8px 12px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  background-color: var(--surface-primary);
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
}

.frequency-dropdown:focus {
  outline: none;
  border-color: var(--primary);
}

.chart-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 500px;
  height: 100%;
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
}

.chart-loading p {
  margin-top: 10px;
  color: var(--text-secondary);
}

/* ====================================================================== */
/* TRANSACTION SECTION */
/* ====================================================================== */
.BottomContainer {
  color: var(--text-primary);
  width: 100%;
  margin-top: 40px;
}

.transaction-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-primary);
}

.transaction-header h1 {
  margin: 0;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.header-actions .btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s;
}

.header-actions .btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ====================================================================== */
/* TABLE STYLES */
/* ====================================================================== */
.table-container {
  background: var(--surface-primary);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.table {
  margin: 0;
  width: 100%;
}

.table thead th {
  background-color: var(--primary);
  font-weight: 600;
  color: #ffffff;
  border-bottom: 2px solid var(--border-primary);
  padding: 12px;
}

.table tbody td {
  padding: 12px;
  vertical-align: middle;
  border-bottom: 1px solid var(--border-secondary, #f3f4f6);
  color: var(--text-primary);
}

.table tbody tr:hover {
  background-color: var(--state-hover, #f9fafb);
}

.id-column {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: help;
}

.total-amount {
  font-weight: bold;
  color: var(--success, #059669);
}

.badge {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 12px;
  font-weight: 500;
  color: #ffffff;
}

.badge-success {
  background-color: #059669;
}

.badge-primary {
  background-color: #3b82f6;
}

.badge-info {
  background-color: #06b6d4;
}

.badge-warning {
  background-color: #eab308;
  color: #374151;
}

.badge-secondary {
  background-color: #6b7280;
}

.badge-dark {
  background-color: #374151;
}

.action-buttons {
  display: flex;
  gap: 5px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s;
  font-size: 16px;
}

.action-btn:hover:not(:disabled) {
  background-color: var(--state-hover, #f3f4f6);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ====================================================================== */
/* LOADING AND EMPTY STATES */
/* ====================================================================== */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-state p {
  margin-top: 16px;
  color: var(--text-secondary);
}

.loading-state-small {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
}

.loading-state-small p {
  margin-top: 8px;
  color: var(--text-secondary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-state p {
  margin: 16px 0;
  color: var(--text-secondary);
  font-size: 16px;
}

.empty-state-small {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;
}

.empty-state-small p {
  margin: 8px 0;
  color: var(--text-secondary);
}

/* ====================================================================== */
/* PAGINATION STYLES */
/* ====================================================================== */
.pagination-container {
  padding: 20px;
  border-top: 1px solid var(--border-primary);
  background-color: var(--surface-secondary, #f9fafb);
}

.pagination-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.pagination-info-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.pagination-text {
  color: var(--text-secondary);
  font-size: 14px;
  text-align: right;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.page-size-selector label {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  white-space: nowrap;
}

.page-size-selector select {
  width: auto;
  min-width: 70px;
  padding: 4px 8px;
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  font-size: 13px;
  background: var(--surface-primary);
  color: var(--text-primary);
}

.pagination {
  margin: 0;
  display: flex;
  list-style: none;
  padding: 0;
  justify-content: center;
  margin-right: 120px;
}

.page-item {
  margin: 0 2px;
}

.page-link {
  color: var(--text-secondary);
  border: 1px solid var(--border-primary);
  padding: 6px 12px;
  text-decoration: none;
  background: var(--surface-primary);
  cursor: pointer;
  border-radius: 4px;
  font-size: 14px;
}

.page-link:hover {
  color: var(--text-primary);
  background-color: var(--state-hover, #f3f4f6);
  border-color: var(--border-primary);
}

.page-item.active .page-link {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}

.page-item.disabled .page-link {
  color: var(--text-tertiary, #9ca3af);
  background-color: var(--surface-secondary, #f9fafb);
  border-color: var(--border-primary);
  cursor: not-allowed;
}

/* ====================================================================== */
/* MODAL STYLES */
/* ====================================================================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex !important;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--surface-primary);
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  z-index: 10000;
  animation: modalFadeIn 0.3s ease-out;
  opacity: 1 !important;
  visibility: visible !important;
  pointer-events: auto !important;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-primary);
  margin: 0;
}

.modal-header h2,
.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.modal-close:hover {
  background-color: var(--state-hover, #f3f4f6);
}

.modal-close:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-primary);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ====================================================================== */
/* TRANSACTION DETAILS MODAL */
/* ====================================================================== */
.transaction-details {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section {
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 16px;
  background-color: var(--surface-secondary, #f9fafb);
}

.detail-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-secondary, #f3f4f6);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row strong {
  min-width: 140px;
  color: var(--text-primary);
  font-weight: 500;
}

.detail-value {
  color: var(--text-secondary);
  text-align: right;
  max-width: 60%;
  word-wrap: break-word;
}

.detail-value.total-highlight {
  color: var(--success, #059669);
  font-weight: bold;
  font-size: 16px;
}

/* ====================================================================== */
/* IMPORT / PROGRESS UTILITIES */
/* ====================================================================== */
.progress-section {
  margin-bottom: 24px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-info span {
  font-size: 14px;
  color: var(--text-primary);
}

.progress-percentage {
  font-weight: 600;
  color: var(--primary);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: var(--border-primary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary);
  border-radius: 4px;
  transition: width 0.3s ease;
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 255, 255, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 20px 20px;
  animation: progress-animation 1s linear infinite;
}

@keyframes progress-animation {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 20px 20px;
  }
}

/* ====================================================================== */
/* BUTTON STYLES */
/* ====================================================================== */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--primary);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-dark, #2563eb);
}

.btn-secondary {
  background-color: var(--secondary, #6b7280);
  color: #ffffff;
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--secondary-dark, #4b5563);
}

.btn-success {
  background-color: var(--success, #10b981);
  color: #ffffff;
}

.btn-success:hover:not(:disabled) {
  background-color: var(--success-dark, #059669);
}

.btn-warning {
  background-color: #f59e0b;
  color: #ffffff;
}

.btn-warning:hover:not(:disabled) {
  background-color: #d97706;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

/* ====================================================================== */
/* RESPONSIVE DESIGN */
/* ====================================================================== */
@media (max-width: 768px) {
  .TopContainer {
    grid-template-columns: 1fr;
    height: auto;
  }
  
  .divider {
    display: none;
  }
  
  .LCL1 {
    gap: 20px;
    flex-direction: column;
    align-items: flex-start;
  }
  
  .chart-container {
    width: 100%;
    height: 300px;
  }
  
  .transaction-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .pagination-header {
    justify-content: center;
  }
  
  .pagination-info-right {
    align-items: center;
    text-align: center;
  }
  
  .modal-content {
    width: 95%;
    margin: 10px;
  }
  
  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .detail-value {
    max-width: 100%;
    text-align: left;
  }
}

@media (max-width: 480px) {
  .table-container {
    overflow-x: auto;
  }
  
  .table {
    min-width: 600px;
  }
  
  .modal-body {
    padding: 16px;
  }
  
  .btn {
    padding: 6px 12px;
    font-size: 13px;
  }
}

/* Auto-refresh status indicator */
.auto-refresh-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--success-soft, #f0fdf4);
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--success-light, #bbf7d0);
  min-width: 280px;
}

.status-text {
  font-size: 0.875rem;
  color: var(--success-dark, #16a34a);
  font-weight: 500;
  flex: 1;
}

/* Connection indicator */
.connection-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.connection-good {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #16a34a;
}

.connection-unstable {
  background: #fefce8;
  border: 1px solid #fde047;
  color: #ca8a04;
}

.connection-lost {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
}

.connection-unknown {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #64748b;
}

.btn-outline-secondary {
  color: #6c757d;
  border: 1px solid #6c757d;
  background-color: transparent;
}

.btn-outline-secondary:hover:not(:disabled) {
  color: #fff;
  background-color: #6c757d;
  border-color: #6c757d;
}

.btn-outline-success {
  color: #10b981;
  border: 1px solid #10b981;
  background-color: transparent;
}

.btn-outline-success:hover:not(:disabled) {
  color: #fff;
  background-color: #10b981;
  border-color: #10b981;
}

/* Spinning icon animation */
.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Extra helpers */
.low-stock {
  color: #d97706;
  font-weight: bold;
}

.critical-stock {
  color: #dc2626;
  font-weight: bold;
  background-color: #fef2f2;
  padding: 2px 6px;
  border-radius: 4px;
}

.product-column {
  font-weight: 500;
  max-width: 200px;
}

.product-column span {
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  cursor: help;
}

.category-column .badge {
  font-size: 11px;
}

.stock-column,
.sold-column {
  text-align: center;
  font-weight: 500;
}

.sales-column,
.price-column {
  text-align: right;
  font-weight: bold;
}

.actions-column {
  text-align: center;
}

.actions-column .btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.date-range-info {
  color: var(--text-secondary);
  font-size: 13px;
}

.date-range-info i {
  margin-right: 4px;
}
</style>
