<template>
  <div 
    :class="cardClasses"
    :style="cardStyles"
    @click="handleClick"
  >
    <!-- Card Header (optional) -->
    <div v-if="$slots.header" class="card-header">
      <slot name="header"></slot>
    </div>

    <!-- Card Body -->
    <div class="card-body" :style="bodyStyles">
      <!-- Title -->
      <h6 v-if="title" :class="titleClasses">{{ title }}</h6>
      
      <!-- Main Content -->
      <slot name="content">
        <div v-if="content" v-html="content"></div>
      </slot>
      
      <!-- Value Display -->
      <div v-if="value !== null && value !== undefined" :class="valueClasses">
        {{ formattedValue }}
      </div>
      
      <!-- Subtitle/Description -->
      <small v-if="subtitle" :class="subtitleClasses">{{ subtitle }}</small>
    </div>

    <!-- Card Footer (optional) -->
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer"></slot>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="card-loading-overlay">
      <div class="spinner-border text-accent" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CardTemplate',
  props: {
    // Size variants - now includes 'custom'
    size: {
      type: String,
      default: 'md',
      validator: (value) => ['mini', 'xs', 'compact', 'sm', 'md', 'lg', 'xl', 'xxl', 'custom'].includes(value)
    },
    
    // Custom dimensions (only used when size is 'custom')
    width: {
      type: [String, Number],
      default: null
    },
    
    height: {
      type: [String, Number],
      default: null
    },
    
    minWidth: {
      type: [String, Number],
      default: null
    },
    
    minHeight: {
      type: [String, Number],
      default: null
    },
    
    maxWidth: {
      type: [String, Number],
      default: null
    },
    
    maxHeight: {
      type: [String, Number],
      default: null
    },
    
    // Custom padding (only used when size is 'custom')
    padding: {
      type: [String, Number],
      default: null
    },
    
    // Border color variants
    borderColor: {
      type: String,
      default: 'none',
      validator: (value) => [
        'none', 'primary', 'secondary', 'success', 'info', 'warning', 
        'danger', 'error', 'tertiary', 'neutral', 'accent'
      ].includes(value)
    },
    
    // Border position
    borderPosition: {
      type: String,
      default: 'start',
      validator: (value) => ['start', 'end', 'top', 'bottom', 'all'].includes(value)
    },
    
    // Content props
    title: {
      type: String,
      default: null
    },
    
    subtitle: {
      type: String,
      default: null
    },
    
    content: {
      type: String,
      default: null
    },
    
    value: {
      type: [String, Number],
      default: null
    },
    
    // Styling props
    clickable: {
      type: Boolean,
      default: false
    },
    
    loading: {
      type: Boolean,
      default: false
    },
    
    shadow: {
      type: String,
      default: 'sm',
      validator: (value) => ['none', 'sm', 'md', 'lg', 'xl'].includes(value)
    },
    
    // Value formatting
    valueType: {
      type: String,
      default: 'text',
      validator: (value) => ['text', 'number', 'currency', 'percentage'].includes(value)
    },
    
    valueColor: {
      type: String,
      default: 'accent',
      validator: (value) => [
        'primary', 'secondary', 'success', 'info', 'warning', 
        'danger', 'error', 'tertiary', 'neutral', 'accent'
      ].includes(value)
    }
  },
  
  emits: ['click'],
  
  computed: {
    cardClasses() {
      const classes = ['card', 'card-template']
      
      // Size classes (only apply if not custom)
      if (this.size !== 'custom') {
        classes.push(`card-${this.size}`)
      }
      
      // Border classes
      if (this.borderColor !== 'none') {
        if (this.borderPosition === 'all') {
          classes.push(`border-${this.borderColor}`)
        } else {
          classes.push(`border-${this.borderPosition}`)
          classes.push(`border-${this.borderColor}`)
        }
        
        // Add border width for visibility
        if (this.borderPosition !== 'all') {
          classes.push('border-4')
        }
      }
      
      // Shadow classes
      if (this.shadow !== 'none') {
        classes.push(`shadow-${this.shadow}`)
      }
      
      // Interactive classes
      if (this.clickable) {
        classes.push('card-clickable')
      }
      
      // Loading state
      if (this.loading) {
        classes.push('card-loading')
      }
      
      return classes
    },
    
    cardStyles() {
      if (this.size !== 'custom') return {}
      
      const styles = {}
      
      // Convert numbers to px, keep strings as-is
      const formatDimension = (value) => {
        if (typeof value === 'number') return `${value}px`
        return value
      }
      
      if (this.width) styles.width = formatDimension(this.width)
      if (this.height) styles.height = formatDimension(this.height)
      if (this.minWidth) styles.minWidth = formatDimension(this.minWidth)
      if (this.minHeight) styles.minHeight = formatDimension(this.minHeight)
      if (this.maxWidth) styles.maxWidth = formatDimension(this.maxWidth)
      if (this.maxHeight) styles.maxHeight = formatDimension(this.maxHeight)
      
      return styles
    },
    
    bodyStyles() {
      if (this.size !== 'custom' || !this.padding) return {}
      
      const formatDimension = (value) => {
        if (typeof value === 'number') return `${value}px`
        return value
      }
      
      return {
        padding: formatDimension(this.padding)
      }
    },
    
    titleClasses() {
      const classes = ['card-title', 'text-primary', 'mb-2']
      
      // Size-based title classes (skip if custom size)
      if (this.size !== 'custom') {
        if (this.size === 'mini') {
          classes.push('small', 'fw-semibold')
        } else if (this.size === 'xs') {
          classes.push('small', 'fw-semibold')
        } else if (this.size === 'compact') {
          classes.push('h6', 'mb-1')
        } else if (this.size === 'sm') {
          classes.push('h6')
        } else if (this.size === 'lg') {
          classes.push('h5')
        } else if (this.size === 'xl') {
          classes.push('h4')
        } else if (this.size === 'xxl') {
          classes.push('h3')
        } else {
          classes.push('h6')
        }
      } else {
        // Default title size for custom cards
        classes.push('h6')
      }
      
      return classes
    },
    
    valueClasses() {
      const classes = ['card-value', 'fw-bold', 'mb-1']
      
      // Color classes
      classes.push(`text-${this.valueColor}`)
      
      // Size-based value classes (skip if custom size)
      if (this.size !== 'custom') {
        if (this.size === 'mini') {
          classes.push('h6', 'mb-0')
        } else if (this.size === 'xs') {
          classes.push('h5', 'mb-0')
        } else if (this.size === 'compact') {
          classes.push('h4', 'mb-1')
        } else if (this.size === 'sm') {
          classes.push('h6')
        } else if (this.size === 'lg') {
          classes.push('h1')
        } else if (this.size === 'xl') {
          classes.push('display-6')
        } else if (this.size === 'xxl') {
          classes.push('display-4')
        } else {
          classes.push('h2')
        }
      } else {
        // Default value size for custom cards
        classes.push('h4')
      }
      
      return classes
    },
    
    subtitleClasses() {
      return ['card-subtitle', 'text-tertiary']
    },
    
    formattedValue() {
      if (this.value === null || this.value === undefined) return ''
      
      switch (this.valueType) {
        case 'currency':
          return `₱${parseFloat(this.value).toFixed(2)}`
        case 'percentage':
          return `${this.value}%`
        case 'number':
          return parseFloat(this.value).toLocaleString()
        default:
          return this.value
      }
    }
  },
  
  methods: {
    handleClick(event) {
      if (this.clickable && !this.loading) {
        this.$emit('click', event)
      }
    }
  }
}
</script>

<style scoped>
/* ==========================================================================
   CARD TEMPLATE COMPONENT - SEMANTIC THEME SYSTEM
   Reusable card component with size and border variants
   ========================================================================== */

.card-template {
  position: relative;
  border-radius: 0.75rem;
  background-color: var(--surface-primary);
  border: 1px solid var(--border-secondary);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}

/* ==========================================================================
   SIZE VARIANTS (excluding custom)
   ========================================================================== */
.card-mini .card-body {
  padding: 0.5rem 0.75rem;
}

.card-xs .card-body {
  padding: 0.625rem 0.875rem;
}

.card-compact .card-body {
  padding: 0.75rem 1rem;
}

.card-sm .card-body {
  padding: 0.75rem;
}

.card-md .card-body {
  padding: 1.25rem;
}

.card-lg .card-body {
  padding: 1.5rem;
}

.card-xl .card-body {
  padding: 2rem;
}

.card-xxl .card-body {
  padding: 2.5rem;
}

/* ==========================================================================
   CUSTOM SIZE DEFAULT STYLING
   When size="custom", apply sensible defaults
   ========================================================================== */
.card-template:not([class*="card-mini"]):not([class*="card-xs"]):not([class*="card-compact"]):not([class*="card-sm"]):not([class*="card-md"]):not([class*="card-lg"]):not([class*="card-xl"]):not([class*="card-xxl"]) .card-body {
  /* Default padding for custom cards */
  padding: 1rem;
}

/* ==========================================================================
   CARD HEADER & FOOTER - SEMANTIC STYLING
   ========================================================================== */

.card-header,
.card-footer {
  background-color: var(--surface-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  transition: all 0.3s ease;
}

/* ==========================================================================
   COMPACT SIZE TYPOGRAPHY ADJUSTMENTS
   ========================================================================== */

.card-mini .card-title {
  font-size: 0.75rem;
  line-height: 1.2;
  margin-bottom: 0.25rem !important;
}

.card-mini .card-value {
  font-size: 1rem;
  line-height: 1.1;
  margin-bottom: 0 !important;
}

.card-mini .card-subtitle {
  font-size: 0.6875rem;
  margin-bottom: 0 !important;
}

.card-xs .card-title {
  font-size: 0.8125rem;
  line-height: 1.2;
  margin-bottom: 0.375rem !important;
}

.card-xs .card-value {
  font-size: 1.125rem;
  line-height: 1.1;
  margin-bottom: 0 !important;
}

.card-xs .card-subtitle {
  font-size: 0.75rem;
  margin-bottom: 0 !important;
}

.card-compact .card-title {
  font-size: 0.875rem;
  line-height: 1.3;
  margin-bottom: 0.5rem !important;
}

.card-compact .card-value {
  font-size: 1.5rem;
  line-height: 1.1;
  margin-bottom: 0.25rem !important;
}

.card-compact .card-subtitle {
  font-size: 0.8125rem;
  margin-bottom: 0 !important;
}

/* ==========================================================================
   BORDER COLOR VARIANTS - SEMANTIC WITH DARK MODE GRADIENTS
   ========================================================================== */

.border-primary {
  border-color: var(--primary) !important;
}

.border-secondary {
  border-color: var(--secondary) !important;
}

.border-accent {
  border-color: var(--text-accent) !important;
}

.border-success {
  border-color: var(--success) !important;
}

.border-info {
  border-color: var(--info) !important;
}

.border-warning {
  border-color: var(--status-warning) !important;
}

.border-danger,
.border-error {
  border-color: var(--error) !important;
}

.border-tertiary {
  border-color: var(--tertiary) !important;
}

.border-neutral {
  border-color: var(--neutral) !important;
}

/* ==========================================================================
   DARK MODE FILLED CARD VARIANTS WITH SOFT GRADIENTS
   ========================================================================== */

/* Dark mode filled backgrounds with gradients */
:root.dark-theme .card-template.border-primary,
.dark-theme .card-template.border-primary {
  background: linear-gradient(135deg, 
    rgba(143, 164, 232, 0.15) 0%, 
    rgba(115, 146, 226, 0.08) 100%);
  border-color: rgba(143, 164, 232, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(143, 164, 232, 0.1);
}

:root.dark-theme .card-template.border-secondary,
.dark-theme .card-template.border-secondary {
  background: linear-gradient(135deg, 
    rgba(192, 153, 236, 0.15) 0%, 
    rgba(160, 123, 227, 0.08) 100%);
  border-color: rgba(192, 153, 236, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(192, 153, 236, 0.1);
}

:root.dark-theme .card-template.border-accent,
.dark-theme .card-template.border-accent {
  background: linear-gradient(135deg, 
    rgba(176, 136, 228, 0.15) 0%, 
    rgba(160, 123, 227, 0.08) 100%);
  border-color: rgba(176, 136, 228, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(176, 136, 228, 0.1);
}

:root.dark-theme .card-template.border-success,
.dark-theme .card-template.border-success {
  background: linear-gradient(135deg, 
    rgba(125, 209, 165, 0.15) 0%, 
    rgba(107, 196, 151, 0.08) 100%);
  border-color: rgba(125, 209, 165, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(125, 209, 165, 0.1);
}

:root.dark-theme .card-template.border-info,
.dark-theme .card-template.border-info {
  background: linear-gradient(135deg, 
    rgba(157, 123, 169, 0.15) 0%, 
    rgba(139, 107, 151, 0.08) 100%);
  border-color: rgba(157, 123, 169, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(157, 123, 169, 0.1);
}

:root.dark-theme .card-template.border-warning,
.dark-theme .card-template.border-warning {
  background: linear-gradient(135deg, 
    rgba(255, 183, 77, 0.15) 0%, 
    rgba(255, 152, 0, 0.08) 100%);
  border-color: rgba(255, 183, 77, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(255, 183, 77, 0.1);
}

:root.dark-theme .card-template.border-error,
.dark-theme .card-template.border-danger {
  background: linear-gradient(135deg, 
    rgba(242, 107, 103, 0.15) 0%, 
    rgba(239, 83, 80, 0.08) 100%);
  border-color: rgba(242, 107, 103, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(242, 107, 103, 0.1);
}

:root.dark-theme .card-template.border-tertiary,
.dark-theme .card-template.border-tertiary {
  background: linear-gradient(135deg, 
    rgba(180, 168, 180, 0.15) 0%, 
    rgba(153, 137, 154, 0.08) 100%);
  border-color: rgba(180, 168, 180, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(180, 168, 180, 0.1);
}

:root.dark-theme .card-template.border-neutral,
.dark-theme .card-template.border-neutral {
  background: linear-gradient(135deg, 
    rgba(188, 188, 188, 0.15) 0%, 
    rgba(146, 146, 146, 0.08) 100%);
  border-color: rgba(188, 188, 188, 0.3) !important;
  box-shadow: 0 4px 6px -1px rgba(188, 188, 188, 0.1);
}

/* ==========================================================================
   VALUE COLOR VARIANTS - SEMANTIC
   ========================================================================== */

.text-primary {
  color: var(--text-primary) !important;
}

.text-secondary {
  color: var(--secondary) !important;
}

.text-accent {
  color: var(--text-accent) !important;
}

.text-success {
  color: var(--success) !important;
}

.text-info {
  color: var(--info) !important;
}

.text-warning {
  color: var(--status-warning) !important;
}

.text-danger,
.text-error {
  color: var(--error) !important;
}

.text-tertiary {
  color: var(--text-tertiary) !important;
}

.text-neutral {
  color: var(--neutral-dark) !important;
}

/* ==========================================================================
   INTERACTIVE STATES - SEMANTIC
   ========================================================================== */

.card-clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.card-clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.card-clickable:active {
  transform: translateY(-1px);
}

/* ==========================================================================
   LOADING STATE - SEMANTIC
   ========================================================================== */

.card-loading {
  pointer-events: none;
  background-color: var(--state-disabled);
  opacity: 0.6;
}

.card-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: inherit;
  z-index: 10;
  background-color: var(--surface-overlay);
}

/* ==========================================================================
   SHADOW VARIANTS - SEMANTIC
   ========================================================================== */

.shadow-sm {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
}

.shadow-lg {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
}

.shadow-xl {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
}

/* ==========================================================================
   RESPONSIVE ADJUSTMENTS
   ========================================================================== */

@media (max-width: 768px) {
  .card-xl .card-body {
    padding: 1.5rem;
  }
  
  .card-xxl .card-body {
    padding: 1.75rem;
  }
  
  .card-lg .card-body {
    padding: 1.25rem;
  }
  
  .card-md .card-body {
    padding: 1rem;
  }
  
  .card-sm .card-body {
    padding: 0.75rem;
  }

  .card-mini .card-body {
    padding: 0.375rem 0.5rem;
  }
  
  .card-xs .card-body {
    padding: 0.5rem 0.625rem;
  }
  
  .card-compact .card-body {
    padding: 0.625rem 0.75rem;
  }
}

/* ==========================================================================
   ACCESSIBILITY ENHANCEMENTS - SEMANTIC
   ========================================================================== */

.card-clickable:focus {
  outline: 2px solid var(--border-accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .card-template,
  .card-clickable {
    transition: none !important;
  }
  
  .card-clickable:hover {
    transform: none;
  }
}

/* ==========================================================================
   ENHANCED VISUAL EFFECTS
   ========================================================================== */

/* Subtle gradient background for elevated cards */
.card-template {
  background: linear-gradient(
    145deg,
    var(--surface-primary) 0%,
    var(--surface-elevated) 100%
  );
}

/* Enhanced hover state for clickable cards */
.card-clickable:hover {
  background: linear-gradient(
    145deg,
    var(--surface-elevated) 0%,
    var(--surface-primary) 100%
  );
}

/* Card content text hierarchy */
.card-body {
  @apply text-secondary;
}

/* Enhanced loading spinner */
.card-loading-overlay .spinner-border {
  width: 2rem;
  height: 2rem;
  border-width: 0.25rem;
}

/* Border position variants with better visual impact */
.border-start.border-4 {
  border-left-width: 4px !important;
  border-left-style: solid !important;
}

.border-end.border-4 {
  border-right-width: 4px !important;
  border-right-style: solid !important;
}

.border-top.border-4 {
  border-top-width: 4px !important;
  border-top-style: solid !important;
}

.border-bottom.border-4 {
  border-bottom-width: 4px !important;
  border-bottom-style: solid !important;
}

/* Enhanced typography spacing */
.card-title + .card-value {
  margin-top: 0.5rem;
}

.card-value + .card-subtitle {
  margin-top: 0.25rem;
}

/* Status indicator styling */
.card-template[class*="border-success"] {
  box-shadow: 0 4px 6px -1px rgba(94, 180, 136, 0.1), 0 2px 4px -1px rgba(94, 180, 136, 0.06);
}

.card-template[class*="border-error"] {
  box-shadow: 0 4px 6px -1px rgba(229, 57, 53, 0.1), 0 2px 4px -1px rgba(229, 57, 53, 0.06);
}

.card-template[class*="border-warning"] {
  box-shadow: 0 4px 6px -1px rgba(255, 193, 7, 0.1), 0 2px 4px -1px rgba(255, 193, 7, 0.06);
}
</style>