<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Import CSV</h1>
        <p class="page-subtitle">Upload contacts and call records from CSV files</p>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

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
import { ref } from 'vue'
import { api } from '../api'

const contactsFile    = ref(null)
const callsFile       = ref(null)
const contactsResult  = ref('')
const callsResult     = ref('')
const loadingContacts = ref(false)
const loadingCalls    = ref(false)
const error           = ref('')
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
