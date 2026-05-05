<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Call History</h1>
        <p class="page-subtitle">All recorded calls with filter and search</p>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="filter-bar">
      <input v-model="phone" placeholder="Filter by phone number" style="min-width:200px" />
      <select v-model="status" style="min-width:140px">
        <option value="">All statuses</option>
        <option value="completed">Completed</option>
        <option value="missed">Missed</option>
      </select>
      <select v-model="callType" style="min-width:130px">
        <option value="">All types</option>
        <option value="inbound">Inbound</option>
        <option value="outbound">Outbound</option>
      </select>
      <div class="date-field">
        <svg class="date-field__icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="1" y="3" width="14" height="12" rx="2"/>
          <path d="M1 7h14M5 1v4M11 1v4"/>
        </svg>
        <input v-model="dateFrom" type="date" />
      </div>
      <div class="date-field">
        <svg class="date-field__icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="1" y="3" width="14" height="12" rx="2"/>
          <path d="M1 7h14M5 1v4M11 1v4"/>
        </svg>
        <input v-model="dateTo" type="date" />
      </div>
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
          <table v-if="calls.length">
            <thead>
              <tr>
                <th>Call ID</th>
                <th>Contact</th>
                <th>Phone</th>
                <th>Date</th>
                <th>Time</th>
                <th>Duration</th>
                <th>Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="call in calls" :key="call.call_id">
                <td class="mono muted" style="font-size:11px">{{ call.call_id }}</td>
                <td><strong>{{ call.contact_name || 'Unknown' }}</strong></td>
                <td class="mono" style="font-size:12px">{{ call.phone_number }}</td>
                <td>{{ call.date }}</td>
                <td class="mono muted" style="font-size:12px">{{ call.time }}</td>
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
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 5a2 2 0 0 1 2-2h3l2 4.5-1.5 1a11 11 0 0 0 5 5l1-1.5 4.5 2v3a2 2 0 0 1-2 2C8 21 3 16 3 5z"/>
            </svg>
            <p>No calls match your filters.</p>
          </div>
        </div>

        <div class="pager">
          <span class="pager-info">Page {{ page }}</span>
          <div class="pager-btns">
            <button class="ghost" @click="prevPage" :disabled="page === 1">← Prev</button>
            <button class="ghost" @click="nextPage" :disabled="!hasNextPage">Next →</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const calls       = ref([])
const phone       = ref('')
const status      = ref('')
const callType    = ref('')
const dateFrom    = ref('')
const dateTo      = ref('')
const page        = ref(1)
const perPage     = 10
const hasNextPage = ref(true)
const loading     = ref(false)
const error       = ref('')

const formatDuration = (s) => {
  const m = Math.floor((s || 0) / 60), sec = (s || 0) % 60
  return `${m}m ${sec}s`
}

const fetchCalls = async () => {
  loading.value = true; error.value = ''
  try {
    const res = await api.getCalls({
      phone:     phone.value     || undefined,
      status:    status.value    || undefined,
      call_type: callType.value || undefined,
      date_from: dateFrom.value  || undefined,
      date_to:   dateTo.value    || undefined,
      page: page.value, limit: perPage + 1,
    })
    hasNextPage.value = res.data.length > perPage
    calls.value = res.data.slice(0, perPage)
    if (calls.value.length === 0 && page.value > 1) { page.value--; await fetchCalls() }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load calls'
  } finally {
    loading.value = false
  }
}

const applyFilters = () => { page.value = 1; fetchCalls() }
const resetFilters = () => { phone.value = ''; status.value = ''; callType.value = ''; dateFrom.value = ''; dateTo.value = ''; page.value = 1; fetchCalls() }
const nextPage     = () => { if (!hasNextPage.value) return; page.value++; fetchCalls() }
const prevPage     = () => { if (page.value > 1) { page.value--; fetchCalls() } }

onMounted(fetchCalls)
</script>

<style scoped>
.date-field {
  position: relative;
  height: 34px;
  min-width: 150px;
  border: 1px solid var(--line-mid);
  border-radius: var(--radius);
  background: var(--bg);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.date-field:hover {
  border-color: rgba(255, 255, 255, 0.18);
}

.date-field:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

/* Icon sits in the left padding zone, non-interactive */
.date-field__icon {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  width: 13px;
  height: 13px;
  color: var(--text-muted);
  pointer-events: none;
  z-index: 0;
}

/* Input stretches to fill the entire field — indicator overlay covers icon area too */
.date-field input[type="date"] {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 0 11px 0 32px;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text-strong);
  font-size: 13px;
  cursor: pointer;
  outline: none;
  border-radius: var(--radius);
}

/* Full-field transparent overlay — any click opens the picker */
.date-field input[type="date"]::-webkit-calendar-picker-indicator {
  position: absolute;
  inset: 0;
  width: auto;
  height: auto;
  opacity: 0;
  cursor: pointer;
}
</style>
