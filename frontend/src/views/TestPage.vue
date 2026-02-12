<template>
  <div class="test-page">
    <h1>Vue Test Page</h1>
    <p>Count: {{ count }}</p>
    <button @click="count++">Increment</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<style scoped>
.test-page {
  padding: 20px;
  background: #0c1221;
  color: white;
  min-height: 100vh;
}

h1 {
  color: #60a5fa;
}

button {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #2563eb;
}
</style>
