<template>
  <div class="app-shell auth-layout">
    <div class="auth-grid">
      <router-view />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.app-shell {
  min-height: 100vh;
  background: var(--pc-bg);
}

.auth-layout {
  min-height: 100vh;
  padding: 40px 48px;
  background: var(--pc-bg);
}

.auth-grid {
  display: grid;
  grid-template-columns: 1fr 520px;
  align-items: start;
  gap: 72px;
  max-width: 1320px;
  margin: 0 auto;
  padding-top: 64px;
}
</style>
