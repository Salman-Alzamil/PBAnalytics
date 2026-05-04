<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Overview of your contacts and call activity</p>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- Skeleton while loading -->
    <template v-if="loading">
      <div class="bento">
        <div class="col-2 skeleton" style="height:100px;border-radius:12px"></div>
        <div class="col-2 skeleton" style="height:100px;border-radius:12px"></div>
        <div class="col-1 skeleton" style="height:100px;border-radius:12px"></div>
        <div class="col-1 skeleton" style="height:100px;border-radius:12px"></div>
        <div class="col-2 skeleton" style="height:260px;border-radius:12px"></div>
        <div class="col-4 skeleton" style="height:260px;border-radius:12px"></div>
        <div class="col-6 skeleton" style="height:200px;border-radius:12px"></div>
      </div>
    </template>

    <template v-else-if="summary">
      <!-- Bento row 1: stats (asymmetric widths) -->
      <div class="bento">
        <div class="stat col-2 stat__accent">
          <div class="stat__label">Total Contacts</div>
          <div class="stat__value">{{ summary.total_contacts ?? 0 }}</div>
        </div>
        <div class="stat col-2 stat__info">
          <div class="stat__label">Total Calls</div>
          <div class="stat__value">{{ summary.total_calls ?? 0 }}</div>
        </div>
        <div class="stat col-1 stat__success">
          <div class="stat__label">Avg Call (min)</div>
          <div class="stat__value" style="font-size:28px">{{ summary.avg_duration_minutes ?? 0 }}</div>
        </div>
        <div class="stat col-1 stat__danger">
          <div class="stat__label">Duplicates</div>
          <div class="stat__value" style="font-size:28px">{{ dupCount }}</div>
        </div>

        <!-- Bento row 2: favourites + chart -->
        <div class="panel col-2">
          <div class="panel-head"><h3>Top Favourites</h3></div>
          <div class="panel-body" style="padding:8px 18px 14px">
            <div v-if="topFavourites.length" class="fav-list">
              <div v-for="(fav, i) in topFavourites" :key="fav.phone" class="fav-item">
                <span class="fav-rank">{{ i + 1 }}</span>
                <img v-if="fav.profile_picture_id" :src="`${API_URL}/ai/images/${fav.profile_picture_id}`" class="fav-avatar" style="object-fit: cover; border-radius: 50%;" />
                <div v-else class="fav-avatar" :style="avatarStyle(i)">{{ initials(fav.name) }}</div>
                <div class="fav-info">
                  <div class="fav-name">{{ fav.name }}</div>
                  <div class="fav-sub">{{ fav.call_count }} calls</div>
                </div>
                <div class="fav-bar">
                  <div class="score-track">
                    <div class="score-fill" :style="{ width: `${fav.score || 0}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state" style="padding:20px 0">
              <p>No favourites data yet.</p>
            </div>
          </div>
        </div>

        <div class="panel col-4">
          <div class="panel-head"><h3>Monthly Call Activity</h3></div>
          <div class="panel-body">
            <div class="chart-frame">
              <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
            </div>
          </div>
        </div>

        <!-- Bento row 3: recent calls -->
        <div class="table-wrap col-6">
          <div class="table-head-bar">
            <h3>Recent Call History</h3>
            <span class="mono muted" style="font-size:11px">Last 5 calls</span>
          </div>
          <div class="table-scroll">
            <table v-if="recentCalls.length">
              <thead>
                <tr>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>Date</th>
                  <th>Duration</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="call in recentCalls" :key="call.call_id">
                  <td><strong>{{ call.contact_name || 'Unknown' }}</strong></td>
                  <td class="mono" style="font-size:12px">{{ call.phone_number }}</td>
                  <td>{{ call.date }}</td>
                  <td class="mono">{{ formatDuration(call.duration_seconds) }}</td>
                  <td class="muted">{{ call.call_type }}</td>
                  <td>
                    <span class="badge" :class="call.status === 'missed' ? 'badge-red' : 'badge-green'">
                      {{ call.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty-state">
              <p>No recent calls found.</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS, Title, Tooltip, Legend,
  BarElement, CategoryScale, LinearScale,
} from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const summary      = ref(null)
const topFavourites = ref([])
const recentCalls  = ref([])
const chartData    = ref(null)
const loading      = ref(false)
const error        = ref('')

const PALETTE = [
  { bg: 'rgba(16,185,129,0.12)',  fg: '#10b981' },
  { bg: 'rgba(56,189,248,0.12)',  fg: '#38bdf8' },
  { bg: 'rgba(244,63,94,0.11)',   fg: '#f43f5e' },
  { bg: 'rgba(167,139,250,0.11)', fg: '#a78bfa' },
  { bg: 'rgba(245,158,11,0.12)',  fg: '#f59e0b' },
]

const avatarStyle = (i) => ({
  background: PALETTE[i % PALETTE.length].bg,
  color: PALETTE[i % PALETTE.length].fg,
})

const initials = (name) =>
  (name || '?').split(' ').slice(0, 2).map(p => p[0]?.toUpperCase()).join('')

const dupCount = computed(() => {
  const d = summary.value?.possible_duplicates ?? summary.value?.duplicates ?? 0
  return Array.isArray(d) ? d.length : d
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#18181f',
      titleColor: '#71717a',
      bodyColor: '#f4f4f5',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: 10,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { precision: 0, color: '#52525b', font: { family: "'Geist Mono'", size: 10 } },
      grid: { color: 'rgba(255,255,255,0.04)' },
      border: { display: false },
    },
    x: {
      grid: { display: false },
      ticks: { color: '#52525b', font: { family: "'Geist Mono'", size: 10 } },
      border: { display: false },
    },
  },
}

const formatDuration = (s) => {
  const m = Math.floor((s || 0) / 60), sec = (s || 0) % 60
  return `${m}m ${sec}s`
}

const buildChart = (calls) => {
  const grouped = {}
  calls.forEach(c => {
    if (!c.date) return
    const k = c.date.slice(0, 7)
    grouped[k] = (grouped[k] || 0) + 1
  })
  const labels = Object.keys(grouped).sort()
  chartData.value = {
    labels,
    datasets: [{
      data: labels.map(k => grouped[k]),
      backgroundColor: '#10b981',
      borderRadius: 4,
      barPercentage: 0.5,
    }],
  }
}

const loadDashboard = async () => {
  loading.value = true; error.value = ''
  try {
    const [s, c] = await Promise.all([api.getSummary(), api.getCalls({ page: 1, limit: 1000 })])
    summary.value       = s.data
    topFavourites.value = (s.data.top_favourites || []).slice(0, 5)
    recentCalls.value   = c.data.slice(0, 5)
    buildChart(c.data)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load dashboard'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>
