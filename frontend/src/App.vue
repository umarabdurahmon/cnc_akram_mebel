<template>
  <div class="app" :data-theme="colorScheme">

    <div v-if="appState === 'loading'" class="splash">
      <div class="splash-dots">···</div>
    </div>

    <div v-else-if="appState === 'error'" class="splash">
      <div class="splash-icon">⚠️</div>
      <div class="splash-msg">{{ errorMessage }}</div>
    </div>

    <template v-else>
      <!-- Контент -->
      <div class="page-content">

        <template v-if="tab === 'home'">
          <WorkerView v-if="role === 'worker'" />
          <HomeView v-else-if="role === 'manager'" :current-employee="currentEmployee" />
        </template>

        <template v-else-if="tab === 'orders'">
          <OrderDetailView
            v-if="selectedOrderId"
            :order-id="selectedOrderId"
            :is-manager="role === 'manager'"
            @back="closeDetail"
          />
          <OrdersView
            v-else
            ref="ordersViewRef"
            :is-manager="role === 'manager'"
            @open="openDetail"
            @create="openCreateForm"
          />
        </template>

        <template v-else-if="tab === 'turnover'">
          <TurnoverView />
        </template>

        <template v-else-if="tab === 'settings'">
          <SettingsView :is-manager="role === 'manager'" />
        </template>

      </div>

      <!-- Bottom navigation -->
      <nav class="bottom-nav">
        <button
          v-for="item in navItems" :key="item.key"
          :class="['nav-item', { active: tab === item.key }]"
          @click="switchTab(item.key)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ t(item.label) }}</span>
          <span v-if="tab === item.key" class="nav-pip" />
        </button>
      </nav>

      <OrderFormModal
        v-if="showOrderForm"
        @close="showOrderForm = false"
        @saved="onOrderSaved"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from './api.js'
import { initTelegram, getColorScheme, onThemeChange } from './telegram.js'
import WorkerView from './views/WorkerView.vue'
import OrdersView from './views/OrdersView.vue'
import OrderDetailView from './views/OrderDetailView.vue'
import OrderFormModal from './views/OrderFormModal.vue'
import HomeView from './views/HomeView.vue'
import TurnoverView from './views/TurnoverView.vue'
import SettingsView from './views/SettingsView.vue'

const { t, locale } = useI18n()

const appState = ref('loading')
const role = ref(null)
const currentEmployee = ref(null)
const errorMessage = ref('')
const colorScheme = ref(getColorScheme())
const tab = ref('home')
const selectedOrderId = ref(null)
const showOrderForm = ref(false)
const ordersViewRef = ref(null)

onThemeChange(() => { colorScheme.value = getColorScheme() })

const tgApp = window.Telegram?.WebApp ?? null

const navItems = computed(() => {
  const items = [
    { key: 'home',   icon: '🏠', label: 'nav.home' },
    { key: 'orders', icon: '📦', label: 'nav.orders' },
  ]
  if (role.value === 'manager') {
    items.push({ key: 'turnover', icon: '💸', label: 'nav.turnover' })
  }
  items.push({ key: 'settings', icon: '⚙️', label: 'nav.settings' })
  return items
})

function updateBackButton() {
  if (!tgApp) return
  if (tab.value === 'orders' && selectedOrderId.value) tgApp.BackButton.show()
  else tgApp.BackButton.hide()
}

function switchTab(newTab) {
  tab.value = newTab
  selectedOrderId.value = null
  updateBackButton()
}

function openDetail(id) { selectedOrderId.value = id; updateBackButton() }
function closeDetail() { selectedOrderId.value = null; updateBackButton() }
function openCreateForm() { showOrderForm.value = true }

function onOrderSaved(order) {
  showOrderForm.value = false
  selectedOrderId.value = order.id
  ordersViewRef.value?.reload?.()
}

onMounted(async () => {
  initTelegram()
  if (tgApp) tgApp.BackButton.onClick(closeDetail)
  try {
    const me = await api.get('/api/me')
    role.value = me.role
    currentEmployee.value = me
    const lang = me.language
    if (lang === 'ru' || lang === 'uz') locale.value = lang
    appState.value = 'ready'
  } catch (err) {
    if (err.code === 'auth_required') errorMessage.value = t('errors.auth_required')
    else if (err.code === 'not_registered') errorMessage.value = t('errors.not_registered')
    else errorMessage.value = t('errors.server_error')
    appState.value = 'error'
  }
})
</script>

<style>
:root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;

  /* ── Telegram theme wrappers ──────────────────────────────── */
  --c-bg:          var(--tg-theme-bg-color, #ffffff);
  --c-surface:     var(--tg-theme-secondary-bg-color, #f2f2f7);
  --c-text:        var(--tg-theme-text-color, #000000);
  --c-hint:        var(--tg-theme-hint-color, #8e8e93);
  --c-accent:      var(--tg-theme-button-color, #2481cc);
  --c-accent-text: var(--tg-theme-button-text-color, #ffffff);

  /* ── Semantic: positive (income / success / active) ──────── */
  --c-positive:      #27ae60;
  --c-positive-bg:   #eafaf1;
  --c-positive-dim:  #d5f5e3;
  --c-positive-dark: #1e8449;

  /* ── Semantic: negative (expense / error / danger) ───────── */
  --c-negative:      #e74c3c;
  --c-negative-bg:   #fde8e8;
  --c-negative-dim:  #fdecea;
  --c-negative-dark: #c0392b;

  /* ── Semantic: warning (operating costs / caution) ───────── */
  --c-warning:       #e67e22;
  --c-warning-bg:    #fff3e0;

  /* ── Deadline urgency pills ──────────────────────────────── */
  --c-due-overdue-bg:   #fde8e8;  --c-due-overdue-text: #c0392b;
  --c-due-urgent-bg:    #fff3e0;  --c-due-urgent-text:  #e65100;
  --c-due-soon-bg:      #fffde7;  --c-due-soon-text:    #f57f17;
  --c-due-ok-bg:        #e8f5e9;  --c-due-ok-text:      #2e7d32;

  /* ── Overlays ────────────────────────────────────────────── */
  --c-overlay:      rgba(0, 0, 0, 0.45);
  --c-overlay-dark: rgba(0, 0, 0, 0.92);

  /* ── WorkerView "on duty" gradient ───────────────────────── */
  --c-checkin-from:  #1b5e20;
  --c-checkin-to:    #2e7d32;
  --c-checkin-pulse: #69f0ae;
}
body { margin: 0; background: var(--c-bg); color: var(--c-text); }
.app { min-height: 100vh; }

/* Splash */
.splash {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.75rem; padding: 2rem;
}
.splash-dots { font-size: 2rem; letter-spacing: 0.3em; color: var(--c-hint); animation: blink 1.2s infinite; }
.splash-icon { font-size: 3rem; }
.splash-msg { font-size: 0.95rem; color: var(--c-hint); text-align: center; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

/* Page layout */
.page-content { padding-bottom: 5rem; min-height: 100vh; }

/* Bottom nav */
.bottom-nav {
  position: fixed; bottom: 0; left: 0; right: 0;
  height: 4.25rem; display: flex;
  background: var(--c-bg);
  border-top: 1px solid var(--c-surface);
  z-index: 50;
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.nav-item {
  flex: 1; border: none; background: none; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.2rem; padding: 0.5rem 0.25rem; position: relative;
  transition: opacity 0.15s;
}
.nav-item:active { opacity: 0.6; }
.nav-icon { font-size: 1.35rem; line-height: 1; }
.nav-label {
  font-size: 0.65rem; font-weight: 500;
  color: var(--c-hint);
  transition: color 0.15s;
}
.nav-item.active .nav-label { color: var(--c-accent); font-weight: 700; }
.nav-pip {
  position: absolute; top: 0.3rem; left: 50%; transform: translateX(-50%);
  width: 1.5rem; height: 3px; border-radius: 0 0 3px 3px;
  background: var(--c-accent);
}

</style>
