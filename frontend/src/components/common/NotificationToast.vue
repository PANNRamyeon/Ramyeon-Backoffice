<template>
  <Transition
    name="toast"
    appear
  >
    <div
      v-if="visible"
      :class="[
        'toast-notification',
        `toast-${type}`,
        { 'toast-dismissible': dismissible }
      ]"
      role="alert"
      aria-live="polite"
    >
      <!-- Icon Section -->
      <div class="toast-icon">
        <component :is="iconComponent" :size="20" />
      </div>
      
      <!-- Content Section -->
      <div class="toast-content">
        <div class="toast-message">{{ message }}</div>
      </div>
      
      <!-- Close Button (if dismissible) -->
      <button
        v-if="dismissible"
        class="toast-close"
        type="button"
        aria-label="Close notification"
        @click="handleClose"
      >
        <X :size="16" />
      </button>
      
      <!-- Progress Bar -->
      <div
        v-if="showProgressBar"
        class="toast-progress-container"
      >
        <div
          class="toast-progress-bar"
          :style="{ animationDuration: `${duration}ms` }"
        ></div>
      </div>
    </div>
  </Transition>
</template>

<script>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-vue-next'

export default {
  name: 'NotificationToast',
  components: {
    CheckCircle,
    AlertCircle,
    AlertTriangle,
    Info,
    X
  },
  props: {
    type: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
    },
    message: {
      type: String,
      required: true
    },
    duration: {
      type: Number,
      default: 4000 // 4 seconds
    },
    dismissible: {
      type: Boolean,
      default: true
    },
    showProgressBar: {
      type: Boolean,
      default: true
    },
    persistent: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const visible = ref(true)
    let timeoutId = null

    const iconComponent = computed(() => {
      const iconMap = {
        success: CheckCircle,
        error: AlertCircle,
        warning: AlertTriangle,
        info: Info
      }
      return iconMap[props.type]
    })

    const handleClose = () => {
      visible.value = false
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      // Emit close event after transition completes
      setTimeout(() => {
        emit('close')
      }, 300)
    }

    const startAutoClose = () => {
      if (!props.persistent && props.duration > 0) {
        timeoutId = setTimeout(() => {
          handleClose()
        }, props.duration)
      }
    }

    onMounted(() => {
      startAutoClose()
    })

    onUnmounted(() => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    })

    return {
      visible,
      iconComponent,
      handleClose
    }
  }
}
</script>

<style scoped>
.toast-notification {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 300px;
  max-width: 500px;
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  background-color: var(--surface-elevated);
  border-radius: 0.5rem;
  box-shadow: var(--shadow-lg);
  border-left: 4px solid;
  overflow: hidden;
  transition: all 0.3s ease;
}

/* Toast Types */
.toast-success {
  border-left-color: var(--status-success);
  background-color: #f0f9f4;
}

.toast-error {
  border-left-color: var(--status-error);
  background-color: #fef2f2;
}

.toast-warning {
  border-left-color: var(--status-warning);
  background-color: #fffbeb;
}

.toast-info {
  border-left-color: var(--status-info);
  background-color: #f0f4ff;
}

/* Dark theme adjustments */
.dark-theme .toast-success {
  background-color: rgba(34, 197, 94, 0.1);
}

.dark-theme .toast-error {
  background-color: rgba(239, 68, 68, 0.1);
}

.dark-theme .toast-warning {
  background-color: rgba(245, 158, 11, 0.1);
}

.dark-theme .toast-info {
  background-color: rgba(59, 130, 246, 0.1);
}

/* Icon Section */
.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-right: 0.75rem;
}

.toast-success .toast-icon {
  color: var(--status-success);
}

.toast-error .toast-icon {
  color: var(--status-error);
}

.toast-warning .toast-icon {
  color: var(--status-warning);
}

.toast-info .toast-icon {
  color: var(--status-info);
}

/* Content Section */
.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-message {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--tertiary-dark);
  line-height: 1.4;
  word-wrap: break-word;
}

/* Close Button */
.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  margin-left: 0.75rem;
  background: none;
  border: none;
  border-radius: 0.25rem;
  color: var(--tertiary-medium);
  cursor: pointer;
  transition: all 0.2s ease;
}

.toast-close:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: var(--tertiary-dark);
}

.dark-theme .toast-close:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.toast-close:focus {
  outline: 2px solid var(--border-accent);
  outline-offset: 1px;
}

/* Progress Bar Container */
.toast-progress-container {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.dark-theme .toast-progress-container {
  background-color: rgba(255, 255, 255, 0.1);
}

/* Progress Bar Animation - Right to Left (100% to 0%) */
.toast-progress-bar {
  height: 100%;
  width: 100%;
  transform-origin: right;
  animation: shrink-right-to-left linear;
}

.toast-success .toast-progress-bar {
  background-color: var(--status-success);
}

.toast-error .toast-progress-bar {
  background-color: var(--status-error);
}

.toast-warning .toast-progress-bar {
  background-color: var(--status-warning);
}

.toast-info .toast-progress-bar {
  background-color: var(--status-info);
}

/* Progress Bar Animation Keyframes */
@keyframes shrink-right-to-left {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

/* Toast Transitions */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* Hover Effects */
.toast-notification:hover .toast-progress-bar {
  animation-play-state: paused;
}

/* Responsive Design */
@media (max-width: 576px) {
  .toast-notification {
    min-width: 280px;
    max-width: calc(100vw - 2rem);
    margin-left: 1rem;
    margin-right: 1rem;
  }
  
  .toast-message {
    font-size: 0.8125rem;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .toast-notification,
  .toast-progress-bar {
    animation: none !important;
    transition: none !important;
  }
}

/* High Contrast Mode */
@media (prefers-contrast: high) {
  .toast-notification {
    border-left-width: 6px;
    border: 2px solid;
  }
  
  .toast-success {
    border-color: var(--status-success);
  }
  
  .toast-error {
    border-color: var(--status-error);
  }
  
  .toast-warning {
    border-color: var(--status-warning);
  }
  
  .toast-info {
    border-color: var(--status-info);
  }
}
</style>