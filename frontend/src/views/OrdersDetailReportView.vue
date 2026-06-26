<template>
  <div class="orders-report-view">
    <div class="sub-header">
      <button class="back-btn" @click="$emit('back')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        {{ t('orders_report.back') }}
      </button>
      <span class="sub-title">{{ t('orders_report.title') }}</span>
    </div>

    <div class="month-badge">{{ monthLabel }}</div>

    <div v-if="loading" class="state-box">
      <div class="spinner"></div>
    </div>
    <p v-else-if="error" class="error-msg">{{ error }}</p>

    <template v-else-if="data">
      <div v-if="data.orders.length === 0" class="empty-state">
        <span class="empty-icon">📋</span>
        <span class="empty-label">{{ t('orders_report.no_data') }}</span>
      </div>

      <div v-else class="orders-list">
        <div v-for="order in data.orders" :key="order.order_id" class="order-card">
          <div class="order-head">
            <div class="order-title-row">
              <span class="order-title">{{ order.title }}</span>
              <span class="order-num">#{{ order.internal_number }}</span>
            </div>
            <span class="order-customer">{{ order.customer_name }}</span>
          </div>

          <div class="order-metrics">
            <div class="om-item">
              <span class="om-label">{{ t('orders_report.paid') }}</span>
              <span class="om-value positive">{{ display(order.paid_in_month) }}</span>
            </div>
            <div class="om-divider"></div>
            <div class="om-item">
              <span class="om-label">{{ t('orders_report.expenses') }}</span>
              <span class="om-value negative">{{ display(order.expenses_in_month) }}</span>
            </div>
            <div class="om-divider"></div>
            <div class="om-item">
              <span class="om-label">{{ t('orders_report.net') }}</span>
              <span class="om-value" :class="toNum(order.net_in_month) >= 0 ? 'positive' : 'negative'">
                {{ display(order.net_in_month) }}
              </span>
            </div>
          </div>

          <div v-if="order.total_amount" class="order-footer">
            <span class="of-label">{{ t('orders_report.total_amount') }}: {{ display(order.total_amount) }}</span>
            <span v-if="toNum(order.total_amount) > toNum(order.total_paid_all_time)" class="of-label">
              {{ t('orders_report.receivable') }}: {{ display(String(toNum(order.total_amount) - toNum(order.total_paid_all_time))) }}
            </span>
          </div>
        </div>
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
function toNum(str) { return parseFloat(str) || 0 }

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.get(`/api/reports/orders-detail?year=${props.year}&month=${props.month}`)
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.orders-report-view {
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

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 2.5rem 0;
}
.empty-icon { font-size: 2rem; }
.empty-label { font-size: 0.875rem; color: var(--c-hint); }

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0 0.875rem;
}

.order-card {
  background: var(--c-surface);
  border-radius: 16px;
  overflow: hidden;
}

.order-head {
  padding: 0.875rem 1rem 0.75rem;
  border-bottom: 1px solid var(--c-bg);
}
.order-title-row {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.2rem;
}
.order-title { font-size: 0.9rem; font-weight: 700; color: var(--c-text); flex: 1; min-width: 0; }
.order-num { font-size: 0.72rem; color: var(--c-hint); white-space: nowrap; flex-shrink: 0; }
.order-customer { font-size: 0.78rem; color: var(--c-hint); }

.order-metrics {
  display: flex;
  align-items: stretch;
  padding: 0.75rem 0;
}
.om-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0 0.5rem;
}
.om-label { font-size: 0.68rem; color: var(--c-hint); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
.om-value { font-size: 0.9rem; font-weight: 700; }
.om-divider { width: 1px; background: var(--c-bg); align-self: stretch; }
.positive { color: var(--c-positive); }
.negative { color: var(--c-negative); }

.order-footer {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 1rem 0.75rem;
  border-top: 1px solid var(--c-bg);
  gap: 0.5rem;
  flex-wrap: wrap;
}
.of-label { font-size: 0.75rem; color: var(--c-hint); }
</style>
