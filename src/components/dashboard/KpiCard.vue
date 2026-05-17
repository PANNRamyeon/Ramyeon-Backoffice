<template>
  <div class="kpi-card" :class="variant">
    <div class="kpi-header">
      <h3>{{ title }}</h3>
      <span v-if="change" class="kpi-change" :class="changeType">{{ change }}</span>
    </div>
    <div class="kpi-value">{{ value }}</div>
    <div class="kpi-subtitle">{{ subtitle }}</div>
    
    <!-- Progress bar for target sales -->
    <div v-if="showProgress" class="progress-section">
      <div class="progress-bar">
        <div class="progress-fill" :style="`width: ${progressPercentage}%`"></div>
      </div>
      <div class="progress-info">
        <span class="progress-percentage">{{ progressPercentage }}%</span>
      </div>
      <button v-if="showButton" class="see-more-btn" @click="$emit('button-click')">
        {{ buttonText }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'KpiCard',
  props: {
    title: {
      type: String,
      required: true
    },
    value: {
      type: [String, Number],
      required: true
    },
    subtitle: {
      type: String,
      required: true
    },
    change: {
      type: String,
      default: null
    },
    changeType: {
      type: String,
      default: 'positive',
      validator: value => ['positive', 'negative', 'neutral'].includes(value)
    },
    variant: {
      type: String,
      default: 'default',
      validator: value => ['default', 'profit', 'products', 'income', 'sold', 'orders', 'target'].includes(value)
    },
    showProgress: {
      type: Boolean,
      default: false
    },
    progressPercentage: {
      type: Number,
      default: 0
    },
    showButton: {
      type: Boolean,
      default: false
    },
    buttonText: {
      type: String,
      default: 'See More'
    }
  },
  emits: ['button-click']
}
</script>

<style scoped>
.kpi-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  border: 3px solid #e5e7eb; /* Full outline instead of left border */
  transition: all 0.3s ease;
  min-height: 125px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.kpi-card:hover {
  transform: translateY(-2px); /* Reduced hover effect since no shadow */
}

.kpi-card.profit {
  border-color: var(--primary);
}

.kpi-card.profit::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-card.products {
  border-color: var(--success);
}

.kpi-card.products::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--success-light), var(--success-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-card.income {
  border-color: var(--secondary);
}

.kpi-card.income::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--secondary-light), var(--secondary-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-card.sold {
  border-color: var(--info);
}

.kpi-card.sold::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--info-light), var(--info-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-card.orders {
  border-color: var(--error);
}

.kpi-card.orders::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--error-light), var(--error-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-card.target {
  border-color: var(--primary-medium);
}

.kpi-card.target::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary-light));
  opacity: 0.1;
  border-radius: 0 0 0 60px;
}

.kpi-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  position: relative;
  z-index: 1;
}

.kpi-header h3 {
  color: #374151;
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
  line-height: 1.4;
  flex: 1;
  padding-right: 1rem;
}

.kpi-change {
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1px solid transparent; /* Add border to change badges */
}

.kpi-change.positive {
  background-color: var(--success-light);
  color: var(--success-dark);
  border-color: var(--success);
}

.kpi-change.negative {
  background-color: var(--error-light);
  color: var(--error-dark);
  border-color: var(--error);
}

.kpi-change.neutral {
  background-color: var(--neutral-light);
  color: var(--neutral-dark);
  border-color: var(--neutral);
}

.kpi-value {
  font-size: 2rem;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 0.5rem;
  line-height: 1.1;
  position: relative;
  z-index: 1;
}

.kpi-subtitle {
  color: #6b7280;
  font-size: 0.85rem;
  line-height: 1.5;
  margin-bottom: auto;
  position: relative;
  z-index: 1;
}

.progress-section {
  margin-top: 1rem;
  position: relative;
  z-index: 1;
}

.progress-bar {
  width: 100%;
  height: 10px;
  background-color: #e5e7eb;
  border-radius: 6px;
  border: 1px solid #d1d5db; /* Add border to progress bar */
  overflow: hidden;
  margin-bottom: 0.75rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 5px; /* Slightly smaller to account for parent border */
  transition: width 0.6s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-info {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}

.progress-percentage {
  font-size: 0.95rem;
  font-weight: 700;
  color: #6366f1;
}

.see-more-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: 1px solid #6366f1; /* Add border to button */
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.see-more-btn:hover {
  transform: translateY(-1px); /* Reduced since no shadow */
  border-color: #4f46e5;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
}

.see-more-btn:active {
  transform: translateY(0);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .kpi-card {
    padding: 1.25rem;
    min-height: 110px;
  }
  
  .kpi-header {
    margin-bottom: 1rem;
  }
  
  .kpi-header h3 {
    font-size: 0.875rem;
  }
  
  .kpi-value {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
  }
  
  .kpi-subtitle {
    font-size: 0.8rem;
  }
  
  .progress-section {
    margin-top: 1rem;
  }
  
  .see-more-btn {
    padding: 0.625rem 1.25rem;
    font-size: 0.85rem;
  }
}

@media (max-width: 480px) {
  .kpi-card {
    padding: 1.25rem;
  }
  
  .kpi-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  
  .kpi-header h3 {
    padding-right: 0;
  }
  
  .kpi-value {
    font-size: 1.75rem;
  }
}
</style>