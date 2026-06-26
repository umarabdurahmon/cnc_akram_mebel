<template>
  <div class="worker-view">

    <!-- Навигация по датам -->
    <div class="date-nav">
      <button class="nav-arrow" @click="prevDay">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
      <div class="date-nav-center">
        <div class="date-label">{{ viewDateLabel }}</div>
        <button v-if="!isToday" class="go-today-btn" @click="goToday">
          {{ t('worker.go_today') }}
        </button>
      </div>
      <button class="nav-arrow" :class="{ 'nav-arrow-disabled': isToday }" :disabled="isToday" @click="nextDay">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
      </button>
    </div>

    <!-- ── СЕГОДНЯ ─────────────────────────────── -->
    <template v-if="isToday">

      <div class="status-hero" :class="openVisit ? 'hero-on' : 'hero-off'">
        <div class="status-indicator">
          <span class="status-dot" :class="openVisit ? 'dot-on' : 'dot-off'" />
          <span class="status-text">{{ openVisit ? t('worker.on_shift') : t('worker.not_on_shift') }}</span>
        </div>
        <template v-if="openVisit">
          <div class="since-time">{{ t('worker.since') }} {{ fmt(openVisit.check_in_at) }}</div>
          <div class="elapsed-timer">{{ elapsedStr }}</div>
        </template>
        <template v-else>
          <div class="day-summary">
            <div class="summary-item">
              <div class="summary-val">{{ fmtHours(todayHours) }}</div>
              <div class="summary-lbl">{{ t('worker.today_hours') }}</div>
            </div>
            <div class="summary-divider" />
            <div class="summary-item">
              <div class="summary-val">{{ closedVisits.length }}</div>
              <div class="summary-lbl">{{ t('worker.visits_count') }}</div>
            </div>
          </div>
        </template>
      </div>

      <button
        class="action-btn"
        :class="openVisit ? 'btn-out' : 'btn-in'"
        :disabled="loading"
        @click="toggle"
      >
        <span v-if="loading" class="btn-spinner">···</span>
        <template v-else>
          <span class="btn-icon">👋</span>
          {{ openVisit ? t('worker.btn_check_out') : t('worker.btn_check_in') }}
        </template>
      </button>

      <div v-if="openVisit && todayHours > 0" class="hours-pill">
        {{ t('worker.also_today', { hours: fmtHours(todayHours) }) }}
      </div>

      <template v-if="closedVisits.length">
        <div class="section-label">{{ t('worker.visits_today') }}</div>
        <div class="visit-list">
          <div v-for="(v, i) in closedVisits" :key="v.id" class="visit-card">
            <div class="visit-num">{{ closedVisits.length - i }}</div>
            <div class="visit-body">
              <div class="visit-times">
                <span class="time-in">{{ fmt(v.check_in_at) }}</span>
                <span class="time-arrow">→</span>
                <span class="time-out">{{ fmt(v.check_out_at) }}</span>
              </div>
            </div>
            <div class="visit-dur">{{ visitDur(v) }}</div>
          </div>
        </div>
      </template>
      <div v-else-if="!openVisit && !loading" class="empty-state">
        {{ t('worker.no_visits') }}
      </div>

    </template>

    <!-- ── ПРОШЛЫЙ ДЕНЬ ────────────────────────── -->
    <template v-else>
      <div v-if="histLoading" class="empty-state">…</div>
      <template v-else>

        <div class="status-hero hero-off">
          <div class="day-summary">
            <div class="summary-item">
              <div class="summary-val">{{ fmtHours(histHours) }}</div>
              <div class="summary-lbl">{{ t('worker.today_hours') }}</div>
            </div>
            <div class="summary-divider" />
            <div class="summary-item">
              <div class="summary-val">{{ histVisits.length }}</div>
              <div class="summary-lbl">{{ t('worker.visits_count') }}</div>
            </div>
          </div>
        </div>

        <template v-if="histVisits.length">
          <div class="section-label">{{ t('worker.visits_today') }}</div>
          <div class="visit-list">
            <div v-for="(v, i) in histVisits" :key="v.id" class="visit-card">
              <div class="visit-num">{{ histVisits.length - i }}</div>
              <div class="visit-body">
                <div class="visit-times">
                  <span class="time-in">{{ fmt(v.check_in_at) }}</span>
                  <span class="time-arrow">→</span>
                  <span class="time-out">{{ fmt(v.check_out_at) }}</span>
                </div>
              </div>
              <div class="visit-dur">{{ visitDur(v) }}</div>
            </div>
          </div>
        </template>
        <div v-else class="empty-state">{{ t('worker.no_visits_day') }}</div>

      </template>
    </template>

    <p v-if="error" class="error-msg">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'

const { t, locale } = useI18n()

// ── Дата ────────────────────────────────────────────────────
function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const viewDate = ref(todayIso())
const isToday = computed(() => viewDate.value === todayIso())

const viewDateLabel = computed(() => {
  const [y, m, d] = viewDate.value.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(
    locale.value === 'uz' ? 'uz-UZ' : 'ru-RU',
    { weekday: 'long', day: 'numeric', month: 'long' },
  )
})

function shiftDate(delta) {
  const [y, m, d] = viewDate.value.split('-').map(Number)
  const dt = new Date(y, m - 1, d + delta)
  viewDate.value = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
}

function prevDay() { shiftDate(-1); if (!isToday.value) loadHist() }
function nextDay() { if (isToday.value) return; shiftDate(1); if (!isToday.value) loadHist() }
function goToday()  { viewDate.value = todayIso() }

// ── Сегодня ─────────────────────────────────────────────────
const openVisit   = ref(null)
const closedVisits = ref([])
const todayHours  = ref(0)
const loading     = ref(false)
const error       = ref('')
const now         = ref(Date.now())
let ticker = null

const elapsedStr = computed(() => {
  if (!openVisit.value) return ''
  const ms = Math.max(0, now.value - new Date(openVisit.value.check_in_at).getTime())
  const m = Math.floor(ms / 60000)
  const h = Math.floor(m / 60)
  return h > 0 ? `${h}ч ${m % 60}м` : `${m}м`
})

// ── История ─────────────────────────────────────────────────
const histVisits  = ref([])
const histHours   = ref(0)
const histLoading = ref(false)

async function loadHist() {
  histLoading.value = true
  error.value = ''
  try {
    const data = await api.get(`/api/attendance/me/day?date=${viewDate.value}`)
    histVisits.value = [...(data.visits ?? [])].reverse()
    histHours.value  = data.today_hours
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    histLoading.value = false
  }
}

// ── Утилиты ─────────────────────────────────────────────────
function fmt(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleTimeString(
    locale.value === 'uz' ? 'uz-UZ' : 'ru-RU',
    { hour: '2-digit', minute: '2-digit' },
  )
}

function fmtHours(h) {
  if (!h) return '0м'
  const total = Math.round(h * 60)
  const hrs = Math.floor(total / 60)
  const min = total % 60
  if (hrs === 0) return `${min}м`
  if (min === 0) return `${hrs}ч`
  return `${hrs}ч ${min}м`
}

function visitDur(v) {
  if (!v.check_out_at) return ''
  const ms = new Date(v.check_out_at) - new Date(v.check_in_at)
  const total = Math.floor(ms / 60000)
  const h = Math.floor(total / 60)
  const m = total % 60
  return h > 0 ? `${h}ч ${m}м` : `${m}м`
}

async function toggle() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try {
    const data = await api.post('/api/attendance/toggle')
    openVisit.value  = data.open ? data.visit : null
    todayHours.value = data.today_hours
    if (!data.open) await loadToday()
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
}

async function loadToday() {
  try {
    const data = await api.get('/api/attendance/me/today')
    openVisit.value    = data.open_visit ?? null
    closedVisits.value = [...(data.visits ?? [])].reverse()
    todayHours.value   = data.today_hours
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  }
}

onMounted(async () => {
  await loadToday()
  ticker = setInterval(() => { now.value = Date.now() }, 10000)
})

onUnmounted(() => {
  clearInterval(ticker)
})
</script>

<style scoped>
.worker-view {
  padding: 0.75rem 1rem 5rem;
  max-width: 480px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 0.75rem;
}

/* ── Date nav ── */
.date-nav {
  display: flex; align-items: center; gap: 0.5rem;
}
.nav-arrow {
  background: var(--c-surface); border: none; border-radius: 10px;
  width: 2.25rem; height: 2.25rem; display: flex; align-items: center; justify-content: center;
  color: var(--c-accent); cursor: pointer; flex-shrink: 0;
  transition: opacity 0.15s;
}
.nav-arrow-disabled { color: var(--c-hint); cursor: default; opacity: 0.35; }
.date-nav-center {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
}
.date-label {
  font-size: 0.85rem; font-weight: 600; color: var(--c-text);
  text-transform: capitalize; text-align: center;
}
.go-today-btn {
  background: var(--c-accent); color: var(--c-accent-text);
  border: none; border-radius: 6px;
  font-size: 0.72rem; font-weight: 700; padding: 0.2rem 0.7rem;
  cursor: pointer;
}

/* ── Status hero ── */
.status-hero {
  border-radius: 20px; padding: 1.375rem 1.25rem;
  display: flex; flex-direction: column; gap: 0.5rem;
  transition: background 0.3s;
}
.hero-on  { background: linear-gradient(135deg, var(--c-checkin-from), var(--c-checkin-to)); }
.hero-off { background: var(--c-surface); }

.status-indicator { display: flex; align-items: center; gap: 0.6rem; }
.status-dot { width: 0.75rem; height: 0.75rem; border-radius: 50%; flex-shrink: 0; }
.dot-on {
  background: var(--c-checkin-pulse);
  box-shadow: 0 0 0 4px rgba(105,240,174,0.25);
  animation: pulse 2s infinite;
}
.dot-off { background: var(--c-hint); }
@keyframes pulse {
  0%,100% { box-shadow: 0 0 0 4px rgba(105,240,174,0.25); }
  50%      { box-shadow: 0 0 0 8px rgba(105,240,174,0.1); }
}
.status-text { font-size: 1rem; font-weight: 700; }
.hero-on  .status-text { color: #fff; }
.hero-off .status-text { color: var(--c-text); }

.since-time { font-size: 0.85rem; color: rgba(255,255,255,0.75); margin-left: 1.35rem; }
.elapsed-timer {
  font-size: 2.5rem; font-weight: 800; color: #fff;
  font-variant-numeric: tabular-nums; letter-spacing: -0.02em; margin-top: 0.25rem;
}

.day-summary { display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; }
.summary-item { flex: 1; text-align: center; }
.summary-val { font-size: 1.5rem; font-weight: 800; color: var(--c-text); }
.summary-lbl { font-size: 0.75rem; color: var(--c-hint); margin-top: 0.1rem; }
.summary-divider { width: 1px; height: 2.5rem; background: var(--c-hint); opacity: 0.35; }

/* ── Action button ── */
.action-btn {
  width: 100%; padding: 1rem; border: none; border-radius: 16px;
  font-size: 1.05rem; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 0.5rem;
  transition: opacity 0.15s, transform 0.1s;
}
.action-btn:active    { transform: scale(0.98); }
.action-btn:disabled  { opacity: 0.5; cursor: not-allowed; }
.btn-in  { background: var(--c-accent); color: var(--c-accent-text); }
.btn-out { background: var(--c-negative-dark); color: #fff; }
.btn-icon    { font-size: 1.1rem; }
.btn-spinner { font-size: 1.25rem; letter-spacing: 0.15em; }

/* ── Hours pill ── */
.hours-pill {
  text-align: center; font-size: 0.82rem; color: var(--c-hint);
  background: var(--c-surface); border-radius: 99px;
  padding: 0.3rem 1rem; align-self: center;
}

/* ── Visits ── */
.section-label {
  font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.07em; color: var(--c-hint);
  padding: 0.25rem 0 0;
}
.visit-list { display: flex; flex-direction: column; gap: 0.375rem; }
.visit-card {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--c-surface); border-radius: 14px; padding: 0.875rem 1rem;
}
.visit-num {
  width: 1.75rem; height: 1.75rem; border-radius: 50%; flex-shrink: 0;
  background: var(--c-bg); color: var(--c-hint);
  font-size: 0.75rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.visit-body { flex: 1; }
.visit-times {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 1rem; font-weight: 600; color: var(--c-text);
}
.time-arrow { color: var(--c-hint); font-size: 0.85rem; }
.visit-dur {
  font-size: 0.82rem; font-weight: 700; color: var(--c-accent);
  background: rgba(36,129,204,0.12); border-radius: 8px;
  padding: 0.2rem 0.6rem; white-space: nowrap; flex-shrink: 0;
}

/* ── States ── */
.empty-state { text-align: center; color: var(--c-hint); font-size: 0.9rem; padding: 1rem 0; }
.error-msg   { color: var(--c-negative); font-size: 0.85rem; text-align: center; }
</style>
