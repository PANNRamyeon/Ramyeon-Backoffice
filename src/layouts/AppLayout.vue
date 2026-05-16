<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <ModernSidebar 
      @sidebar-toggled="handleSidebarToggle"
    />
    
    <!-- Main Content Area -->
    <main class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <!-- Page Content -->
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script>
import ModernSidebar from '@/components/layouts/Sidebar.vue'

export default {
  name: 'AppLayout',
  components: {
    ModernSidebar
  },
  data() {
    return {
      sidebarCollapsed: false
    }
  },
  methods: {
    handleSidebarToggle(collapsed) {
      this.sidebarCollapsed = collapsed
    }
  },
  mounted() {
    // Load sidebar state from localStorage
    const savedState = localStorage.getItem('sidebar-collapsed')
    if (savedState !== null) {
      this.sidebarCollapsed = JSON.parse(savedState)
      
      // Emit the initial state to sync with sidebar
      this.$nextTick(() => {
        this.handleSidebarToggle(this.sidebarCollapsed)
      })
    }
  }
}
</script>

<style scoped>
/* ==========================================================================
   APP LAYOUT - SEMANTIC THEME SYSTEM
   ========================================================================== */

.app-layout {
  min-height: 100vh;
  @apply page-container transition-theme;
}

/* ==========================================================================
   MAIN CONTENT AREA - SEMANTIC STYLING
   ========================================================================== */

.main-content {
  margin-left: 280px; /* Default sidebar width */
  transition: margin-left 0.3s ease;
  min-height: 100vh;
  min-width: 0; /* Prevent overflow issues */
}

.main-content.sidebar-collapsed {
  margin-left: 80px; /* Collapsed sidebar width */
}

/* ==========================================================================
   PAGE CONTENT - SEMANTIC STYLING
   ========================================================================== */

.page-content {
  overflow-x: hidden;
  min-height: 100vh;
  padding: 0; /* Router-view handles its own spacing */
  @apply page-container transition-theme;
}

/* ==========================================================================
   RESPONSIVE DESIGN
   ========================================================================== */

@media (max-width: 768px) {
  .main-content {
    margin-left: 0;
    width: 100vw;
  }
  
  .main-content.sidebar-collapsed {
    margin-left: 0;
    width: 100vw;
  }
}

/* ==========================================================================
   ENHANCED VISUAL EFFECTS
   ========================================================================== */

/* Subtle background pattern for depth */
.app-layout {
  background: 
    radial-gradient(circle at 20% 50%, var(--surface-secondary) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, var(--surface-secondary) 0%, transparent 50%),
    var(--surface-secondary);
}

/* Content elevation */
.page-content {
  position: relative;
}

.page-content::before {
  content: '';
  position: fixed;
  top: 0;
  left: 280px;
  right: 0;
  height: 100vh;
  background: linear-gradient(
    135deg,
    var(--surface-secondary) 0%,
    var(--surface-primary) 100%
  );
  z-index: -1;
  transition: left 0.3s ease;
  pointer-events: none;
}

.sidebar-collapsed .page-content::before {
  left: 80px;
}

/* ==========================================================================
   ACCESSIBILITY & REDUCED MOTION
   ========================================================================== */

@media (prefers-reduced-motion: reduce) {
  .app-layout,
  .main-content,
  .page-content,
  .page-content::before {
    transition: none !important;
  }
}

/* ==========================================================================
   RESPONSIVE BACKGROUND ADJUSTMENTS
   ========================================================================== */

@media (max-width: 768px) {
  .page-content::before {
    left: 0;
  }
}

/* ==========================================================================
   GLOBAL BOX SIZING
   ========================================================================== */

* {
  box-sizing: border-box;
}
</style>