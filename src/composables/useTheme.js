import { ref, onMounted, watch } from 'vue'

export function useTheme() {
  const currentTheme = ref('light')
  const availableThemes = ref(['light', 'dark'])
  
  // Available background presets
  const backgroundPresets = ref({
    light: {
      primary: '#EEEEEE',
      secondary: '#FFFFFF',
      muted: '#E0E0E0'
    },
    dark: {
      primary: '#1a1a1a',
      secondary: '#2d2d2d',
      muted: '#3a3a3a'
    },
    custom: {
      primary: '#F0F8FF', // Alice Blue
      secondary: '#E6F3FF',
      muted: '#D6E9FF'
    }
  })

  // Set theme
  const setTheme = (theme) => {
    currentTheme.value = theme
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
    
    // Apply background colors from preset
    const preset = backgroundPresets.value[theme]
    if (preset) {
      applyBackgroundColors(preset)
    }
  }

  // Apply custom background colors
  const applyBackgroundColors = (colors) => {
    const root = document.documentElement
    root.style.setProperty('--bg-primary', colors.primary)
    root.style.setProperty('--bg-secondary', colors.secondary)
    root.style.setProperty('--bg-muted', colors.muted)
  }

  // Set custom background color
  const setCustomBackground = (colorType, color) => {
    const root = document.documentElement
    root.style.setProperty(`--bg-${colorType}`, color)
    
    // Save to localStorage
    const customColors = JSON.parse(localStorage.getItem('customColors') || '{}')
    customColors[colorType] = color
    localStorage.setItem('customColors', JSON.stringify(customColors))
  }

  // Reset to default theme
  const resetTheme = () => {
    setTheme('light')
    localStorage.removeItem('customColors')
  }

  // Load saved theme and custom colors
  const loadSavedTheme = () => {
    const savedTheme = localStorage.getItem('theme') || 'light'
    const customColors = JSON.parse(localStorage.getItem('customColors') || '{}')
    
    setTheme(savedTheme)
    
    // Apply any saved custom colors
    Object.entries(customColors).forEach(([colorType, color]) => {
      document.documentElement.style.setProperty(`--bg-${colorType}`, color)
    })
  }

  // Toggle between light and dark
  const toggleTheme = () => {
    const newTheme = currentTheme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }

  // Watch for system theme changes
  const watchSystemTheme = () => {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
          setTheme(e.matches ? 'dark' : 'light')
        }
      })
    }
  }

  onMounted(() => {
    loadSavedTheme()
    watchSystemTheme()
  })

  return {
    currentTheme,
    availableThemes,
    backgroundPresets,
    setTheme,
    setCustomBackground,
    toggleTheme,
    resetTheme,
    applyBackgroundColors
  }
}