<template>
  <div class="test">
    <h1>Vue Works!</h1>
    <p>Count: {{ count }}</p>
    <button @click="count++">Click me</button>
  </div>
</template>

<script>
export default {
  data() {
    return { count: 0 }
  }
}
</script>

<style scoped>
.test {
  padding: 50px;
  text-align: center;
  color: white;
  background: #0c1221;
  min-height: 100vh;
}

h1 {
  color: #60a5fa;
}
</style>
