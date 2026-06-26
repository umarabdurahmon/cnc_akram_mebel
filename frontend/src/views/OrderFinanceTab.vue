<template>
  <div class="order-finance">
    <!-- Balance card -->
    <div v-if="balance" class="balance-card">
      <div class="balance-main">
        <span class="balance-label">{{ t('finance.balance') }}</span>
        <span :class="['balance-amount', profitClass(balance.balance)]">{{ display(balance.balance) }}</span>
      </div>
      <div class="balance-rows">
        <div class="bal-row">
          <span class="bal-name positive-dot">{{ t('finance.total_paid') }}</span>
          <span class="bal-val positive">{{ display(balance.total_paid) }}</span>
        </div>
        <div class="bal-row">
          <span class="bal-name negative-dot">{{ t('finance.total_expenses') }}</span>
          <span class="bal-val negative">{{ display(balance.total_expenses) }}</span>
        </div>
        <div v-if="balance.receivable && Number(balance.receivable) > 0" class="bal-row">
          <span class="bal-name">{{ t('finance.receivable') }}</span>
          <span class="bal-val warn">{{ display(balance.receivable) }}</span>
        </div>
      </div>
    </div>

    <!-- Payments section -->
    <div class="section">
      <div class="section-header" @click="showPayForm = !showPayForm">
        <h3 class="section-title">{{ t('finance.payments_title') }}</h3>
        <button class="toggle-btn" :class="{ open: showPayForm }">+</button>
      </div>

      <transition name="slide">
        <div v-if="showPayForm" class="form-card">
          <div class="form-row">
            <input v-model="payForm.spent_on" type="date" class="input-field" />
            <input v-model="payForm.amountStr" type="text" inputmode="decimal" class="input-field"
              :placeholder="t('finance.amount_placeholder')" @blur="cleanPay" />
          </div>
          <input v-model="payForm.note" type="text" class="input-field full" :placeholder="t('finance.note')" />
          <p v-if="payError" class="field-error">{{ payError }}</p>
          <button class="btn-add" :disabled="paySaving || !payForm.spent_on" @click="addPayment">
            {{ paySaving ? '…' : t('finance.add_payment') }}
          </button>
        </div>
      </transition>

      <p v-if="payments.length === 0" class="hint">{{ t('finance.no_payments') }}</p>
      <ul v-else class="fin-list">
        <li v-for="p in payments" :key="p.id">
          <div class="fin-item">
            <div class="fin-left">
              <span class="fin-amount positive">{{ display(p.amount) }}</span>
              <span v-if="p.note" class="fin-note">{{ p.note }}</span>
            </div>
            <div class="fin-right">
              <span class="fin-date">{{ fmtDate(p.received_on) }}</span>
              <button class="btn-icon" :class="{ active: editingPayId === p.id }"
                @click="editingPayId === p.id ? cancelPayEdit() : startPayEdit(p)">✏</button>
              <button class="btn-del" @click="deletePayment(p)">✕</button>
            </div>
          </div>
          <transition name="slide">
            <div v-if="editingPayId === p.id" class="fin-edit-form">
              <div class="fef-row">
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.date') }}</span>
                  <input v-model="payEditForm.spent_on" type="date" class="fef-input" />
                </div>
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.amount') }}</span>
                  <input v-model="payEditForm.amountStr" type="text" inputmode="decimal" class="fef-input"
                    :placeholder="t('finance.amount_placeholder')" @blur="cleanPayEdit" />
                </div>
              </div>
              <div class="fef-field" style="margin-top:0.375rem">
                <input v-model="payEditForm.note" type="text" class="fef-input"
                  :placeholder="t('finance.note')" />
              </div>
              <p v-if="payEditError" class="field-error">{{ payEditError }}</p>
              <div class="fef-actions">
                <button class="fef-cancel" @click="cancelPayEdit">{{ t('finance.cancel') }}</button>
                <button class="fef-save" :disabled="payEditSaving" @click="savePayEdit(p)">
                  {{ payEditSaving ? '…' : t('finance.save') }}
                </button>
              </div>
            </div>
          </transition>
        </li>
      </ul>
    </div>

    <!-- Expenses section -->
    <div class="section">
      <div class="section-header" @click="showExpForm = !showExpForm">
        <h3 class="section-title">{{ t('finance.expenses_title') }}</h3>
        <button class="toggle-btn" :class="{ open: showExpForm }">+</button>
      </div>

      <transition name="slide">
        <div v-if="showExpForm" class="form-card">
          <div class="form-row">
            <select v-model="expForm.category_id" class="input-field">
              <option value="">{{ t('finance.category') }}</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <select v-model="expForm.direction" class="input-field">
              <option value="general">{{ t('finance.dir_general') }}</option>
              <option value="to_employee">{{ t('finance.dir_to_employee') }}</option>
            </select>
          </div>
          <div v-if="expForm.direction === 'to_employee'" class="form-row">
            <select v-model="expForm.employee_id" class="input-field">
              <option value="">{{ t('finance.employee') }}</option>
              <option v-for="e in employees" :key="e.id" :value="e.id">{{ e.full_name }}</option>
            </select>
          </div>
          <div class="form-row">
            <input v-model="expForm.spent_on" type="date" class="input-field" />
            <input v-model="expForm.amountStr" type="text" inputmode="decimal" class="input-field"
              :placeholder="t('finance.amount_placeholder')" @blur="cleanExp" />
          </div>
          <input v-model="expForm.note" type="text" class="input-field full" :placeholder="t('finance.note')" />
          <p v-if="expError" class="field-error">{{ expError }}</p>
          <button class="btn-add" :disabled="expSaving || !expForm.category_id || !expForm.spent_on" @click="addExpense">
            {{ expSaving ? '…' : t('finance.add_expense') }}
          </button>
        </div>
      </transition>

      <p v-if="expenses.length === 0" class="hint">{{ t('finance.no_expenses') }}</p>
      <ul v-else class="fin-list">
        <li v-for="e in expenses" :key="e.id">
          <div class="fin-item">
            <div class="fin-left">
              <span class="fin-amount negative">{{ display(e.amount) }}</span>
              <span class="fin-meta">
                <span class="fin-cat">{{ categoryName(e.category_id) }}</span>
                <span v-if="e.direction === 'to_employee'" class="fin-badge">{{ employeeName(e.employee_id) }}</span>
                <span v-if="e.note" class="fin-note">{{ e.note }}</span>
              </span>
            </div>
            <div class="fin-right">
              <span class="fin-date">{{ fmtDate(e.spent_on) }}</span>
              <button class="btn-icon" :class="{ active: editingExpId === e.id }"
                @click="editingExpId === e.id ? cancelExpEdit() : startExpEdit(e)">✏</button>
              <button class="btn-del" @click="deleteExpense(e)">✕</button>
            </div>
          </div>
          <transition name="slide">
            <div v-if="editingExpId === e.id" class="fin-edit-form">
              <div class="fef-row">
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.category') }}</span>
                  <select v-model="expEditForm.category_id" class="fef-input">
                    <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                </div>
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.direction') }}</span>
                  <select v-model="expEditForm.direction" class="fef-input">
                    <option value="general">{{ t('finance.dir_general') }}</option>
                    <option value="to_employee">{{ t('finance.dir_to_employee') }}</option>
                  </select>
                </div>
              </div>
              <div v-if="expEditForm.direction === 'to_employee'" class="fef-field" style="margin-top:0.375rem">
                <span class="fef-label">{{ t('finance.employee') }}</span>
                <select v-model="expEditForm.employee_id" class="fef-input">
                  <option value="">—</option>
                  <option v-for="emp in employees" :key="emp.id" :value="emp.id">{{ emp.full_name }}</option>
                </select>
              </div>
              <div class="fef-row" style="margin-top:0.375rem">
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.date') }}</span>
                  <input v-model="expEditForm.spent_on" type="date" class="fef-input" />
                </div>
                <div class="fef-field">
                  <span class="fef-label">{{ t('finance.amount') }}</span>
                  <input v-model="expEditForm.amountStr" type="text" inputmode="decimal" class="fef-input"
                    :placeholder="t('finance.amount_placeholder')" @blur="cleanExpEdit" />
                </div>
              </div>
              <div class="fef-field" style="margin-top:0.375rem">
                <input v-model="expEditForm.note" type="text" class="fef-input"
                  :placeholder="t('finance.note')" />
              </div>
              <p v-if="expEditError" class="field-error">{{ expEditError }}</p>
              <div class="fef-actions">
                <button class="fef-cancel" @click="cancelExpEdit">{{ t('finance.cancel') }}</button>
                <button class="fef-save" :disabled="expEditSaving" @click="saveExpEdit(e)">
                  {{ expEditSaving ? '…' : t('finance.save') }}
                </button>
              </div>
            </div>
          </transition>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showConfirm, showAlert } from '../telegram.js'
import { parseAmount, displayAmount, profitClass } from '../money.js'

const props = defineProps({ orderId: { type: Number, required: true } })
const { t } = useI18n()

const balance = ref(null)
const payments = ref([])
const expenses = ref([])
const categories = ref([])
const employees = ref([])

const showPayForm = ref(false)
const showExpForm = ref(false)

const payForm = ref({ spent_on: '', amountStr: '', note: '' })
const payError = ref('')
const paySaving = ref(false)

const expForm = ref({ direction: 'general', category_id: '', employee_id: '', spent_on: '', amountStr: '', note: '' })
const expError = ref('')
const expSaving = ref(false)

// --- Payment edit ---
const editingPayId = ref(null)
const payEditForm = ref({ spent_on: '', amountStr: '', note: '' })
const payEditError = ref('')
const payEditSaving = ref(false)

// --- Expense edit ---
const editingExpId = ref(null)
const expEditForm = ref({ direction: 'general', category_id: '', employee_id: '', spent_on: '', amountStr: '', note: '' })
const expEditError = ref('')
const expEditSaving = ref(false)

function display(str) { return displayAmount(str, 'сум') }
function cleanPay() { const c = parseAmount(payForm.value.amountStr); if (c) payForm.value.amountStr = c }
function cleanExp() { const c = parseAmount(expForm.value.amountStr); if (c) expForm.value.amountStr = c }
function cleanPayEdit() { const c = parseAmount(payEditForm.value.amountStr); if (c) payEditForm.value.amountStr = c }
function cleanExpEdit() { const c = parseAmount(expEditForm.value.amountStr); if (c) expEditForm.value.amountStr = c }

function categoryName(id) {
  return categories.value.find(c => c.id === id)?.name ?? '—'
}
function employeeName(id) {
  return employees.value.find(e => e.id === id)?.full_name ?? '—'
}

function fmtDate(iso) {
  if (!iso) return ''
  const [, m, d] = iso.split('-')
  return `${d}.${m}`
}

async function loadAll() {
  const [pay, exp, bal, cats, emps] = await Promise.all([
    api.get(`/api/orders/${props.orderId}/payments`),
    api.get(`/api/orders/${props.orderId}/expenses`),
    api.get(`/api/orders/${props.orderId}/balance`),
    api.get('/api/expense-categories'),
    api.get('/api/employees'),
  ])
  payments.value = pay
  expenses.value = exp
  balance.value = bal
  categories.value = cats
  employees.value = emps
}

async function refreshBalance() {
  balance.value = await api.get(`/api/orders/${props.orderId}/balance`)
}

async function addPayment() {
  payError.value = ''
  const amount = parseAmount(payForm.value.amountStr)
  if (!amount) { payError.value = t('finance.invalid_amount'); return }
  paySaving.value = true
  try {
    const created = await api.post(`/api/orders/${props.orderId}/payments`, {
      amount, received_on: payForm.value.spent_on, note: payForm.value.note || null,
    })
    payments.value.push(created)
    payForm.value = { spent_on: '', amountStr: '', note: '' }
    showPayForm.value = false
    await refreshBalance()
  } catch (err) {
    await showAlert(err.status === 400 ? t('finance.invalid_amount') : t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    paySaving.value = false
  }
}

async function deletePayment(p) {
  if (!await showConfirm(t('finance.confirm_delete'))) return
  try {
    await api.delete(`/api/orders/${props.orderId}/payments/${p.id}`)
    payments.value = payments.value.filter((x) => x.id !== p.id)
    await refreshBalance()
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

function startPayEdit(p) {
  editingPayId.value = p.id
  payEditForm.value = {
    spent_on: p.received_on,
    amountStr: String(parseFloat(p.amount)),
    note: p.note ?? '',
  }
  payEditError.value = ''
  showPayForm.value = false
}

function cancelPayEdit() { editingPayId.value = null }

async function savePayEdit(p) {
  if (payEditSaving.value) return
  payEditError.value = ''
  const amount = parseAmount(payEditForm.value.amountStr)
  if (!amount) { payEditError.value = t('finance.invalid_amount'); return }
  payEditSaving.value = true
  try {
    const updated = await api.patch(`/api/orders/${props.orderId}/payments/${p.id}`, {
      amount,
      received_on: payEditForm.value.spent_on || undefined,
      note: payEditForm.value.note || null,
    })
    const idx = payments.value.findIndex(x => x.id === updated.id)
    if (idx >= 0) payments.value[idx] = updated
    editingPayId.value = null
    await refreshBalance()
  } catch (err) {
    payEditError.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    payEditSaving.value = false
  }
}

async function addExpense() {
  expError.value = ''
  const amount = parseAmount(expForm.value.amountStr)
  if (!amount) { expError.value = t('finance.invalid_amount'); return }
  if (expForm.value.direction === 'to_employee' && !expForm.value.employee_id) {
    expError.value = t('finance.employee'); return
  }
  expSaving.value = true
  try {
    const body = {
      direction: expForm.value.direction,
      category_id: Number(expForm.value.category_id),
      amount,
      spent_on: expForm.value.spent_on,
      note: expForm.value.note || null,
      employee_id: expForm.value.direction === 'to_employee' ? Number(expForm.value.employee_id) : null,
    }
    const created = await api.post(`/api/orders/${props.orderId}/expenses`, body)
    expenses.value.push(created)
    expForm.value = { direction: 'general', category_id: '', employee_id: '', spent_on: '', amountStr: '', note: '' }
    showExpForm.value = false
    await refreshBalance()
  } catch (err) {
    await showAlert(err.status === 400 ? t('finance.invalid_amount') : t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    expSaving.value = false
  }
}

async function deleteExpense(e) {
  if (!await showConfirm(t('finance.confirm_delete'))) return
  try {
    await api.delete(`/api/orders/${props.orderId}/expenses/${e.id}`)
    expenses.value = expenses.value.filter((x) => x.id !== e.id)
    await refreshBalance()
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

function startExpEdit(e) {
  editingExpId.value = e.id
  expEditForm.value = {
    direction: e.direction,
    category_id: e.category_id,
    employee_id: e.employee_id ?? '',
    spent_on: e.spent_on,
    amountStr: String(parseFloat(e.amount)),
    note: e.note ?? '',
  }
  expEditError.value = ''
  showExpForm.value = false
}

function cancelExpEdit() { editingExpId.value = null }

async function saveExpEdit(e) {
  if (expEditSaving.value) return
  expEditError.value = ''
  const amount = parseAmount(expEditForm.value.amountStr)
  if (!amount) { expEditError.value = t('finance.invalid_amount'); return }
  if (expEditForm.value.direction === 'to_employee' && !expEditForm.value.employee_id) {
    expEditError.value = t('finance.employee'); return
  }
  expEditSaving.value = true
  try {
    const body = {
      direction: expEditForm.value.direction,
      category_id: Number(expEditForm.value.category_id),
      amount,
      spent_on: expEditForm.value.spent_on || undefined,
      note: expEditForm.value.note || null,
      employee_id: expEditForm.value.direction === 'to_employee'
        ? Number(expEditForm.value.employee_id)
        : null,
    }
    const updated = await api.patch(`/api/orders/${props.orderId}/expenses/${e.id}`, body)
    const idx = expenses.value.findIndex(x => x.id === updated.id)
    if (idx >= 0) expenses.value[idx] = updated
    editingExpId.value = null
    await refreshBalance()
  } catch (err) {
    expEditError.value = err.status === 400 ? t('finance.invalid_amount') : t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    expEditSaving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.order-finance { display: flex; flex-direction: column; gap: 0.75rem; }

/* Balance card */
.balance-card {
  background: var(--c-surface);
  border-radius: 14px;
  padding: 1rem;
}
.balance-main {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 0.625rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--c-bg);
}
.balance-label { font-size: 0.8rem; color: var(--c-hint); font-weight: 500; }
.balance-amount { font-size: 1.3rem; font-weight: 700; }
.balance-rows { display: flex; flex-direction: column; gap: 0.3rem; }
.bal-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.83rem; }
.bal-name { color: var(--c-hint); display: flex; align-items: center; gap: 0.35rem; }
.bal-name::before { content: ''; width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.positive-dot::before { background: #27ae60; }
.negative-dot::before { background: var(--c-negative); }
.bal-val { font-weight: 600; }
.positive { color: var(--c-positive); }
.negative { color: var(--c-negative); }
.warn { color: var(--c-warning); }

/* Section */
.section { background: var(--c-surface); border-radius: 14px; overflow: hidden; }
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  user-select: none;
}
.section-title { font-size: 0.9rem; font-weight: 600; margin: 0; color: var(--c-text); }
.toggle-btn {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--c-accent);
  color: var(--c-accent-text);
  border: none; cursor: pointer;
  font-size: 1.1rem; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s;
  flex-shrink: 0;
}
.toggle-btn.open { transform: rotate(45deg); }

/* Form */
.form-card { padding: 0.75rem 1rem; border-top: 1px solid var(--c-bg); }
.form-row { display: flex; gap: 0.375rem; margin-bottom: 0.375rem; }
.input-field {
  background: var(--c-bg); border: none; border-radius: 8px;
  padding: 0.45rem 0.6rem; font-size: 0.85rem; color: var(--c-text);
  flex: 1; min-width: 0; outline: none;
}
.input-field.full { width: 100%; box-sizing: border-box; margin-bottom: 0.375rem; display: block; }
.field-error { color: var(--c-negative); font-size: 0.78rem; margin: 0.2rem 0; }
.btn-add {
  width: 100%; background: var(--c-accent);
  color: var(--c-accent-text); border: none;
  border-radius: 8px; padding: 0.55rem; font-size: 0.875rem;
  font-weight: 600; cursor: pointer; margin-top: 0.25rem;
}
.btn-add:disabled { opacity: 0.5; cursor: not-allowed; }

/* List */
.hint { color: var(--c-hint); font-size: 0.85rem; padding: 0.5rem 1rem 0.75rem; }
.fin-list { list-style: none; padding: 0; margin: 0; }
.fin-item {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 0.6rem 1rem;
  border-top: 1px solid var(--c-bg);
  gap: 0.5rem;
}
.fin-left { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; flex: 1; }
.fin-amount { font-size: 0.95rem; font-weight: 700; }
.fin-meta { display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center; }
.fin-cat { font-size: 0.75rem; color: var(--c-hint); }
.fin-badge {
  font-size: 0.7rem; background: var(--tg-theme-bg-color, #e8f0fe);
  color: var(--c-accent);
  border-radius: 4px; padding: 0.1rem 0.35rem;
}
.fin-note { font-size: 0.75rem; color: var(--c-hint); font-style: italic; }
.fin-right { display: flex; align-items: center; gap: 0.375rem; flex-shrink: 0; }
.fin-date { font-size: 0.78rem; color: var(--c-hint); }
.btn-icon {
  background: none; border: none; cursor: pointer;
  font-size: 0.85rem; padding: 0.15rem 0.25rem;
  color: var(--c-hint); border-radius: 4px;
  transition: color 0.15s;
}
.btn-icon.active { color: var(--c-accent); }
.btn-del { background: none; border: none; color: var(--c-negative); cursor: pointer; font-size: 0.85rem; padding: 0.1rem; }

/* Inline edit form */
.fin-edit-form {
  padding: 0.625rem 1rem 0.75rem;
  border-top: 2px solid var(--c-accent);
  background: var(--c-surface);
  overflow: hidden;
}
.fef-row { display: flex; gap: 0.375rem; }
.fef-field { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; min-width: 0; }
.fef-label { font-size: 0.68rem; color: var(--c-hint); font-weight: 500; text-transform: uppercase; letter-spacing: 0.03em; }
.fef-input {
  background: var(--c-bg); border: none; border-radius: 8px;
  padding: 0.45rem 0.6rem; font-size: 0.85rem; color: var(--c-text);
  width: 100%; box-sizing: border-box; outline: none;
}
.fef-actions { display: flex; gap: 0.375rem; margin-top: 0.625rem; }
.fef-cancel {
  flex: 1; padding: 0.5rem; border: none; border-radius: 8px;
  background: var(--c-bg); color: var(--c-hint);
  font-size: 0.85rem; font-weight: 600; cursor: pointer;
}
.fef-save {
  flex: 2; padding: 0.5rem; border: none; border-radius: 8px;
  background: var(--c-accent); color: var(--c-accent-text);
  font-size: 0.85rem; font-weight: 600; cursor: pointer;
}
.fef-save:disabled { opacity: 0.5; cursor: not-allowed; }

/* Slide transition */
.slide-enter-active, .slide-leave-active { transition: max-height 0.2s ease, opacity 0.2s ease; max-height: 400px; overflow: hidden; }
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; }
</style>
