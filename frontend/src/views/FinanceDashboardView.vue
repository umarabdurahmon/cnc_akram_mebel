<template>
  <div class="finance-view">

    <!-- Month navigator -->
    <div class="month-nav">
      <button class="nav-btn" @click="goPrevMonth">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
      <span class="month-label">{{ monthLabel }}</span>
      <button class="nav-btn" :disabled="isCurrentMonth" @click="goNextMonth">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
      </button>
    </div>

    <div v-if="loading" class="state-box">
      <div class="spinner"></div>
      <span class="state-label">{{ t('finance.loading') }}</span>
    </div>
    <p v-else-if="error" class="error-msg">{{ error }}</p>

    <template v-else-if="report">

      <!-- Profit hero -->
      <div class="hero-card" :class="profitClass(report.profit)">
        <span class="hero-label">{{ t('finance.profit') }}</span>
        <span class="hero-value">{{ display(report.profit) }}</span>
        <div class="hero-bottom-row">
          <span class="hero-badge" :class="profitClass(report.profit)">
            {{ toNum(report.profit) >= 0 ? ('↑ ' + t('finance.revenue')) : ('↓ ' + t('finance.loss')) }}
          </span>
          <span
            v-if="prevReport && deltaLabel(report.profit, prevReport.profit)"
            class="hero-delta"
            :class="deltaUp(report.profit, prevReport.profit) ? 'delta-up' : 'delta-down'"
          >{{ deltaLabel(report.profit, prevReport.profit) }} {{ t('finance.vs_prev') }}</span>
        </div>
      </div>

      <!-- Revenue + Expenses side by side -->
      <div class="metrics-row">
        <div class="metric-card income">
          <div class="metric-icon">↑</div>
          <span class="metric-label">{{ t('finance.revenue') }}</span>
          <span class="metric-value positive">{{ display(report.revenue) }}</span>
          <span
            v-if="prevReport && deltaLabel(report.revenue, prevReport.revenue)"
            class="metric-delta"
            :class="deltaUp(report.revenue, prevReport.revenue) ? 'delta-up' : 'delta-down'"
          >{{ deltaLabel(report.revenue, prevReport.revenue) }}</span>
        </div>
        <div class="metric-card expenses">
          <div class="metric-icon">↓</div>
          <span class="metric-label">{{ t('finance.expenses') }}</span>
          <span class="metric-value negative">{{ display(report.total_expenses) }}</span>
          <span
            v-if="prevReport && deltaLabel(report.total_expenses, prevReport.total_expenses)"
            class="metric-delta"
            :class="deltaUp(report.total_expenses, prevReport.total_expenses) ? 'delta-down' : 'delta-up'"
          >{{ deltaLabel(report.total_expenses, prevReport.total_expenses) }}</span>
        </div>
      </div>

      <!-- Expense breakdown bars -->
      <div class="split-card">
        <p class="section-title">{{ t('finance.expense_structure') }}</p>

        <div class="split-item">
          <div class="split-header">
            <span class="split-dot order-dot"></span>
            <span class="split-label">{{ t('finance.order_expenses') }}</span>
            <span class="split-pct">{{ orderExpPct }}%</span>
            <span class="split-val">{{ display(report.order_expenses) }}</span>
          </div>
          <div class="split-track">
            <div class="split-fill order-fill" :style="{ width: orderExpPct + '%' }"></div>
          </div>
        </div>

        <div class="split-item">
          <div class="split-header">
            <span class="split-dot op-dot"></span>
            <span class="split-label">{{ t('finance.operating_expenses') }}</span>
            <span class="split-pct">{{ opExpPct }}%</span>
            <span class="split-val">{{ display(report.operating_expenses) }}</span>
          </div>
          <div class="split-track">
            <div class="split-fill op-fill" :style="{ width: opExpPct + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Category breakdown -->
      <div v-if="report.breakdown.length > 0" class="breakdown-card">
        <p class="section-title">{{ t('finance.breakdown') }}</p>
        <ul class="breakdown-list">
          <li
            v-for="(item, idx) in sortedBreakdown"
            :key="item.category_id"
            class="breakdown-row"
          >
            <div class="bd-rank">{{ idx + 1 }}</div>
            <div class="bd-body">
              <div class="bd-header">
                <span class="bd-name">{{ item.category_name }}</span>
                <span class="bd-amount">{{ display(item.amount) }}</span>
              </div>
              <div class="bd-track">
                <div class="bd-fill" :style="{ width: barPct(item.amount) + '%' }"></div>
              </div>
              <span class="bd-pct">{{ barPct(item.amount) }}% {{ t('finance.of_expenses') }}</span>
            </div>
          </li>
        </ul>
      </div>
      <div v-else class="empty-state">
        <span class="empty-icon">📊</span>
        <span class="empty-label">{{ t('finance.no_data') }}</span>
      </div>

      <!-- Link to reports page -->
      <button class="report-action-btn reports-link" @click="emit('go-reports', { year: year, month: month })">
        <span class="ra-icon">📊</span>
        <span class="ra-label">{{ t('finance.reports_page') }}</span>
        <svg class="ra-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
      </button>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { displayAmount, profitClass } from '../money.js'

const emit = defineEmits(['go-reports'])

const { t, locale } = useI18n()

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)
const report = ref(null)
const prevReport = ref(null)
const loading = ref(false)
const error = ref('')

const isCurrentMonth = computed(
  () => year.value === today.getFullYear() && month.value === today.getMonth() + 1,
)

const monthLabel = computed(() => {
  const d = new Date(year.value, month.value - 1, 1)
  const name = d.toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { month: 'long' })
  return name.charAt(0).toUpperCase() + name.slice(1) + ' ' + year.value
})

function display(str) { return displayAmount(str, 'сум') }
function toNum(str) { return parseFloat(str) || 0 }

function prevMonthCoords() {
  return month.value === 1
    ? { y: year.value - 1, m: 12 }
    : { y: year.value, m: month.value - 1 }
}

function deltaLabel(current, previous) {
  const cur = toNum(current)
  const prev = toNum(previous)
  if (!prev) return null
  const pct = Math.round(((cur - prev) / Math.abs(prev)) * 100)
  return (pct >= 0 ? '+' : '') + pct + '%'
}

function deltaUp(current, previous) {
  return toNum(current) >= toNum(previous)
}

const sortedBreakdown = computed(() => {
  if (!report.value) return []
  return [...report.value.breakdown].sort((a, b) => toNum(b.amount) - toNum(a.amount))
})

const maxBreakdown = computed(() => {
  if (!sortedBreakdown.value.length) return 1
  return toNum(sortedBreakdown.value[0].amount) || 1
})

function barPct(amount) {
  return Math.round((toNum(amount) / maxBreakdown.value) * 100)
}

const orderExpPct = computed(() => {
  const total = toNum(report.value?.total_expenses)
  if (!total) return 0
  return Math.round((toNum(report.value?.order_expenses) / total) * 100)
})

const opExpPct = computed(() => {
  const total = toNum(report.value?.total_expenses)
  if (!total) return 0
  return Math.round((toNum(report.value?.operating_expenses) / total) * 100)
})

function goPrevMonth() {
  if (month.value === 1) { month.value = 12; year.value-- }
  else month.value--
}

function goNextMonth() {
  if (isCurrentMonth.value) return
  if (month.value === 12) { month.value = 1; year.value++ }
  else month.value++
}

async function loadReport() {
  loading.value = true
  error.value = ''
  try {
    const { y, m } = prevMonthCoords()
    const [cur, prev] = await Promise.all([
      api.get(`/api/reports/monthly?year=${year.value}&month=${month.value}`),
      api.get(`/api/reports/monthly?year=${y}&month=${m}`),
    ])
    report.value = cur
    prevReport.value = prev
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
}


watch([year, month], loadReport)
onMounted(loadReport)
defineExpose({ reload: loadReport })
</script>

<style scoped>
.finance-view {
  padding: 0 0.875rem 2rem;
  width: 100%;
  box-sizing: border-box;
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
  padding: 0.25rem 0.5rem;
}
.nav-btn {
  background: transparent;
  border: none;
  color: var(--c-text);
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 10px;
  transition: background 0.15s;
}
.nav-btn:active { background: var(--c-bg); }
.nav-btn:disabled { opacity: 0.3; cursor: default; }
.month-label { font-size: 1rem; font-weight: 600; color: var(--c-text); }

/* ── Loading state ─────────────────────────────────────────── */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 0;
}
.state-label { font-size: 0.875rem; color: var(--c-hint); }
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--c-surface);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { color: var(--c-negative); font-size: 0.875rem; text-align: center; }

/* ── Profit hero ───────────────────────────────────────────── */
.hero-card {
  background: var(--c-surface);
  border-radius: 20px;
  padding: 1.5rem 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  text-align: center;
  border: 2px solid transparent;
}
.hero-card.positive { border-color: var(--c-positive); }
.hero-card.negative { border-color: var(--c-negative); }
.hero-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--c-hint);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.hero-value {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.1;
  color: var(--c-text);
}
.hero-card.positive .hero-value { color: var(--c-positive); }
.hero-card.negative .hero-value { color: var(--c-negative); }
.hero-bottom-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 0.25rem;
}
.hero-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.75rem;
  border-radius: 100px;
}
.hero-badge.positive { background: var(--c-positive-dim); color: var(--c-positive-dark); }
.hero-badge.negative { background: var(--c-negative-dim); color: var(--c-negative-dark); }
.hero-delta {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--c-hint);
}
.hero-delta.delta-up { color: var(--c-positive-dark); }
.hero-delta.delta-down { color: var(--c-negative-dark); }

/* ── Revenue / Expenses row ────────────────────────────────── */
.metrics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.625rem; }
.metric-card {
  background: var(--c-surface);
  border-radius: 16px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.metric-icon {
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.125rem;
}
.metric-card.income .metric-icon { color: var(--c-positive); }
.metric-card.expenses .metric-icon { color: var(--c-negative); }
.metric-label { font-size: 0.75rem; color: var(--c-hint); }
.metric-value { font-size: 1.05rem; font-weight: 700; }
.positive { color: var(--c-positive); }
.negative { color: var(--c-negative); }
.metric-delta {
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 0.1rem;
}
.delta-up { color: var(--c-positive-dark); }
.delta-down { color: var(--c-negative-dark); }

/* ── Section titles ────────────────────────────────────────── */
.section-title {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--c-hint);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin: 0 0 0.875rem;
}

/* ── Expense split ─────────────────────────────────────────── */
.split-card {
  background: var(--c-surface);
  border-radius: 16px;
  padding: 1rem;
}
.split-item { margin-bottom: 0.875rem; }
.split-item:last-child { margin-bottom: 0; }
.split-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.split-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.order-dot { background: var(--c-negative); }
.op-dot { background: var(--c-warning); }
.split-label { font-size: 0.83rem; color: var(--c-text); flex: 1; }
.split-pct {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--c-hint);
  min-width: 30px;
  text-align: right;
}
.split-val {
  font-size: 0.83rem;
  font-weight: 700;
  color: var(--c-text);
  min-width: 80px;
  text-align: right;
}
.split-track {
  height: 7px;
  background: var(--c-bg);
  border-radius: 6px;
  overflow: hidden;
}
.split-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
  min-width: 4px;
}
.order-fill { background: var(--c-negative); }
.op-fill { background: var(--c-warning); }

/* ── Category breakdown ────────────────────────────────────── */
.breakdown-card {
  background: var(--c-surface);
  border-radius: 16px;
  padding: 1rem;
}
.breakdown-list {
  list-style: none;
  padding: 0; margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.breakdown-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}
.bd-rank {
  width: 22px; height: 22px;
  background: var(--c-bg);
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--c-hint);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}
.bd-body { flex: 1; min-width: 0; }
.bd-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.3rem;
}
.bd-name { font-size: 0.875rem; color: var(--c-text); font-weight: 500; }
.bd-amount { font-size: 0.875rem; font-weight: 700; color: var(--c-text); white-space: nowrap; margin-left: 0.5rem; }
.bd-track {
  height: 7px;
  background: var(--c-bg);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 0.25rem;
}
.bd-fill {
  height: 100%;
  border-radius: 6px;
  background: var(--c-accent);
  transition: width 0.5s ease;
  min-width: 4px;
}
.bd-pct { font-size: 0.7rem; color: var(--c-hint); }

/* ── Empty state ───────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2.5rem 0;
}
.empty-icon { font-size: 2rem; }
.empty-label { font-size: 0.875rem; color: var(--c-hint); }

/* ── Report navigation actions ─────────────────────────────── */
.report-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.report-action-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--c-surface);
  border: none;
  border-radius: 14px;
  padding: 0.875rem 1rem;
  cursor: pointer;
  text-align: left;
  transition: opacity 0.15s;
  width: 100%;
}
.report-action-btn:active { opacity: 0.7; }
.report-action-btn:disabled { opacity: 0.5; cursor: default; }
.ra-icon { font-size: 1.1rem; flex-shrink: 0; }
.ra-label { flex: 1; font-size: 0.875rem; font-weight: 600; color: var(--c-text); }
.ra-chevron { color: var(--c-hint); flex-shrink: 0; }
.csv-btn .ra-label { color: var(--c-accent); }
</style>
