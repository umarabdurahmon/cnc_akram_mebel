<template>
  <div class="settings-view">

    <!-- Главное меню -->
    <template v-if="!section">
      <div class="settings-hero">
        <div class="settings-hero-icon">⚙️</div>
        <div class="settings-hero-title">{{ t('settings.title') }}</div>
      </div>

      <div class="menu-group">
        <button class="menu-item" @click="section = 'language'">
          <div class="menu-icon-wrap" style="background: #e3f2fd;">🌐</div>
          <div class="menu-text">
            <span class="menu-label">{{ t('settings.language') }}</span>
            <span class="menu-desc">Русский / O'zbekcha</span>
          </div>
          <span class="menu-arrow">›</span>
        </button>
        <template v-if="isManager">
          <div class="menu-divider" />
          <button class="menu-item" @click="openEmployees">
            <div class="menu-icon-wrap" style="background: #e8f5e9;">👥</div>
            <div class="menu-text">
              <span class="menu-label">{{ t('settings.employees') }}</span>
              <span class="menu-desc">Добавление и управление</span>
            </div>
            <span class="menu-arrow">›</span>
          </button>
          <div class="menu-divider" />
          <button class="menu-item" @click="section = 'catalog'">
            <div class="menu-icon-wrap" style="background: #fff3e0;">📋</div>
            <div class="menu-text">
              <span class="menu-label">{{ t('settings.catalog') }}</span>
              <span class="menu-desc">Этапы и категории расходов</span>
            </div>
            <span class="menu-arrow">›</span>
          </button>
          <div class="menu-divider" />
          <button class="menu-item" @click="openCompany">
            <div class="menu-icon-wrap" style="background: #f3e5f5;">🏢</div>
            <div class="menu-text">
              <span class="menu-label">{{ t('settings.company') }}</span>
              <span class="menu-desc">{{ t('settings.company_desc') }}</span>
            </div>
            <span class="menu-arrow">›</span>
          </button>
        </template>
      </div>
    </template>

    <!-- Смена языка -->
    <template v-else-if="section === 'language'">
      <div class="page-hero">
        <button class="hero-back" @click="section = null">‹</button>
        <span class="hero-icon">🌐</span>
        <span class="hero-title">{{ t('settings.language') }}</span>
      </div>
      <div class="menu-group">
        <template v-for="(lang, idx) in langs" :key="lang.code">
          <button
            class="menu-item"
            :class="{ active: currentLang === lang.code }"
            @click="setLang(lang.code)"
          >
            <div class="menu-text"><span class="menu-label">{{ lang.label }}</span></div>
            <span v-if="currentLang === lang.code" class="check">✓</span>
          </button>
          <div v-if="idx < langs.length - 1" class="menu-divider" />
        </template>
      </div>
    </template>

    <!-- Сотрудники -->
    <template v-else-if="section === 'employees'">
      <div class="page-hero">
        <button class="hero-back" @click="closeEmployees">‹</button>
        <span class="hero-icon">👥</span>
        <span class="hero-title">{{ t('settings.employees') }}</span>
        <button class="add-btn" @click="showForm = !showForm" :class="{ open: showForm }">+</button>
      </div>

      <!-- Форма добавления — раскрывается по кнопке + -->
      <transition name="slide-down">
        <div v-if="showForm" class="add-form">
          <div class="tg-id-hint">
            💡 {{ t('settings.tg_id_hint') }}
            <strong>@userinfobot</strong>
          </div>

          <div class="field" :class="{ 'field-error': errors.telegram_id }">
            <label>Telegram ID</label>
            <input
              v-model="newEmp.telegram_id"
              type="number"
              inputmode="numeric"
              class="input-text"
              placeholder="123456789"
              @input="errors.telegram_id = ''"
            />
            <span v-if="errors.telegram_id" class="error-text">{{ errors.telegram_id }}</span>
          </div>

          <div class="field" :class="{ 'field-error': errors.full_name }">
            <label>{{ t('settings.full_name') }}</label>
            <input
              v-model="newEmp.full_name"
              type="text"
              class="input-text"
              :placeholder="t('settings.full_name_placeholder')"
              @input="errors.full_name = ''"
              @keyup.enter="addEmployee"
            />
            <span v-if="errors.full_name" class="error-text">{{ errors.full_name }}</span>
          </div>

          <div class="field">
            <label>{{ t('settings.position') }}</label>
            <input
              v-model="newEmp.position"
              type="text"
              class="input-text"
              :placeholder="t('settings.position_placeholder')"
              @keyup.enter="addEmployee"
            />
          </div>

          <div v-if="errors.general" class="general-error">{{ errors.general }}</div>

          <div class="form-actions">
            <button class="btn-cancel-sm" @click="cancelForm">{{ t('settings.cancel') }}</button>
            <button
              class="btn-add"
              :disabled="empSaving"
              @click="addEmployee"
            >
              <span v-if="empSaving" class="spinner">⏳</span>
              <span v-else>{{ t('settings.add') }}</span>
            </button>
          </div>
        </div>
      </transition>

      <!-- Успех -->
      <transition name="fade">
        <div v-if="successMsg" class="success-banner">
          ✓ {{ successMsg }}
        </div>
      </transition>

      <!-- Список -->
      <div v-if="empLoading" class="loading-row">
        <span class="spinner-dots">···</span>
      </div>
      <div v-else-if="employees.length" class="emp-list">
        <div v-for="emp in employees" :key="emp.id" class="emp-card-wrap">
          <div class="emp-item" :class="{ 'emp-inactive': !emp.is_active }">
            <div class="emp-avatar">{{ initials(emp.full_name) }}</div>
            <div class="emp-info">
              <div class="emp-name">{{ emp.full_name }}</div>
              <div class="emp-sub">
                <span class="emp-role">{{ emp.role === 'manager' ? 'Руководитель' : 'Рабочий' }}</span>
                <span v-if="emp.position" class="emp-pos">{{ emp.position }}</span>
                <span v-if="!emp.is_active" class="emp-inactive-badge">{{ t('settings.inactive') }}</span>
              </div>
            </div>
            <button
              class="emp-edit-btn"
              :class="{ active: editingEmpId === emp.id }"
              :title="t('settings.edit')"
              @click="editingEmpId === emp.id ? cancelEdit() : startEdit(emp)"
            >✏</button>
            <div
              class="emp-toggle"
              :class="{ on: emp.is_active }"
              :title="emp.is_active ? t('settings.deactivate') : t('settings.activate')"
              @click="toggleActive(emp)"
            >
              <div class="emp-toggle-thumb" />
            </div>
          </div>

          <!-- Inline edit form -->
          <transition name="slide-down">
            <div v-if="editingEmpId === emp.id" class="emp-edit-form">
              <div class="field" :class="{ 'field-error': editErrors.full_name }">
                <label>{{ t('settings.full_name') }}</label>
                <input
                  v-model="editEmp.full_name"
                  type="text"
                  class="input-text"
                  :placeholder="t('settings.full_name_placeholder')"
                  @input="editErrors.full_name = ''"
                  @keyup.enter="saveEdit(emp)"
                />
                <span v-if="editErrors.full_name" class="error-text">{{ editErrors.full_name }}</span>
              </div>
              <div class="field">
                <label>{{ t('settings.position') }}</label>
                <input
                  v-model="editEmp.position"
                  type="text"
                  class="input-text"
                  :placeholder="t('settings.position_placeholder')"
                  @keyup.enter="saveEdit(emp)"
                />
              </div>
              <div class="form-actions">
                <button class="btn-cancel-sm" @click="cancelEdit">{{ t('settings.cancel') }}</button>
                <button class="btn-add" :disabled="editSaving" @click="saveEdit(emp)">
                  <span v-if="editSaving" class="spinner">⏳</span>
                  <span v-else>{{ t('settings.save') }}</span>
                </button>
              </div>
              <button class="btn-delete-emp" :disabled="editSaving" @click="deleteEmployee(emp)">
                🗑 {{ t('settings.delete') }}
              </button>
            </div>
          </transition>
        </div>
      </div>
      <div v-else-if="!showForm" class="empty-state">
        <div class="empty-icon">👤</div>
        <div class="empty-text">{{ t('settings.no_employees') }}</div>
        <button class="btn-primary" @click="showForm = true">{{ t('settings.add_first') }}</button>
      </div>
    </template>

    <!-- Справочники — список -->
    <template v-else-if="section === 'catalog'">
      <div class="page-hero">
        <button class="hero-back" @click="section = null">‹</button>
        <span class="hero-icon">📋</span>
        <span class="hero-title">{{ t('settings.catalog') }}</span>
      </div>
      <div class="menu-group">
        <template v-for="(cat, idx) in catalogs" :key="cat.key">
          <button class="menu-item" @click="openCatalog(cat)">
            <div class="menu-icon-wrap" style="background: var(--c-surface);">{{ cat.icon }}</div>
            <div class="menu-text"><span class="menu-label">{{ t(cat.labelKey) }}</span></div>
            <span class="menu-arrow">›</span>
          </button>
          <div v-if="idx < catalogs.length - 1" class="menu-divider" />
        </template>
      </div>
    </template>

    <!-- Конкретный справочник -->
    <template v-else-if="section === 'catalog-detail'">
      <div class="page-hero">
        <button class="hero-back" @click="section = 'catalog'">‹</button>
        <span class="hero-icon">{{ activeCatalog.icon }}</span>
        <span class="hero-title">{{ t(activeCatalog.labelKey) }}</span>
      </div>
      <CatalogPanel
        :list-url="activeCatalog.listUrl"
        :create-url="activeCatalog.createUrl"
        :patch-url="activeCatalog.patchUrl"
        :has-position="activeCatalog.hasPosition"
      />
    </template>

    <!-- Информация о предприятии -->
    <template v-else-if="section === 'company'">
      <div class="page-hero">
        <button class="hero-back" @click="section = null">‹</button>
        <span class="hero-icon">🏢</span>
        <span class="hero-title">{{ t('settings.company') }}</span>
      </div>

      <div v-if="companyLoading" class="loading-row">
        <span class="spinner-dots">···</span>
      </div>

      <template v-else>
        <div class="tg-id-hint" style="margin-bottom: 1rem;">💡 {{ t('settings.company_hint') }}</div>

        <div class="add-form">
          <div class="field">
            <label>{{ t('settings.company_brand') }}</label>
            <input v-model="company.brand_name" type="text" class="input-text"
              :placeholder="t('settings.company_brand_ph')" />
          </div>
          <div class="field">
            <label>{{ t('settings.company_phone') }}</label>
            <input v-model="company.phone" type="text" class="input-text"
              :placeholder="t('settings.company_phone_ph')" />
          </div>
          <div class="field">
            <label>{{ t('settings.company_address') }}</label>
            <input v-model="company.address" type="text" class="input-text"
              :placeholder="t('settings.company_address_ph')" />
          </div>
          <div class="field">
            <label>{{ t('settings.company_hours') }}</label>
            <input v-model="company.working_hours" type="text" class="input-text"
              :placeholder="t('settings.company_hours_ph')" />
          </div>
          <div class="field">
            <label>{{ t('settings.company_website') }}</label>
            <input v-model="company.website" type="text" class="input-text"
              :placeholder="t('settings.company_website_ph')" />
          </div>
          <div class="field">
            <label>{{ t('settings.company_note') }}</label>
            <textarea v-model="company.footer_note" class="input-text" rows="2"
              :placeholder="t('settings.company_note_ph')" />
          </div>

          <transition name="fade">
            <div v-if="companySaved" class="success-banner">✓ {{ t('settings.company_saved') }}</div>
          </transition>

          <button class="btn-add" :disabled="companySaving" style="width: 100%; margin-top: 0.25rem;"
            @click="saveCompany">
            <span v-if="companySaving" class="spinner">⏳</span>
            <span v-else>{{ t('settings.company_save') }}</span>
          </button>
        </div>
      </template>
    </template>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showAlert, showConfirm } from '../telegram.js'
import CatalogPanel from './CatalogPanel.vue'

defineProps({
  isManager: { type: Boolean, required: true },
})

const { t, locale } = useI18n()

const section = ref(null)

// --- Справочники ---
const catalogs = [
  {
    key: 'stages',
    icon: '🏭',
    labelKey: 'settings.stages',
    listUrl: '/api/stages',
    createUrl: '/api/stages',
    patchUrl: '/api/stages',
    hasPosition: true,
  },
  {
    key: 'categories',
    icon: '🗂️',
    labelKey: 'settings.categories',
    listUrl: '/api/expense-categories',
    createUrl: '/api/expense-categories',
    patchUrl: '/api/expense-categories',
    hasPosition: false,
  },
]
const activeCatalog = ref(null)

function openCatalog(cat) {
  activeCatalog.value = cat
  section.value = 'catalog-detail'
}

// --- Информация о предприятии ---
const company = ref({
  brand_name: '', phone: '', address: '', working_hours: '', website: '', footer_note: '',
})
const companyLoading = ref(false)
const companySaving = ref(false)
const companySaved = ref(false)

async function openCompany() {
  section.value = 'company'
  companyLoading.value = true
  try {
    const data = await api.get('/api/company')
    company.value = {
      brand_name: data.brand_name ?? '',
      phone: data.phone ?? '',
      address: data.address ?? '',
      working_hours: data.working_hours ?? '',
      website: data.website ?? '',
      footer_note: data.footer_note ?? '',
    }
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    companyLoading.value = false
  }
}

async function saveCompany() {
  if (companySaving.value) return
  companySaving.value = true
  try {
    await api.patch('/api/company', { ...company.value })
    companySaved.value = true
    setTimeout(() => { companySaved.value = false }, 3000)
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    companySaving.value = false
  }
}

// --- Язык ---
const langs = [
  { code: 'ru', label: 'Русский' },
  { code: 'uz', label: "O'zbek" },
]
const currentLang = ref(locale.value)

async function setLang(code) {
  locale.value = code
  currentLang.value = code
  try { await api.patch('/api/me/language', { language: code }) } catch { /* non-critical */ }
}

// --- Сотрудники ---
const employees = ref([])
const empLoading = ref(false)
const empSaving = ref(false)
const showForm = ref(false)
const successMsg = ref('')
const newEmp = ref({ telegram_id: '', full_name: '', position: '' })
const errors = ref({ telegram_id: '', full_name: '', general: '' })

// Редактирование сотрудника
const editingEmpId = ref(null)
const editEmp = ref({ full_name: '', position: '' })
const editSaving = ref(false)
const editErrors = ref({ full_name: '' })

function initials(name) {
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

async function openEmployees() {
  section.value = 'employees'
  empLoading.value = true
  try {
    employees.value = await api.get('/api/employees')
  } catch {
    employees.value = []
  } finally {
    empLoading.value = false
  }
}

function closeEmployees() {
  section.value = null
  showForm.value = false
  resetForm()
}

function cancelForm() {
  showForm.value = false
  resetForm()
}

function resetForm() {
  newEmp.value = { telegram_id: '', full_name: '', position: '' }
  errors.value = { telegram_id: '', full_name: '', general: '' }
}

function validate() {
  let ok = true
  errors.value = { telegram_id: '', full_name: '', general: '' }
  const id = Number(newEmp.value.telegram_id)
  if (!id || id <= 0) {
    errors.value.telegram_id = t('settings.err_invalid_id')
    ok = false
  }
  if (!newEmp.value.full_name.trim()) {
    errors.value.full_name = t('settings.err_name_required')
    ok = false
  }
  return ok
}

async function addEmployee() {
  if (empSaving.value || !validate()) return
  empSaving.value = true
  try {
    const emp = await api.post('/api/employees', {
      telegram_id: Number(newEmp.value.telegram_id),
      full_name: newEmp.value.full_name.trim(),
      language: locale.value,
      position: newEmp.value.position.trim() || null,
    })
    const idx = employees.value.findIndex(e => e.id === emp.id)
    if (idx >= 0) employees.value[idx] = emp
    else employees.value.unshift(emp)

    successMsg.value = t('settings.added_success', { name: emp.full_name })
    setTimeout(() => { successMsg.value = '' }, 3000)
    showForm.value = false
    resetForm()
  } catch (err) {
    if (err.status === 409) {
      errors.value.telegram_id = t('settings.err_already_manager')
    } else {
      errors.value.general = t(`errors.${err.code ?? 'unknown'}`)
    }
  } finally {
    empSaving.value = false
  }
}

async function toggleActive(emp) {
  try {
    const updated = await api.patch(`/api/employees/${emp.id}`, { is_active: !emp.is_active })
    const idx = employees.value.findIndex(e => e.id === updated.id)
    if (idx >= 0) employees.value[idx] = updated
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  }
}

function startEdit(emp) {
  editingEmpId.value = emp.id
  editEmp.value = { full_name: emp.full_name, position: emp.position ?? '' }
  editErrors.value = { full_name: '' }
  showForm.value = false
}

function cancelEdit() {
  editingEmpId.value = null
}

async function deleteEmployee(emp) {
  if (!await showConfirm(t('settings.confirm_delete_emp', { name: emp.full_name }))) return
  try {
    await api.delete(`/api/employees/${emp.id}`)
    employees.value = employees.value.filter(e => e.id !== emp.id)
    editingEmpId.value = null
  } catch (err) {
    if (err.status === 409) {
      await showAlert(t('settings.delete_emp_in_use'))
    } else {
      await showAlert(t(`errors.${err.code ?? 'unknown'}`))
    }
  }
}

async function saveEdit(emp) {
  if (editSaving.value) return
  editErrors.value = { full_name: '' }
  if (!editEmp.value.full_name.trim()) {
    editErrors.value.full_name = t('settings.err_name_required')
    return
  }
  editSaving.value = true
  try {
    const updated = await api.patch(`/api/employees/${emp.id}`, {
      full_name: editEmp.value.full_name.trim(),
      position: editEmp.value.position.trim() || null,
    })
    const idx = employees.value.findIndex(e => e.id === updated.id)
    if (idx >= 0) employees.value[idx] = updated
    editingEmpId.value = null
    successMsg.value = t('settings.updated_success', { name: updated.full_name })
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (err) {
    editErrors.value.full_name = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    editSaving.value = false
  }
}
</script>

<style scoped>
.settings-view { padding: 0 1rem 2rem; max-width: 600px; margin: 0 auto; }

/* Hero */
.settings-hero {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1.25rem 0 1.5rem;
}
.settings-hero-icon { font-size: 2rem; line-height: 1; }
.settings-hero-title { font-size: 1.4rem; font-weight: 700; color: var(--c-text); }

/* Grouped menu (iOS-style) */
.menu-group {
  background: var(--c-surface);
  border-radius: 16px;
  overflow: hidden;
}
.menu-item {
  display: flex; align-items: center; gap: 0.875rem;
  background: none; border: none;
  padding: 0.875rem 1rem;
  font-size: 1rem; color: var(--c-text);
  cursor: pointer; text-align: left; width: 100%;
  transition: opacity 0.15s;
}
.menu-item:active { opacity: 0.6; }
.menu-item.active { color: var(--c-accent); }
.menu-icon-wrap {
  width: 2.25rem; height: 2.25rem; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; flex-shrink: 0;
}
.menu-text { flex: 1; display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.menu-label { font-weight: 500; font-size: 0.95rem; }
.menu-desc { font-size: 0.75rem; color: var(--c-hint); }
.menu-arrow { color: var(--c-hint); font-size: 1.2rem; font-weight: 300; flex-shrink: 0; }
.menu-divider { height: 1px; background: var(--c-bg); margin-left: 4.125rem; }
.check { color: var(--c-accent); font-weight: 700; }

/* Page hero (shared across sub-sections) */
.page-hero {
  display: flex; align-items: center; gap: 0.625rem;
  padding: 1.25rem 0 1.125rem;
}
.hero-back {
  background: none; border: none; font-size: 1.75rem; line-height: 1;
  padding: 0 0.25rem 0 0; cursor: pointer; color: var(--c-accent); flex-shrink: 0;
}
.hero-icon { font-size: 1.75rem; line-height: 1; flex-shrink: 0; }
.hero-title { font-size: 1.4rem; font-weight: 700; color: var(--c-text); flex: 1; }
.add-btn {
  width: 2rem; height: 2rem; border-radius: 50%; border: none;
  background: var(--c-accent); color: var(--c-accent-text);
  font-size: 1.4rem; line-height: 1; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s; flex-shrink: 0;
}
.add-btn.open { transform: rotate(45deg); }

/* Add form */
.add-form {
  background: var(--c-surface);
  border-radius: 14px; padding: 1rem; margin-bottom: 1rem;
  overflow: hidden;
}
.tg-id-hint {
  font-size: 0.82rem; color: var(--c-hint);
  background: var(--c-bg);
  border-radius: 8px; padding: 0.5rem 0.75rem;
  margin-bottom: 0.875rem; line-height: 1.4;
}
.field { margin-bottom: 0.75rem; }
.field label { display: block; font-size: 0.78rem; color: var(--c-hint); margin-bottom: 0.25rem; font-weight: 500; }
.input-text {
  background: var(--c-bg); border: 1.5px solid transparent;
  border-radius: 8px; padding: 0.55rem 0.75rem;
  font-size: 0.95rem; color: var(--c-text);
  width: 100%; box-sizing: border-box; transition: border-color 0.15s;
}
.input-text:focus { outline: none; border-color: var(--c-accent); }
.field-error .input-text { border-color: var(--c-negative); }
.error-text { display: block; font-size: 0.76rem; color: var(--c-negative); margin-top: 0.2rem; }
.general-error { font-size: 0.82rem; color: var(--c-negative); margin-bottom: 0.5rem; text-align: center; }

.form-actions { display: flex; gap: 0.5rem; margin-top: 0.25rem; }
.btn-cancel-sm {
  flex: 1; padding: 0.65rem; border: none; border-radius: 10px;
  background: var(--c-bg);
  color: var(--c-hint);
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.btn-add {
  flex: 2; padding: 0.65rem; border: none; border-radius: 10px;
  background: var(--c-accent);
  color: var(--c-accent-text);
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.btn-add:disabled { opacity: 0.5; cursor: not-allowed; }

/* Success banner */
.success-banner {
  background: var(--c-due-ok-bg); color: var(--c-positive); border-radius: 10px;
  padding: 0.6rem 1rem; font-size: 0.9rem; font-weight: 500;
  margin-bottom: 0.75rem; text-align: center;
}

/* Employee list */
.loading-row { text-align: center; padding: 1.5rem 0; color: var(--c-hint); font-size: 1.5rem; letter-spacing: 0.2em; }
.emp-list { display: flex; flex-direction: column; gap: 0.5rem; }
.emp-item {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--c-surface);
  border-radius: 14px; padding: 0.75rem 1rem;
  transition: border-radius 0.2s;
}
.emp-card-wrap:has(.emp-edit-form) .emp-item { border-radius: 14px 14px 0 0; }
.emp-inactive { opacity: 0.5; }
.emp-avatar {
  width: 2.75rem; height: 2.75rem; border-radius: 50%;
  background: var(--c-accent);
  color: var(--c-accent-text);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 700; flex-shrink: 0;
}
.emp-inactive .emp-avatar { background: var(--c-hint); }
.emp-info { flex: 1; min-width: 0; }
.emp-name { font-weight: 600; font-size: 0.95rem; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.emp-sub { display: flex; align-items: center; gap: 0.375rem; margin-top: 0.15rem; }
.emp-role { font-size: 0.72rem; color: var(--c-hint); }
.emp-inactive-badge {
  font-size: 0.68rem; font-weight: 600;
  background: var(--c-negative-bg); color: var(--c-negative-dark);
  border-radius: 4px; padding: 0.05rem 0.3rem;
}

/* Employee edit */
.emp-card-wrap { display: flex; flex-direction: column; }
.emp-edit-btn {
  background: none; border: none; cursor: pointer;
  font-size: 0.95rem; padding: 0.25rem 0.35rem;
  color: var(--c-hint); border-radius: 6px;
  flex-shrink: 0; transition: color 0.15s, background 0.15s;
}
.emp-edit-btn:hover, .emp-edit-btn.active { color: var(--c-accent); background: var(--c-bg); }
.emp-pos {
  font-size: 0.72rem; color: var(--c-hint);
  background: var(--c-bg); border-radius: 4px;
  padding: 0.05rem 0.35rem;
}
.emp-edit-form {
  background: var(--c-surface);
  border-top: 1px solid var(--c-bg);
  border-radius: 0 0 14px 14px;
  padding: 0.75rem 1rem 0.875rem;
  overflow: hidden;
}

.btn-delete-emp {
  width: 100%; margin-top: 0.5rem; padding: 0.5rem;
  background: none; border: 1px solid var(--c-negative);
  color: var(--c-negative); border-radius: 8px;
  font-size: 0.82rem; font-weight: 500; cursor: pointer;
}
.btn-delete-emp:disabled { opacity: 0.4; cursor: not-allowed; }

/* Employee active toggle */
.emp-toggle {
  width: 3rem; height: 1.625rem; border-radius: 99px;
  background: var(--c-hint); border: none; cursor: pointer;
  position: relative; flex-shrink: 0;
  transition: background 0.2s;
  opacity: 0.5;
}
.emp-toggle.on { background: var(--c-positive); opacity: 1; }
.emp-toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: calc(1.625rem - 8px); height: calc(1.625rem - 8px);
  border-radius: 50%; background: #fff;
  transition: transform 0.2s;
}
.emp-toggle.on .emp-toggle-thumb { transform: translateX(1.375rem); }

/* Empty state */
.empty-state { text-align: center; padding: 2rem 1rem; }
.empty-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.empty-text { color: var(--c-hint); margin-bottom: 1.25rem; font-size: 0.95rem; }
.btn-primary { padding: 0.75rem 1.5rem; border: none; border-radius: 10px; background: var(--c-accent); color: var(--c-accent-text); font-size: 0.95rem; font-weight: 600; cursor: pointer; }

/* Transitions */
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.25s ease; max-height: 400px; }
.slide-down-enter-from, .slide-down-leave-to { max-height: 0; opacity: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
