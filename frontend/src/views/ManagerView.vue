<template>
  <div class="manager-view">

    <!-- Навигация по дате -->
    <div class="date-nav-bar">
      <button class="date-arrow" @click="prevDay">‹</button>
      <div class="date-center">
        <div class="date-weekday">{{ displayWeekday }}</div>
        <div class="date-full">{{ displayDate }}</div>
      </div>
      <button class="date-arrow" :disabled="isToday" @click="nextDay">›</button>
    </div>

    <!-- Итого за день -->
    <div v-if="!loading && summary.length" class="day-summary">
      <div class="ds-item">
        <div class="ds-val">{{ onShiftCount }}</div>
        <div class="ds-lbl">{{ t('manager.on_shift') }}</div>
      </div>
      <div class="ds-div" />
      <div class="ds-item">
        <div class="ds-val">{{ fmtH(totalHours) }}</div>
        <div class="ds-lbl">{{ t('manager.total_hours_label') }}</div>
      </div>
      <div class="ds-div" />
      <div class="ds-item">
        <div class="ds-val">{{ summary.length }}</div>
        <div class="ds-lbl">{{ t('manager.employees_label') }}</div>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="loading-row">···</div>
    <p v-else-if="loadError" class="error-msg">{{ loadError }}</p>
    <div v-else-if="summary.length === 0" class="empty-day">
      <div class="empty-icon">👤</div>
      <div class="empty-text">{{ t('manager.no_employees') }}</div>
    </div>

    <!-- Карточки сотрудников -->
    <div v-else class="emp-list">
      <div v-for="emp in summary" :key="emp.employee_id" class="emp-card">

        <!-- Шапка карточки -->
        <div class="emp-head">
          <div class="emp-avatar">{{ initials(emp.full_name) }}</div>
          <div class="emp-info">
            <div class="emp-name">{{ emp.full_name }}</div>
            <div class="emp-status" :class="emp.open_visit ? 'status-on' : 'status-off'">
              <span class="status-dot" />
              {{ emp.open_visit
                ? t('manager.on_shift_since', { time: fmtTime(emp.open_visit.check_in_at) })
                : t('manager.not_on_shift') }}
            </div>
          </div>
          <div class="emp-hours-badge">{{ fmtH(emp.total_hours) }}</div>
        </div>

        <!-- Визиты -->
        <div v-if="allVisits(emp).length" class="visits">
          <div
            v-for="v in allVisits(emp)"
            :key="v.id"
            class="visit-block"
            :class="`vst-${v.verification_status}`"
          >
            <div class="visit-row-main">
              <!-- Время -->
              <div class="visit-time">
                <span class="vt-in">{{ fmtTime(v.check_in_at) }}</span>
                <span class="vt-sep">→</span>
                <span class="vt-out">{{ v.check_out_at ? fmtTime(v.check_out_at) : '…' }}</span>
                <span v-if="v.check_out_at" class="vt-dur">{{ visitDur(v) }}</span>
              </div>
              <!-- Статус -->
              <span class="visit-status-badge" :class="`badge-${v.verification_status}`">
                {{ t(`manager.status_${v.verification_status}`) }}
              </span>
            </div>

            <!-- Кто проверил / изменил -->
            <div v-if="v.verified_by" class="visit-provenance">
              ✓ {{ resolveName(v.verified_by) }}, {{ fmtTime(v.verified_at) }}
            </div>
            <div v-if="v.edited_by" class="visit-provenance">
              ✏ {{ resolveName(v.edited_by) }}, {{ fmtTime(v.edited_at) }}
            </div>

            <!-- Кнопки верификации -->
            <div v-if="v.check_out_at" class="visit-actions">
              <button
                class="va-btn va-confirm"
                :class="{ active: v.verification_status === 'confirmed' }"
                :disabled="verifying[v.id]"
                @click="verify(emp, v, 'confirmed')"
              >✓ {{ t('manager.btn_confirm') }}</button>
              <button
                class="va-btn va-discr"
                :class="{ active: v.verification_status === 'discrepancy' }"
                :disabled="verifying[v.id]"
                @click="verify(emp, v, 'discrepancy')"
              >⚠ {{ t('manager.btn_discrepancy_full') }}</button>
              <button class="va-btn va-edit" @click="openEdit(emp, v)">
                ✏
              </button>
            </div>
          </div>
        </div>
        <div v-else class="no-visits-hint">{{ t('manager.no_visits_today') }}</div>
      </div>
    </div>

    <!-- Расхождения — раскрывающийся раздел -->
    <div class="discr-section">
      <button class="discr-toggle" @click="showDiscr = !showDiscr">
        {{ showDiscr ? '▾' : '▸' }} {{ t('manager.discrepancies_title') }}
      </button>
      <div v-if="showDiscr" class="discr-body">
        <div class="discr-range">
          <div class="discr-field">
            <label>{{ t('manager.discrepancies_from') }}</label>
            <input type="date" v-model="discrFrom" class="date-input" />
          </div>
          <div class="discr-field">
            <label>{{ t('manager.discrepancies_to') }}</label>
            <input type="date" v-model="discrTo" class="date-input" />
          </div>
          <button class="discr-load-btn" @click="loadDiscrepancies" :disabled="discrLoading">
            {{ t('manager.discrepancies_load') }}
          </button>
        </div>
        <div v-if="discrLoading" class="loading-row">···</div>
        <p v-else-if="discrLoaded && discrepancies.length === 0" class="empty-text-sm">
          {{ t('manager.discrepancies_empty') }}
        </p>
        <div v-else class="discr-list">
          <div v-for="d in discrepancies" :key="d.employee_id" class="discr-row">
            <div class="discr-avatar">{{ initials(d.full_name) }}</div>
            <div class="discr-name">{{ d.full_name }}</div>
            <div class="discr-count">{{ d.count }}</div>
          </div>
        </div>
      </div>
    </div>

    <EditVisitModal
      v-if="editingVisit"
      :visit="editingVisit"
      :employee-name="editingEmpName"
      :total-hours="editingEmpHours"
      @close="editingVisit = null"
      @saved="onVisitSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import EditVisitModal from './EditVisitModal.vue'

const props = defineProps({
  currentEmployee: { type: Object, default: null },
})

const { t } = useI18n()
const SHOP_TZ = 'Asia/Tashkent'

function todayStr() {
  return new Date().toLocaleDateString('sv', { timeZone: SHOP_TZ })
}

const currentDate = ref(todayStr())
const summary = ref([])
const loading = ref(false)
const loadError = ref('')
const showDiscr = ref(false)

const isToday = computed(() => currentDate.value === todayStr())

const displayWeekday = computed(() => {
  const d = new Date(currentDate.value + 'T00:00:00')
  const wd = d.toLocaleDateString('ru-RU', { weekday: 'long', timeZone: SHOP_TZ })
  return wd.charAt(0).toUpperCase() + wd.slice(1)
})

const displayDate = computed(() => {
  const d = new Date(currentDate.value + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', timeZone: SHOP_TZ })
})

const onShiftCount = computed(() => summary.value.filter(e => e.open_visit).length)
const totalHours = computed(() => summary.value.reduce((s, e) => s + (e.total_hours || 0), 0))

const nameMap = computed(() => {
  const m = new Map()
  for (const e of summary.value) m.set(e.employee_id, e.full_name)
  if (props.currentEmployee) m.set(props.currentEmployee.id, props.currentEmployee.full_name)
  return m
})

function resolveName(id) { return nameMap.value.get(id) ?? `#${id}` }

function initials(name) {
  return (name ?? '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function fmtTime(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: SHOP_TZ })
}

function fmtH(h) {
  if (!h) return '0м'
  const m = Math.round(h * 60)
  const hrs = Math.floor(m / 60); const min = m % 60
  if (hrs === 0) return `${min}м`
  if (min === 0) return `${hrs}ч`
  return `${hrs}ч ${min}м`
}

function visitDur(v) {
  if (!v.check_out_at) return ''
  const ms = new Date(v.check_out_at) - new Date(v.check_in_at)
  return fmtH(ms / 3600000)
}

function prevDay() {
  const d = new Date(currentDate.value + 'T00:00:00')
  d.setDate(d.getDate() - 1)
  currentDate.value = d.toLocaleDateString('sv', { timeZone: SHOP_TZ })
}

function nextDay() {
  if (isToday.value) return
  const d = new Date(currentDate.value + 'T00:00:00')
  d.setDate(d.getDate() + 1)
  currentDate.value = d.toLocaleDateString('sv', { timeZone: SHOP_TZ })
}

function allVisits(emp) {
  const closed = emp.visits ?? []
  return emp.open_visit ? [...closed, emp.open_visit] : closed
}

async function loadSummary() {
  loading.value = true; loadError.value = ''
  try {
    const data = await api.get(`/api/attendance/summary?day=${currentDate.value}`)
    summary.value = data.employees ?? []
  } catch (err) {
    loadError.value = t(`errors.${err.code ?? 'unknown'}`)
    summary.value = []
  } finally { loading.value = false }
}

watch(currentDate, loadSummary)
onMounted(loadSummary)

// Верификация
const verifying = ref({})
async function verify(emp, visit, status) {
  if (verifying.value[visit.id]) return
  verifying.value[visit.id] = true
  try {
    const updated = await api.post(`/api/attendance/${visit.id}/verify`, { status })
    const ei = summary.value.findIndex(e => e.employee_id === emp.employee_id)
    if (ei !== -1) {
      const e = summary.value[ei]
      summary.value[ei] = {
        ...e,
        visits: (e.visits ?? []).map(v => v.id === updated.id ? updated : v),
        open_visit: e.open_visit?.id === updated.id ? updated : e.open_visit,
      }
    }
  } catch { /* silent */ } finally { verifying.value[visit.id] = false }
}

// Редактирование
const editingVisit = ref(null)
const editingEmpName = ref('')
const editingEmpHours = ref(0)

function openEdit(emp, visit) {
  editingVisit.value = visit
  editingEmpName.value = emp.full_name
  editingEmpHours.value = emp.total_hours
}
function onVisitSaved() { editingVisit.value = null; loadSummary() }

// Расхождения
const discrFrom = ref((() => {
  const d = new Date(); d.setDate(d.getDate() - 30)
  return d.toLocaleDateString('sv', { timeZone: SHOP_TZ })
})())
const discrTo = ref(todayStr())
const discrepancies = ref([])
const discrLoading = ref(false)
const discrLoaded = ref(false)

async function loadDiscrepancies() {
  if (discrLoading.value) return
  discrLoading.value = true; discrLoaded.value = false
  try {
    const data = await api.get(`/api/attendance/discrepancies?from_date=${discrFrom.value}&to_date=${discrTo.value}`)
    discrepancies.value = data.employees ?? []
  } catch { discrepancies.value = [] } finally {
    discrLoading.value = false; discrLoaded.value = true
  }
}
</script>

<style scoped>
.manager-view { padding: 0 0 1rem; max-width: 600px; margin: 0 auto; }

/* Date nav */
.date-nav-bar {
  display: flex; align-items: center; gap: 0;
  padding: 0.875rem 1rem 0.625rem;
  position: sticky; top: 0; z-index: 10;
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-surface);
}
.date-arrow {
  background: var(--c-surface);
  border: none; border-radius: 10px; width: 2.25rem; height: 2.25rem;
  font-size: 1.25rem; cursor: pointer; color: var(--c-text);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.date-arrow:disabled { opacity: 0.3; cursor: default; }
.date-center { flex: 1; text-align: center; }
.date-weekday { font-size: 0.75rem; color: var(--c-hint); text-transform: capitalize; }
.date-full { font-size: 0.95rem; font-weight: 600; color: var(--c-text); }

/* Day summary bar */
.day-summary {
  display: flex; align-items: center;
  margin: 0.75rem 1rem;
  background: var(--c-surface);
  border-radius: 14px; overflow: hidden;
}
.ds-item { flex: 1; padding: 0.75rem 0.5rem; text-align: center; }
.ds-val { font-size: 1.3rem; font-weight: 800; color: var(--c-text); line-height: 1; }
.ds-lbl { font-size: 0.65rem; color: var(--c-hint); margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.04em; }
.ds-div { width: 1px; height: 2.5rem; background: var(--c-hint); opacity: 0.4; flex-shrink: 0; }

/* Employee list */
.emp-list { display: flex; flex-direction: column; gap: 0.75rem; padding: 0 1rem; }

.emp-card {
  background: var(--c-surface);
  border-radius: 16px; overflow: hidden;
}

/* Card header */
.emp-head {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.875rem 1rem 0.75rem;
}
.emp-avatar {
  width: 2.5rem; height: 2.5rem; border-radius: 50%; flex-shrink: 0;
  background: var(--c-accent);
  color: var(--c-accent-text);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 700;
}
.emp-info { flex: 1; min-width: 0; }
.emp-name { font-weight: 600; font-size: 0.95rem; color: var(--c-text); }
.emp-status { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; margin-top: 0.1rem; }
.status-dot { width: 0.45rem; height: 0.45rem; border-radius: 50%; flex-shrink: 0; }
.status-on { color: var(--c-positive); }
.status-on .status-dot { background: var(--c-positive); box-shadow: 0 0 0 3px rgba(39,174,96,0.2); animation: pulse 2s infinite; }
.status-off { color: var(--c-hint); }
.status-off .status-dot { background: var(--c-hint); }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 3px rgba(39,174,96,.2);}50%{box-shadow:0 0 0 6px rgba(39,174,96,.05);} }
.emp-hours-badge {
  background: var(--c-bg);
  border-radius: 10px; padding: 0.25rem 0.6rem;
  font-size: 0.85rem; font-weight: 700; color: var(--c-text);
  flex-shrink: 0;
}

/* Visits */
.visits { display: flex; flex-direction: column; gap: 0; }
.visit-block {
  background: var(--c-bg);
  margin: 0 0.75rem 0.5rem; border-radius: 12px;
  padding: 0.75rem 0.875rem;
  border-left: 3px solid transparent;
}
.vst-confirmed    { border-left-color: var(--c-positive); }
.vst-discrepancy  { border-left-color: var(--c-negative); }
.vst-not_checked  { border-left-color: var(--c-hint); }

.visit-row-main { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.35rem; }
.visit-time { display: flex; align-items: center; gap: 0.35rem; font-size: 0.92rem; }
.vt-in  { font-weight: 600; color: var(--c-text); }
.vt-sep { color: var(--c-hint); font-size: 0.75rem; }
.vt-out { font-weight: 600; color: var(--c-text); }
.vt-dur {
  font-size: 0.72rem; font-weight: 700;
  background: var(--c-surface);
  border-radius: 5px; padding: 0.1rem 0.4rem;
  color: var(--c-accent);
}

.visit-status-badge {
  font-size: 0.7rem; font-weight: 600; border-radius: 6px; padding: 0.15rem 0.45rem; white-space: nowrap;
}
.badge-not_checked  { background: var(--c-surface); color: var(--c-hint); }
.badge-confirmed    { background: var(--c-positive-dim); color: var(--c-positive-dark); }
.badge-discrepancy  { background: var(--c-negative-dim); color: var(--c-negative-dark); }

.visit-provenance { font-size: 0.72rem; color: var(--c-hint); margin-bottom: 0.15rem; }

.visit-actions { display: flex; gap: 0.375rem; margin-top: 0.5rem; }
.va-btn {
  border: none; border-radius: 8px; padding: 0.4rem 0.75rem;
  font-size: 0.78rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.va-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.va-confirm { background: var(--c-positive-bg); color: var(--c-positive); flex: 1; }
.va-confirm.active { background: var(--c-positive); color: #fff; }
.va-discr { background: var(--c-negative-dim); color: var(--c-negative); flex: 1; }
.va-discr.active { background: var(--c-negative); color: #fff; }
.va-edit { background: var(--c-surface); color: var(--c-hint); width: 2.25rem; flex-shrink: 0; }

.no-visits-hint { font-size: 0.8rem; color: var(--c-hint); text-align: center; padding: 0.5rem 1rem 0.875rem; }

/* Discrepancies */
.discr-section { margin: 1.25rem 1rem 0; }
.discr-toggle {
  background: none; border: none; font-size: 0.875rem; font-weight: 600;
  color: var(--c-accent); cursor: pointer; padding: 0.25rem 0;
}
.discr-body { margin-top: 0.75rem; }
.discr-range { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.75rem; }
.discr-field { display: flex; align-items: center; gap: 0.5rem; }
.discr-field label { font-size: 0.78rem; color: var(--c-hint); width: 4rem; flex-shrink: 0; }
.date-input {
  flex: 1; background: var(--c-surface); border: none;
  border-radius: 8px; padding: 0.4rem 0.625rem; font-size: 0.875rem;
  color: var(--c-text);
}
.discr-load-btn {
  background: var(--c-accent);
  color: var(--c-accent-text);
  border: none; border-radius: 10px; padding: 0.55rem 1rem;
  font-size: 0.875rem; font-weight: 600; cursor: pointer; align-self: flex-start;
}
.discr-load-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.discr-list { display: flex; flex-direction: column; gap: 0.375rem; }
.discr-row {
  display: flex; align-items: center; gap: 0.625rem;
  background: var(--c-surface);
  border-radius: 10px; padding: 0.6rem 0.875rem;
}
.discr-avatar {
  width: 2rem; height: 2rem; border-radius: 50%; flex-shrink: 0;
  background: var(--c-negative-dim); color: var(--c-negative-dark);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700;
}
.discr-name { flex: 1; font-size: 0.9rem; color: var(--c-text); }
.discr-count {
  background: var(--c-negative-dim); color: var(--c-negative-dark); border-radius: 99px;
  font-size: 0.75rem; font-weight: 700; padding: 0.1rem 0.5rem;
}

/* Utils */
.loading-row { text-align: center; padding: 2rem 0; font-size: 1.5rem; letter-spacing: 0.2em; color: var(--c-hint); }
.error-msg { color: var(--c-negative); font-size: 0.875rem; padding: 0 1rem; }
.empty-day { display: flex; flex-direction: column; align-items: center; padding: 3rem 1rem; gap: 0.5rem; }
.empty-icon { font-size: 3rem; }
.empty-text { font-size: 0.9rem; color: var(--c-hint); }
.empty-text-sm { font-size: 0.85rem; color: var(--c-hint); text-align: center; padding: 0.5rem 0; }
</style>
