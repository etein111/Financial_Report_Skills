<template>
  <div class="users-page">
    <div class="page-header">
      <h1>User Management</h1>
      <button @click="showCreateDialog = true" class="btn-primary">
        Add User
      </button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by email or name..."
        class="search-input"
        @input="handleSearch"
      />
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="users.length === 0" class="empty">
      <p>No users found.</p>
      <button @click="showCreateDialog = true" class="btn-primary">
        Add First User
      </button>
    </div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Email</th>
          <th>Name</th>
          <th>Role</th>
          <th>Status</th>
          <th>Last Sign In</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.email }}</td>
          <td>{{ user.full_name || '-' }}</td>
          <td>
            <span :class="['role-badge', user.role]">
              {{ user.role.toUpperCase() }}
            </span>
          </td>
          <td>
            <span :class="['status-badge', user.banned ? 'banned' : 'active']">
              {{ user.banned ? 'Disabled' : 'Active' }}
            </span>
          </td>
          <td>{{ formatDate(user.last_sign_in_at) }}</td>
          <td class="actions">
            <button @click="editUser(user)" class="btn-icon" title="Edit">✏️</button>
            <button @click="changePassword(user)" class="btn-icon" title="Change Password">🔑</button>
            <button @click="toggleStatus(user)" :class="['btn-icon', user.banned ? 'btn-success' : 'btn-warning']" :title="user.banned ? 'Enable' : 'Disable'">
              {{ user.banned ? '✅' : '⏸' }}
            </button>
            <button @click="confirmDelete(user)" class="btn-icon btn-danger" title="Delete">🗑️</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create/Edit Dialog -->
    <div v-if="showCreateDialog || editingUser" class="dialog-overlay" @click.self="closeDialog">
      <div class="dialog">
        <h2>{{ editingUser ? 'Edit User' : 'Add User' }}</h2>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="email">Email *</label>
            <input
              id="email"
              v-model="formData.email"
              type="email"
              required
              placeholder="user@example.com"
              class="input"
              :disabled="editingUser !== null"
            />
          </div>

          <div class="form-group">
            <label for="full_name">Full Name</label>
            <input
              id="full_name"
              v-model="formData.full_name"
              type="text"
              placeholder="e.g. John Doe"
              class="input"
            />
          </div>

          <div class="form-group">
            <label for="password">Password *</label>
            <input
              id="password"
              v-model="formData.password"
              type="password"
              :required="!editingUser"
              :placeholder="editingUser ? 'Leave empty to keep current' : 'Enter password'"
              minlength="6"
              class="input"
            />
          </div>

          <div class="form-group">
            <label for="role">Role *</label>
            <select id="role" v-model="formData.role" required class="input">
              <option value="analyst">Analyst</option>
              <option value="sa">SA (Supervisor)</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div class="dialog-actions">
            <button type="button" @click="closeDialog" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary">
              {{ editingUser ? 'Update' : 'Create' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Change Password Dialog -->
    <div v-if="showPasswordDialog && selectedUser" class="dialog-overlay" @click.self="closePasswordDialog">
      <div class="dialog">
        <h2>Change Password</h2>
        <p class="dialog-description">Change password for <strong>{{ selectedUser.email }}</strong></p>
        <form @submit.prevent="handlePasswordChange">
          <div class="form-group">
            <label for="new_password">New Password *</label>
            <input
              id="new_password"
              v-model="passwordForm.new_password"
              type="password"
              required
              minlength="6"
              placeholder="Enter new password"
              class="input"
            />
          </div>

          <div class="dialog-actions">
            <button type="button" @click="closePasswordDialog" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary">Change Password</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog && userToDelete" class="dialog-overlay" @click.self="closeDeleteDialog">
      <div class="dialog dialog-small">
        <h2>Confirm Delete</h2>
        <p>Are you sure you want to delete user <strong>{{ userToDelete.email }}</strong>?</p>
        <p class="warning">This action cannot be undone.</p>
        <div class="dialog-actions">
          <button @click="closeDeleteDialog" class="btn-secondary">Cancel</button>
          <button @click="executeDelete" class="btn-danger">Delete</button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <div v-if="toast.show" :class="['toast', toast.type]">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import apiClient from '@/api/client'

interface User {
  id: string
  email: string
  full_name?: string
  role: 'admin' | 'sa' | 'analyst'
  banned: boolean
  created_at: string
  last_sign_in_at?: string
}

const loading = ref(false)
const error = ref('')
const users = ref<User[]>([])
const searchQuery = ref('')

// Dialog states
const showCreateDialog = ref(false)
const editingUser = ref<User | null>(null)
const showPasswordDialog = ref(false)
const showDeleteDialog = ref(false)
const selectedUser = ref<User | null>(null)
const userToDelete = ref<User | null>(null)

// Form data
const formData = reactive({
  email: '',
  full_name: '',
  password: '',
  role: 'analyst' as 'admin' | 'sa' | 'analyst'
})

const passwordForm = reactive({
  new_password: ''
})

// Toast notification
const toast = reactive({
  show: false,
  message: '',
  type: 'success' as 'success' | 'error'
})

// Load users
const loadUsers = async (search = '') => {
  loading.value = true
  error.value = ''

  try {
    const params = search ? { search } : {}
    const response = await apiClient.get('/api/users', { params })
    users.value = response.data.data || []
  } catch (err: any) {
    error.value = 'Failed to load users'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Search
const handleSearch = () => {
  loadUsers(searchQuery.value)
}

// Format date
const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleDateString()
}

// Open create dialog
const openCreateDialog = () => {
  editingUser.value = null
  formData.email = ''
  formData.full_name = ''
  formData.password = ''
  formData.role = 'analyst'
  showCreateDialog.value = true
}

// Edit user
const editUser = (user: User) => {
  editingUser.value = user
  formData.email = user.email
  formData.full_name = user.full_name || ''
  formData.password = '' // Don't pre-fill password
  formData.role = user.role
  showCreateDialog.value = true
}

// Close dialog
const closeDialog = () => {
  showCreateDialog.value = false
  editingUser.value = null
  formData.email = ''
  formData.full_name = ''
  formData.password = ''
  formData.role = 'analyst'
}

// Submit form (create or update)
const handleSubmit = async () => {
  try {
    if (editingUser.value) {
      // Update user
      await apiClient.put(`/api/users/${editingUser.value.id}`, {
        email: formData.email,
        full_name: formData.full_name
      })
      showToast('User updated successfully', 'success')
    } else {
      // Create user
      await apiClient.post('/api/users', {
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        role: formData.role
      })
      showToast('User created successfully', 'success')
    }

    closeDialog()
    loadUsers(searchQuery.value)
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || 'Operation failed'
    showToast(errorMsg, 'error')
  }
}

// Change password
const changePassword = (user: User) => {
  selectedUser.value = user
  passwordForm.new_password = ''
  showPasswordDialog.value = true
}

const closePasswordDialog = () => {
  showPasswordDialog.value = false
  selectedUser.value = null
  passwordForm.new_password = ''
}

const handlePasswordChange = async () => {
  if (!selectedUser.value) return

  try {
    await apiClient.put(`/api/users/${selectedUser.value.id}/password`, {
      new_password: passwordForm.new_password
    })
    showToast('Password changed successfully', 'success')
    closePasswordDialog()
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || 'Failed to change password'
    showToast(errorMsg, 'error')
  }
}

// Toggle user status (enable/disable)
const toggleStatus = async (user: User) => {
  try {
    await apiClient.put(`/api/users/${user.id}/toggle-status`)
    const action = user.banned ? 'enabled' : 'disabled'
    showToast(`User ${action} successfully`, 'success')
    loadUsers(searchQuery.value)
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || 'Failed to update status'
    showToast(errorMsg, 'error')
  }
}

// Confirm delete
const confirmDelete = (user: User) => {
  userToDelete.value = user
  showDeleteDialog.value = true
}

const closeDeleteDialog = () => {
  showDeleteDialog.value = false
  userToDelete.value = null
}

// Execute delete
const executeDelete = async () => {
  if (!userToDelete.value) return

  try {
    await apiClient.delete(`/api/users/${userToDelete.value.id}`)
    showToast('User deleted successfully', 'success')
    closeDeleteDialog()
    loadUsers(searchQuery.value)
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || 'Failed to delete user'
    showToast(errorMsg, 'error')
  }
}

// Show toast notification
const showToast = (message: string, type: 'success' | 'error') => {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 3000)
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-page {
  min-height: 100vh;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0;
}

.search-bar {
  margin-bottom: 1.5rem;
}

.search-input {
  width: 100%;
  max-width: 400px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.loading, .error, .empty {
  text-align: center;
  padding: 3rem;
  color: #94a3b8;
}

.error {
  color: #fca5a5;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  overflow: hidden;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.data-table th {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 500;
  color: #cbd5e1;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  color: #e2e8f0;
  font-size: 14px;
}

.data-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.role-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.role-badge.admin {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.role-badge.sa {
  background: rgba(234, 179, 8, 0.2);
  color: #fcd34d;
}

.role-badge.analyst {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.status-badge.inactive,
.status-badge.banned {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px 20px;
  color: #cbd5e1;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 10px 20px;
  color: #fca5a5;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.2);
}

.btn-icon {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 6px 10px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 16px;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-icon.btn-warning {
  color: #fbbf24;
}

.btn-icon.btn-success {
  color: #4ade80;
}

.btn-icon.btn-danger {
  color: #fca5a5;
}

.btn-icon.btn-danger:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.dialog {
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

.dialog h2 {
  margin: 0 0 20px 0;
  color: #f1f5f9;
  font-size: 20px;
  font-weight: 600;
}

.dialog-description {
  color: #94a3b8;
  margin-bottom: 20px;
}

.warning {
  color: #fca5a5;
  font-size: 14px;
  margin-top: 8px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
}

.input {
  width: 100%;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #ffffff;
  font-size: 14px;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* Toast notification */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
  z-index: 2000;
}

.toast.success {
  background: rgba(34, 197, 94, 0.9);
}

.toast.error {
  background: rgba(239, 68, 68, 0.9);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
