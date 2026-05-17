<template>
  <div class="theme-settings">
    <div class="card">
      <div class="card-header">
        <h5 class="card-title mb-0">Theme Settings</h5>
      </div>
      <div class="card-body">
        <!-- Theme Selection -->
        <div class="mb-3">
          <label class="form-label">Choose Theme</label>
          <div class="btn-group w-100" role="group">
            <button
              v-for="theme in availableThemes"
              :key="theme"
              type="button"
              class="btn"
              :class="currentTheme === theme ? 'btn-primary' : 'btn-outline-secondary'"
              @click="setTheme(theme)"
            >
              {{ theme.charAt(0).toUpperCase() + theme.slice(1) }}
            </button>
          </div>
        </div>

        <!-- Quick Toggle -->
        <div class="mb-3">
          <button 
            type="button" 
            class="btn btn-secondary w-100"
            @click="toggleTheme"
          >
            Toggle Light/Dark
          </button>
        </div>

        <!-- Custom Background Colors -->
        <div class="mb-3">
          <h6 class="text-muted">Custom Background Colors</h6>
          <div class="row g-2">
            <div class="col-4">
              <label class="form-label small">Primary</label>
              <input
                type="color"
                class="form-control form-control-color"
                :value="currentColors.primary"
                @change="updateCustomColor('primary', $event.target.value)"
              />
            </div>
            <div class="col-4">
              <label class="form-label small">Secondary</label>
              <input
                type="color"
                class="form-control form-control-color"
                :value="currentColors.secondary"
                @change="updateCustomColor('secondary', $event.target.value)"
              />
            </div>
            <div class="col-4">
              <label class="form-label small">Muted</label>
              <input
                type="color"
                class="form-control form-control-color"
                :value="currentColors.muted"
                @change="updateCustomColor('muted', $event.target.value)"
              />
            </div>
          </div>
        </div>

        <!-- Background Presets -->
        <div class="mb-3">
          <label class="form-label">Background Presets</label>
          <div class="d-grid gap-2">
            <button
              v-for="(preset, name) in backgroundPresets"
              :key="name"
              type="button"
              class="btn btn-outline-primary"
              @click="applyPreset(name, preset)"
            >
              {{ name.charAt(0).toUpperCase() + name.slice(1) }} Theme
            </button>
          </div>
        </div>

        <!-- Reset Button -->
        <div class="d-grid">
          <button 
            type="button" 
            class="btn btn-outline-danger"
            @click="resetTheme"
          >
            Reset to Default
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useTheme } from '@/composables/useTheme'
import { ref, computed } from 'vue'

export default {
  name: 'ThemeSettings',
  setup() {
    const {
      currentTheme,
      availableThemes,
      backgroundPresets,
      setTheme,
      setCustomBackground,
      toggleTheme,
      resetTheme,
      applyBackgroundColors
    } = useTheme()

    const currentColors = ref({
      primary: '#EEEEEE',
      secondary: '#FFFFFF',
      muted: '#E0E0E0'
    })

    const updateCustomColor = (colorType, color) => {
      currentColors.value[colorType] = color
      setCustomBackground(colorType, color)
    }

    const applyPreset = (themeName, preset) => {
      currentColors.value = { ...preset }
      applyBackgroundColors(preset)
      setTheme(themeName)
    }

    return {
      currentTheme,
      availableThemes,
      backgroundPresets,
      currentColors,
      setTheme,
      toggleTheme,
      resetTheme,
      updateCustomColor,
      applyPreset,
      applyBackgroundColors
    }
  }
}
</script>

<style scoped>
.theme-settings {
  max-width: 400px;
}

.form-control-color {
  width: 100%;
  height: 38px;
  border-radius: 0.375rem;
}

.btn-group .btn {
  flex: 1;
}
</style>