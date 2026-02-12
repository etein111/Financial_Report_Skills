<template>
  <div class="login-page">
    <ParticleBackground />

    <div class="login-container">
      <div class="login-header">
        <h1 class="title">The Future is Now</h1>
        <p class="subtitle">Research Report Management System</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div class="form-group">
          <label for="email" class="label">Email</label>
          <input
            id="email"
            type="email"
            v-model="email"
            placeholder="Enter your email"
            required
            class="input"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="password" class="label">Password</label>
          <input
            id="password"
            type="password"
            v-model="password"
            placeholder="Enter your password"
            required
            minlength="6"
            class="input"
            :disabled="loading"
          />
        </div>

        <button type="submit" class="login-button" :disabled="loading || !isFormValid">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { login } from '@/api/auth'
import ParticleBackground from '@/components/common/ParticleBackground.vue'

const router = useRouter()
const { login: authLogin } = useAuth()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const isFormValid = computed(() => {
  return email.value.trim() !== '' && password.value.length >= 6
})

const handleLogin = async () => {
  error.value = ''

  if (!isFormValid.value) {
    error.value = 'Please fill in all fields correctly'
    return
  }

  loading.value = true

  try {
    const response = await login({
      email: email.value,
      password: password.value
    })

    if (response.success && response.data) {
      // 登录成功，保存 token 和用户信息
      authLogin(response.data.token, response.data.user)
      // 跳转到桌面
      router.push('/desktop')
    } else {
      error.value = response.message || 'Login failed'
    }
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      error.value = axiosError.response?.data?.detail || 'Login failed. Please try again.'
    } else {
      error.value = 'Network error. Please check your connection.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-container {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  margin: 20px;
  position: relative;
  z-index: 1;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #60a5fa 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 8px 0;
  line-height: 1.3;
}

.subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #ffffff;
  font-size: 14px;
  transition: all 0.2s;
}

/* 覆盖浏览器自动填充样式 */
.input:-webkit-autofill,
.input:-webkit-autofill:hover,
.input:-webkit-autofill:focus {
  -webkit-text-fill-color: #ffffff;
  -webkit-box-shadow: 0 0 0 30px rgba(255, 255, 255, 0.05) inset;
  transition: background-color 5000s ease-in-out 0s;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: rgba(255, 255, 255, 0.08);
}

.input:focus:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 30px rgba(255, 255, 255, 0.08) inset, 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input::placeholder {
  color: #64748b;
}

.login-button {
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  border: none;
  border-radius: 8px;
  padding: 14px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.login-button:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

.login-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 12px;
  color: #fca5a5;
  font-size: 13px;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
