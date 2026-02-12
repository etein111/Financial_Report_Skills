<template>
  <div class="regions-page">
    <div class="page-header">
      <h1>Regions</h1>
      <button v-if="canManageRegions" @click="showCreateDialog = true" class="btn-primary">
        Add Region
      </button>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else-if="regions.length === 0" class="empty">
      <p>No regions found.</p>
      <button v-if="canManageRegions" @click="showCreateDialog = true" class="btn-primary">
        Add First Region
      </button>
    </div>

    <table v-else class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Code</th>
          <th>Created</th>
          <th v-if="canManageRegions">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="region in regions" :key="region.id">
          <td>{{ region.name }}</td>
          <td><code>{{ region.code }}</code></td>
          <td>{{ formatDate(region.created_at) }}</td>
          <td v-if="canManageRegions" class="actions">
            <button @click="editRegion(region)" class="btn-icon" title="Edit">✏️</button>
            <button @click="confirmDelete(region)" class="btn-icon btn-danger" title="Delete">🗑️</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create/Edit Dialog -->
    <div v-if="showCreateDialog || editingRegion" class="dialog-overlay" @click.self="closeDialog">
      <div class="dialog">
        <h2>{{ editingRegion ? 'Edit Region' : 'Add Region' }}</h2>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="name">Name</label>
            <input
              id="name"
              v-model="formData.name"
              type="text"
              required
              placeholder="e.g. Hong Kong"
              class="input"
            />
          </div>
          <div class="form-group">
            <label for="code">Code</label>
            <input
              id="code"
              v-model="formData.code"
              type="text"
              required
              placeholder="e.g. HK"
              maxlength="10"
              class="input"
            />
          </div>
          <div v-if="formError" class="error-message">{{ formError }}</div>
          <div class="dialog-actions">
            <button type="button" @click="closeDialog" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="deletingRegion" class="dialog-overlay" @click.self="deletingRegion = null">
      <div class="dialog dialog-small">
        <h2>Confirm Delete</h2>
        <p>Are you sure you want to delete region <strong>{{ deletingRegion.name }}</strong>?</p>
        <div v-if="deleteError" class="error-message">{{ deleteError }}</div>
        <div class="dialog-actions">
          <button @click="deletingRegion = null" class="btn-secondary">Cancel</button>
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
import { getRegions, createRegion, updateRegion, deleteRegion, type Region } from '@/api/regions'
import { usePermission } from '@/composables/usePermission'

const { canManageRegions } = usePermission()

const regions = ref<Region[]>([])
const loading = ref(true)
const error = ref('')

const showCreateDialog = ref(false)
const editingRegion = ref<Region | null>(null)
const deletingRegion = ref<Region | null>(null)

const formData = ref({ name: '', code: '' })
const formError = ref('')
const deleteError = ref('')
const submitting = ref(false)

onMounted(async () => {
  await loadRegions()
})

async function loadRegions() {
  loading.value = true
  error.value = ''
  try {
    regions.value = await getRegions()
  } catch (err: unknown) {
    error.value = 'Failed to load regions. Please try again.'
  } finally {
    loading.value = false
  }
}

function editRegion(region: Region) {
  editingRegion.value = region
  formData.value = { name: region.name, code: region.code }
  formError.value = ''
}

function confirmDelete(region: Region) {
  deletingRegion.value = region
  deleteError.value = ''
}

function closeDialog() {
  showCreateDialog.value = false
  editingRegion.value = null
  formData.value = { name: '', code: '' }
  formError.value = ''
}

async function handleSubmit() {
  formError.value = ''
  submitting.value = true

  try {
    if (editingRegion.value) {
      await updateRegion(editingRegion.value.id, formData.value)
    } else {
      await createRegion(formData.value)
    }
    await loadRegions()
    closeDialog()
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      formError.value = axiosError.response?.data?.detail || 'Failed to save region.'
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
    await deleteRegion(deletingRegion.value!.id)
    await loadRegions()
    deletingRegion.value = null
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      deleteError.value = axiosError.response?.data?.detail || 'Failed to delete region.'
    } else {
      deleteError.value = 'Network error. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}
</script>

<style scoped>
.regions-page {
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

code {
  background: rgba(255, 255, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
  color: #60a5fa;
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
}

.dialog {
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 32px;
  width: 100%;
  max-width: 400px;
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
</style>
