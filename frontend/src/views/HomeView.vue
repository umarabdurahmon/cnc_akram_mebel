<template>
  <div class="home-view">

    <!-- ── Sub-view header (attendance drill-down only) ─────────── -->
    <div v-if="activeView === 'attendance'" class="sub-header">
      <button class="back-btn" @click="goBack">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        Назад
      </button>
      <span class="sub-title">{{ selectedEmployee?.full_name ?? '' }}</span>
    </div>

    <!-- ── REPORTS sub-view ───────────────────────────────────── -->
    <template v-if="activeView === 'reports'">
      <ReportsView
        :year="reportYear"
        :month="reportMonth"
        @back="activeView = null"
      />
    </template>

    <!-- ── ATTENDANCE sub-view ─────────────────────────────────── -->
    <template v-else-if="activeView === 'attendance'">
      <div class="emp-name-bar">
        <div class="emp-avatar-lg">{{ initials(selectedEmployee.full_name) }}</div>
        <span class="emp-name-lg">{{ selectedEmployee.full_name }}</span>
      </div>
      <AttendanceCalendarView :employee="selectedEmployee" />
    </template>

    <!-- ── DASHBOARD ──────────────────────────────────────────── -->
    <template v-else-if="!activeView">

      <!-- Greeting -->
      <div class="greeting">
        <span class="greeting-wave">{{ greetingEmoji }}</span>
        <div>
          <div class="greeting-text">{{ greetingText }}</div>
          <div class="greeting-date">{{ todayLabel }}</div>
        </div>
      </div>

      <!-- ── Attendance section ─────────────────────────────── -->
      <div class="section-header">
        <span class="section-title">{{ t('nav.attendance') }}</span>
        <div class="att-controls">
          <span class="section-hint">{{ t('home.on_shift_count', { n: onShiftCount }) }}</span>
          <div class="att-view-toggle">
            <button :class="['avt-btn', { active: attView === 'list' }]" @click="attView = 'list'">
              <svg width="13" height="13" viewBox="0 0 14 14" fill="currentColor">
                <rect x="0" y="1" width="14" height="2.2" rx="1.1" />
                <rect x="0" y="5.9" width="14" height="2.2" rx="1.1" />
                <rect x="0" y="10.8" width="14" height="2.2" rx="1.1" />
              </svg>
            </button>
            <button :class="['avt-btn', { active: attView === 'chart' }]" @click="attView = 'chart'">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5" />
                <path d="M8 8 L8 1 A7 7 0 0 1 14.06 11.5 Z" fill="currentColor" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="attLoading" class="widget-loading">
        <div class="mini-spinner"></div>
      </div>
      <div v-else-if="employees.length === 0" class="empty-section">{{ t('home.no_employees') }}</div>

      <!-- Список -->
      <div v-else-if="attView === 'list'" class="emp-list">
        <button
          v-for="emp in employees"
          :key="emp.employee_id"
          class="emp-row"
          @click="openEmployee(emp)"
        >
          <div class="emp-avatar" :class="emp.open_since ? 'avatar-on' : 'avatar-off'">
            {{ initials(emp.full_name) }}
          </div>
          <div class="emp-info">
            <span class="emp-name">{{ emp.full_name }}</span>
            <span class="emp-sub" :class="emp.open_since ? 'sub-on' : 'sub-off'">
              <span class="emp-dot"></span>
              {{ emp.open_since ? t('home.on_since', { time: fmtTime(emp.open_since) }) : t('home.not_on_shift') }}
            </span>
          </div>
          <svg class="emp-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>
      </div>

      <!-- Pie chart -->
      <div v-else class="pie-widget">
        <svg viewBox="0 0 120 120" class="pie-svg">
          <!-- Фон (серое кольцо) -->
          <circle cx="60" cy="60" r="42" fill="none"
            stroke="var(--c-hint)" stroke-width="20" opacity="0.18" />
          <!-- На смене (зелёная дуга) -->
          <circle cx="60" cy="60" r="42" fill="none"
            stroke="var(--c-positive)" stroke-width="20"
            stroke-linecap="round"
            :stroke-dasharray="`${onPct * 263.9} ${(1 - onPct) * 263.9}`"
            transform="rotate(-90 60 60)" />
          <!-- Центр: число -->
          <text x="60" y="54" text-anchor="middle"
            font-size="22" font-weight="700"
            fill="var(--c-text)" font-family="system-ui, sans-serif">
            {{ onShiftCount }}
          </text>
          <text x="60" y="70" text-anchor="middle"
            font-size="10" fill="var(--c-hint)" font-family="system-ui, sans-serif">
            {{ t('home.of_total', { n: employees.length }) }}
          </text>
        </svg>
        <div class="pie-legend">
          <div class="pie-leg-row">
            <span class="pie-dot" style="background: var(--c-positive)"></span>
            <span class="pie-leg-label">{{ t('manager.on_shift') }}</span>
            <span class="pie-leg-val">{{ onShiftCount }}</span>
          </div>
          <div class="pie-leg-row">
            <span class="pie-dot" style="background: var(--c-hint); opacity: 0.4"></span>
            <span class="pie-leg-label">{{ t('home.not_on_shift') }}</span>
            <span class="pie-leg-val">{{ employees.length - onShiftCount }}</span>
          </div>
        </div>
      </div>

      <!-- ── Finance widget ───────────────────────────────────── -->
      <div class="section-header section-header-spaced">
        <span class="section-title">{{ t('nav.finance') }}</span>
      </div>

      <FinanceDashboardView
        @go-reports="openReports"
      />

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import AttendanceCalendarView from './AttendanceCalendarView.vue'
import FinanceDashboardView from './FinanceDashboardView.vue'
import ReportsView from './ReportsView.vue'

const props = defineProps({
  currentEmployee: { type: Object, default: null },
})

const { t, locale } = useI18n()

// ── Navigation ─────────────────────────────────────────────────
const activeView = ref(null)   // null | 'attendance' | 'reports'
const selectedEmployee = ref(null)
const reportYear = ref(null)
const reportMonth = ref(null)

function openEmployee(emp) {
  selectedEmployee.value = emp
  activeView.value = 'attendance'
}

function openReports({ year, month }) {
  reportYear.value = year
  reportMonth.value = month
  activeView.value = 'reports'
}

function goBack() {
  activeView.value = null
  loadAttendance()
}

// ── Greeting ───────────────────────────────────────────────────
const SHOP_TZ = 'Asia/Tashkent'

function todayStr() {
  return new Date().toLocaleDateString('sv', { timeZone: SHOP_TZ })
}

const todayLabel = computed(() => {
  const d = new Date(todayStr() + 'T00:00:00')
  return d.toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', {
    weekday: 'long', day: 'numeric', month: 'long',
  })
})

const greetingEmoji = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '🌙'
  if (h < 12) return '🌅'
  if (h < 18) return '☀️'
  return '🌆'
})

const greetingText = computed(() => {
  const name = props.currentEmployee?.full_name?.split(' ')[0] ?? ''
  const h = new Date().getHours()
  const key = h < 12 ? 'home.good_morning' : h < 18 ? 'home.good_afternoon' : 'home.good_evening'
  const base = t(key)
  return name ? `${base}, ${name}!` : `${base}!`
})

// ── Attendance data ────────────────────────────────────────────
const attLoading = ref(false)
const employees = ref([])
const attView = ref('list')

const onShiftCount = computed(() => employees.value.filter(e => e.open_since).length)
const onPct = computed(() => employees.value.length ? onShiftCount.value / employees.value.length : 0)

function initials(name) {
  return (name ?? '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function fmtTime(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: SHOP_TZ })
}

async function loadAttendance() {
  attLoading.value = true
  try {
    const data = await api.get('/api/attendance/employees-status')
    employees.value = [...data.employees].sort((a, b) => {
      if (!!a.open_since !== !!b.open_since) return a.open_since ? -1 : 1
      return a.full_name.localeCompare(b.full_name)
    })
  } catch {
    employees.value = []
  } finally {
    attLoading.value = false
  }
}

onMounted(loadAttendance)
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* ── Sub-view header ───────────────────────────────────────── */
.sub-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.75rem 0.75rem 0.5rem;
  position: sticky; top: 0; z-index: 20;
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-surface);
}
.back-btn {
  display: flex; align-items: center; gap: 0.25rem;
  background: none; border: none;
  color: var(--c-accent); font-size: 0.9rem; font-weight: 600;
  cursor: pointer; padding: 0.25rem 0.5rem 0.25rem 0; flex-shrink: 0;
}
.sub-title {
  font-size: 1rem; font-weight: 700; color: var(--c-text);
  flex: 1; text-align: center; padding-right: 4.5rem;
}

/* ── Employee name bar (attendance sub-view) ───────────────── */
.emp-name-bar {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.875rem 1rem 0;
}
.emp-avatar-lg {
  width: 2.75rem; height: 2.75rem; border-radius: 50%;
  background: var(--c-accent); color: var(--c-accent-text);
  font-size: 1rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.emp-name-lg { font-size: 1.1rem; font-weight: 700; color: var(--c-text); }

/* ── Dashboard ─────────────────────────────────────────────── */
.greeting {
  display: flex; align-items: center; gap: 0.875rem;
  padding: 1.25rem 1rem 0.5rem;
}
.greeting-wave { font-size: 2rem; line-height: 1; flex-shrink: 0; }
.greeting-text { font-size: 1.1rem; font-weight: 700; color: var(--c-text); }
.greeting-date { font-size: 0.78rem; color: var(--c-hint); text-transform: capitalize; margin-top: 0.1rem; }

/* ── Section headers ───────────────────────────────────────── */
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem 0.375rem;
}
.section-header-spaced { padding-top: 1.25rem; }
.section-title {
  font-size: 0.8rem; font-weight: 700; color: var(--c-hint);
  text-transform: uppercase; letter-spacing: 0.06em;
}
.section-hint { font-size: 0.78rem; color: var(--c-hint); }

.report-cta {
  display: flex; align-items: center; gap: 0.25rem;
  background: none; border: none;
  font-size: 0.78rem; font-weight: 600; color: var(--c-accent);
  cursor: pointer; padding: 0;
}

/* ── Employee list ─────────────────────────────────────────── */
.emp-list {
  display: flex; flex-direction: column; gap: 0.375rem;
  padding: 0 0.875rem;
}
.emp-row {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--c-surface); border: none; border-radius: 14px;
  padding: 0.75rem 0.875rem; cursor: pointer; text-align: left;
  transition: opacity 0.15s; width: 100%;
}
.emp-row:active { opacity: 0.7; }

.emp-avatar {
  width: 2.25rem; height: 2.25rem; border-radius: 50%;
  font-size: 0.8rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.avatar-on  { background: var(--c-positive); color: #fff; }
.avatar-off { background: var(--c-surface); color: var(--c-hint); border: 1.5px solid var(--c-hint); opacity: 0.6; }

.emp-info { flex: 1; min-width: 0; }
.emp-name { display: block; font-size: 0.9rem; font-weight: 600; color: var(--c-text); }
.emp-sub {
  display: flex; align-items: center; gap: 0.3rem;
  font-size: 0.75rem; margin-top: 0.1rem;
}
.sub-on  { color: var(--c-positive); }
.sub-off { color: var(--c-hint); }
.emp-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; background: currentColor; }
.sub-on .emp-dot { animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
.emp-chevron { color: var(--c-hint); flex-shrink: 0; }

/* ── Attendance view toggle ────────────────────────────────── */
.att-controls { display: flex; align-items: center; gap: 0.5rem; }
.att-view-toggle {
  display: flex; gap: 2px;
  background: var(--c-surface);
  border-radius: 8px; padding: 2px;
}
.avt-btn {
  background: none; border: none; cursor: pointer;
  width: 26px; height: 26px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  color: var(--c-hint); transition: background 0.15s, color 0.15s;
}
.avt-btn.active { background: var(--c-accent); color: var(--c-accent-text); }

/* ── Pie chart widget ──────────────────────────────────────── */
.pie-widget {
  display: flex; align-items: center; gap: 1.25rem;
  margin: 0 0.875rem;
  background: var(--c-surface);
  border-radius: 16px; padding: 1.125rem 1.25rem;
}
.pie-svg { width: 110px; height: 110px; flex-shrink: 0; }
.pie-legend { display: flex; flex-direction: column; gap: 0.625rem; flex: 1; }
.pie-leg-row { display: flex; align-items: center; gap: 0.5rem; }
.pie-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.pie-leg-label { flex: 1; font-size: 0.82rem; color: var(--c-hint); }
.pie-leg-val { font-size: 1rem; font-weight: 700; color: var(--c-text); }

/* ── Loading / empty ───────────────────────────────────────── */
.widget-loading { display: flex; align-items: center; padding: 0.75rem 1rem; }
.mini-spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--c-bg); border-top-color: var(--c-accent);
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-section { font-size: 0.83rem; color: var(--c-hint); padding: 0 1rem; }
</style>
