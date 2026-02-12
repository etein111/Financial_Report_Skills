<template>
  <div class="analyst-info-page">
    <div class="page-header">
      <h1>Analyst Information</h1>
      <button v-if="canManageAnalystInfo" @click="showCreateDialog = true" class="btn-primary">
        Add Analyst
      </button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search by name or email..."
        class="search-input"
        @input="handleSearch"
      />
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="analysts.length === 0" class="empty">
      <p>No analyst information found.</p>
      <button v-if="canManageAnalystInfo" @click="showCreateDialog = true" class="btn-primary">
        Add First Analyst
      </button>
    </div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Region</th>
          <th>SFC</th>
          <th>Status</th>
          <th v-if="canManageAnalystInfo">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="analyst in analysts" :key="analyst.id">
          <td>
            <div class="name-cell">
              <div class="primary-name">{{ analyst.full_name }}</div>
              <div v-if="analyst.chinese_name" class="secondary-name">{{ analyst.chinese_name }}</div>
            </div>
          </td>
          <td>{{ analyst.email }}</td>
          <td>{{ analyst.region?.name || '-' }}</td>
          <td><code>{{ analyst.sfc || '-' }}</code></td>
          <td>
            <span :class="['status-badge', analyst.is_active ? 'active' : 'inactive']">
              {{ analyst.is_active ? 'Active' : 'Inactive' }}
            </span>
          </td>
          <td v-if="canManageAnalystInfo" class="actions">
            <button @click="editAnalyst(analyst)" class="btn-icon" title="Edit">✏️</button>
            <button @click="confirmDelete(analyst)" class="btn-icon btn-danger" title="Delete">🗑️</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create/Edit Dialog -->
    <div v-if="showCreateDialog || editingAnalyst" class="dialog-overlay" @click.self="closeDialog">
      <div class="dialog dialog-large">
        <h2>{{ editingAnalyst ? 'Edit Analyst' : 'Add Analyst' }}</h2>
        <form @submit.prevent="handleSubmit">
          <div class="form-row">
            <div class="form-group">
              <label for="full_name">Full Name *</label>
              <input
                id="full_name"
                v-model="formData.full_name"
                type="text"
                required
                placeholder="e.g. John Smith"
                class="input"
              />
            </div>
            <div class="form-group">
              <label for="chinese_name">Chinese Name</label>
              <input
                id="chinese_name"
                v-model="formData.chinese_name"
                type="text"
                placeholder="e.g. 張三"
                class="input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="email">Email *</label>
            <input
              id="email"
              v-model="formData.email"
              type="email"
              required
              placeholder="e.g. john.smith@example.com"
              class="input"
              @blur="checkEmail"
            />
            <span v-if="emailStatus === 'exists'" class="field-error">Email already exists</span>
            <span v-else-if="emailStatus === 'checking'" class="field-info">Checking...</span>
            <span v-else-if="emailStatus === 'available'" class="field-success">Email available</span>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="suffix">Suffix</label>
              <input
                id="suffix"
                v-model="formData.suffix"
                type="text"
                placeholder="e.g. CFA, CPA"
                class="input"
              />
            </div>
            <div class="form-group">
              <label for="sfc">SFC License</label>
              <input
                id="sfc"
                v-model="formData.sfc"
                type="text"
                placeholder="e.g. ABC123"
                class="input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="region">Region</label>
            <select id="region" v-model="formData.region_id" class="input">
              <option value="">Select a region</option>
              <option v-for="region in availableRegions" :key="region.id" :value="region.id">
                {{ region.name }}
              </option>
            </select>
          </div>

          <div v-if="!editingAnalyst" class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="formData.is_active" />
              <span>Active</span>
            </label>
          </div>

          <div v-if="formError" class="error-message">{{ formError }}</div>
          <div class="dialog-actions">
            <button type="button" @click="closeDialog" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="submitting || emailStatus === 'exists'">
              {{ submitting ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="deletingAnalyst" class="dialog-overlay" @click.self="deletingAnalyst = null">
      <div class="dialog dialog-small">
        <h2>Confirm Delete</h2>
        <p>Are you sure you want to delete analyst <strong>{{ deletingAnalyst.full_name }}</strong>?</p>
        <div v-if="deleteError" class="error-message">{{ deleteError }}</div>
        <div class="dialog-actions">
          <button @click="deletingAnalyst = null" class="btn-secondary">Cancel</button>
          <button @click="handleDelete" class="btn-danger" :disabled="submitting">
            {{ submitting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getAnalysts,
  createAnalyst,
  updateAnalyst,
  deleteAnalyst,
  checkAnalystEmail,
  type Analyst
} from '@/api/analystInfo'
import { getRegions, type Region } from '@/api/regions'
import { usePermission } from '@/composables/usePermission'

const { canManageAnalystInfo } = usePermission()

const analysts = ref<Analyst[]>([])
const availableRegions = ref<Region[]>([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')

const showCreateDialog = ref(false)
const editingAnalyst = ref<Analyst | null>(null)
const deletingAnalyst = ref<Analyst | null>(null)

const formData = ref({
  full_name: '',
  chinese_name: '',
  email: '',
  suffix: '',
  sfc: '',
  region_id: '',
  is_active: true
})
const formError = ref('')
const deleteError = ref('')
const submitting = ref(false)
const emailStatus = ref<'idle' | 'checking' | 'exists' | 'available'>('idle')
let emailCheckTimer: number | null = null

onMounted(async () => {
  await Promise.all([loadAnalysts(), loadRegions()])
})

async function loadAnalysts(search?: string) {
  loading.value = true
  error.value = ''
  try {
    analysts.value = await getAnalysts(search)
  } catch (err: unknown) {
    error.value = 'Failed to load analysts. Please try again.'
  } finally {
    loading.value = false
  }
}

async function loadRegions() {
  try {
    availableRegions.value = await getRegions()
  } catch (err) {
    // Silently fail for regions
  }
}

function handleSearch() {
  loadAnalysts(searchQuery.value || undefined)
}

function editAnalyst(analyst: Analyst) {
  editingAnalyst.value = analyst
  formData.value = {
    full_name: analyst.full_name,
    chinese_name: analyst.chinese_name || '',
    email: analyst.email,
    suffix: analyst.suffix || '',
    sfc: analyst.sfc || '',
    region_id: analyst.region_id || '',
    is_active: analyst.is_active
  }
  formError.value = ''
  emailStatus.value = 'idle'
}

function confirmDelete(analyst: Analyst) {
  deletingAnalyst.value = analyst
  deleteError.value = ''
}

function closeDialog() {
  showCreateDialog.value = false
  editingAnalyst.value = null
  formData.value = {
    full_name: '',
    chinese_name: '',
    email: '',
    suffix: '',
    sfc: '',
    region_id: '',
    is_active: true
  }
  formError.value = ''
  emailStatus.value = 'idle'
}

async function checkEmail() {
  const email = formData.value.email.trim()
  if (!email || email === editingAnalyst.value?.email) {
    emailStatus.value = 'idle'
    return
  }

  emailStatus.value = 'checking'

  try {
    const result = await checkAnalystEmail(email)
    emailStatus.value = result.exists ? 'exists' : 'available'
  } catch {
    emailStatus.value = 'idle'
  }
}

async function handleSubmit() {
  formError.value = ''
  submitting.value = true

  try {
    if (editingAnalyst.value) {
      const updateData = { ...formData.value }
      delete updateData.is_active
      await updateAnalyst(editingAnalyst.value.id, updateData)
    } else {
      await createAnalyst(formData.value)
    }
    await loadAnalysts(searchQuery.value || undefined)
    closeDialog()
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      formError.value = axiosError.response?.data?.detail || 'Failed to save analyst.'
    } else {
      formError.value = 'Network error. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}

async function handleDelete() {
  deleteError.value = ''
  submitting.value = true

  try {
    await deleteAnalyst(deletingAnalyst.value!.id)
    await loadAnalysts(searchQuery.value || undefined)
    deletingAnalyst.value = null
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      deleteError.value = axiosError.response?.data?.detail || 'Failed to delete analyst.'
    } else {
      deleteError.value = 'Network error. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.analyst-info-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
}

.search-bar {
  margin-bottom: 24px;
}

.search-input {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: #ffffff;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.loading, .error, .empty {
  text-align: center;
  padding: 48px 24px;
  color: #94a3b8;
}

.error {
  color: #fca5a5;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  overflow: hidden;
}

thead {
  background: rgba(255, 255, 255, 0.05);
}

th {
  padding: 16px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

tbody tr {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.2s;
}

tbody tr:hover {
  background: rgba(255, 255, 255, 0.05);
}

td {
  padding: 16px;
  font-size: 14px;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.primary-name {
  font-weight: 500;
  color: #f1f5f9;
}

.secondary-name {
  font-size: 12px;
  color: #94a3b8;
}

code {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #60a5fa;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
}

.status-badge.inactive {
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
}

.actions {
  white-space: nowrap;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-icon:hover {
  opacity: 1;
}

.btn-danger:hover {
  color: #fca5a5;
}

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
  padding: 20px;
  overflow-y: auto;
}

.dialog {
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 32px;
  width: 100%;
  max-width: 500px;
}

.dialog-large {
  max-width: 600px;
}

.dialog-small {
  max-width: 360px;
}

.dialog h2 {
  margin: 0 0 24px 0;
  font-size: 20px;
}

.dialog p {
  color: #94a3b8;
  margin-bottom: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
  margin-bottom: 8px;
}

.input {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 14px;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #cbd5e1;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.field-error {
  display: block;
  font-size: 12px;
  color: #fca5a5;
  margin-top: 4px;
}

.field-info {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.field-success {
  display: block;
  font-size: 12px;
  color: #4ade80;
  margin-top: 4px;
}

.error-message {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 12px;
  color: #fca5a5;
  font-size: 13px;
  margin-bottom: 16px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.btn-primary, .btn-secondary, .btn-danger {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.2);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
