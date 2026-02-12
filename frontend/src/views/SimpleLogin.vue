<template>
  <div class="simple-login">
    <h1>Neolyst Login</h1>
    <form @submit.prevent="handleSubmit">
      <div>
        <label>Email:</label>
        <input v-model="email" type="email" required />
      </div>
      <div>
        <label>Password:</label>
        <input v-model="password" type="password" required />
      </div>
      <button type="submit">Login</button>
    </form>
    <p v-if="message" :style="{ color: messageColor }">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const email = ref('admin@neolyst.com')
const password = ref('Admin123')
const message = ref('')
const messageColor = ref('white')

const handleSubmit = async () => {
  message.value = 'Logging in...'
  messageColor.value = '#94a3b8'

  try {
    const response = await fetch('http://127.0.0.1:8001/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.value,
        password: password.value
      })
    })

    const data = await response.json()

    if (data.success) {
      message.value = 'Login successful!'
      messageColor.value = '#4ade80'
      localStorage.setItem('auth_token', data.data.token)
      localStorage.setItem('user_info', JSON.stringify(data.data.user))

      setTimeout(() => {
        window.location.href = '/desktop'
      }, 500)
    } else {
      message.value = data.message || 'Login failed'
      messageColor.value = '#fca5a5'
    }
  } catch (error) {
    message.value = 'Network error'
    messageColor.value = '#fca5a5'
    console.error('Login error:', error)
  }
}
</script>

<style scoped>
.simple-login {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(to bottom, #0c1221 0%, #09090b 50%, #020617 100%);
  color: white;
  padding: 20px;
}

h1 {
  color: #60a5fa;
  margin-bottom: 30px;
}

form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: rgba(15, 23, 42, 0.8);
  padding: 40px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  min-width: 300px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
}

input {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: white;
  font-size: 14px;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

button {
  padding: 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

button:hover {
  opacity: 0.9;
}
</style>
