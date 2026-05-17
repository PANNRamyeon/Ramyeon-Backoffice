import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'

// Import Bootstrap CSS and JS
import 'bootstrap/dist/css/bootstrap.min.css'
import * as bootstrap from 'bootstrap/dist/js/bootstrap.bundle.min.js'

// Custom Global Styling - Import in this specific order
import './assets/styles/colors.css'
import './assets/styles/buttons.css'
import './assets/styles/global.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import lucidePlugin from './plugins/lucide.js'

// Make Bootstrap available globally
window.bootstrap = bootstrap

const app = createApp(App)

app.component('VueDatePicker', VueDatePicker)

// Optional: Add a global method to change themes
app.config.globalProperties.$setTheme = (theme) => {
  document.documentElement.setAttribute('data-theme', theme)
  // Save to localStorage for persistence
  localStorage.setItem('theme', theme)
}

// Load saved theme on app startup
const savedTheme = localStorage.getItem('theme')
if (savedTheme) {
  document.documentElement.setAttribute('data-theme', savedTheme)
}

app.use(createPinia())
app.use(router)
app.use(lucidePlugin)

app.mount('#app')