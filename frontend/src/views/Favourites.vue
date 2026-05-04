<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Favourites</h1>
        <p class="page-subtitle">Auto-ranked by call frequency and total duration</p>
      </div>
      <div class="tabs">
        <button class="tab-btn" :class="{ active: mode === 'most_called' }"   @click="setMode('most_called')">Most Called</button>
        <button class="tab-btn" :class="{ active: mode === 'longest_calls' }" @click="setMode('longest_calls')">Longest Calls</button>
        <button class="tab-btn" :class="{ active: mode === 'recent' }"        @click="setMode('recent')">Recent</button>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- Skeleton -->
    <template v-if="loading">
      <div class="podium">
        <div v-for="n in 3" :key="n" class="skeleton" style="height:180px;border-radius:12px"></div>
      </div>
      <div class="table-wrap">
        <div style="padding:12px 18px;display:flex;flex-direction:column;gap:8px">
          <div v-for="n in 6" :key="n" class="skeleton skeleton-row" style="border-radius:6px"></div>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- Podium -->
      <div v-if="topThree.length" class="podium">
        <div
          v-for="(fav, i) in topThree"
          :key="fav.phone"
          class="podium-card"
          :class="`rank-${i + 1}`"
        >
          <div class="podium-badge">{{ ['1st Place','2nd Place','3rd Place'][i] }}</div>
          <img v-if="fav.profile_picture_id" :src="`${API_URL}/ai/images/${fav.profile_picture_id}`" class="podium-avatar" style="object-fit: cover; border-radius: 50%;" />
          <div v-else class="podium-avatar">{{ initials(fav.name) }}</div>
          <div class="podium-name">{{ fav.name }}</div>
          <div class="podium-phone">{{ fav.phone }}</div>
          <div class="score-track">
            <div class="score-fill" :style="{ width: `${fav.score || 0}%` }"></div>
          </div>
          <div class="podium-score">Score {{ fav.score || 0 }}</div>
        </div>
      </div>

      <!-- Ranked table -->
      <div class="table-wrap">
        <div class="table-head-bar"><h3>Full Rankings</h3></div>
        <div class="table-scroll">
          <table v-if="favourites.length">
            <thead>
              <tr>
                <th>#</th>
                <th>Contact</th>
                <th>Phone</th>
                <th>City</th>
                <th>Total Calls</th>
                <th>Total Duration</th>
                <th>Last Call</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(fav, i) in favourites" :key="fav.phone">
                <td class="mono muted" style="font-size:11px">#{{ i + 1 }}</td>
                <td>
                  <div style="display:flex;align-items:center;gap:8px">
                    <img v-if="fav.profile_picture_id" :src="`${API_URL}/ai/images/${fav.profile_picture_id}`" class="t-avatar" style="object-fit: cover; border-radius: 50%;" />
                    <div v-else class="t-avatar" :style="avatarStyle(i)">{{ initials(fav.name) }}</div>
                    <strong>{{ fav.name }}</strong>
                  </div>
                </td>
                <td class="mono" style="font-size:12px">{{ fav.phone }}</td>
                <td>{{ fav.city || '—' }}</td>
                <td class="mono" style="color:var(--accent)">{{ fav.call_count }}</td>
                <td class="mono">{{ formatDuration(fav.total_duration_seconds) }}</td>
                <td class="muted">{{ fav.last_call_date || '—' }}</td>
                <td style="min-width:140px">
                  <div class="score-track" style="margin-bottom:4px">
                    <div class="score-fill" :style="{ width: `${fav.score || 0}%` }"></div>
                  </div>
                  <span class="mono muted" style="font-size:10px">{{ fav.score || 0 }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state"><p>No favourites data available.</p></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const favourites = ref([])
const mode       = ref('most_called')
const loading    = ref(false)
const error      = ref('')

const topThree = computed(() => favourites.value.slice(0, 3))

const PALETTE = [
  { bg: 'rgba(16,185,129,0.12)',  fg: '#10b981' },
  { bg: 'rgba(148,163,184,0.1)', fg: '#94a3b8' },
  { bg: 'rgba(161,98,7,0.1)',    fg: '#ca8a04' },
  { bg: 'rgba(56,189,248,0.12)', fg: '#38bdf8' },
  { bg: 'rgba(167,139,250,0.11)',fg: '#a78bfa' },
]

const avatarStyle = (i) => ({
  background: PALETTE[i % PALETTE.length].bg,
  color:      PALETTE[i % PALETTE.length].fg,
})

const initials = (name) =>
  (name || '?').split(' ').slice(0, 2).map(p => p[0]?.toUpperCase()).join('')

const formatDuration = (s) => {
  const h = Math.floor((s || 0) / 3600)
  const m = Math.floor(((s || 0) % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

const fetchFavourites = async () => {
  loading.value = true; error.value = ''
  try {
    const res = await api.getFavourites(mode.value, 15)
    favourites.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load favourites'
  } finally {
    loading.value = false
  }
}

const setMode = (m) => { mode.value = m; fetchFavourites() }

onMounted(fetchFavourites)
</script>
