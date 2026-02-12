<template>
  <div
    v-if="!isAdminOnly || isAdmin"
    @click="handleClick"
    class="card"
    :class="{ 'card-coming-soon': isComingSoon, 'card-clickable': url && !isComingSoon }"
  >
    <div class="card-icon">{{ icon }}</div>
    <div class="card-content">
      <h3 class="card-title">{{ title }}</h3>
      <p class="card-description">{{ description }}</p>
      <span v-if="isComingSoon" class="card-badge">Coming Soon</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'

interface Props {
  title: string
  description: string
  icon: string
  url?: string
  comingSoon?: boolean
  adminOnly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  url: '',
  comingSoon: false,
  adminOnly: false
})

const { userState } = useAuth()
const router = useRouter()

const isComingSoon = computed(() => props.comingSoon)
const isAdmin = computed(() => userState.value?.role === 'admin')

const handleClick = () => {
  if (props.url && !isComingSoon.value) {
    router.push(props.url)
  }
}
</script>

<style scoped>
.card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.card-clickable {
  cursor: pointer;
}

.card-clickable:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(96, 165, 250, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.card-coming-soon {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-icon {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #f1f5f9;
}

.card-description {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
  line-height: 1.4;
}

.card-badge {
  display: inline-block;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  color: #60a5fa;
  margin-top: 8px;
}
</style>
