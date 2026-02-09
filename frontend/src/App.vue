<template>
  <div id="app">
    <!-- Renders the current page -->
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App',

  // ❌ This block causes redirect loops and breaks refresh behavior
  // ❌ Also conflicts with router guards
  // ❌ We hide it but keep it in case you need to reference later

  /*
  mounted() {
    this.checkAuthStatus()
  },
  methods: {
    checkAuthStatus() {
      const token = localStorage.getItem('authToken')
      const currentPath = this.$route.path

      // If no token and not on login page, redirect to login
      if (!token && currentPath !== '/login') {
        this.$router.push('/login')
      }

      // If has token and on login page, redirect to dashboard
      if (token && currentPath === '/login') {
        this.$router.push('/dashboard')
      }
    }
  }
  */
}
</script>

<style>
/* Global reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow-x: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f9fafb;
}

#app {
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>
