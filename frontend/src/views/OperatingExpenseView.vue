<template>
  <div class="op-view">
    <!-- Add form toggle -->
    <div class="section-header" @click="showForm = !showForm">
      <h2 class="section-title">{{ t('finance.operating_title') }}</h2>
      <button class="toggle-btn" :class="{ open: showForm }">+</button>
    </div>

    <transition name="slide">
      <div v-if="showForm" class="form-card">
        <div class="form-row">
          <select v-model="form.category_id" class="input-field">
            <option value="">{{ t('finance.category') }}</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <input v-model="form.spent_on" type="date" class="input-field" />
        </div>
        <div class="form-row">
          <input v-model="form.amountStr" type="text" inputmode="decimal" class="input-field"
            :placeholder="t('finance.amount_placeholder')" @blur="cleanAmount" />
          <input v-model="form.note" type="text" class="input-field" :placeholder="t('finance.note')" />
        </div>
        <p v-if="formError" class="field-error">{{ formError }}</p>
        <button class="btn-add" :disabled="submitting || !form.category_id || !form.spent_on" @click="submit">
          {{ submitting ? '…' : t('finance.add') }}
        </button>
      </div>
    </transition>

    <!-- List -->
    <div v-if="loading" class="hint">…</div>
    <p v-else-if="items.length === 0" class="hint">{{ t('finance.no_operating') }}</p>
    <ul v-else class="expense-list">
      <li v-for="item in items" :key="item.id" class="expense-item">
        <div class="exp-main">
          <div class="exp-left">
            <span class="exp-amount">{{ display(item.amount) }}</span>
            <span class="exp-cat">{{ categoryName(item.category_id) }}</span>
            <span v-if="item.note" class="exp-note">{{ item.note }}</span>
          </div>
          <div class="exp-right">
            <span class="exp-date">{{ fmtDate(item.spent_on) }}</span>
            <button class="btn-edit" :class="{ active: editingId === item.id }"
              @click="editingId === item.id ? cancelEdit() : startEdit(item)">✏</button>
            <button class="btn-del" @click="remove(item)">✕</button>
          </div>
        </div>

        <!-- Inline edit form -->
        <transition name="slide">
          <div v-if="editingId === item.id" class="fin-edit-form">
            <div class="fef-row">
              <div class="fef-field">
                <label class="fef-label">{{ t('finance.category') }}</label>
                <select v-model="editForm.category_id" class="fef-input">
                  <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </div>
              <div class="fef-field">
                <label class="fef-label">{{ t('finance.date') }}</label>
                <input v-model="editForm.spent_on" type="date" class="fef-input" />
              </div>
            </div>
            <div class="fef-row">
              <div class="fef-field">
                <label class="fef-label">{{ t('finance.amount') }}</label>
                <input v-model="editForm.amountStr" type="text" inputmode="decimal"
                  class="fef-input" :placeholder="t('finance.amount_placeholder')"
                  @blur="cleanEditAmount" />
              </div>
              <div class="fef-field">
                <label class="fef-label">{{ t('finance.note') }}</label>
                <input v-model="editForm.note" type="text" class="fef-input"
                  :placeholder="t('finance.note')" />
              </div>
            </div>
            <p v-if="editError" class="field-error">{{ editError }}</p>
            <div class="fef-actions">
              <button class="fef-cancel" @click="cancelEdit">{{ t('finance.cancel') }}</button>
              <button class="fef-save" :disabled="editSaving || !editForm.category_id || !editForm.spent_on"
                @click="saveEdit(item)">
                {{ editSaving ? '…' : t('finance.save') }}
              </button>
            </div>
          </div>
        </transition>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showConfirm, showAlert } from '../telegram.js'
import { parseAmount, displayAmount } from '../money.js'

const { t } = useI18n()
const categories = ref([])
const items = ref([])
const loading = ref(false)
const submitting = ref(false)
const formError = ref('')
const showForm = ref(false)

const form = ref({ category_id: '', spent_on: '', amountStr: '', note: '' })

const editingId = ref(null)
const editForm = ref({ category_id: '', spent_on: '', amountStr: '', note: '' })
const editError = ref('')
const editSaving = ref(false)

function display(str) { return displayAmount(str, 'сум') }

function categoryName(id) {
  return categories.value.find(c => c.id === id)?.name ?? '—'
}

function fmtDate(iso) {
  if (!iso) return ''
  const [, m, d] = iso.split('-')
  return `${d}.${m}`
}

function cleanAmount() {
  const cleaned = parseAmount(form.value.amountStr)
  if (cleaned) form.value.amountStr = cleaned
}

function cleanEditAmount() {
  const cleaned = parseAmount(editForm.value.amountStr)
  if (cleaned) editForm.value.amountStr = cleaned
}

function startEdit(item) {
  editingId.value = item.id
  editError.value = ''
  editForm.value = {
    category_id: item.category_id,
    spent_on: item.spent_on,
    amountStr: String(parseFloat(item.amount)),
    note: item.note ?? '',
  }
}

function cancelEdit() {
  editingId.value = null
  editError.value = ''
}

async function saveEdit(item) {
  editError.value = ''
  const amount = parseAmount(editForm.value.amountStr)
  if (!amount) { editError.value = t('finance.invalid_amount'); return }
  editSaving.value = true
  try {
    const updated = await api.patch(`/api/operating-expenses/${item.id}`, {
      category_id: Number(editForm.value.category_id),
      amount,
      spent_on: editForm.value.spent_on,
      note: editForm.value.note || null,
    })
    const idx = items.value.findIndex(x => x.id === item.id)
    if (idx !== -1) items.value[idx] = updated
    cancelEdit()
  } catch (err) {
    editError.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    editSaving.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [cats, list] = await Promise.all([
      api.get('/api/expense-categories'),
      api.get('/api/operating-expenses'),
    ])
    categories.value = cats
    items.value = list
  } catch { /* silent */ } finally {
    loading.value = false
  }
}

async function submit() {
  formError.value = ''
  const amount = parseAmount(form.value.amountStr)
  if (!amount) { formError.value = t('finance.invalid_amount'); return }
  submitting.value = true
  try {
    const created = await api.post('/api/operating-expenses', {
      category_id: Number(form.value.category_id),
      amount,
      spent_on: form.value.spent_on,
      note: form.value.note || null,
    })
    items.value.unshift(created)
    form.value = { category_id: '', spent_on: '', amountStr: '', note: '' }
    showForm.value = false
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    submitting.value = false
  }
}

async function remove(item) {
  const ok = await showConfirm(t('finance.confirm_delete'))
  if (!ok) return
  try {
    await api.delete(`/api/operating-expenses/${item.id}`)
    items.value = items.value.filter((x) => x.id !== item.id)
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  }
}

onMounted(loadAll)
</script>

<style scoped>
.op-view { padding: 0 1rem 1rem; display: flex; flex-direction: column; gap: 0.5rem; }

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  cursor: pointer; user-select: none; padding: 0.25rem 0;
}
.section-title { font-size: 1rem; font-weight: 600; margin: 0; color: var(--tg-theme-text-color, inherit); }
.toggle-btn {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--tg-theme-button-color, #2481cc);
  color: var(--tg-theme-button-text-color, #fff);
  border: none; cursor: pointer;
  font-size: 1.1rem; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s;
  flex-shrink: 0;
}
.toggle-btn.open { transform: rotate(45deg); }

.form-card {
  background: var(--tg-theme-secondary-bg-color, #f0f0f0);
  border-radius: 14px; padding: 0.875rem;
}
.form-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.input-field {
  background: var(--tg-theme-bg-color, #fff); border: none; border-radius: 8px;
  padding: 0.45rem 0.6rem; font-size: 0.85rem; color: var(--tg-theme-text-color, inherit);
  flex: 1; min-width: 0; outline: none;
}
.field-error { color: var(--c-danger); font-size: 0.8rem; margin: 0.25rem 0; }
.btn-add {
  width: 100%; margin-top: 0.25rem;
  background: var(--tg-theme-button-color, #2481cc);
  color: var(--tg-theme-button-text-color, #fff);
  border: none; border-radius: 8px; padding: 0.6rem;
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.btn-add:disabled { opacity: 0.5; cursor: not-allowed; }

.hint { color: var(--tg-theme-hint-color, #888); text-align: center; font-size: 0.875rem; }

.expense-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.375rem; }
.expense-item {
  background: var(--tg-theme-secondary-bg-color, #f0f0f0);
  border-radius: 12px; padding: 0.625rem 0.875rem;
  overflow: hidden;
}
.exp-main { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
.exp-left { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.exp-amount { font-size: 0.95rem; font-weight: 700; color: var(--tg-theme-text-color, inherit); }
.exp-cat { font-size: 0.78rem; color: var(--tg-theme-hint-color, #888); }
.exp-note { font-size: 0.75rem; color: var(--tg-theme-hint-color, #888); font-style: italic; }
.exp-right { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
.exp-date { font-size: 0.78rem; color: var(--tg-theme-hint-color, #888); }
.btn-edit {
  background: none; border: none; cursor: pointer;
  font-size: 0.85rem; padding: 0.1rem;
  color: var(--tg-theme-hint-color, #888);
  transition: color 0.15s;
}
.btn-edit.active { color: var(--c-accent); }
.btn-del { background: none; border: none; color: var(--c-danger); cursor: pointer; font-size: 0.9rem; padding: 0.1rem; }

/* Inline edit form */
.fin-edit-form {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 2px solid var(--c-accent);
}
.fef-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.fef-field { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; min-width: 0; }
.fef-label { font-size: 0.72rem; color: var(--tg-theme-hint-color, #888); font-weight: 500; }
.fef-input {
  background: var(--tg-theme-bg-color, #fff);
  border: none; border-radius: 8px;
  padding: 0.45rem 0.6rem;
  font-size: 0.85rem; color: var(--tg-theme-text-color, inherit);
  width: 100%; box-sizing: border-box; outline: none;
}
.fef-actions { display: flex; gap: 0.5rem; margin-top: 0.25rem; }
.fef-cancel {
  flex: 1; padding: 0.5rem; border: none; border-radius: 8px; cursor: pointer;
  font-size: 0.85rem; font-weight: 600;
  background: var(--tg-theme-bg-color, #fff);
  color: var(--tg-theme-hint-color, #888);
}
.fef-save {
  flex: 2; padding: 0.5rem; border: none; border-radius: 8px; cursor: pointer;
  font-size: 0.85rem; font-weight: 600;
  background: var(--c-accent);
  color: #fff;
}
.fef-save:disabled { opacity: 0.5; cursor: not-allowed; }

.slide-enter-active, .slide-leave-active { transition: max-height 0.22s ease, opacity 0.2s ease; max-height: 400px; overflow: hidden; }
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; }
</style>
