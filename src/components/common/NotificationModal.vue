<template>
  <transition name="notification" appear>
    <div v-if="show" class="notification-overlay" @click="handleOverlayClick">
      <div class="notification-container" :class="notificationClass" @click.stop>
        <div class="notification-header">
          <div class="notification-icon">
            <!-- Success Icon -->
            <svg v-if="type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
            
            <!-- Error Icon -->
            <svg v-else-if="type === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            
            <!-- Info Icon -->
            <svg v-else-if="type === 'info'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
          </div>
          
          <div class="notification-content">
            <h3 class="notification-title">{{ title }}</h3>
            <p class="notification-message">{{ message }}</p>
          </div>
          
          <button v-if="showCloseButton" class="close-button" @click="$emit('close')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        
        <!-- Details Section (for bulk operations) -->
        <div v-if="details && (details.successful || details.failed)" class="notification-details">
          <div v-if="details.successful > 0" class="detail-item success-detail">
            <svg class="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"/>
            </svg>
            <span>{{ details.successful }} product{{ details.successful > 1 ? 's' : '' }} created successfully</span>
          </div>
          
          <div v-if="details.failed > 0" class="detail-item error-detail">
            <svg class="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>{{ details.failed }} product{{ details.failed > 1 ? 's' : '' }} failed to create</span>
          </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="notification-actions">
          <button 
            v-if="type === 'error'" 
            class="btn btn-submit btn-with-icon btn-sm" 
            @click="$emit('retry')"
          >
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
              <path d="M21 21v-5h-5"/>
            </svg>
            Try Again
          </button>
          
          <button class="btn btn-cancel btn-sm" @click="$emit('close')">
            Close
          </button>
        </div>
        
        <!-- Auto-close Progress Bar -->
        <div v-if="autoClose && showProgress" class="progress-container">
          <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'NotificationModal',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    type: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'error', 'info', 'warning'].includes(value)
    },
    title: {
      type: String,
      required: true
    },
    message: {
      type: String,
      required: true
    },
    details: {
      type: Object,
      default: null
    },
    showCloseButton: {
      type: Boolean,
      default: true
    },
    autoClose: {
      type: Boolean,
      default: true
    },
    duration: {
      type: Number,
      default: 5000
    },
    showProgress: {
      type: Boolean,
      default: true
    },
    closeOnOverlay: {
      type: Boolean,
      default: true
    }
  },
  emits: ['close', 'confirm', 'retry'],
  data() {
    return {
      progress: 100,
      timer: null,
      progressTimer: null
    }
  },
  computed: {
    notificationClass() {
      return `notification-${this.type}`
    }
  },
  watch: {
    show(newVal) {
      if (newVal && this.autoClose) {
        this.startAutoClose()
      } else {
        this.clearTimers()
      }
    }
  },
  methods: {
    handleOverlayClick() {
      if (this.closeOnOverlay) {
        this.$emit('close')
      }
    },
    
    startAutoClose() {
      this.clearTimers()
      
      if (this.showProgress) {
        this.progress = 100
        this.progressTimer = setInterval(() => {
          this.progress -= (100 / (this.duration / 100))
          if (this.progress <= 0) {
            this.progress = 0
            clearInterval(this.progressTimer)
          }
        }, 100)
      }
      
      this.timer = setTimeout(() => {
        this.$emit('close')
      }, this.duration)
    },
    
    clearTimers() {
      if (this.timer) {
        clearTimeout(this.timer)
        this.timer = null
      }
      if (this.progressTimer) {
        clearInterval(this.progressTimer)
        this.progressTimer = null
      }
    }
  },
  mounted() {
    if (this.show && this.autoClose) {
      this.startAutoClose()
    }
  },
  beforeUnmount() {
    this.clearTimers()
  }
}
</script>

<style scoped>
/* ==========================================================================
   NOTIFICATION MODAL - SEMANTIC THEME SYSTEM
   ========================================================================== */

.notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  @apply modal-overlay-theme transition-theme;
}

.notification-container {
  border-radius: 1rem;
  max-width: 500px;
  width: 100%;
  overflow: hidden;
  position: relative;
  @apply modal-theme shadow-2xl text-primary transition-theme;
}

/* ==========================================================================
   NOTIFICATION TYPES - SEMANTIC STYLING
   ========================================================================== */

.notification-success {
  border-top: 4px solid var(--status-success);
}

.notification-error {
  border-top: 4px solid var(--status-error);
}

.notification-info {
  border-top: 4px solid var(--status-info);
}

.notification-warning {
  border-top: 4px solid var(--status-warning);
}

/* ==========================================================================
   HEADER SECTION - SEMANTIC STYLING
   ========================================================================== */

.notification-header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
}

.notification-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  @apply transition-theme;
}

.notification-success .notification-icon {
  background-color: var(--status-success-bg);
  color: var(--status-success);
}

.notification-error .notification-icon {
  background-color: var(--status-error-bg);
  color: var(--status-error);
}

.notification-info .notification-icon {
  background-color: var(--status-info-bg);
  color: var(--status-info);
}

.notification-warning .notification-icon {
  background-color: var(--status-warning-bg);
  color: var(--status-warning);
}

.notification-icon svg {
  width: 24px;
  height: 24px;
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  line-height: 1.3;
  @apply text-primary transition-theme;
}

.notification-message {
  font-size: 0.9375rem;
  margin: 0;
  line-height: 1.5;
  @apply text-secondary transition-theme;
}

.close-button {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  @apply text-tertiary transition-all-theme;
}

.close-button:hover {
  @apply surface-tertiary text-secondary;
}

.close-button svg {
  width: 18px;
  height: 18px;
}

/* ==========================================================================
   DETAILS SECTION - SEMANTIC STYLING
   ========================================================================== */

.notification-details {
  padding: 0 1.5rem;
  @apply border-top-theme border-bottom-theme transition-theme;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  font-size: 0.875rem;
  font-weight: 500;
}

.detail-item:not(:last-child) {
  @apply border-bottom-theme;
}

.detail-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.success-detail {
  color: var(--status-success);
}

.success-detail .detail-icon {
  color: var(--status-success);
}

.error-detail {
  color: var(--status-error);
}

.error-detail .detail-icon {
  color: var(--status-error);
}

/* ==========================================================================
   ACTION BUTTONS - SEMANTIC STYLING
   ========================================================================== */

.notification-actions {
  display: flex;
  gap: 0.75rem;
  padding: 1.5rem;
  justify-content: flex-end;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

/* ==========================================================================
   PROGRESS BAR - SEMANTIC STYLING
   ========================================================================== */

.progress-container {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  @apply surface-tertiary;
}

.progress-bar {
  height: 100%;
  @apply transition-all-theme;
  transition: width 0.1s linear;
}

.notification-success .progress-bar {
  background-color: var(--status-success);
}

.notification-error .progress-bar {
  background-color: var(--status-error);
}

.notification-info .progress-bar {
  background-color: var(--status-info);
}

.notification-warning .progress-bar {
  background-color: var(--status-warning);
}

/* ==========================================================================
   ANIMATIONS
   ========================================================================== */

.notification-enter-active {
  @apply transition-all-theme;
  transition-duration: 0.3s;
}

.notification-leave-active {
  @apply transition-all-theme;
  transition-duration: 0.3s;
}

.notification-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

.notification-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

/* Success Animation */
.notification-success.notification-enter-active {
  animation: successBounce 0.6s ease;
}

@keyframes successBounce {
  0% {
    opacity: 0;
    transform: scale(0.3) translateY(-50px);
  }
  50% {
    transform: scale(1.05) translateY(-10px);
  }
  70% {
    transform: scale(0.95) translateY(0);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Error Animation */
.notification-error.notification-enter-active {
  animation: errorShake 0.5s ease;
}

@keyframes errorShake {
  0%, 100% {
    opacity: 1;
    transform: translateX(0);
  }
  20%, 60% {
    transform: translateX(-10px);
  }
  40%, 80% {
    transform: translateX(10px);
  }
}

/* Info Animation */
.notification-info.notification-enter-active {
  animation: infoSlide 0.4s ease;
}

@keyframes infoSlide {
  0% {
    opacity: 0;
    transform: translateY(-30px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Warning Animation */
.notification-warning.notification-enter-active {
  animation: warningPulse 0.5s ease;
}

@keyframes warningPulse {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  50% {
    transform: scale(1.02);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* ==========================================================================
   RESPONSIVE DESIGN
   ========================================================================== */

@media (max-width: 640px) {
  .notification-overlay {
    padding: 0.5rem;
  }
  
  .notification-container {
    max-width: 100%;
  }
  
  .notification-header {
    padding: 1rem;
  }
  
  .notification-details {
    padding: 0 1rem;
  }
  
  .notification-actions {
    padding: 1rem;
    flex-direction: column;
  }
  
  .notification-actions .btn {
    width: 100%;
    justify-content: center;
  }
  
  .notification-title {
    font-size: 1.125rem;
  }
  
  .notification-message {
    font-size: 0.875rem;
  }
  
  .notification-icon {
    width: 40px;
    height: 40px;
  }
  
  .notification-icon svg {
    width: 20px;
    height: 20px;
  }
}

/* ==========================================================================
   ACCESSIBILITY & FOCUS STATES
   ========================================================================== */

.close-button:focus {
  @apply focus-ring-theme;
}

/* Enhanced focus for action buttons handled by button utilities */

/* ==========================================================================
   ENHANCED VISUAL EFFECTS
   ========================================================================== */

/* Backdrop blur effect */
@supports (backdrop-filter: blur(8px)) {
  .notification-overlay {
    backdrop-filter: blur(8px);
  }
}

/* Enhanced shadow for elevated notification */
.notification-container:hover {
  @apply shadow-2xl;
  transform: translateY(-2px);
}

/* Status indicator glow effect */
.notification-success {
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px var(--status-success),
    0 0 20px rgba(94, 180, 136, 0.1);
}

.notification-error {
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px var(--status-error),
    0 0 20px rgba(229, 57, 53, 0.1);
}

.notification-info {
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px var(--status-info),
    0 0 20px rgba(127, 89, 139, 0.1);
}

.notification-warning {
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.25),
    0 0 0 1px var(--status-warning),
    0 0 20px rgba(255, 152, 0, 0.1);
}

/* Icon animation on appear */
.notification-icon {
  animation: iconScale 0.6s ease;
}

@keyframes iconScale {
  0% {
    transform: scale(0);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

/* ==========================================================================
   REDUCED MOTION SUPPORT
   ========================================================================== */

@media (prefers-reduced-motion: reduce) {
  .notification-enter-active,
  .notification-leave-active,
  .notification-container,
  .notification-icon,
  .progress-bar {
    transition: none !important;
    animation: none !important;
  }
  
  .notification-container:hover {
    transform: none !important;
  }
}
</style>