<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Face Search</h1>
        <p class="page-subtitle">Find contacts by face or identify people in a group photo</p>
      </div>
      <button class="ghost precompute-btn" @click="runPrecompute" :disabled="precomputing">
        <span v-if="precomputing" class="btn-spinner" />
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0"/>
          <path d="M12 8v4l3 3"/>
        </svg>
        {{ precomputing ? 'Indexing…' : 'Index Faces' }}
      </button>
    </div>

    <div v-if="indexStale" class="precompute-banner banner-warn">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      Face index is out of date — click <strong>Index Faces</strong> before searching.
    </div>

    <div v-if="precomputeResult" class="precompute-banner" :class="precomputeResult.errors?.length ? 'banner-warn' : 'banner-ok'">
      Indexed {{ precomputeResult.success }} / {{ precomputeResult.processed }} contacts
      <span v-if="precomputeResult.skipped"> · {{ precomputeResult.skipped }} skipped (no clear face)</span>
      <button class="ghost banner-close" @click="precomputeResult = null">✕</button>
    </div>

    <div v-if="singleResult && singleResult.index_stale && !searching" class="precompute-banner banner-warn" style="margin-bottom:12px">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      Result may be wrong — index is stale. Click <strong>Index Faces</strong> then search again.
    </div>

    <!-- ── Tabs ─────────────────────────────────────────── -->
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: tab === 'single' }" @click="switchTab('single')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
        </svg>
        Find Person
      </button>
      <button class="tab-btn" :class="{ active: tab === 'group' }" @click="switchTab('group')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="9" cy="7" r="3"/><circle cx="17" cy="7" r="3"/>
          <path d="M1 20c0-3 3-6 8-6s8 3 8 6"/><path d="M17 14c3 0 6 2 6 6"/>
        </svg>
        Group Photo
      </button>
    </div>

    <!-- ════════════════════════════════════════════════════
         FEATURE 1 — Single face search
         ════════════════════════════════════════════════════ -->
    <div v-if="tab === 'single'" class="feature-panel">
      <div class="panel-left">
        <div
          class="drop-zone"
          :class="{ 'drop-active': singleDrop, 'has-image': !!singlePreview }"
          @dragover.prevent="singleDrop = true"
          @dragleave.prevent="singleDrop = false"
          @drop.prevent="onSingleDrop"
          @click="singleInput?.click()"
        >
          <input ref="singleInput" type="file" accept="image/*" style="display:none" @change="onSingleChange" />

          <template v-if="singlePreview">
            <img :src="singlePreview" class="drop-preview" />
            <div class="drop-hover-overlay">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              Change image
            </div>
          </template>

          <div v-else class="drop-empty">
            <div class="drop-icon-wrap">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
              </svg>
            </div>
            <p class="drop-text">Drop a photo or click to upload</p>
            <p class="drop-hint">One face only · JPG · PNG · WEBP</p>
          </div>
        </div>

        <div v-if="singleFile" class="drop-actions">
          <button @click="searchSingle" :disabled="searching" style="flex:1;justify-content:center">
            <span v-if="searching" class="btn-spinner" />
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            {{ searching ? 'Searching…' : 'Search' }}
          </button>
          <button class="ghost" @click="resetSingle" :disabled="searching">Clear</button>
        </div>
      </div>

      <!-- Result panel -->
      <div class="panel-right">
        <div v-if="!singleResult && !searching" class="result-placeholder">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            <circle cx="11" cy="9" r="2.5"/><path d="M7 16c0-2 1.8-3.5 4-3.5s4 1.5 4 3.5"/>
          </svg>
          <p>Upload a photo with a single face<br>to find a matching contact</p>
        </div>

        <div v-if="searching" class="result-placeholder">
          <span class="spinner-lg" />
          <p>Searching face database…</p>
        </div>

        <Transition name="result-reveal">
          <div v-if="singleResult && !searching">
            <!-- Error / no-match -->
            <div v-if="singleError" class="result-card result-danger">
              <div class="rc-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><path d="M15 9 9 15M9 9l6 6"/>
                </svg>
              </div>
              <div>
                <p class="rc-label">No match</p>
                <p class="rc-sub">{{ singleError }}</p>
              </div>
            </div>

            <!-- Match found -->
            <div v-else-if="singleResult.matched" class="result-card result-success">
              <div class="rc-avatar-wrap">
                <img
                  v-if="singleResult.contact.profile_picture_id"
                  :src="`${API_URL}/ai/images/${singleResult.contact.profile_picture_id}`"
                  class="rc-avatar"
                />
                <div v-else class="rc-avatar" :style="avatarStyle(fullName(singleResult.contact))">
                  {{ initials(fullName(singleResult.contact)) }}
                </div>
              </div>
              <div class="rc-body">
                <div class="rc-name-row">
                  <p class="rc-name">{{ fullName(singleResult.contact) }}</p>
                  <span v-if="singleResult.contact.possible_duplicates" class="rc-badge rc-badge-dup">Duplicate</span>
                </div>
                <p class="rc-phone mono">{{ singleResult.contact.phone }}</p>
                <p v-if="singleResult.contact.email" class="rc-detail muted">{{ singleResult.contact.email }}</p>
                <p v-if="singleResult.contact.city" class="rc-detail">{{ singleResult.contact.city }}</p>
                <p v-if="singleResult.contact.notes" class="rc-notes">{{ singleResult.contact.notes }}</p>
                <div class="sim-row">
                  <span class="sim-label">Similarity</span>
                  <div class="sim-track">
                    <div class="sim-fill" :style="{ width: (singleResult.similarity * 100) + '%' }" />
                  </div>
                  <span class="sim-pct">{{ (singleResult.similarity * 100).toFixed(1) }}%</span>
                </div>
                <RouterLink to="/contacts" class="rc-view-link">View in Contacts →</RouterLink>
              </div>
            </div>

            <!-- No match -->
            <div v-else class="result-card result-warn">
              <div class="rc-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </div>
              <div>
                <p class="rc-label">No match found</p>
                <p class="rc-sub">Best similarity was {{ (singleResult.similarity * 100).toFixed(1) }}% — below the 62% threshold</p>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- ════════════════════════════════════════════════════
         FEATURE 2 — Group photo
         ════════════════════════════════════════════════════ -->
    <div v-if="tab === 'group'" class="feature-panel">
      <!-- Upload zone (shown before analysis) -->
      <template v-if="!groupFaces">
        <div class="group-upload">
          <div
            class="drop-zone drop-zone-lg"
            :class="{ 'drop-active': groupDrop }"
            @dragover.prevent="groupDrop = true"
            @dragleave.prevent="groupDrop = false"
            @drop.prevent="onGroupDrop"
            @click="groupInput?.click()"
          >
            <input ref="groupInput" type="file" accept="image/*" style="display:none" @change="onGroupChange" />
            <div class="drop-empty">
              <div class="drop-icon-wrap">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="9" cy="7" r="3"/><circle cx="17" cy="7" r="3"/>
                  <path d="M1 20c0-3 3-6 8-6s8 3 8 6"/><path d="M17 14c3 0 6 2 6 6"/>
                </svg>
              </div>
              <p class="drop-text">Drop a group photo or click to upload</p>
              <p class="drop-hint">Multiple faces · JPG · PNG · WEBP</p>
            </div>
          </div>
          <div v-if="analyzing" class="analyzing-state">
            <span class="spinner-lg" />
            <p>Detecting faces…</p>
          </div>
        </div>
      </template>

      <!-- After analysis: photo with clickable face boxes + side panel -->
      <template v-else>
        <div class="group-workspace">
          <!-- Photo + face boxes -->
          <div class="photo-col">
            <div class="photo-wrapper" ref="photoWrapper">
              <img
                ref="groupImage"
                :src="groupPreview"
                class="group-photo"
                @load="onGroupImageLoad"
              />
              <div
                v-for="face in groupFaces"
                :key="face.face_index"
                class="face-box"
                :class="{
                  'face-box--selected': selectedFace?.face_index === face.face_index,
                  'face-box--identified': identifiedFaces[face.face_index]?.matched,
                  'face-box--no-match': identifiedFaces[face.face_index] && !identifiedFaces[face.face_index].matched
                }"
                :style="getFaceBoxStyle(face)"
                @click="clickFace(face)"
                :title="face.embedding ? 'Click to identify' : 'Face features unavailable'"
              >
                <span class="face-box__index">{{ face.face_index + 1 }}</span>
              </div>
            </div>
            <p class="photo-hint">
              {{ groupFaces.length }} face{{ groupFaces.length !== 1 ? 's' : '' }} detected · click any face to identify
            </p>
            <button class="ghost" style="margin-top:8px" @click="resetGroup">Upload different photo</button>
          </div>

          <!-- Identity panel -->
          <div class="id-panel">
            <div v-if="!selectedFace && !identifying" class="result-placeholder">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="9" cy="9" r="2"/><circle cx="16" cy="9" r="2"/>
                <path d="M6 15c0-2 1.5-3 3-3h6c1.5 0 3 1 3 3"/>
              </svg>
              <p>Click a face in the photo<br>to identify them</p>
            </div>

            <div v-if="identifying" class="result-placeholder">
              <span class="spinner-lg" />
              <p>Identifying face {{ (selectedFace?.face_index ?? 0) + 1 }}…</p>
            </div>

            <Transition name="result-reveal">
              <div v-if="selectedFace && !identifying">
                <p class="id-face-label">Face {{ selectedFace.face_index + 1 }}</p>

                <!-- No embedding -->
                <div v-if="!selectedFace.embedding" class="result-card result-danger">
                  <div class="rc-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/><path d="M15 9 9 15M9 9l6 6"/>
                    </svg>
                  </div>
                  <div>
                    <p class="rc-label">Could not extract features</p>
                    <p class="rc-sub">Face is too small, blurry, or partially visible</p>
                  </div>
                </div>

                <!-- Match / no-match from identify call -->
                <template v-else-if="identifiedFaces[selectedFace.face_index]">
                  <div
                    v-if="identifiedFaces[selectedFace.face_index].matched"
                    class="result-card result-success"
                  >
                    <div class="rc-avatar-wrap">
                      <img
                        v-if="identifiedFaces[selectedFace.face_index].contact.profile_picture_id"
                        :src="`${API_URL}/ai/images/${identifiedFaces[selectedFace.face_index].contact.profile_picture_id}`"
                        class="rc-avatar"
                      />
                      <div v-else class="rc-avatar" :style="avatarStyle(fullName(identifiedFaces[selectedFace.face_index].contact))">
                        {{ initials(fullName(identifiedFaces[selectedFace.face_index].contact)) }}
                      </div>
                    </div>
                    <div class="rc-body">
                      <div class="rc-name-row">
                        <p class="rc-name">{{ fullName(identifiedFaces[selectedFace.face_index].contact) }}</p>
                        <span v-if="identifiedFaces[selectedFace.face_index].contact.possible_duplicates" class="rc-badge rc-badge-dup">Duplicate</span>
                      </div>
                      <p class="rc-phone mono">{{ identifiedFaces[selectedFace.face_index].contact.phone }}</p>
                      <p v-if="identifiedFaces[selectedFace.face_index].contact.email" class="rc-detail muted">
                        {{ identifiedFaces[selectedFace.face_index].contact.email }}
                      </p>
                      <p v-if="identifiedFaces[selectedFace.face_index].contact.city" class="rc-detail">
                        {{ identifiedFaces[selectedFace.face_index].contact.city }}
                      </p>
                      <p v-if="identifiedFaces[selectedFace.face_index].contact.notes" class="rc-notes">
                        {{ identifiedFaces[selectedFace.face_index].contact.notes }}
                      </p>
                      <div class="sim-row">
                        <span class="sim-label">Similarity</span>
                        <div class="sim-track">
                          <div class="sim-fill" :style="{ width: (identifiedFaces[selectedFace.face_index].similarity * 100) + '%' }" />
                        </div>
                        <span class="sim-pct">{{ (identifiedFaces[selectedFace.face_index].similarity * 100).toFixed(1) }}%</span>
                      </div>
                      <RouterLink to="/contacts" class="rc-view-link">View in Contacts →</RouterLink>
                    </div>
                  </div>

                  <div v-else class="result-card result-warn">
                    <div class="rc-icon">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                      </svg>
                    </div>
                    <div>
                      <p class="rc-label">Contact not found</p>
                      <p class="rc-sub">No contact matches this face above the 62% threshold</p>
                    </div>
                  </div>
                </template>
              </div>
            </Transition>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Shared helpers ────────────────────────────────────────────────────────────
const fullName = (c) => `${c.first_name} ${c.last_name}`
const initials = (name) =>
  (name || '?').split(' ').slice(0, 2).map(p => p[0]?.toUpperCase()).join('')

const PALETTE = [
  { bg: 'rgba(16,185,129,0.12)', fg: '#10b981' },
  { bg: 'rgba(56,189,248,0.12)', fg: '#38bdf8' },
  { bg: 'rgba(244,63,94,0.11)',  fg: '#f43f5e' },
  { bg: 'rgba(167,139,250,0.11)',fg: '#a78bfa' },
  { bg: 'rgba(245,158,11,0.12)', fg: '#f59e0b' },
]
const avatarStyle = (name) => {
  const hash = (name || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const p = PALETTE[hash % PALETTE.length]
  return { background: p.bg, color: p.fg }
}

// ── Index staleness check ─────────────────────────────────────────────────────
const indexStale = ref(false)

onMounted(async () => {
  try {
    const res = await api.faceIndexStatus()
    indexStale.value = res.data.index_stale
  } catch { /* ignore if endpoint not available */ }
})

// ── Tab ───────────────────────────────────────────────────────────────────────
const tab = ref('single')
const switchTab = (t) => {
  tab.value = t
  resetSingle()
  resetGroup()
}

// ── Pre-compute ───────────────────────────────────────────────────────────────
const precomputing = ref(false)
const precomputeResult = ref(null)

const runPrecompute = async () => {
  precomputing.value = true
  precomputeResult.value = null
  try {
    const res = await api.precomputeFaceEmbeddings()
    precomputeResult.value = res.data
    indexStale.value = false
  } catch {
    precomputeResult.value = { success: 0, processed: 0, skipped: 0, errors: ['Failed — check console'] }
  } finally {
    precomputing.value = false
  }
}

// ── Feature 1: Single face search ────────────────────────────────────────────
const singleInput = ref(null)
const singleDrop  = ref(false)
const singleFile  = ref(null)
const singlePreview = ref(null)
const searching   = ref(false)
const singleResult = ref(null)
const singleError  = ref(null)

const setSingleFile = (file) => {
  if (!file || !file.type.startsWith('image/')) return
  if (singlePreview.value) URL.revokeObjectURL(singlePreview.value)
  singleFile.value    = file
  singlePreview.value = URL.createObjectURL(file)
  singleResult.value  = null
  singleError.value   = null
}

const onSingleDrop   = (e) => { singleDrop.value = false; setSingleFile(e.dataTransfer?.files?.[0]) }
const onSingleChange = (e) => setSingleFile(e.target?.files?.[0])

const resetSingle = () => {
  if (singlePreview.value) URL.revokeObjectURL(singlePreview.value)
  singleFile.value    = null
  singlePreview.value = null
  singleResult.value  = null
  singleError.value   = null
  if (singleInput.value) singleInput.value.value = ''
}

const searchSingle = async () => {
  if (!singleFile.value || searching.value) return
  searching.value    = true
  singleResult.value = null
  singleError.value  = null
  try {
    const res = await api.searchByFace(singleFile.value)
    singleResult.value = res.data
  } catch (err) {
    const detail = err.response?.data?.detail || 'Search failed — please try again'
    singleError.value  = detail
    singleResult.value = { matched: false, similarity: 0 }
  } finally {
    searching.value = false
  }
}

// ── Feature 2: Group photo ────────────────────────────────────────────────────
const groupInput   = ref(null)
const groupDrop    = ref(false)
const groupPreview = ref(null)
const groupFaces   = ref(null)
const analyzing    = ref(false)
const groupImage   = ref(null)
const photoWrapper = ref(null)
const naturalSize  = ref(null)
const selectedFace = ref(null)
const identifying  = ref(false)
const identifiedFaces = reactive({})

const onGroupDrop   = (e) => { groupDrop.value = false; processGroupFile(e.dataTransfer?.files?.[0]) }
const onGroupChange = (e) => processGroupFile(e.target?.files?.[0])

const processGroupFile = async (file) => {
  if (!file || !file.type.startsWith('image/')) return
  if (groupPreview.value) URL.revokeObjectURL(groupPreview.value)
  groupPreview.value = URL.createObjectURL(file)
  groupFaces.value   = null
  naturalSize.value  = null
  selectedFace.value = null
  Object.keys(identifiedFaces).forEach(k => delete identifiedFaces[k])

  analyzing.value = true
  try {
    const res = await api.analyzeGroupImage(file)
    groupFaces.value = res.data.faces
  } catch (err) {
    alert(err.response?.data?.detail || 'Face analysis failed')
    resetGroup()
  } finally {
    analyzing.value = false
  }
}

const onGroupImageLoad = () => {
  const img = groupImage.value
  if (!img) return
  naturalSize.value = { w: img.naturalWidth, h: img.naturalHeight }
}

const getFaceBoxStyle = (face) => {
  if (!naturalSize.value) return {}
  const { x, y, width, height } = face.box
  const { w, h } = naturalSize.value
  return {
    left:   `${(x / w) * 100}%`,
    top:    `${(y / h) * 100}%`,
    width:  `${(width  / w) * 100}%`,
    height: `${(height / h) * 100}%`,
  }
}

const clickFace = async (face) => {
  selectedFace.value = face

  // Already identified — just show cached result
  if (identifiedFaces[face.face_index] !== undefined) return

  if (!face.embedding) return  // no embedding, show "unavailable" message

  identifying.value = true
  try {
    const res = await api.identifyFace(face.embedding)
    identifiedFaces[face.face_index] = res.data
  } catch {
    identifiedFaces[face.face_index] = { matched: false, message: 'Identification failed' }
  } finally {
    identifying.value = false
  }
}

const resetGroup = () => {
  if (groupPreview.value) URL.revokeObjectURL(groupPreview.value)
  groupPreview.value = null
  groupFaces.value   = null
  naturalSize.value  = null
  selectedFace.value = null
  Object.keys(identifiedFaces).forEach(k => delete identifiedFaces[k])
  if (groupInput.value) groupInput.value.value = ''
}
</script>

<style scoped>
/* ── Precompute button ── */
.precompute-btn {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  margin-top: 4px;
}

/* ── Banner ── */
.precompute-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: var(--radius);
  border: 1px solid;
  font-size: 13px;
  margin-bottom: 16px;
}
.banner-ok   { background: rgba(34,197,94,0.07); border-color: rgba(34,197,94,0.2); color: var(--success); }
.banner-warn { background: rgba(245,158,11,0.07); border-color: rgba(245,158,11,0.2); color: var(--warning); }
.banner-close { padding: 2px 6px; font-size: 11px; margin-left: auto; }

/* ── Tabs ── */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  border-radius: 0;
  transition: color 0.15s;
}

.tab-btn:hover { color: var(--text-strong); background: transparent; }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Feature panel layout ── */
.feature-panel {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.panel-left  { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px; }
.panel-right { flex: 1; min-width: 0; }

/* ── Drop zone ── */
.drop-zone {
  position: relative;
  border: 1px dashed var(--line-mid);
  border-radius: var(--radius-lg);
  cursor: pointer;
  overflow: hidden;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, background 0.2s;
  user-select: none;
}

.drop-zone:hover { border-color: rgba(255,255,255,0.2); }
.drop-zone.drop-active { border-color: var(--accent); border-style: solid; background: var(--accent-dim); }
.drop-zone.has-image  { min-height: 220px; border-style: solid; border-color: var(--line-mid); }
.drop-zone-lg { min-height: 280px; width: 100%; max-width: 520px; }

.drop-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px;
  text-align: center;
  pointer-events: none;
}

.drop-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--line-mid);
  display: grid;
  place-items: center;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.drop-text  { font-size: 13px; color: var(--text-strong); font-weight: 500; }
.drop-hint  { font-size: 10px; color: var(--text-muted); font-family: var(--mono); letter-spacing: 0.06em; }

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
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.2s;
}
.drop-zone.has-image:hover .drop-hover-overlay { opacity: 1; }

/* ── Drop actions ── */
.drop-actions { display: flex; gap: 8px; }

/* ── Spinner ── */
.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(0,0,0,0.18);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

.spinner-lg {
  display: inline-block;
  width: 24px;
  height: 24px;
  border: 2px solid var(--line-mid);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Result placeholder ── */
.result-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 24px;
  color: var(--text-muted);
  text-align: center;
  font-size: 13px;
  line-height: 1.6;
  border: 1px dashed var(--line);
  border-radius: var(--radius-lg);
  min-height: 200px;
}

/* ── Result cards ── */
.result-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 18px;
  border-radius: var(--radius-lg);
  border: 1px solid;
}

.result-success { background: rgba(34,197,94,0.07);  border-color: rgba(34,197,94,0.2); }
.result-danger  { background: rgba(244,63,94,0.07);  border-color: rgba(244,63,94,0.2);  color: var(--danger); }
.result-warn    { background: rgba(245,158,11,0.07); border-color: rgba(245,158,11,0.2); color: var(--warning); }

.rc-icon { flex-shrink: 0; padding-top: 1px; }

.rc-avatar-wrap { flex-shrink: 0; }
.rc-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  object-fit: cover;
  display: grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
}

.rc-body { flex: 1; min-width: 0; }
.rc-name  { font-size: 15px; font-weight: 600; color: var(--text-strong); margin-bottom: 3px; }
.rc-phone { font-size: 12px; color: var(--text-muted); margin-bottom: 3px; }
.rc-detail { font-size: 12px; margin-bottom: 2px; }
.rc-label { font-size: 14px; font-weight: 600; margin-bottom: 4px; color: inherit; }
.rc-sub   { font-size: 12px; opacity: 0.8; line-height: 1.5; }

/* ── Similarity bar ── */
.sim-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.sim-label { font-size: 10px; font-family: var(--mono); color: var(--text-muted); flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.06em; }
.sim-track { flex: 1; height: 3px; background: rgba(34,197,94,0.15); border-radius: 2px; overflow: hidden; }
.sim-fill  { height: 100%; background: var(--success); border-radius: 2px; transition: width 0.6s cubic-bezier(0.16,1,0.3,1); }
.sim-pct   { font-size: 11px; font-family: var(--mono); flex-shrink: 0; color: var(--success); }

/* ── Group photo workspace ── */
.group-upload { display: flex; flex-direction: column; align-items: center; gap: 16px; width: 100%; }
.analyzing-state { display: flex; flex-direction: column; align-items: center; gap: 10px; color: var(--text-muted); font-size: 13px; }

.group-workspace {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  width: 100%;
}

.photo-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.id-panel { width: 300px; flex-shrink: 0; }

/* ── Photo + face box overlay ── */
.photo-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
  line-height: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--line-mid);
}

.group-photo {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-lg);
}

.face-box {
  position: absolute;
  border: 2px solid rgba(56,189,248,0.7);
  border-radius: 4px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.3);
}

.face-box:hover {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(56,189,248,0.2);
}

.face-box--selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(56,189,248,0.3);
}

.face-box--identified {
  border-color: rgba(34,197,94,0.8);
}

.face-box--no-match {
  border-color: rgba(245,158,11,0.8);
}

.face-box__index {
  position: absolute;
  top: -2px;
  left: -2px;
  background: rgba(56,189,248,0.85);
  color: #000;
  font-size: 9px;
  font-weight: 700;
  font-family: var(--mono);
  padding: 1px 4px;
  border-radius: 2px 0 2px 0;
  line-height: 1.4;
}

.face-box--identified .face-box__index { background: rgba(34,197,94,0.85); }
.face-box--no-match .face-box__index   { background: rgba(245,158,11,0.85); }

.photo-hint { font-size: 11px; color: var(--text-muted); font-family: var(--mono); }

/* ── Identity panel sub-label ── */
.id-face-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  font-family: var(--mono);
  margin-bottom: 10px;
}

/* ── Transition ── */
.result-reveal-enter-active { transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.16,1,0.3,1); }
.result-reveal-leave-active { transition: opacity 0.18s ease; }
.result-reveal-enter-from   { opacity: 0; transform: translateY(8px); }
.result-reveal-leave-to     { opacity: 0; }

/* ── mono / muted helpers ── */
.mono  { font-family: var(--mono); }
.muted { color: var(--text-muted); }

/* ── Contact profile extras ── */
.rc-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 3px;
  flex-wrap: wrap;
}
.rc-name-row .rc-name { margin-bottom: 0; }

.rc-badge {
  font-size: 9px;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.rc-badge-dup {
  background: rgba(245,158,11,0.15);
  color: var(--warning);
  border: 1px solid rgba(245,158,11,0.3);
}

.rc-notes {
  font-size: 11px;
  color: var(--text-muted);
  margin: 4px 0 2px;
  line-height: 1.5;
  font-style: italic;
}

.rc-view-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
  opacity: 0.85;
  transition: opacity 0.15s;
}
.rc-view-link:hover { opacity: 1; text-decoration: underline; }

@media (max-width: 900px) {
  .feature-panel    { flex-direction: column; }
  .panel-left       { width: 100%; }
  .group-workspace  { flex-direction: column; }
  .id-panel         { width: 100%; }
}
</style>
