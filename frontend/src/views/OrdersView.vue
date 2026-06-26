<template>
  <div class="orders-view">
    <div class="page-hero">
      <span class="hero-icon">📦</span>
      <span class="hero-title">{{ t('orders.title') }}</span>
      <button v-if="isManager" class="btn-create" @click="$emit('create')">+</button>
    </div>

    <!-- Табы Активные / Архив -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ 'tab-active': tab === 'active' }"
        @click="tab = 'active'"
      >
        {{ t('orders.tab_active') }}
        <span v-if="activeOrders.length" class="tab-count">{{ activeOrders.length }}</span>
      </button>
      <button
        class="tab-btn"
        :class="{ 'tab-active': tab === 'archive' }"
        @click="tab = 'archive'"
      >
        {{ t('orders.tab_archive') }}
        <span v-if="archivedOrders.length" class="tab-count tab-count-dim">{{ archivedOrders.length }}</span>
      </button>
    </div>

    <div v-if="loading" class="hint">…</div>

    <template v-else>
      <p v-if="visibleOrders.length === 0" class="hint">
        {{ tab === 'active' ? t('orders.empty') : t('orders.empty_archive') }}
      </p>
      <div v-else class="order-list">
        <div
          v-for="o in visibleOrders" :key="o.id"
          class="order-card"
          :class="{ 'card-closed': o.is_closed }"
          @click="$emit('open', o.id)"
        >
          <!-- Строка 1: название + номер/код/бейдж -->
          <div class="card-top">
            <span class="order-title">{{ o.title }}</span>
            <div class="card-top-right">
              <span class="order-num">#{{ o.internal_number }}</span>
              <span v-if="o.is_closed" class="badge-closed">🔒 {{ t('orders.closed') }}</span>
              <span v-else class="order-code">{{ o.public_code }}</span>
            </div>
          </div>
          <!-- Строка 2: клиент + этап -->
          <div class="card-mid">
            <span class="order-customer">{{ o.customer_name }}</span>
            <span class="order-stage" :class="o.current_stage_name ? 'stage-set' : 'stage-empty'">
              {{ o.current_stage_name || t('orders.no_stage') }}
            </span>
          </div>
          <!-- Строка 3: финансы (только менеджеру) -->
          <div v-if="isManager && o.total_amount" class="card-finance">
            <span class="fin-item">
              <span class="fin-lbl">{{ t('orders.total_amount_short') }}</span>
              <span class="fin-val">{{ fmtAmount(o.total_amount) }}</span>
            </span>
            <span class="fin-sep">·</span>
            <span class="fin-item">
              <span class="fin-lbl">{{ t('orders.paid_short') }}</span>
              <span class="fin-val fin-paid">{{ fmtAmount(o.total_paid) }}</span>
            </span>
            <template v-if="o.balance !== null">
              <span class="fin-sep">·</span>
              <span class="fin-item">
                <span class="fin-lbl">{{ t('orders.balance_short') }}</span>
                <span class="fin-val" :class="o.balance > 0 ? 'fin-debt' : 'fin-ok'">{{ fmtAmount(o.balance) }}</span>
              </span>
            </template>
          </div>
          <!-- Строка 4: дедлайн -->
          <div v-if="o.deadline" class="card-deadline">
            📅 {{ fmtDate(o.deadline) }}
            <span class="days-badge" :class="daysClass(o.deadline)">{{ daysLabel(o.deadline) }}</span>
          </div>
        </div>
      </div>
    </template>

    <p v-if="error" class="error-msg">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'

defineProps({
  isManager: { type: Boolean, required: true },
})
defineEmits(['open', 'create'])

const { t, locale } = useI18n()

const tab = ref('active')
const orders = ref([])
const loading = ref(false)
const error = ref('')

const activeOrders = computed(() => orders.value.filter(o => !o.is_closed))
const archivedOrders = computed(() => orders.value.filter(o => o.is_closed))
const visibleOrders = computed(() => tab.value === 'active' ? activeOrders.value : archivedOrders.value)

function fmtAmount(val) {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('ru-RU') + ' сум'
}

function fmtDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { day: 'numeric', month: 'short' })
}

function daysLeft(deadline) {
  return Math.ceil((new Date(deadline) - new Date()) / 86400000)
}

function daysLabel(deadline) {
  const d = daysLeft(deadline)
  if (d < 0) return t('orders.overdue')
  if (d === 0) return t('orders.due_today')
  return t('orders.days_left', { n: d })
}

function daysClass(deadline) {
  const d = daysLeft(deadline)
  if (d < 0) return 'days-overdue'
  if (d <= 2) return 'days-urgent'
  if (d <= 7) return 'days-soon'
  return 'days-ok'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    orders.value = await api.get('/api/orders')
  } catch (err) {
    error.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
}

onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.orders-view { padding: 1rem; max-width: 600px; margin: 0 auto; }
.page-hero {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 1.25rem 0 1.125rem;
}
.hero-icon { font-size: 1.75rem; line-height: 1; flex-shrink: 0; }
.hero-title { font-size: 1.4rem; font-weight: 700; color: var(--c-text); flex: 1; }
.btn-create {
  background: var(--c-accent);
  color: var(--c-accent-text);
  border: none; border-radius: 50%; width: 2rem; height: 2rem;
  font-size: 1.25rem; cursor: pointer; line-height: 1;
}

/* Табы */
.tab-bar {
  display: flex; gap: 0.375rem;
  background: var(--c-surface);
  border-radius: 12px; padding: 0.25rem;
  margin-bottom: 0.75rem;
}
.tab-btn {
  flex: 1; border: none; background: transparent;
  color: var(--c-hint); font-size: 0.875rem; font-weight: 600;
  padding: 0.5rem 0; border-radius: 9px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 0.35rem;
  transition: background 0.15s, color 0.15s;
}
.tab-btn.tab-active {
  background: var(--c-bg);
  color: var(--c-text);
  box-shadow: 0 1px 4px var(--c-shadow);
}
.tab-count {
  font-size: 0.72rem; font-weight: 700;
  background: var(--c-accent); color: var(--c-accent-text);
  border-radius: 10px; padding: 0.05rem 0.4rem; line-height: 1.4;
}
.tab-count-dim {
  background: var(--c-surface-2, var(--c-surface)); color: var(--c-hint);
}

.hint { color: var(--c-hint); text-align: center; margin-top: 2rem; }
.order-list { display: flex; flex-direction: column; gap: 0.5rem; }
.order-card {
  background: var(--c-surface);
  border-radius: 14px; padding: 0.875rem 1rem; cursor: pointer;
}
.card-closed { opacity: 0.6; }
.card-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.25rem; }
.order-title { font-weight: 600; font-size: 0.95rem; color: var(--c-text); }
.card-top-right { display: flex; align-items: center; flex-shrink: 0; margin-left: 0.5rem; }
.order-num { font-size: 0.72rem; font-weight: 700; color: var(--c-accent); margin-right: 0.25rem; }
.order-code { font-size: 0.72rem; color: var(--c-hint); font-family: monospace; }
.badge-closed { font-size: 0.72rem; font-weight: 700; color: var(--c-hint); }
.card-mid { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }
.order-customer { font-size: 0.85rem; color: var(--c-hint); }
.order-stage { font-size: 0.75rem; font-weight: 600; border-radius: 5px; padding: 0.15rem 0.45rem; }
.stage-set { background: #e3f2fd; color: #1565c0; }
.stage-empty { background: transparent; color: var(--c-hint); }

.card-finance {
  display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;
  font-size: 0.78rem; margin-top: 0.375rem; margin-bottom: 0.1rem;
  background: var(--c-bg);
  border-radius: 8px; padding: 0.35rem 0.6rem;
}
.fin-item { display: flex; gap: 0.25rem; align-items: baseline; }
.fin-lbl { color: var(--c-hint); }
.fin-val { font-weight: 600; color: var(--c-text); }
.fin-paid { color: var(--c-positive); }
.fin-debt { color: var(--c-negative); }
.fin-ok   { color: var(--c-positive); }
.fin-sep  { color: var(--c-hint); }

.card-deadline { font-size: 0.78rem; color: var(--c-hint); margin-top: 0.3rem; display: flex; gap: 0.4rem; align-items: center; }
.days-badge { font-size: 0.72rem; font-weight: 700; border-radius: 5px; padding: 0.1rem 0.4rem; }
.days-overdue { background: var(--c-due-overdue-bg); color: var(--c-due-overdue-text); }
.days-urgent  { background: var(--c-due-urgent-bg);  color: var(--c-due-urgent-text); }
.days-soon    { background: var(--c-due-soon-bg);    color: var(--c-due-soon-text); }
.days-ok      { background: var(--c-due-ok-bg);      color: var(--c-due-ok-text); }
.error-msg { color: var(--c-negative); font-size: 0.875rem; }
</style>
