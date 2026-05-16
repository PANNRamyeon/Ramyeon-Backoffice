<template>
  <div class="sales-chart">
    <div class="chart-header">
      <div class="chart-title-section">
        <h3>Product Sale</h3>
        <p class="chart-subtitle">Sales performance by category</p>
      </div>
      <select v-model="selectedFrequency" @change="updateChart" class="frequency-select">
        <option value="daily">Daily</option>
        <option value="weekly">Weekly</option>
        <option value="monthly">Monthly</option>
        <option value="yearly">Yearly</option>
      </select>
    </div>
    
    <div class="chart-container">
      <div class="chart-bars">
        <div v-for="(period, index) in chartData" :key="index" class="bar-group">
          <div 
            v-for="(category, catIndex) in categories" 
            :key="catIndex"
            class="bar" 
            :class="category.class"
            :style="`height: ${period[category.key] || 0}px`"
            :title="`${category.label}: ${period[category.key] || 0}`"
            @mouseenter="highlightCategory(category.key)"
            @mouseleave="removeHighlight"
          ></div>
          <span class="period-label">{{ period.label }}</span>
        </div>
      </div>
      
      <div class="chart-legend">
        <div v-for="category in categories" :key="category.key" 
             class="legend-item" 
             :class="{ highlighted: highlightedCategory === category.key }"
             @mouseenter="highlightCategory(category.key)"
             @mouseleave="removeHighlight">
          <span class="legend-color" :class="category.class"></span>
          <span class="legend-label">{{ category.label }}</span>
          <span class="legend-value">{{ getTotalForCategory(category.key) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SalesChart',
  data() {
    return {
      selectedFrequency: 'monthly',
      highlightedCategory: null,
      categories: [
        { key: 'noodles', label: 'Noodles', class: 'noodles' },
        { key: 'toppings', label: 'Toppings', class: 'toppings' },
        { key: 'snacks', label: 'Snacks', class: 'snacks' },
        { key: 'drinks', label: 'Drinks', class: 'drinks' }
      ],
      chartData: [
        { label: 'Jan', noodles: 80, toppings: 60, snacks: 40, drinks: 30 },
        { label: 'Feb', noodles: 70, toppings: 50, snacks: 45, drinks: 35 },
        { label: 'Mar', noodles: 60, toppings: 40, snacks: 35, drinks: 25 },
        { label: 'Apr', noodles: 90, toppings: 70, snacks: 50, drinks: 40 }
      ]
    }
  },
  methods: {
    updateChart() {
      // Here you would typically fetch new data based on selectedFrequency
    },
    highlightCategory(categoryKey) {
      this.highlightedCategory = categoryKey;
    },
    removeHighlight() {
      this.highlightedCategory = null;
    },
    getTotalForCategory(categoryKey) {
      return this.chartData.reduce((total, period) => {
        return total + (period[categoryKey] || 0);
      }, 0);
    }
  }
}
</script>

<style scoped>
.sales-chart {
  background: white;
  border-radius: 16px;
  padding: 1.5rem; /* Reduced from 2rem */
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sales-chart:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem; /* Reduced from 2rem */
  gap: 1rem;
}

.chart-title-section {
  flex: 1;
}

.chart-header h3 {
  color: #1f2937;
  font-size: 1.25rem; /* Reduced from 1.5rem */
  font-weight: 700;
  margin: 0 0 0.25rem 0; /* Reduced from 0.5rem */
  line-height: 1.2;
}

.chart-subtitle {
  color: #6b7280;
  font-size: 0.85rem; /* Reduced from 0.95rem */
  margin: 0;
  line-height: 1.4;
}

.frequency-select {
  padding: 0.75rem 1rem;
  border: 2px solid var(--neutral-medium);
  border-radius: 10px;
  color: var(--neutral-dark);
  background-color: white;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  min-width: 120px;
}

.frequency-select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px rgba(115, 146, 226, 0.1);
}

.frequency-select:hover {
  border-color: var(--neutral);
  box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.1);
}

.chart-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 180px; /* Reduced from 300px (40% reduction) */
}

.chart-bars {
  flex: 1;
  display: flex;
  align-items: end;
  justify-content: space-around;
  padding: 0 1.5rem 1.5rem; /* Reduced from 2.5rem */
  position: relative;
}

.chart-bars::before {
  content: '';
  position: absolute;
  bottom: 1.5rem; /* Reduced from 2.5rem */
  left: 1.5rem; /* Reduced from 2rem */
  right: 1.5rem; /* Reduced from 2rem */
  height: 1px;
  background: #e5e7eb;
}

.bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  position: relative;
}

.bar {
  width: 22px;
  border-radius: 4px;
  margin: 1px;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.6s ease;
}

.bar:hover::after {
  left: 100%;
}

.bar:hover {
  transform: scaleY(1.1) scaleX(1.1);
  filter: brightness(1.1);
}

.bar.noodles {
  background: linear-gradient(135deg, var(--primary), var(--primary-medium));
  box-shadow: 0 2px 4px rgba(115, 146, 226, 0.3);
}

.bar.toppings {
  background: linear-gradient(135deg, var(--success), var(--success-medium));
  box-shadow: 0 2px 4px rgba(94, 180, 136, 0.3);
}

.bar.snacks {
  background: linear-gradient(135deg, var(--info), var(--info-medium));
  box-shadow: 0 2px 4px rgba(127, 89, 139, 0.3);
}

.bar.drinks {
  background: linear-gradient(135deg, var(--error), var(--error-medium));
  box-shadow: 0 2px 4px rgba(229, 57, 53, 0.3);
}

.period-label {
  margin-top: 0.75rem; /* Reduced from 1rem */
  font-size: 0.8rem; /* Reduced from 0.9rem */
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.chart-legend {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); /* Reduced from 140px */
  gap: 1rem; /* Reduced from 1.5rem */
  padding-top: 1rem; /* Reduced from 1.5rem */
  border-top: 2px solid #f3f4f6;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem; /* Reduced from 0.75rem */
  font-size: 0.8rem; /* Reduced from 0.9rem */
  color: #6b7280;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 0.5rem; /* Reduced from 0.75rem */
  border-radius: 6px; /* Reduced from 8px */
  background: #f9fafb;
}

.legend-item:hover,
.legend-item.highlighted {
  color: #374151;
  background: #f3f4f6;
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
}

.legend-color.noodles {
  background: linear-gradient(135deg, var(--primary), var(--primary-medium));
}

.legend-color.toppings {
  background: linear-gradient(135deg, var(--success), var(--success-medium));
}

.legend-color.snacks {
  background: linear-gradient(135deg, var(--info), var(--info-medium));
}

.legend-color.drinks {
  background: linear-gradient(135deg, var(--error), var(--error-medium));
}

.legend-label {
  flex: 1;
  font-weight: 500;
}

.legend-value {
  font-weight: 700;
  color: var(--tertiary-dark);
  font-size: 0.85rem;
}

/* Responsive design */
@media (max-width: 1024px) {
  .chart-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1.5rem;
  }
  
  .frequency-select {
    align-self: flex-end;
    min-width: 140px;
  }
}

@media (max-width: 768px) {
  .sales-chart {
    padding: 1.5rem;
  }
  
  .chart-header {
    margin-bottom: 1.5rem;
  }
  
  .chart-header h3 {
    font-size: 1.25rem;
  }
  
  .chart-subtitle {
    font-size: 0.875rem;
  }
  
  .chart-container {
    height: 320px;
  }
  
  .chart-bars {
    padding: 0 1rem 2rem;
  }
  
  .bar {
    width: 18px;
  }
  
  .chart-legend {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
  
  .legend-item {
    padding: 0.5rem;
    font-size: 0.85rem;
  }
}

@media (max-width: 480px) {
  .sales-chart {
    padding: 1.25rem;
  }
  
  .chart-legend {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
  
  .bar {
    width: 16px;
  }
  
  .period-label {
    font-size: 0.8rem;
  }
}
</style>