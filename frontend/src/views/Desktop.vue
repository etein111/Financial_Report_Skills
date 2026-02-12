<template>
  <div class="desktop-page">
    <header class="navbar">
      <div class="navbar-container">
        <div class="logo">Neolyst</div>
        <div class="user-info">
          <span class="welcome-text">Welcome, {{ displayName }}</span>
          <button @click="handleLogout" class="logout-button">Logout</button>
        </div>
      </div>
    </header>

    <main class="desktop-content">
      <div class="card-grid">
        <div class="card-group">
          <h2 class="group-title">Reports</h2>
          <DesktopCard
            title="Reports"
            description="View and manage reports"
            icon="📄"
            :coming-soon="true"
          />
          <DesktopCard
            title="New Report"
            description="Create a new report"
            icon="➕"
            :coming-soon="true"
          />
          <DesktopCard
            title="Report Review"
            description="Review pending reports"
            icon="✓"
            :coming-soon="true"
          />
          <DesktopCard
            title="Templates"
            description="Manage report templates"
            icon="📋"
            :coming-soon="true"
          />
        </div>

        <div class="card-group">
          <h2 class="group-title">MANAGEMENT</h2>
          <DesktopCard
            v-if="isAdmin"
            title="Users"
            description="Manage system users"
            icon="👥"
            url="/users"
          />
          <DesktopCard
            title="Analyst Info"
            description="View analyst information"
            icon="👤"
            url="/analyst-info"
            :admin-only="true"
          />
          <DesktopCard
            title="Coverage"
            description="Manage coverage areas"
            icon="🌍"
            :coming-soon="true"
          />
          <DesktopCard
            title="Sectors"
            description="Manage industry sectors"
            icon="🏢"
            :coming-soon="true"
          />
          <DesktopCard
            title="Regions"
            description="Manage regions"
            icon="📍"
            url="/regions"
            :admin-only="true"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/stores/auth'
import DesktopCard from '@/components/desktop/DesktopCard.vue'

const router = useRouter()
const { userState, logout } = useAuth()

const displayName = computed(() => {
  return userState.user?.full_name || userState.user?.email || 'User'
})

const isAdmin = computed(() => {
  return userState.user?.role === 'admin'
})

const handleLogout = () => {
  logout()
  router.push('/login')
}
</script>

<style scoped>
.desktop-page {
  min-height: 100vh;
}

.navbar {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #60a5fa 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.welcome-text {
  color: #e2e8f0;
  font-size: 14px;
}

.logout-button {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  padding: 6px 14px;
  color: #fca5a5;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-button:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
}

.desktop-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px 32px 24px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 32px;
}

.card-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-title {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  margin: 0 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
</style>
