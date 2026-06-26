<template>
  <div class="reports-view">

    <!-- ── EMPLOYEE WAGES sub-view ──────────────────────────────── -->
    <template v-if="activeSubView === 'employee-wages'">
      <EmployeeWagesView
        :year="year"
        :month="month"
        @back="activeSubView = null"
      />
    </template>

    <!-- ── ORDERS DETAIL sub-view ───────────────────────────────── -->
    <template v-else-if="activeSubView === 'orders-detail'">
      <OrdersDetailReportView
        :year="year"
        :month="month"
        @back="activeSubView = null"
      />
    </template>

    <!-- ── MAIN reports list ─────────────────────────────────────── -->
    <template v-else>
      <div class="sub-header">
        <button class="back-btn" @click="$emit('back')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
          {{ t('wages.back') }}
        </button>
        <span class="sub-title">{{ t('finance.reports_page') }}</span>
      </div>

      <div class="period-badge">{{ monthLabel }}</div>

      <div class="report-list">
        <button class="report-row" @click="activeSubView = 'employee-wages'">
          <span class="rr-icon">👷</span>
          <span class="rr-label">{{ t('finance.wages_report') }}</span>
          <svg class="rr-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>

        <button class="report-row" @click="activeSubView = 'orders-detail'">
          <span class="rr-icon">📋</span>
          <span class="rr-label">{{ t('finance.orders_detail_report') }}</span>
          <svg class="rr-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>

      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import EmployeeWagesView from './EmployeeWagesView.vue'
import OrdersDetailReportView from './OrdersDetailReportView.vue'

const props = defineProps({
  year: { type: Number, required: true },
  month: { type: Number, required: true },
})

defineEmits(['back'])

const { t, locale } = useI18n()

const activeSubView = ref(null)   // null | 'employee-wages' | 'orders-detail'

const monthLabel = computed(() => {
  const d = new Date(props.year, props.month - 1, 1)
  const name = d.toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { month: 'long' })
  return name.charAt(0).toUpperCase() + name.slice(1) + ' ' + props.year
})

</script>

<style scoped>
.reports-view {
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

/* ── Period badge ──────────────────────────────────────────── */
.period-badge {
  margin: 1rem 0.875rem 0.5rem;
  font-size: 0.8rem; font-weight: 700; color: var(--c-hint);
  text-transform: uppercase; letter-spacing: 0.06em;
}

/* ── Report list ───────────────────────────────────────────── */
.report-list {
  display: flex; flex-direction: column; gap: 0.375rem;
  padding: 0 0.875rem;
}
.report-row {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--c-surface); border: none; border-radius: 14px;
  padding: 0.875rem 1rem; cursor: pointer; text-align: left;
  transition: opacity 0.15s; width: 100%;
}
.report-row:active { opacity: 0.7; }
.report-row:disabled { opacity: 0.5; cursor: default; }
.rr-icon { font-size: 1.1rem; flex-shrink: 0; }
.rr-label { flex: 1; font-size: 0.9rem; font-weight: 600; color: var(--c-text); }
.rr-chevron { color: var(--c-hint); flex-shrink: 0; }
</style>
