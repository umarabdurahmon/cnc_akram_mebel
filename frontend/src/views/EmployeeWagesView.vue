<template>
  <div class="wages-view">
    <div class="sub-header">
      <button class="back-btn" @click="$emit('back')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        {{ t('wages.back') }}
      </button>
      <span class="sub-title">{{ t('wages.title') }}</span>
    </div>

    <div class="month-badge">{{ monthLabel }}</div>

    <div v-if="loading" class="state-box">
      <div class="spinner"></div>
    </div>
    <p v-else-if="error" class="error-msg">{{ error }}</p>

    <template v-else-if="data">
      <div class="total-card">
        <span class="total-label">{{ t('wages.total_label') }}</span>
        <span class="total-value">{{ display(data.total) }}</span>
      </div>

      <div v-if="data.employees.length === 0" class="empty-state">
        <span class="empty-icon">💼</span>
        <span class="empty-label">{{ t('wages.no_data') }}</span>
      </div>

      <div v-for="emp in data.employees" :key="emp.employee_id" class="emp-card">
        <div class="emp-header">
          <div class="emp-avatar">{{ initials(emp.full_name) }}</div>
          <span class="emp-name">{{ emp.full_name }}</span>
          <span class="emp-total">{{ display(emp.total) }}</span>
        </div>
        <ul class="exp-list">
          <li v-for="(exp, i) in emp.expenses" :key="i" class="exp-row">
            <div class="exp-main">
              <span class="exp-order">
                <span v-if="exp.order_internal_number" class="exp-num">#{{ exp.order_internal_number }}</span>{{ exp.order_title }}
              </span>
              <span class="exp-amount">{{ display(exp.amount) }}</span>
            </div>
            <div class="exp-meta">
              <span class="exp-cat">{{ exp.category_name }}</span>
              <span class="exp-dot">·</span>
              <span class="exp-date">{{ fmtDate(exp.spent_on) }}</span>
              <template v-if="exp.note">
                <span class="exp-dot">·</span>
                <span class="exp-note">{{ exp.note }}</span>
              </template>
            </div>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { displayAmount } from '../money.js'

const props = defineProps({
  year: { type: Number, required: true },
  month: { type: Number, required: true },
})
defineEmits(['back'])

const { t, locale } = useI18n()

const data = ref(null)
const loading = ref(false)
const error = ref('')

const monthLabel = computed(() => {
  const d = new Date(props.year, props.month - 1, 1)
  const name = d.toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { month: 'long' })
  return name.charAt(0).toUpperCase() + name.slice(1) + ' ' + props.year
})

function display(str) { return displayAmount(str, 'сум') }

function initials(name) {
  return (name ?? '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function fmtDate(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(
    locale.value === 'uz' ? 'uz-UZ' : 'ru-RU',
    { day: 'numeric', month: 'short' },
  )
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.get(`/api/reports/employee-wages?year=${props.year}&month=${props.month}`)
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wages-view {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-bottom: 2rem;
}

.sub-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.75rem 0.875rem 0.5rem;
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
  flex: 1; text-align: center; padding-right: 4rem;
}

.month-badge {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--c-hint);
  text-align: center;
  padding: 0 0.875rem;
}

.state-box {
  display: flex; justify-content: center; padding: 3rem 0;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--c-surface);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { color: var(--c-negative); font-size: 0.875rem; text-align: center; padding: 0 1rem; }

.total-card {
  background: var(--c-surface);
  border-radius: 16px;
  padding: 1rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 0.875rem;
}
.total-label { font-size: 0.83rem; color: var(--c-hint); }
.total-value { font-size: 1.1rem; font-weight: 800; color: var(--c-text); }

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 2.5rem 0;
}
.empty-icon { font-size: 2rem; }
.empty-label { font-size: 0.875rem; color: var(--c-hint); }

.emp-card {
  background: var(--c-surface);
  border-radius: 16px;
  overflow: hidden;
  margin: 0 0.875rem;
}
.emp-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid var(--c-bg);
}
.emp-avatar {
  width: 2rem; height: 2rem; border-radius: 50%;
  background: var(--c-accent); color: var(--c-accent-text);
  font-size: 0.75rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.emp-name { flex: 1; font-size: 0.9rem; font-weight: 700; color: var(--c-text); }
.emp-total { font-size: 0.9rem; font-weight: 700; color: var(--c-negative); }

.exp-list { list-style: none; padding: 0; margin: 0; }
.exp-row {
  padding: 0.625rem 1rem;
  border-bottom: 1px solid var(--c-bg);
}
.exp-row:last-child { border-bottom: none; }
.exp-main {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.2rem;
}
.exp-order { font-size: 0.83rem; color: var(--c-text); font-weight: 500; flex: 1; min-width: 0; }
.exp-num { font-size: 0.72rem; font-weight: 700; color: var(--c-accent); margin-right: 0.3rem; }
.exp-amount { font-size: 0.83rem; font-weight: 700; color: var(--c-negative); white-space: nowrap; margin-left: 0.5rem; }
.exp-meta { display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap; }
.exp-cat { font-size: 0.72rem; color: var(--c-hint); }
.exp-dot { font-size: 0.72rem; color: var(--c-hint); }
.exp-date { font-size: 0.72rem; color: var(--c-hint); }
.exp-note { font-size: 0.72rem; color: var(--c-hint); font-style: italic; }
</style>
