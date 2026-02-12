<template>
  <div class="coming-soon-page">
    <div class="page-header">
      <a href="/desktop" class="back-link">← Back to Desktop</a>
    </div>
    <div class="coming-soon-content">
      <div class="icon">🚧</div>
      <h1>Coming Soon</h1>
      <p>This feature is under development and will be available soon.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.coming-soon-page {
  min-height: 100vh;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
}

.page-header {
  max-width: 1200px;
  margin: 0 auto 24px;
}

.back-link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  display: inline-block;
}

.back-link:hover {
  color: #60a5fa;
}

.coming-soon-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.icon {
  font-size: 64px;
  margin-bottom: 24px;
}

h1 {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 16px 0;
}

p {
  color: #94a3b8;
  font-size: 16px;
  margin: 0;
  max-width: 400px;
}
</style>
