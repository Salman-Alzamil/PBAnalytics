<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Manage Contacts</h1>
        <p class="page-subtitle">Add contacts manually or upload CSV files</p>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- Add Contact Form -->
    <div class="section-card">
      <h3 class="section-title">Add Contact</h3>
      <form @submit.prevent="submitContact" class="contact-form">
        <div class="form-row">
          <div class="form-field">
            <label>First Name <span class="required">*</span></label>
            <input v-model="form.first_name" placeholder="e.g. Salman" required />
          </div>
          <div class="form-field">
            <label>Last Name <span class="required">*</span></label>
            <input v-model="form.last_name" placeholder="e.g. Al-Zamil" required />
          </div>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label>Phone <span class="required">*</span></label>
            <input v-model="form.phone" placeholder="+966XXXXXXXXX" required />
          </div>
          <div class="form-field">
            <label>Email <span class="required">*</span></label>
            <input v-model="form.email" type="email" placeholder="name@example.com" required />
          </div>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label>City</label>
            <input v-model="form.city" placeholder="e.g. Riyadh" />
          </div>
          <div class="form-field form-field--submit">
            <button type="submit" :disabled="submitting">
              <span v-if="submitting" class="btn-spinner" />
              {{ submitting ? 'Adding…' : 'Add Contact' }}
            </button>
          </div>
        </div>
        <div v-if="contactAddResult" class="form-result" :class="contactAddResult.type === 'success' ? 'form-result--success' : 'form-result--error'">
          {{ contactAddResult.message }}
        </div>
      </form>
    </div>

    <!-- CSV Uploads -->
    <div class="upload-grid">
      <div class="upload-box">
        <div>
          <h3>Contacts CSV</h3>
          <p style="font-size:12px;color:var(--text-muted);margin-top:4px">
            Upload a CSV file containing contact records
          </p>
        </div>
        <div
          class="drop-zone"
          :class="{ 'drop-active': contactsDragActive, 'has-file': !!contactsFile }"
          @dragover.prevent="contactsDragActive = true"
          @dragleave.prevent="contactsDragActive = false"
          @drop.prevent="onContactsDrop"
          @click="$refs.contactsInput.click()"
        >
          <input ref="contactsInput" type="file" accept=".csv" style="display:none" @change="handleContactsFile" />
          <div v-if="contactsFile" class="drop-file-name">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            {{ contactsFile.name }}
          </div>
          <div v-else class="drop-hint-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Drop CSV or click to upload</span>
          </div>
        </div>
        <button @click="uploadContacts" :disabled="!contactsFile || loadingContacts">
          {{ loadingContacts ? 'Uploading…' : 'Upload Contacts' }}
        </button>
        <div v-if="contactsResult" class="upload-result">{{ contactsResult }}</div>
      </div>

      <div class="upload-box">
        <div>
          <h3>Calls CSV</h3>
          <p style="font-size:12px;color:var(--text-muted);margin-top:4px">
            Upload a CSV file containing call history records
          </p>
        </div>
        <div
          class="drop-zone"
          :class="{ 'drop-active': callsDragActive, 'has-file': !!callsFile }"
          @dragover.prevent="callsDragActive = true"
          @dragleave.prevent="callsDragActive = false"
          @drop.prevent="onCallsDrop"
          @click="$refs.callsInput.click()"
        >
          <input ref="callsInput" type="file" accept=".csv" style="display:none" @change="handleCallsFile" />
          <div v-if="callsFile" class="drop-file-name">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            {{ callsFile.name }}
          </div>
          <div v-else class="drop-hint-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Drop CSV or click to upload</span>
          </div>
        </div>
        <button @click="uploadCalls" :disabled="!callsFile || loadingCalls">
          {{ loadingCalls ? 'Uploading…' : 'Upload Calls' }}
        </button>
        <div v-if="callsResult" class="upload-result">{{ callsResult }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { api } from '../api'

const error = ref('')

// ── Add contact form ──────────────────────────────────────────
const form = reactive({ first_name: '', last_name: '', phone: '', email: '', city: '' })
const submitting = ref(false)
const contactAddResult = ref(null)

const submitContact = async () => {
  submitting.value = true
  contactAddResult.value = null
  error.value = ''
  try {
    await api.createContact({
      first_name: form.first_name,
      last_name:  form.last_name,
      phone:      form.phone,
      email:      form.email,
      city:       form.city || undefined,
    })
    contactAddResult.value = { type: 'success', message: `${form.first_name} ${form.last_name} added successfully` }
    form.first_name = ''
    form.last_name  = ''
    form.phone      = ''
    form.email      = ''
    form.city       = ''
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map(d => d.msg).join(', ')
      : detail || 'Failed to add contact'
    contactAddResult.value = { type: 'error', message: msg }
  } finally {
    submitting.value = false
  }
}

// ── CSV uploads ───────────────────────────────────────────────
const contactsFile    = ref(null)
const callsFile       = ref(null)
const contactsResult  = ref('')
const callsResult     = ref('')
const loadingContacts = ref(false)
const loadingCalls    = ref(false)
const contactsDragActive = ref(false)
const callsDragActive    = ref(false)

const handleContactsFile = (e) => { contactsFile.value = e.target.files[0] }
const handleCallsFile    = (e) => { callsFile.value    = e.target.files[0] }

const onContactsDrop = (e) => {
  contactsDragActive.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.csv')) contactsFile.value = file
}
const onCallsDrop = (e) => {
  callsDragActive.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.csv')) callsFile.value = file
}

const uploadContacts = async () => {
  loadingContacts.value = true; error.value = ''; contactsResult.value = ''
  try {
    const res = await api.importContacts(contactsFile.value)
    contactsResult.value = res.data.message || `Imported ${res.data.contacts_imported || 0} contacts`
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to import contacts'
  } finally {
    loadingContacts.value = false
  }
}

const uploadCalls = async () => {
  loadingCalls.value = true; error.value = ''; callsResult.value = ''
  try {
    const res = await api.importCalls(callsFile.value)
    callsResult.value = res.data.message || `Imported ${res.data.calls_imported || 0} calls`
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to import calls'
  } finally {
    loadingCalls.value = false
  }
}
</script>

<style scoped>
.section-card {
  background: var(--bg-el);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 20px 24px 24px;
  margin-bottom: 24px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-strong);
  margin-bottom: 16px;
  letter-spacing: -0.02em;
}

.contact-form { display: flex; flex-direction: column; gap: 14px; }

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 600px) {
  .form-row { grid-template-columns: 1fr; }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-field label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
  font-family: var(--mono);
}

.required { color: var(--danger); }

.form-field input {
  height: 36px;
  padding: 0 10px;
  font-size: 13px;
}

.form-field--submit {
  justify-content: flex-end;
}

.form-field--submit button {
  align-self: flex-end;
  height: 36px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.form-result {
  font-size: 12px;
  padding: 9px 13px;
  border-radius: var(--radius);
  border: 1px solid;
}

.form-result--success {
  background: rgba(34, 197, 94, 0.07);
  border-color: rgba(34, 197, 94, 0.2);
  color: var(--success);
}

.form-result--error {
  background: rgba(244, 63, 94, 0.07);
  border-color: rgba(244, 63, 94, 0.2);
  color: var(--danger);
}

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(0, 0, 0, 0.2);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

.drop-zone {
  border: 1px dashed var(--line-mid);
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  min-height: 72px;
  user-select: none;
}
.drop-zone:hover,
.drop-zone.drop-active {
  border-color: var(--accent);
  background: var(--accent-dim);
}
.drop-file-name {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-family: var(--mono);
  color: var(--accent);
}
.drop-hint-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
  pointer-events: none;
}
</style>
