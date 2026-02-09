<template>
  <div class="SBC-page">
    <!-- ========================================== -->
    <!-- TOP SECTION: Analytics & Chart -->
    <!-- ========================================== -->
    <div class="TopContainer">
      <!-- Left: Top Categories List -->
      <div class="LC-SBC">
        <div class="LCL1">
          <h1>Top Categories</h1>
          <h3>Net Sales</h3>
        </div>
        
        <!-- Loading state for top categories -->
        <div v-if="loadingTopItems" class="loading-state-small">
          <div class="spinner-border-sm"></div>
          <p>Loading top categories...</p>
        </div>
        
        <!-- Top categories list -->
        <ul v-else-if="topItems && topItems.length > 0" class="LCL2">
          <li v-for="(item, index) in topItems" :key="index" class="list-item">
            <div class="category-info">
              <span class="item-name">{{ item.name }}</span>
              <div v-if="item.trend" class="trend-indicator" :class="item.trend">
                <i :class="getTrendIcon(item.trend)"></i>
                <span v-if="item.sales_growth_percent" class="trend-percent">
                  {{ Math.abs(item.sales_growth_percent) }}%
                </span>
              </div>
            </div>
            <span class="item-price">{{ item.price }}</span>
          </li>
        </ul>
        
        <!-- Empty state for top categories -->
        <div v-else class="empty-state-small">
          <p>No category data available</p>
          <button @click="loadAllCategoryData" class="btn btn-sm btn-primary">Retry Loading</button>
        </div>
      </div>
      
      <div class="divider"></div>
      
      <!-- Right: Sales Chart -->
      <div class="RC-SBC">
        <div class="chart-header">
          <h1>Sales Chart</h1>
          <select v-model="selectedFrequency" @change="onFrequencyChange" class="frequency-dropdown">
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
          <PieChartView v-else :chartData="chartData" :selectedFrequency="selectedFrequency" />
        </div>
      </div>
    </div>
    
    <!-- ========================================== -->
    <!-- BOTTOM SECTION: Category Analysis -->
    <!-- ========================================== -->
    <div class="BottomContainer">
      <!-- Header with Date Range Info -->
      <div class="transaction-header">
        <div class="header-left">
          <h1>Category Analysis</h1>
          <!--  <div class="date-range-info">
            <i class="bi bi-calendar-range"></i>
            {{ dateRangeDisplay }}
          </div>-->
        </div>
        <div class="header-actions">
          <!-- View Toggle -->
          <div class="view-toggle">
            <button 
              class="btn btn-sm" 
              :class="showTrends ? 'btn-primary' : 'btn-outline-primary'"
              @click="toggleTrends"
            >
              <i class="bi bi-graph-up"></i>
              {{ showTrends ? 'Hide Trends' : 'Show Trends' }}
            </button>
          </div>

          <!-- Auto-refresh status and controls -->
          <div class="auto-refresh-status">
            <i class="bi bi-arrow-repeat text-success" :class="{ 'spinning': loading }"></i>
            <span class="status-text">
              <span v-if="autoRefreshEnabled">Updates in {{ countdown }}s </span>
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
          <div class="connection-indicator" :class="getConnectionStatus()">
            <i :class="getConnectionIcon()"></i>
            <span class="connection-text">{{ getConnectionText() }}</span>
          </div>
          
          <!-- Emergency Refresh - Only show if error or connection lost -->
          <button 
            v-if="error || connectionLost" 
            class="btn btn-warning" 
            @click="emergencyReconnect"
            :disabled="loading"
          >
            <i class="bi bi-arrow-clockwise" :class="{ 'spinning': loading }"></i>
            {{ loading ? 'Reconnecting...' : 'Reconnect' }}
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner-border text-primary"></div>
        <p>Loading category data...</p>
      </div>

      <!-- Category Table -->
      <div v-else class="table-container">
        <table class="table table-striped">
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col" style="text-align: center">Total Items Sold</th>
              <th scope="col" style="text-align: center">Total Sales</th>
              <th scope="col" style="text-align: center"># of Products</th>
              <th scope="col" style="text-align: center">Transactions</th>
              <th scope="col" v-if="showTrends" style="text-align: center">Trend</th>
              <th scope="col" v-if="showTrends" style="text-align: center">Avg per Transaction</th>
            </tr>
          </thead>
          <tbody class="table-group-divider">
            <tr v-for="category in categories" :key="category.id || category._id">
              <td class="category-name">
                <span>{{ category.name || category.category_name }}</span>
                <button 
                  v-if="category.category_id" 
                  @click="viewCategoryDetails(category)"
                  class="btn btn-sm btn-outline-info ms-2"
                  title="View Details"
                >
                  <i class="bi bi-eye"></i>
                </button>
              </td>
              <td class="items-sold">{{ formatNumber(category.total_items_sold) }}</td>
              <td class="net-sales" style="text-align: center">
                <span class="total-amount" >{{ formatCurrency(category.total_sales || 0) }}</span>
              </td>
              <td class="product-count">{{ category.product_count || 0 }}</td>
              <td class="transaction-count">{{ formatNumber(category.transaction_count) }}</td>
              <td v-if="showTrends" class="trend-cell">
                <div v-if="category.trend" class="trend-indicator" :class="category.trend">
                  <i :class="getTrendIcon(category.trend)"></i>
                  <span v-if="category.sales_growth_percent" class="trend-percent">
                    {{ Math.abs(category.sales_growth_percent) }}%
                  </span>
                  <span v-else class="trend-text">{{ category.trend }}</span>
                </div>
                <span v-else class="text-muted">-</span>
              </td>
              <td v-if="showTrends" class="avg-transaction" style="text-align: center">
                {{ formatCurrency(category.avg_sale_per_transaction) }}
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- Empty State -->
        <div v-if="categories.length === 0 && !loading" class="empty-state">
          <i class="bi bi-grid" style="font-size: 3rem; color: #6b7280;"></i>
          <p>No categories found for this time period</p>
          <button class="btn btn-primary" @click="loadAllCategoryData">
            <i class="bi bi-arrow-clockwise"></i> Refresh Data
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PieChartView from '@/components/PieChartView.vue';
import categoryDisplayService from '@/services/apiSalesByCategory';

export default {
  name: 'SalesByCategory',
  components: {
    PieChartView
  },

  data() {
    return {
      loading: false,
      loadingTopItems: false,
      loadingChart: false,
      error: null,

      selectedFrequency: 'monthly',
      currentDateRange: null,
      showTrends: false,

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

      categories: [],

      // Auto-refresh
      autoRefreshEnabled: true,
      autoRefreshInterval: 30000,
      autoRefreshTimer: null,
      countdown: 30,
      countdownTimer: null,

      // Connection tracking
      connectionLost: false,
      consecutiveErrors: 0,
      lastSuccessfulLoad: null
    };
  },

  computed: {
    dateRangeDisplay() {
      if (!this.currentDateRange) return 'Select date range';
      const start = new Date(this.currentDateRange.start_date);
      const end = new Date(this.currentDateRange.end_date);
      const opts = { year: 'numeric', month: 'short', day: 'numeric' };
      return `${start.toLocaleDateString('en-US', opts)} - ${end.toLocaleDateString('en-US', opts)}`;
    }
  },

  async mounted() {
    try {
      await this.loadAllCategoryData();
      if (this.autoRefreshEnabled) this.startAutoRefresh();
    } catch (err) {
      // Error on mount
    }
  },

  beforeUnmount() {
    this.stopAutoRefresh();
  },

  methods: {
    // =========================================================
    // CORE DATA FETCHING
    // =========================================================
    async loadAllCategoryData() {
      try {
        this.loading = this.loadingTopItems = this.loadingChart = true;
        const range = this.calculateDateRange(this.selectedFrequency);
        this.currentDateRange = range;

        // 1️⃣ Fetch all category data (table + chart)
        const allCategories = await categoryDisplayService.getSalesByCategory(
          range.start_date, 
          range.end_date,
          false, // include_voided
          this.showTrends // include_trends
        );

        // 2️⃣ Fetch top categories (top list + chart)
        const topCategories = await categoryDisplayService.getTopCategories(
          range.start_date, 
          range.end_date, 
          5
        );

        // 3️⃣ Process data
        this.processCategoryData(allCategories);
        this.updateChartData(topCategories.slice(0, 6));
        this.updateTopItems(topCategories);

        // ✅ Connection OK
        this.connectionLost = false;
        this.consecutiveErrors = 0;
        this.lastSuccessfulLoad = Date.now();
      } catch (error) {
        this.consecutiveErrors++;
        if (this.consecutiveErrors >= 3) this.connectionLost = true;
        this.setFallbackData();
      } finally {
        this.loading = this.loadingTopItems = this.loadingChart = false;
      }
    },

    async onFrequencyChange() {
      this.loadingChart = true;
      this.loadingTopItems = true;
      this.loading = true;
      try {
        const range = this.calculateDateRange(this.selectedFrequency);
        this.currentDateRange = range;
        
        // Fetch all category data for the new date range
        const allCategories = await categoryDisplayService.getSalesByCategory(
          range.start_date, 
          range.end_date,
          false, // include_voided
          this.showTrends // include_trends
        );
        
        // Fetch top categories for chart and top list
        const topCategories = await categoryDisplayService.getTopCategories(
          range.start_date, 
          range.end_date, 
          6
        );
        
        // Update all data
        this.processCategoryData(allCategories);
        this.updateChartData(topCategories);
        this.updateTopItems(topCategories);
      } catch (error) {
        this.setDefaultChartData();
      } finally {
        this.loadingChart = false;
        this.loadingTopItems = false;
        this.loading = false;
      }
    },

    toggleTrends() {
      this.showTrends = !this.showTrends;
      this.loadAllCategoryData();
    },

    // =========================================================
    // DATA PROCESSING
    // =========================================================
    processCategoryData(data) {
      this.categories = (data || []).map((cat, i) => ({
        id: cat.category_id || i,
        category_id: cat.category_id,
        name: cat.category_name || 'Unknown Category',
        total_items_sold: cat.total_items_sold || 0,
        total_sales: cat.total_sales || 0,
        product_count: cat.product_count || 0,
        transaction_count: cat.transaction_count || 0,
        avg_sale_per_transaction: cat.avg_sale_per_transaction || 0,
        avg_items_per_transaction: cat.avg_items_per_transaction || 0,
        sales_growth_percent: cat.sales_growth_percent,
        trend: cat.trend
      }));
    },

    updateTopItems(categories) {
      this.topItems = categories.map(cat => ({
        name: cat.category_name || 'Unknown',
        price: this.formatCurrency(cat.total_sales),
        trend: cat.trend,
        sales_growth_percent: cat.sales_growth_percent
      }));
    },

    updateChartData(categories) {
      if (!categories || categories.length === 0) {
        this.setDefaultChartData();
        return;
      }

      const colors = this.generateChartColors(categories.length);
      this.chartData = {
        labels: categories.map(c => c.category_name || 'Unknown'),
        datasets: [{
          label: `Category Sales (${this.selectedFrequency})`,
          data: categories.map(c => c.total_sales || 0),
          backgroundColor: colors.background,
          borderColor: colors.border,
          borderWidth: 1
        }]
      };
    },

    generateChartColors(count) {
      const base = [
        '#ef4444', '#3b82f6', '#eab308', '#22c55e',
        '#8b5cf6', '#f59e0b', '#10b981', '#6366f1', '#f97316', '#84cc16'
      ];
      const border = [
        '#dc2626', '#2563eb', '#ca8a04', '#16a34a',
        '#7c3aed', '#d97706', '#059669', '#4f46e5', '#ea580c', '#65a30d'
      ];
      return {
        background: Array.from({ length: count }, (_, i) => base[i % base.length]),
        border: Array.from({ length: count }, (_, i) => border[i % border.length])
      };
    },

    getTrendIcon(trend) {
      switch (trend) {
        case 'up': return 'bi bi-arrow-up-circle-fill text-success';
        case 'down': return 'bi bi-arrow-down-circle-fill text-danger';
        case 'new': return 'bi bi-star-fill text-warning';
        default: return 'bi bi-dash-circle text-muted';
      }
    },

    setFallbackData() {
      this.topItems = [
        { name: 'Noodles', price: '₱15,234.21', trend: 'up', sales_growth_percent: 12.5 },
        { name: 'Drinks', price: '₱5,789.50', trend: 'down', sales_growth_percent: -3.2 },
        { name: 'Snacks', price: '₱3,821.25', trend: 'up', sales_growth_percent: 5.7 }
      ];
      this.setDefaultChartData();
      this.categories = [
        { 
          id: 1, 
          name: 'Noodles', 
          total_items_sold: 450, 
          total_sales: 15234.21, 
          product_count: 12,
          transaction_count: 89,
          avg_sale_per_transaction: 171.17,
          trend: 'up',
          sales_growth_percent: 12.5
        },
        { 
          id: 2, 
          name: 'Drinks', 
          total_items_sold: 320, 
          total_sales: 5789.50, 
          product_count: 8,
          transaction_count: 156,
          avg_sale_per_transaction: 37.11,
          trend: 'down',
          sales_growth_percent: -3.2
        }
      ];
    },

    setDefaultChartData() {
      this.chartData = {
        labels: ['Noodles', 'Drinks', 'Snacks'],
        datasets: [{
          label: `Category Sales (${this.selectedFrequency})`,
          data: [15234.21, 5789.50, 3821.25],
          backgroundColor: ['#ef4444', '#3b82f6', '#22c55e'],
          borderColor: ['#dc2626', '#2563eb', '#16a34a'],
          borderWidth: 1
        }]
      };
    },

    // =========================================================
    // UTILITIES
    // =========================================================
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
          // Last 3 years (consistent with SalesByItem)
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

    formatCurrency(amount) {
      let num = parseFloat(amount) || 0;
      return `₱${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },

    formatNumber(num) {
      return parseInt(num) || 0;
    },

    viewCategoryDetails(category) {
      // You can implement a modal or navigation to detailed view
      this.$notify({
        title: 'Category Details',
        message: `Detailed view for ${category.name} would open here`,
        type: 'info'
      });
    },

    // =========================================================
    // AUTO REFRESH
    // =========================================================
    toggleAutoRefresh() {
      this.autoRefreshEnabled = !this.autoRefreshEnabled;
      if (this.autoRefreshEnabled) this.startAutoRefresh();
      else this.stopAutoRefresh();
    },

    startAutoRefresh() {
      this.stopAutoRefresh();
      this.countdown = this.autoRefreshInterval / 1000;
      this.countdownTimer = setInterval(() => {
        this.countdown--;
        if (this.countdown <= 0) this.countdown = this.autoRefreshInterval / 1000;
      }, 1000);

      this.autoRefreshTimer = setInterval(() => {
        this.loadAllCategoryData();
      }, this.autoRefreshInterval);
    },

    stopAutoRefresh() {
      if (this.autoRefreshTimer) clearInterval(this.autoRefreshTimer);
      if (this.countdownTimer) clearInterval(this.countdownTimer);
      this.autoRefreshTimer = null;
      this.countdownTimer = null;
    },

    async emergencyReconnect() {
      this.consecutiveErrors = 0;
      this.connectionLost = false;
      await this.loadAllCategoryData();
      if (!this.autoRefreshEnabled) {
        this.autoRefreshEnabled = true;
        this.startAutoRefresh();
      }
    },

    // =========================================================
    // CONNECTION STATUS HELPERS
    // =========================================================
    getConnectionStatus() {
      if (this.connectionLost) return 'connection-lost';
      if (this.consecutiveErrors > 0) return 'connection-unstable';
      if (this.lastSuccessfulLoad && Date.now() - this.lastSuccessfulLoad < 60000)
        return 'connection-good';
      return 'connection-unknown';
    },

    getConnectionIcon() {
      switch (this.getConnectionStatus()) {
        case 'connection-good': return 'bi bi-wifi text-success';
        case 'connection-unstable': return 'bi bi-wifi-1 text-warning';
        case 'connection-lost': return 'bi bi-wifi-off text-danger';
        default: return 'bi bi-wifi text-muted';
      }
    },

    getConnectionText() {
      switch (this.getConnectionStatus()) {
        case 'connection-good': return 'Connected';
        case 'connection-unstable': return 'Unstable';
        case 'connection-lost': return 'Connection Lost';
        default: return 'Connecting...';
      }
    }
  }
};
</script>

<style scoped>
/* ====================================================================== */
/* MAIN LAYOUT */
/* ====================================================================== */
.SBC-page {
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
  background-color: #e5e7eb;
  justify-self: center;
}

/* ====================================================================== */
/* TOP CATEGORIES SECTION */
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
  font-size: 29px;
  font-weight: bold;
}

.LC-SBC h1 {
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
  margin-bottom: 15px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
  height: 30px;
}

.item-name {
  font-size: 25px;
  font-weight: bold;
  color: var(--text-primary);
}

.item-price {
  font-size: 15px;
  font-weight: bold;
  color: green;
  white-space: nowrap;
}

/* ====================================================================== */
/* CHART SECTION */
/* ====================================================================== */
.RC-SBC {
  color: var(--text-primary);
}

.RC-SBC h1 {
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
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background-color: white;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
}

.frequency-dropdown:focus {
  outline: none;
  border-color: #3b82f6;
}

.chart-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 150px;
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
  color: var(--text-muted);
}

/* ====================================================================== */
/* CATEGORY ANALYSIS SECTION */
/* ====================================================================== */
.BottomContainer {
  color: var(--text-primary);
  width: 100%;
  margin-top: 40px;
}

.transaction-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-left h1 {
  margin: 0 0 4px 0;
  font-weight: bold;
  color: var(--text-primary);
}

.date-range-info {
  color: var(--text-muted);
  font-size: 13px;
}

.date-range-info i {
  margin-right: 4px;
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
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.table {
  margin: 0;
  width: 100%;
}

.table thead th {
  background-color: #567cdc;
  font-weight: 600;
  color: white;
  border-bottom: 2px solid #e5e7eb;
  padding: 12px;
}

.table tbody td {
  padding: 12px;
  vertical-align: middle;
  border-bottom: 1px solid #f3f4f6;
}

.table tbody tr:hover {
  background-color: #f9fafb;
}

.category-name {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: var(--text-primary);
}

.category-description {
  color: var(--text-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub-categories {
  font-size: 13px;
  color: var(--text-muted);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.items-sold,
.product-count {
  text-align: center;
  font-weight: 500;
}

.net-sales {
  text-align: right;
}

.total-amount {
  font-weight: bold;
  color: #059669;
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
  color: var(--text-muted);
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
  color: var(--text-muted);
}

.spinner-border-sm {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-border {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
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
  color: var(--text-muted);
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
  color: var(--text-muted);
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
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.text-muted {
  color: var(--text-muted) !important;
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

  .table-container {
    overflow-x: auto;
  }

  .table {
    min-width: 800px;
  }

  .category-description {
    max-width: 150px;
  }

  .sub-categories {
    max-width: 120px;
  }
}

@media (max-width: 480px) {
  .LCL1 {
    gap: 10px;
  }

  .chart-header h1 {
    font-size: 24px;
  }

  .table {
    min-width: 600px;
  }

  .btn {
    padding: 6px 12px;
    font-size: 13px;
  }

  .header-left h1 {
    font-size: 24px;
  }

  .date-range-info {
    font-size: 12px;
  }
}

/* Auto-refresh status indicator */
.auto-refresh-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #f0fdf4;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #bbf7d0;
  min-width: 280px;
}

.status-text {
  font-size: 0.875rem;
  color: #16a34a;
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

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.8125rem;
  border-radius: 0.25rem;
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

/* Responsive adjustments */
@media (max-width: 768px) {
  .auto-refresh-status {
    flex-direction: column;
    text-align: center;
    gap: 0.25rem;
    min-width: auto;
  }

  .connection-indicator {
    order: -1;
  }
}

.category-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.trend-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-top: 2px;
}

.trend-indicator.up {
  color: #16a34a;
}

.trend-indicator.down {
  color: #dc2626;
}

.trend-indicator.new {
  color: #d97706;
}

.trend-percent {
  font-weight: 500;
}

.trend-cell .trend-indicator {
  justify-content: center;
}

.view-toggle {
  margin-right: 1rem;
}

.avg-transaction {
  text-align: right;
  font-weight: 500;
  color: var(--text-primary);
}

.transaction-count {
  text-align: center;
  font-weight: 500;
}

</style>
