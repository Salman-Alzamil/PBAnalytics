<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Contacts</h1>
        <p class="page-subtitle">Manage and search your contacts</p>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="filter-bar">
      <input v-model="search" placeholder="Search by name, phone, email…" style="min-width:220px" />
      <input v-model="city"   placeholder="Filter by city" style="min-width:130px" />
      <select v-model="sortBy" style="min-width:140px">
        <option value="name_asc">Name A → Z</option>
        <option value="name_desc">Name Z → A</option>
        <option value="city_asc">City A → Z</option>
      </select>
      <button @click="applyFilters">Apply</button>
      <button class="ghost" @click="resetFilters">Reset</button>
    </div>

    <div class="table-wrap">
      <template v-if="loading">
        <div style="padding:12px 18px;display:flex;flex-direction:column;gap:8px">
          <div v-for="n in 8" :key="n" class="skeleton skeleton-row" style="border-radius:6px"></div>
        </div>
      </template>

      <template v-else>
        <div class="table-scroll">
          <table v-if="pageContacts.length">
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>City</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in pageContacts"
                :key="c.id"
                class="contact-row"
                @click="openContact(c)"
              >
                <td>
                  <div style="display:flex;align-items:center;gap:9px">
                    <img v-if="c.profile_picture_id" :src="`${API_URL}/ai/images/${c.profile_picture_id}`" class="t-avatar" style="object-fit: cover; border-radius: 50%;" />
                    <div v-else class="t-avatar" :style="nameAvatarStyle(fullName(c))">
                      {{ initials(fullName(c)) }}
                    </div>
                    <strong>{{ fullName(c) }}</strong>
                  </div>
                </td>
                <td class="mono" style="font-size:12px">{{ c.phone }}</td>
                <td class="muted" style="font-size:12px">{{ c.email }}</td>
                <td>{{ c.city || '—' }}</td>
                <td>
                  <span v-if="c.possible_duplicates || c.possible_duplicate" class="badge badge-orange">Duplicate</span>
                  <span v-else class="badge badge-green">OK</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <p>No contacts match your filters.</p>
          </div>
        </div>

        <div class="pager">
          <span class="pager-info">
            Page {{ page }} of {{ totalPages }} &nbsp;·&nbsp; {{ sortedContacts.length }} contacts
          </span>
          <div class="pager-btns">
            <button class="ghost" @click="prevPage" :disabled="page === 1">← Prev</button>
            <button class="ghost" @click="nextPage" :disabled="!hasNextPage">Next →</button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- ── Contact Drawer ──────────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="overlay">
      <div v-if="drawerOpen" class="drawer-overlay" @click="closeDrawer" />
    </Transition>

    <Transition name="drawer-slide">
      <div v-if="drawerOpen && selectedContact" class="contact-drawer" role="dialog">

        <!-- Header -->
        <div class="drawer-header">
          <span class="drawer-label">Contact Profile</span>
          <button class="ghost close-btn" @click="closeDrawer" title="Close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Identity -->
        <div class="drawer-identity">
          <img v-if="selectedContact.profile_picture_id" :src="`${API_URL}/ai/images/${selectedContact.profile_picture_id}`" class="drawer-avatar-lg" style="object-fit: cover; border-radius: 50%;" />
          <div v-else class="drawer-avatar-lg" :style="nameAvatarStyle(fullName(selectedContact))">
            {{ initials(fullName(selectedContact)) }}
          </div>
          <div>
            <h2 class="drawer-name">{{ fullName(selectedContact) }}</h2>
            <p class="drawer-phone">{{ selectedContact.phone }}</p>
            <span
              v-if="selectedContact.possible_duplicates || selectedContact.possible_duplicate"
              class="badge badge-orange"
            >Duplicate</span>
            <span v-else class="badge badge-green">OK</span>
          </div>
        </div>

        <!-- Details -->
        <div
          v-if="selectedContact.email || selectedContact.city"
          class="drawer-details"
        >
          <div v-if="selectedContact.email" class="detail-row">
            <span class="detail-label">Email</span>
            <span class="detail-val muted">{{ selectedContact.email }}</span>
          </div>
          <div v-if="selectedContact.city" class="detail-row">
            <span class="detail-label">City</span>
            <span class="detail-val">{{ selectedContact.city }}</span>
          </div>
        </div>

        <div class="drawer-sep" />

        <!-- Appearance Analysis -->
        <div class="drawer-section">
          <div class="section-head">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            Appearance Analysis
          </div>

          <!-- Drop zone -->
          <div
            class="drop-zone"
            :class="{ 'drop-active': dropActive, 'has-image': !!previewUrl }"
            @dragover.prevent="dropActive = true"
            @dragleave.prevent="dropActive = false"
            @drop.prevent="onFileDrop"
            @click="triggerFileInput"
          >
            <input
              ref="fileInput"
              type="file"
              accept="image/*"
              style="display:none"
              @change="onFileChange"
            />

            <template v-if="previewUrl">
              <img :src="previewUrl" class="drop-preview" alt="" />
              <div class="drop-hover-overlay">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Change image
              </div>
            </template>

            <div v-else class="drop-empty">
              <div class="drop-icon-wrap">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
              </div>
              <p class="drop-text">Drop image or click to upload</p>
              <p class="drop-hint">JPG · PNG · WEBP</p>
            </div>
          </div>

          <!-- Actions -->
          <div v-if="selectedFile" class="drop-actions">
            <button @click="analyze" :disabled="classifying" style="flex:1;justify-content:center">
              <span v-if="classifying" class="btn-spinner" />
              <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="m9 18 6-6-6-6"/>
              </svg>
              {{ classifying ? 'Analyzing…' : 'Analyze' }}
            </button>
            <button class="ghost" @click="clearImage" :disabled="classifying">Clear</button>
          </div>

          <!-- Result -->
          <Transition name="result-reveal">
            <div v-if="classifyResult && !classifying" class="classify-result" :class="`result-${resultStatus}`">
              <div class="result-icon-wrap">
                <svg v-if="resultStatus === 'danger'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M15 9 9 15M9 9l6 6"/>
                </svg>
                <svg v-else-if="resultStatus === 'warning'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <div class="result-body">
                <p class="result-msg">{{ resultMessage }}</p>
                <div class="conf-row">
                  <div class="conf-track">
                    <div class="conf-fill" :style="{ width: classifyResult.confidence + '%' }" />
                  </div>
                  <span class="conf-pct">{{ classifyResult.confidence.toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ── Toasts ──────────────────────────────────────────────── -->
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast-pop">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast-item"
          :class="`toast-${t.type}`"
        >
          <svg v-if="t.type === 'success'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <svg v-else-if="t.type === 'danger'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M15 9 9 15M9 9l6 6"/>
          </svg>
          <svg v-else-if="t.type === 'warning'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
import { api } from '../api'

// ── Contact list ───────────────────────────────────────────────
const allContacts   = ref([])
const search        = ref('')
const city          = ref('')
const sortBy        = ref('name_asc')
const appliedSortBy = ref('name_asc')
const page          = ref(1)
const perPage       = 10
const loading       = ref(false)
const error         = ref('')

const fullName = (c) => `${c.first_name} ${c.last_name}`

const initials = (name) =>
  (name || '?').split(' ').slice(0, 2).map(p => p[0]?.toUpperCase()).join('')

const PALETTE = [
  { bg: 'rgba(16,185,129,0.12)',  fg: '#10b981' },
  { bg: 'rgba(56,189,248,0.12)',  fg: '#38bdf8' },
  { bg: 'rgba(244,63,94,0.11)',   fg: '#f43f5e' },
  { bg: 'rgba(167,139,250,0.11)', fg: '#a78bfa' },
  { bg: 'rgba(245,158,11,0.12)',  fg: '#f59e0b' },
  { bg: 'rgba(34,197,94,0.11)',   fg: '#22c55e' },
]

const nameAvatarStyle = (name) => {
  const hash = (name || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const p = PALETTE[hash % PALETTE.length]
  return { background: p.bg, color: p.fg }
}

const sortedContacts = computed(() => {
  const list = [...allContacts.value]
  if (appliedSortBy.value === 'name_asc')  list.sort((a, b) => fullName(a).localeCompare(fullName(b)))
  if (appliedSortBy.value === 'name_desc') list.sort((a, b) => fullName(b).localeCompare(fullName(a)))
  if (appliedSortBy.value === 'city_asc')  list.sort((a, b) => (a.city || '').localeCompare(b.city || ''))
  return list
})

const totalPages   = computed(() => Math.max(1, Math.ceil(sortedContacts.value.length / perPage)))
const hasNextPage  = computed(() => page.value < totalPages.value)
const pageContacts = computed(() => {
  const start = (page.value - 1) * perPage
  return sortedContacts.value.slice(start, start + perPage)
})

const fetchContacts = async () => {
  loading.value = true; error.value = ''
  try {
    const res = await api.getContacts({
      search: search.value || undefined,
      city:   city.value   || undefined,
      page: 1, limit: 10000,
    })
    allContacts.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load contacts'
  } finally {
    loading.value = false
  }
}

const applyFilters = () => { appliedSortBy.value = sortBy.value; page.value = 1; fetchContacts() }
const resetFilters = () => { search.value = ''; city.value = ''; sortBy.value = 'name_asc'; appliedSortBy.value = 'name_asc'; page.value = 1; fetchContacts() }
const nextPage     = () => { if (hasNextPage.value) page.value++ }
const prevPage     = () => { if (page.value > 1) page.value-- }

onMounted(fetchContacts)

// ── Drawer ─────────────────────────────────────────────────────
const drawerOpen      = ref(false)
const selectedContact = ref(null)
const fileInput       = ref(null)
const dropActive      = ref(false)
const selectedFile    = ref(null)
const previewUrl      = ref(null)
const classifying     = ref(false)
const classifyResult  = ref(null)

function openContact(c) {
  selectedContact.value = c
  classifyResult.value  = null
  drawerOpen.value      = true
}

function closeDrawer() {
  drawerOpen.value = false
  setTimeout(() => {
    selectedContact.value = null
    clearImage()
  }, 300)
}

function triggerFileInput() {
  fileInput.value?.click()
}

function setFile(file) {
  if (!file || !file.type.startsWith('image/')) return
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value   = file
  previewUrl.value     = URL.createObjectURL(file)
  classifyResult.value = null
}

function onFileDrop(e)  { dropActive.value = false; setFile(e.dataTransfer?.files?.[0]) }
function onFileChange(e){ setFile(e.target?.files?.[0]) }

function clearImage() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value   = null
  previewUrl.value     = null
  classifyResult.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function analyze() {
  if (!selectedFile.value || classifying.value) return
  classifying.value    = true
  classifyResult.value = null
  try {
    const res = await api.classifyImage(selectedFile.value)
    classifyResult.value = res.data
    const { image_id, prediction, confidence } = res.data
    
    if (image_id && selectedContact.value) {
      await api.updateContactPicture(selectedContact.value.id, image_id)
      selectedContact.value.profile_picture_id = image_id
      // Update in allContacts array directly to avoid full refetch
      const idx = allContacts.value.findIndex(c => c.id === selectedContact.value.id)
      if (idx !== -1) allContacts.value[idx].profile_picture_id = image_id
    }

    if (confidence < 80) {
      addToast('warning', `Confidence too low (${confidence.toFixed(1)}%) — try a clearer photo`)
    } else if (prediction === 'not_human') {
      addToast('danger', 'This image does not contain a person')
    } else if (prediction === 'saudi_formal') {
      addToast('success', 'Person is wearing Saudi formal clothing')
    } else {
      addToast('info', 'Person is wearing casual clothing')
    }
  } catch {
    addToast('danger', 'Classification failed — please try again')
  } finally {
    classifying.value = false
  }
}

const resultStatus = computed(() => {
  if (!classifyResult.value) return null
  const { prediction, confidence } = classifyResult.value
  if (confidence < 80)                  return 'warning'
  if (prediction === 'not_human')       return 'danger'
  if (prediction === 'saudi_formal')    return 'success'
  return 'info'
})

const resultMessage = computed(() => {
  if (!classifyResult.value) return ''
  const { prediction, confidence } = classifyResult.value
  if (confidence < 80)                  return `Confidence too low (${confidence.toFixed(1)}%) — try a clearer photo`
  if (prediction === 'not_human')       return 'No person detected in this image'
  if (prediction === 'saudi_formal')    return 'Person is wearing Saudi formal clothing'
  return 'Person is wearing casual clothing'
})

// ── Toasts ─────────────────────────────────────────────────────
const toasts = ref([])
let _toastId = 0

function addToast(type, message) {
  const id = ++_toastId
  toasts.value.push({ id, type, message })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}
</script>

<style scoped>
/* ── Clickable rows ── */
.contact-row { cursor: pointer; }

/* ── Drawer overlay ── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 200;
}

/* ── Drawer panel ── */
.contact-drawer {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 440px;
  background: var(--bg-el);
  border-left: 1px solid var(--line-mid);
  z-index: 201;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

@media (max-width: 520px) {
  .contact-drawer { width: 100%; }
}

/* ── Drawer header ── */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: var(--bg-el);
  z-index: 1;
}

.drawer-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-family: var(--mono);
}

.close-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  display: grid;
  place-items: center;
  border-radius: 6px;
  flex-shrink: 0;
}

/* ── Identity block ── */
.drawer-identity {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 22px 20px 18px;
}

.drawer-avatar-lg {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 17px;
  font-weight: 700;
  flex-shrink: 0;
  letter-spacing: -0.02em;
  object-fit: cover;
  object-position: top center;
}

.drawer-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-strong);
  letter-spacing: -0.03em;
  line-height: 1.2;
  margin-bottom: 3px;
}

.drawer-phone {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--mono);
  margin-bottom: 8px;
}

/* ── Detail rows ── */
.drawer-details {
  padding: 0 20px 18px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  gap: 16px;
}

.detail-row:last-child { border-bottom: none; }

.detail-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-family: var(--mono);
  flex-shrink: 0;
}

.detail-val {
  font-size: 13px;
  color: var(--text-strong);
  text-align: right;
  word-break: break-word;
}

/* ── Separator ── */
.drawer-sep {
  height: 1px;
  background: var(--line);
}

/* ── Analysis section ── */
.drawer-section {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-family: var(--mono);
}

/* ── Drop zone ── */
.drop-zone {
  position: relative;
  border: 1px dashed var(--line-mid);
  border-radius: var(--radius-lg);
  cursor: pointer;
  overflow: hidden;
  min-height: 148px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, background 0.2s;
  user-select: none;
}

.drop-zone:hover { border-color: rgba(255,255,255,0.2); }

.drop-zone.drop-active {
  border-color: var(--accent);
  border-style: solid;
  background: var(--accent-dim);
}

.drop-zone.has-image {
  min-height: 200px;
  border-style: solid;
  border-color: var(--line-mid);
}

.drop-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 24px;
  text-align: center;
  pointer-events: none;
}

.drop-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--line-mid);
  display: grid;
  place-items: center;
  color: var(--text-muted);
  margin-bottom: 3px;
}

.drop-text {
  font-size: 13px;
  color: var(--text-strong);
  font-weight: 500;
}

.drop-hint {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--mono);
  letter-spacing: 0.06em;
}

.drop-preview {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.drop-hover-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.2s;
  letter-spacing: 0.01em;
}

.drop-zone.has-image:hover .drop-hover-overlay { opacity: 1; }

/* ── Drop actions ── */
.drop-actions {
  display: flex;
  gap: 8px;
}

/* ── Spinner ── */
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

/* ── Classification result ── */
.classify-result {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px 15px;
  border-radius: var(--radius);
  border: 1px solid;
}

.result-success {
  background: rgba(34, 197, 94, 0.07);
  border-color: rgba(34, 197, 94, 0.2);
  color: var(--success);
}

.result-danger {
  background: rgba(244, 63, 94, 0.07);
  border-color: rgba(244, 63, 94, 0.2);
  color: var(--danger);
}

.result-warning {
  background: rgba(245, 158, 11, 0.07);
  border-color: rgba(245, 158, 11, 0.2);
  color: var(--warning);
}

.result-info {
  background: rgba(56, 189, 248, 0.07);
  border-color: rgba(56, 189, 248, 0.2);
  color: var(--info);
}

.result-icon-wrap { flex-shrink: 0; padding-top: 1px; }

.result-body { flex: 1; min-width: 0; }

.result-msg {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: inherit;
  line-height: 1.4;
}

.conf-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conf-track {
  flex: 1;
  height: 3px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.conf-fill {
  height: 100%;
  background: currentColor;
  border-radius: 2px;
  opacity: 0.65;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.conf-pct {
  font-size: 10px;
  font-family: var(--mono);
  flex-shrink: 0;
  opacity: 0.75;
}

/* ── Toast stack ── */
.toast-stack {
  position: fixed;
  bottom: 24px;
  left: 92px;
  z-index: 400;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

@media (max-width: 900px) {
  .toast-stack {
    left: 16px;
    bottom: 16px;
  }
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 15px;
  border-radius: var(--radius);
  border: 1px solid;
  background: var(--bg-el);
  font-size: 12px;
  font-weight: 500;
  pointer-events: all;
  min-width: 260px;
  max-width: 340px;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.45);
  line-height: 1.4;
}

.toast-success { border-color: rgba(34, 197, 94, 0.22);  color: var(--success); }
.toast-danger  { border-color: rgba(244, 63, 94, 0.22);  color: var(--danger); }
.toast-warning { border-color: rgba(245, 158, 11, 0.22); color: var(--warning); }
.toast-info    { border-color: rgba(56, 189, 248, 0.22); color: var(--info); }

/* ── Transitions ── */
.overlay-enter-active,
.overlay-leave-active { transition: opacity 0.22s ease; }
.overlay-enter-from,
.overlay-leave-to { opacity: 0; }

.drawer-slide-enter-active { transition: transform 0.38s cubic-bezier(0.16, 1, 0.3, 1); }
.drawer-slide-leave-active { transition: transform 0.22s ease; }
.drawer-slide-enter-from,
.drawer-slide-leave-to { transform: translateX(100%); }

.result-reveal-enter-active { transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1); }
.result-reveal-leave-active { transition: opacity 0.18s ease; }
.result-reveal-enter-from { opacity: 0; transform: translateY(8px); }
.result-reveal-leave-to { opacity: 0; }

.toast-pop-enter-active { transition: all 0.32s cubic-bezier(0.16, 1, 0.3, 1); }
.toast-pop-leave-active { transition: all 0.22s ease; }
.toast-pop-enter-from { opacity: 0; transform: translateX(-16px) scale(0.96); }
.toast-pop-leave-to { opacity: 0; transform: translateX(-16px); }
</style>
