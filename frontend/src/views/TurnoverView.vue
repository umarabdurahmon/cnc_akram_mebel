<template>
  <div class="turnover-view">

    <!-- ── Order finance sub-view ──────────────────────────────── -->
    <template v-if="selectedOrder">
      <div class="sub-header">
        <button class="back-btn" @click="selectedOrder = null">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
          {{ t('turnover.back') }}
        </button>
        <div class="sub-title-block">
          <span class="sub-title">{{ selectedOrder.title }}</span>
          <span class="sub-sub">{{ selectedOrder.customer_name }}</span>
        </div>
      </div>
      <div class="sub-content">
        <OrderFinanceTab :order-id="selectedOrder.id" />
      </div>
    </template>

    <!-- ── Main view ───────────────────────────────────────────── -->
    <template v-else>
      <!-- Sticky segment control -->
      <div class="seg-bar">
        <button :class="['seg-btn', { 'seg-active': tab === 'operating' }]" @click="tab = 'operating'">
          {{ t('turnover.tab_operating') }}
        </button>
        <button :class="['seg-btn', { 'seg-active': tab === 'orders' }]" @click="tab = 'orders'">
          {{ t('turnover.tab_orders') }}
        </button>
      </div>

      <!-- ── Операционные расходы ──────────────────────────── -->
      <div v-if="tab === 'operating'" class="tab-content">
        <OperatingExpenseView />
      </div>

      <!-- ── По заказам ────────────────────────────────────── -->
      <div v-else class="tab-content">

        <!-- Search -->
        <div class="search-wrap">
          <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          <input
            v-model="searchQuery"
            class="search-input"
            type="text"
            :placeholder="t('turnover.search_orders')"
          />
          <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">✕</button>
        </div>

        <div v-if="ordersLoading" class="loading-box">
          <div class="spinner"></div>
        </div>
        <p v-else-if="ordersError" class="error-msg">{{ ordersError }}</p>
        <p v-else-if="filteredOrders.length === 0" class="empty-msg">
          {{ searchQuery ? t('turnover.nothing_found') : t('turnover.no_orders') }}
        </p>

        <div v-else class="order-list">
          <button
            v-for="o in filteredOrders"
            :key="o.id"
            class="order-card"
            :class="{ 'card-closed': o.is_closed }"
            @click="selectedOrder = o"
          >
            <!-- Строка 1: название + номер + бейдж закрыт -->
            <div class="oc-top">
              <span class="oc-title">{{ o.title }}</span>
              <div class="oc-top-right">
                <span class="oc-num">#{{ o.internal_number }}</span>
                <span v-if="o.is_closed" class="badge-closed">🔒 {{ t('orders.closed') }}</span>
              </div>
            </div>
            <!-- Строка 2: клиент + этап -->
            <div class="oc-mid">
              <span class="oc-customer">{{ o.customer_name }}</span>
              <span v-if="o.current_stage_name" class="oc-stage">{{ o.current_stage_name }}</span>
            </div>
            <!-- Строка 3: финансы -->
            <div v-if="o.total_amount" class="oc-fin">
              <div class="fin-pill fin-total">
                <span class="fp-lbl">{{ t('orders.total_amount_short') }}</span>
                <span class="fp-val">{{ fmtAmt(o.total_amount) }}</span>
              </div>
              <div class="fin-pill fin-paid">
                <span class="fp-lbl">{{ t('orders.paid_short') }}</span>
                <span class="fp-val positive">{{ fmtAmt(o.total_paid) }}</span>
              </div>
              <div v-if="Number(o.balance) !== 0" class="fin-pill" :class="Number(o.balance) > 0 ? 'fin-debt' : 'fin-ok'">
                <span class="fp-lbl">{{ t('orders.balance_short') }}</span>
                <span class="fp-val" :class="Number(o.balance) > 0 ? 'negative' : 'positive'">
                  {{ fmtAmt(o.balance) }}
                </span>
              </div>
              <div v-else class="fin-pill fin-ok">
                <span class="fp-val positive">✓ {{ t('turnover.fully_paid') }}</span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { displayAmount } from '../money.js'
import OperatingExpenseView from './OperatingExpenseView.vue'
import OrderFinanceTab from './OrderFinanceTab.vue'

const { t } = useI18n()

const tab = ref('operating')
const selectedOrder = ref(null)

// ── Orders list ────────────────────────────────────────────────
const orders = ref([])
const ordersLoading = ref(false)
const ordersError = ref('')
const searchQuery = ref('')

const filteredOrders = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return orders.value
  return orders.value.filter(o =>
    o.title.toLowerCase().includes(q) ||
    o.customer_name?.toLowerCase().includes(q) ||
    o.public_code?.toLowerCase().includes(q) ||
    o.internal_number?.toLowerCase().includes(q),
  )
})

function fmtAmt(val) {
  return displayAmount(String(val ?? '0'), 'сум')
}

async function loadOrders() {
  if (ordersLoading.value) return
  ordersLoading.value = true
  ordersError.value = ''
  try {
    orders.value = await api.get('/api/orders')
  } catch {
    ordersError.value = t('turnover.load_error')
  } finally {
    ordersLoading.value = false
  }
}

// Load orders when switching to orders tab
watch(tab, (t) => { if (t === 'orders' && orders.value.length === 0) loadOrders() })
</script>

<style scoped>
.turnover-view {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* ── Segment bar ───────────────────────────────────────────── */
.seg-bar {
  display: flex; gap: 0.375rem;
  background: var(--c-surface);
  border-radius: 12px; padding: 0.25rem;
  margin: 0.75rem 0.75rem 0;
  position: sticky; top: 0.5rem; z-index: 10;
}
.seg-btn {
  flex: 1; border: none; background: transparent;
  color: var(--c-hint); font-size: 0.875rem; font-weight: 600;
  padding: 0.5rem 0; border-radius: 9px; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.seg-btn.seg-active {
  background: var(--c-bg);
  color: var(--c-text);
  box-shadow: 0 1px 4px var(--c-shadow);
}

.tab-content { padding: 0.75rem 0 0; }

/* ── Sub-view header ───────────────────────────────────────── */
.sub-header {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 0.75rem 0.75rem 0.625rem;
  position: sticky; top: 0; z-index: 20;
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-surface);
}
.back-btn {
  display: flex; align-items: center; gap: 0.2rem;
  background: none; border: none; color: var(--c-accent);
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
  padding: 0.25rem 0.5rem 0.25rem 0; flex-shrink: 0;
}
.sub-title-block { flex: 1; min-width: 0; }
.sub-title { display: block; font-size: 0.95rem; font-weight: 700; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub-sub { font-size: 0.75rem; color: var(--c-hint); }
.sub-content { padding: 0.75rem 0.75rem 0; }

/* ── Search ────────────────────────────────────────────────── */
.search-wrap {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--c-surface);
  border-radius: 12px; padding: 0.5rem 0.75rem;
  margin: 0 0.75rem 0.625rem;
}
.search-icon { color: var(--c-hint); flex-shrink: 0; }
.search-input {
  flex: 1; background: none; border: none; outline: none;
  font-size: 0.875rem; color: var(--c-text);
}
.search-input::placeholder { color: var(--c-hint); }
.search-clear {
  background: none; border: none; color: var(--c-hint);
  cursor: pointer; font-size: 0.8rem; padding: 0; flex-shrink: 0;
}

/* ── Order list ────────────────────────────────────────────── */
.order-list {
  display: flex; flex-direction: column; gap: 0.5rem;
  padding: 0 0.75rem;
}
.order-card {
  background: var(--c-surface); border: none; border-radius: 14px;
  padding: 0.875rem 1rem; cursor: pointer; text-align: left;
  transition: opacity 0.15s; width: 100%;
  display: flex; flex-direction: column; gap: 0.25rem;
}
.order-card:active { opacity: 0.7; }
.card-closed { opacity: 0.6; }

.oc-top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
.oc-title { font-size: 0.95rem; font-weight: 600; color: var(--c-text); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.oc-top-right { display: flex; align-items: center; gap: 0.35rem; flex-shrink: 0; }
.oc-num { font-size: 0.72rem; font-weight: 700; color: var(--c-accent); }
.badge-closed { font-size: 0.72rem; font-weight: 700; color: var(--c-hint); flex-shrink: 0; }

.oc-mid { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; }
.oc-customer { font-size: 0.82rem; color: var(--c-hint); }
.oc-stage { font-size: 0.72rem; font-weight: 600; background: #e3f2fd; color: #1565c0; border-radius: 5px; padding: 0.1rem 0.4rem; flex-shrink: 0; }

.oc-fin {
  display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.25rem;
}
.fin-pill {
  display: flex; align-items: baseline; gap: 0.25rem;
  background: var(--c-bg); border-radius: 7px; padding: 0.2rem 0.5rem;
}
.fp-lbl { font-size: 0.72rem; color: var(--c-hint); }
.fp-val { font-size: 0.8rem; font-weight: 700; color: var(--c-text); }
.positive { color: var(--c-positive); }
.negative { color: var(--c-negative); }

/* ── States ────────────────────────────────────────────────── */
.loading-box { display: flex; justify-content: center; padding: 2rem 0; }
.spinner {
  width: 24px; height: 24px;
  border: 3px solid var(--c-surface); border-top-color: var(--c-accent);
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { color: var(--c-negative); font-size: 0.875rem; padding: 0 0.75rem; }
.empty-msg { color: var(--c-hint); font-size: 0.875rem; padding: 1rem 0.75rem; }
</style>
