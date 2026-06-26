<template>
  <div class="att-cal-view">

    <!-- ── CALENDAR ───────────────────────────────────────────── -->
    <template v-if="!selectedDay">
      <!-- Month navigator -->
      <div class="month-nav">
        <button class="mnav-btn" @click="prevMonth">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <span class="month-label">{{ monthLabel }}</span>
        <button class="mnav-btn" :disabled="isCurrentMonth" @click="nextMonth">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>
      </div>

      <!-- Month stats -->
      <div v-if="!calLoading && dayMap.size > 0" class="month-stats">
        <div class="mstat">
          <span class="mstat-val">{{ totalDays }}</span>
          <span class="mstat-lbl">{{ t('calendar.days') }}</span>
        </div>
        <div class="mstat-div"></div>
        <div class="mstat">
          <span class="mstat-val">{{ fmtH(totalMonthHours) }}</span>
          <span class="mstat-lbl">{{ t('calendar.hours') }}</span>
        </div>
        <div class="mstat-div"></div>
        <div class="mstat">
          <span class="mstat-val mstat-warn">{{ discrepancyDays }}</span>
          <span class="mstat-lbl">{{ t('calendar.discrepancies') }}</span>
        </div>
      </div>

      <div v-if="calLoading" class="cal-loading">
        <div class="spinner"></div>
      </div>
      <template v-else>
        <!-- Weekday header -->
        <div class="cal-grid">
          <div v-for="wd in WEEKDAYS" :key="wd" class="cal-wd">{{ wd }}</div>

          <!-- Leading empty cells -->
          <div v-for="n in leadingBlanks" :key="'b'+n" class="cal-cell cal-blank"></div>

          <!-- Day cells -->
          <button
            v-for="day in calDays"
            :key="day.date"
            class="cal-cell"
            :class="dayClass(day)"
            @click="day.hasData && openDay(day.date)"
          >
            <span class="cal-day-num">{{ day.num }}</span>
            <span v-if="day.summary" class="cal-hours">{{ fmtHShort(day.summary.total_hours) }}</span>
          </button>
        </div>

        <!-- Legend -->
        <div class="legend">
          <span class="leg-item"><span class="leg-dot leg-present"></span>{{ t('calendar.legend_present') }}</span>
          <span class="leg-item"><span class="leg-dot leg-open"></span>{{ t('calendar.legend_on_shift') }}</span>
          <span class="leg-item"><span class="leg-dot leg-discr"></span>{{ t('calendar.legend_discrepancy') }}</span>
        </div>

        <p v-if="dayMap.size === 0" class="cal-empty">{{ t('calendar.no_records') }}</p>
      </template>
    </template>

    <!-- ── DAY DETAIL ─────────────────────────────────────────── -->
    <template v-else>
      <div class="day-header">
        <button class="back-day-btn" @click="selectedDay = null">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
          {{ t('calendar.back') }}
        </button>
        <span class="day-title">{{ dayLabel }}</span>
      </div>

      <div v-if="dayLoading" class="cal-loading"><div class="spinner"></div></div>
      <template v-else-if="dayData">
        <div class="day-total-pill">
          {{ t('calendar.day_total', { hours: fmtH(dayData.total_hours) }) }}
        </div>

        <div v-if="allDayVisits.length === 0" class="cal-empty">{{ t('calendar.no_visits') }}</div>
        <div v-else class="visit-list">
          <div
            v-for="v in allDayVisits"
            :key="v.id"
            class="visit-card"
            :class="`vst-${v.verification_status}`"
          >
            <!-- Times row -->
            <div class="vst-top">
              <div class="vst-times">
                <span class="vst-time">{{ fmtTime(v.check_in_at) }}</span>
                <span class="vst-arrow">→</span>
                <span class="vst-time">{{ v.check_out_at ? fmtTime(v.check_out_at) : '…' }}</span>
                <span v-if="v.check_out_at" class="vst-dur">{{ visitDur(v) }}</span>
              </div>
              <div class="vst-right">
                <span class="vst-badge" :class="`badge-${v.verification_status}`">
                  {{ statusLabel(v.verification_status) }}
                </span>
                <button class="vst-edit-btn" @click="openEdit(v)">✏</button>
              </div>
            </div>

            <!-- Verify buttons — only for closed visits -->
            <div v-if="v.check_out_at" class="vst-actions">
              <button
                class="va-btn va-confirm"
                :class="{ active: v.verification_status === 'confirmed' }"
                :disabled="!!verifying[v.id]"
                @click="verify(v, 'confirmed')"
              >{{ t('calendar.btn_confirm') }}</button>
              <button
                class="va-btn va-discr"
                :class="{ active: v.verification_status === 'discrepancy' }"
                :disabled="!!verifying[v.id]"
                @click="verify(v, 'discrepancy')"
              >{{ t('calendar.btn_discrepancy') }}</button>
            </div>

            <!-- Provenance -->
            <div v-if="v.verified_by" class="vst-provenance">
              ✓ проверено {{ fmtTime(v.verified_at) }}
            </div>
            <div v-if="v.edited_by" class="vst-provenance">
              ✏ изменено {{ fmtTime(v.edited_at) }}
            </div>
          </div>
        </div>
      </template>
    </template>

  </div>

  <!-- Edit modal -->
  <EditVisitModal
    v-if="editingVisit"
    :visit="editingVisit"
    :employee-name="props.employee.full_name"
    :total-hours="dayData?.total_hours ?? 0"
    @close="editingVisit = null"
    @saved="onVisitSaved"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import EditVisitModal from './EditVisitModal.vue'

const { t } = useI18n()

const props = defineProps({
  employee: { type: Object, required: true },
})

const SHOP_TZ = 'Asia/Tashkent'
const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

function todayInTz() {
  return new Date(new Date().toLocaleDateString('sv', { timeZone: SHOP_TZ }) + 'T00:00:00')
}

const now = todayInTz()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1) // 1-based

const isCurrentMonth = computed(
  () => calYear.value === now.getFullYear() && calMonth.value === now.getMonth() + 1,
)
const monthLabel = computed(() => `${MONTHS_RU[calMonth.value - 1]} ${calYear.value}`)

function prevMonth() {
  if (calMonth.value === 1) { calMonth.value = 12; calYear.value-- }
  else calMonth.value--
}
function nextMonth() {
  if (isCurrentMonth.value) return
  if (calMonth.value === 12) { calMonth.value = 1; calYear.value++ }
  else calMonth.value++
}

// ── Calendar data ────────────────────────────────────────────
const calLoading = ref(false)
const dayMap = ref(new Map()) // date-string → DaySummaryItem

async function loadMonth() {
  calLoading.value = true
  dayMap.value = new Map()
  try {
    const data = await api.get(
      `/api/attendance/employee/${props.employee.employee_id}/month?year=${calYear.value}&month=${calMonth.value}`,
    )
    const m = new Map()
    for (const d of data.days) m.set(d.date, d)
    dayMap.value = m
  } catch { /* silent */ } finally {
    calLoading.value = false
  }
}

watch([calYear, calMonth], loadMonth)
onMounted(loadMonth)

// ── Calendar grid computation ────────────────────────────────
const daysInMonth = computed(() => new Date(calYear.value, calMonth.value, 0).getDate())

// Monday-based: 0=Mon … 6=Sun
const leadingBlanks = computed(() => {
  const firstDay = new Date(calYear.value, calMonth.value - 1, 1).getDay()
  return (firstDay + 6) % 7 // convert Sun=0 to Mon=0
})

const calDays = computed(() => {
  const days = []
  for (let d = 1; d <= daysInMonth.value; d++) {
    const dateStr = `${calYear.value}-${String(calMonth.value).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const summary = dayMap.value.get(dateStr) ?? null
    days.push({ date: dateStr, num: d, summary, hasData: !!summary })
  }
  return days
})

const totalDays = computed(() => dayMap.value.size)
const totalMonthHours = computed(() => [...dayMap.value.values()].reduce((s, d) => s + d.total_hours, 0))
const discrepancyDays = computed(() => [...dayMap.value.values()].filter(d => d.has_discrepancy).length)

function dayClass(day) {
  if (!day.summary) return 'cal-empty-day'
  if (day.summary.has_discrepancy) return 'cal-discr'
  if (day.summary.has_open_visit) return 'cal-open'
  return 'cal-present'
}

// ── Stats helpers ────────────────────────────────────────────
function fmtH(h) {
  if (!h) return '0м'
  const m = Math.round(h * 60)
  const hrs = Math.floor(m / 60); const min = m % 60
  if (hrs === 0) return `${min}м`
  if (min === 0) return `${hrs}ч`
  return `${hrs}ч ${min}м`
}
function fmtHShort(h) {
  if (!h) return ''
  const hrs = Math.floor(h)
  const min = Math.round((h - hrs) * 60)
  if (hrs === 0) return `${min}м`
  if (min === 0) return `${hrs}ч`
  return `${hrs}ч`
}

// ── Day detail ───────────────────────────────────────────────
const selectedDay = ref(null) // date string e.g. "2026-06-07"
const dayLoading = ref(false)
const dayData = ref(null)

const dayLabel = computed(() => {
  if (!selectedDay.value) return ''
  const d = new Date(selectedDay.value + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', weekday: 'long' })
})

const allDayVisits = computed(() => {
  if (!dayData.value) return []
  const v = [...dayData.value.visits]
  if (dayData.value.open_visit) v.push(dayData.value.open_visit)
  return v
})

async function openDay(dateStr) {
  selectedDay.value = dateStr
  dayLoading.value = true
  dayData.value = null
  try {
    dayData.value = await api.get(
      `/api/attendance/employee/${props.employee.employee_id}/day?date=${dateStr}`,
    )
  } catch { /* silent */ } finally {
    dayLoading.value = false
  }
}

function fmtTime(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: SHOP_TZ })
}

function visitDur(v) {
  if (!v.check_out_at) return ''
  const ms = new Date(v.check_out_at) - new Date(v.check_in_at)
  return fmtH(ms / 3600000)
}

function statusLabel(s) {
  const map = { not_checked: t('manager.status_not_checked'), confirmed: t('manager.status_confirmed'), discrepancy: t('manager.status_discrepancy') }
  return map[s] ?? s
}

// ── Verification ─────────────────────────────────────────────
const verifying = ref({})

async function verify(visit, status) {
  if (verifying.value[visit.id]) return
  verifying.value[visit.id] = true
  try {
    const updated = await api.post(`/api/attendance/${visit.id}/verify`, { status })
    patchVisitInDay(updated)
  } catch { /* silent */ } finally {
    verifying.value[visit.id] = false
  }
}

function patchVisitInDay(updated) {
  if (!dayData.value) return
  const replace = (list) => list.map(v => v.id === updated.id ? updated : v)
  dayData.value = {
    ...dayData.value,
    visits: replace(dayData.value.visits),
    open_visit: dayData.value.open_visit?.id === updated.id ? updated : dayData.value.open_visit,
  }
  // Refresh calendar dot for this day
  loadMonth()
}

// ── Edit modal ───────────────────────────────────────────────
const editingVisit = ref(null)

function openEdit(visit) {
  editingVisit.value = visit
}

function onVisitSaved(updated) {
  editingVisit.value = null
  patchVisitInDay(updated)
  // Recalculate total hours for the day
  if (dayData.value) {
    const allClosed = [...dayData.value.visits, dayData.value.open_visit]
      .filter(v => v && v.check_out_at)
    const total = allClosed.reduce((s, v) => {
      return s + (new Date(v.check_out_at) - new Date(v.check_in_at)) / 3600000
    }, 0)
    dayData.value = { ...dayData.value, total_hours: Math.round(total * 10000) / 10000 }
  }
}
</script>

<style scoped>
.att-cal-view {
  padding: 0 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── Month nav ─────────────────────────────────────────────── */
.month-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--c-surface);
  border-radius: 14px;
  padding: 0.125rem 0.5rem;
  margin-top: 0.5rem;
}
.mnav-btn {
  background: transparent; border: none;
  color: var(--c-text); width: 38px; height: 38px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; border-radius: 10px; transition: background 0.15s;
}
.mnav-btn:active { background: var(--c-bg); }
.mnav-btn:disabled { opacity: 0.3; cursor: default; }
.month-label { font-size: 0.95rem; font-weight: 600; color: var(--c-text); }

/* ── Month stats ───────────────────────────────────────────── */
.month-stats {
  display: flex;
  align-items: center;
  background: var(--c-surface);
  border-radius: 14px;
  overflow: hidden;
}
.mstat { flex: 1; padding: 0.75rem 0.5rem; text-align: center; }
.mstat-val { display: block; font-size: 1.25rem; font-weight: 800; color: var(--c-text); line-height: 1; }
.mstat-warn { color: var(--c-negative); }
.mstat-lbl { display: block; font-size: 0.65rem; color: var(--c-hint); margin-top: 0.15rem; text-transform: uppercase; letter-spacing: 0.04em; }
.mstat-div { width: 1px; height: 2rem; background: var(--c-hint); opacity: 0.3; flex-shrink: 0; }

/* ── Loading ───────────────────────────────────────────────── */
.cal-loading { display: flex; justify-content: center; padding: 2rem 0; }
.spinner {
  width: 26px; height: 26px;
  border: 3px solid var(--c-surface);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Calendar grid ─────────────────────────────────────────── */
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  background: var(--c-surface);
  border-radius: 16px;
  padding: 0.75rem;
}
.cal-wd {
  text-align: center;
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--c-hint);
  padding-bottom: 0.375rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.cal-blank { background: transparent !important; cursor: default !important; }
.cal-cell {
  aspect-ratio: 1;
  border-radius: 10px;
  border: none;
  background: var(--c-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: transform 0.1s;
  gap: 1px;
  padding: 0;
}
.cal-present   { background: var(--c-positive-dim); cursor: pointer; }
.cal-open      { background: var(--c-accent); cursor: pointer; }
.cal-discr     { background: var(--c-negative-dim); cursor: pointer; }
.cal-empty-day { background: var(--c-bg); }
.cal-cell:active { transform: scale(0.93); }

.cal-day-num {
  font-size: 0.85rem;
  font-weight: 700;
  line-height: 1;
  color: var(--c-text);
}
.cal-present .cal-day-num   { color: var(--c-positive-dark); }
.cal-open    .cal-day-num   { color: var(--c-accent-text); }
.cal-discr   .cal-day-num   { color: var(--c-negative-dark); }
.cal-empty-day .cal-day-num { color: var(--c-hint); opacity: 0.6; }

.cal-hours {
  font-size: 0.55rem;
  font-weight: 600;
  color: var(--c-hint);
  line-height: 1;
}
.cal-present .cal-hours { color: var(--c-positive-dark); opacity: 0.75; }
.cal-open    .cal-hours { color: var(--c-accent-text); opacity: 0.8; }
.cal-discr   .cal-hours { color: var(--c-negative-dark); opacity: 0.75; }

/* ── Legend ────────────────────────────────────────────────── */
.legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0 0.25rem;
}
.leg-item { display: flex; align-items: center; gap: 0.35rem; font-size: 0.75rem; color: var(--c-hint); }
.leg-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.leg-present { background: var(--c-positive-dim); }
.leg-open    { background: var(--c-accent); }
.leg-discr   { background: var(--c-negative-dim); }

.cal-empty { font-size: 0.875rem; color: var(--c-hint); text-align: center; padding: 1rem 0; }

/* ── Day detail ────────────────────────────────────────────── */
.day-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0 0.25rem;
}
.back-day-btn {
  display: flex; align-items: center; gap: 0.2rem;
  background: none; border: none;
  color: var(--c-accent); font-size: 0.875rem; font-weight: 600;
  cursor: pointer; padding: 0.25rem 0.5rem 0.25rem 0;
  flex-shrink: 0;
}
.day-title {
  font-size: 0.95rem; font-weight: 700; color: var(--c-text);
  text-transform: capitalize;
}

.day-total-pill {
  display: inline-block;
  background: var(--c-surface);
  border-radius: 99px;
  padding: 0.35rem 1rem;
  font-size: 0.83rem;
  color: var(--c-hint);
  align-self: flex-start;
}
.day-total-pill strong { color: var(--c-text); }

.visit-list { display: flex; flex-direction: column; gap: 0.5rem; }
.visit-card {
  background: var(--c-surface);
  border-radius: 14px;
  padding: 0.75rem 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-left: 3px solid transparent;
}
.vst-confirmed   { border-left-color: var(--c-positive); }
.vst-discrepancy { border-left-color: var(--c-negative); }
.vst-not_checked { border-left-color: var(--c-hint); }

/* Top row: times + badge + edit */
.vst-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.vst-times { display: flex; align-items: center; gap: 0.4rem; }
.vst-time { font-size: 0.95rem; font-weight: 600; color: var(--c-text); }
.vst-arrow { font-size: 0.75rem; color: var(--c-hint); }
.vst-dur {
  font-size: 0.72rem; font-weight: 700;
  background: var(--c-bg);
  border-radius: 5px; padding: 0.1rem 0.4rem;
  color: var(--c-accent);
}
.vst-right { display: flex; align-items: center; gap: 0.375rem; flex-shrink: 0; }
.vst-badge {
  font-size: 0.68rem; font-weight: 600;
  border-radius: 6px; padding: 0.2rem 0.45rem;
  white-space: nowrap;
}
.badge-not_checked  { background: var(--c-bg); color: var(--c-hint); }
.badge-confirmed    { background: var(--c-positive-dim); color: var(--c-positive-dark); }
.badge-discrepancy  { background: var(--c-negative-dim); color: var(--c-negative-dark); }

.vst-edit-btn {
  background: var(--c-bg);
  border: none;
  border-radius: 7px;
  width: 28px; height: 28px;
  font-size: 0.8rem;
  cursor: pointer;
  color: var(--c-hint);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}
.vst-edit-btn:active { background: var(--c-surface); }

/* Action buttons */
.vst-actions { display: flex; gap: 0.375rem; }
.va-btn {
  flex: 1;
  border: none; border-radius: 9px;
  padding: 0.45rem 0.5rem;
  font-size: 0.78rem; font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.va-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.va-confirm { background: var(--c-positive-bg); color: var(--c-positive); }
.va-confirm.active { background: var(--c-positive); color: #fff; }
.va-discr { background: var(--c-negative-dim); color: var(--c-negative); }
.va-discr.active { background: var(--c-negative); color: #fff; }

/* Provenance */
.vst-provenance { font-size: 0.7rem; color: var(--c-hint); }
</style>
