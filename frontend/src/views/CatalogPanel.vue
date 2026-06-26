<template>
  <div class="catalog-panel">
    <!-- Форма добавления -->
    <div class="add-card">
      <div class="add-fields">
        <input
          v-if="hasPosition"
          v-model.number="newPos"
          type="number"
          inputmode="numeric"
          class="pos-input"
          :placeholder="t('settings.pos_placeholder')"
          @keydown.enter="add"
        />
        <input
          v-model="newName"
          type="text"
          class="name-input"
          :placeholder="t('settings.name_placeholder')"
          @keydown.enter="add"
          @keydown.escape="newName = ''"
          @focus="addFocused = true"
          @blur="addFocused = false"
        />
      </div>
      <button class="btn-add" :disabled="!newName.trim() || adding" @click="add">
        <span v-if="adding">…</span><span v-else>+</span>
      </button>
    </div>
    <p v-if="addError" class="inline-error">{{ addError }}</p>

    <!-- Загрузка -->
    <div v-if="loading" class="loading-dots">···</div>

    <template v-else>
      <!-- Активные -->
      <div v-if="activeItems.length" class="item-list">
        <div v-for="item in activeItems" :key="item.id" class="item-row">

          <!-- Позиция — редактируется прямо в строке -->
          <input
            v-if="hasPosition"
            :value="item.position"
            type="number"
            inputmode="numeric"
            class="pos-cell"
            @change="patchPosition(item, $event.target.value)"
            @click.stop
            :title="t('settings.pos_label')"
          />

          <!-- Название — клик для редактирования -->
          <div class="name-cell" @click="startEdit(item)">
            <span v-if="editingId !== item.id" class="item-name">{{ item.name }}</span>
            <input
              v-else
              :ref="el => editRefs[item.id] = el"
              v-model="editName"
              class="name-edit"
              @blur="saveEdit(item)"
              @keydown.enter="saveEdit(item)"
              @keydown.escape="cancelEdit"
              @click.stop
            />
          </div>

          <button class="deact-btn" @click="toggleActive(item)">
            {{ t('settings.deactivate') }}
          </button>
        </div>
      </div>
      <div v-else class="empty-hint">{{ t('settings.catalog_empty') }}</div>

      <!-- Архив -->
      <div v-if="inactiveItems.length" class="archive-section">
        <button class="archive-toggle" @click="showArchive = !showArchive">
          {{ showArchive ? '▾' : '▸' }} {{ t('settings.archived') }} ({{ inactiveItems.length }})
        </button>
        <transition name="fade">
          <div v-if="showArchive" class="item-list archive-list">
            <div v-for="item in inactiveItems" :key="item.id" class="item-row item-row-off">
              <span v-if="hasPosition" class="pos-cell-off">{{ item.position }}</span>
              <span class="item-name item-name-off">{{ item.name }}</span>
              <div class="archive-actions">
                <button class="act-btn" @click="toggleActive(item)">{{ t('settings.activate') }}</button>
                <button class="del-btn" @click="confirmDelete(item)">🗑</button>
              </div>
            </div>
          </div>
        </transition>

    <!-- Модальное подтверждение удаления -->
    <transition name="fade">
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal">
          <p class="modal-text">{{ t('settings.confirm_delete', { name: deleteTarget.name }) }}</p>
          <p class="modal-warn">{{ t('settings.delete_warn') }}</p>
          <div class="modal-actions">
            <button class="modal-cancel" @click="deleteTarget = null">{{ t('settings.cancel') }}</button>
            <button class="modal-confirm" :disabled="deleting" @click="doDelete">
              {{ deleting ? '…' : t('settings.delete') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
      </div>
    </template>

    <p v-if="listError" class="inline-error">{{ listError }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'

const props = defineProps({
  listUrl: { type: String, required: true },
  createUrl: { type: String, required: true },
  patchUrl: { type: String, required: true },
  hasPosition: { type: Boolean, default: false },
})

const { t } = useI18n()

const items = ref([])
const loading = ref(false)
const listError = ref('')
const addError = ref('')
const newName = ref('')
const newPos = ref('')
const adding = ref(false)
const addFocused = ref(false)
const showArchive = ref(false)
const editingId = ref(null)
const editName = ref('')
const editRefs = ref({})
const deleteTarget = ref(null)
const deleting = ref(false)

const activeItems = computed(() => items.value.filter(i => i.is_active))
const inactiveItems = computed(() => items.value.filter(i => !i.is_active))

async function load() {
  loading.value = true
  listError.value = ''
  try {
    items.value = await api.get(`${props.listUrl}?include_inactive=true`)
  } catch (err) {
    listError.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    loading.value = false
  }
}

async function add() {
  const name = newName.value.trim()
  if (!name || adding.value) return
  adding.value = true
  addError.value = ''
  try {
    const body = { name }
    if (props.hasPosition && newPos.value !== '') body.position = Number(newPos.value)
    const created = await api.post(props.createUrl, body)
    items.value.push(created)
    items.value.sort((a, b) => (a.position ?? 999) - (b.position ?? 999) || a.name.localeCompare(b.name))
    newName.value = ''
    newPos.value = ''
  } catch (err) {
    addError.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    adding.value = false
  }
}

function startEdit(item) {
  editingId.value = item.id
  editName.value = item.name
  setTimeout(() => editRefs.value[item.id]?.focus(), 30)
}

function cancelEdit() {
  editingId.value = null
  editName.value = ''
}

async function saveEdit(item) {
  const name = editName.value.trim()
  if (!name || name === item.name) { cancelEdit(); return }
  const prev = item.name
  item.name = name
  cancelEdit()
  try {
    const updated = await api.patch(`${props.patchUrl}/${item.id}`, { name })
    const idx = items.value.findIndex(x => x.id === item.id)
    if (idx !== -1) items.value[idx] = updated
  } catch (err) {
    item.name = prev
    listError.value = t(`errors.${err.code ?? 'unknown'}`)
  }
}

async function patchPosition(item, rawVal) {
  const pos = parseInt(rawVal)
  if (isNaN(pos) || pos === item.position) return
  const prev = item.position
  item.position = pos
  try {
    const updated = await api.patch(`${props.patchUrl}/${item.id}`, { position: pos })
    const idx = items.value.findIndex(x => x.id === item.id)
    if (idx !== -1) items.value[idx] = updated
    items.value.sort((a, b) => (a.position ?? 999) - (b.position ?? 999))
  } catch (err) {
    item.position = prev
    listError.value = t(`errors.${err.code ?? 'unknown'}`)
  }
}

async function toggleActive(item) {
  listError.value = ''
  try {
    const updated = await api.patch(`${props.patchUrl}/${item.id}`, { is_active: !item.is_active })
    const idx = items.value.findIndex(x => x.id === item.id)
    if (idx !== -1) items.value[idx] = updated
  } catch (err) {
    listError.value = t(`errors.${err.code ?? 'unknown'}`)
  }
}

function confirmDelete(item) {
  deleteTarget.value = item
}

async function doDelete() {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  listError.value = ''
  const target = deleteTarget.value
  try {
    await api.delete(`${props.patchUrl}/${target.id}`)
    items.value = items.value.filter(x => x.id !== target.id)
    deleteTarget.value = null
  } catch (err) {
    listError.value = err.status === 409
      ? t('settings.delete_in_use')
      : t(`errors.${err.code ?? 'unknown'}`)
    deleteTarget.value = null
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.catalog-panel { padding-bottom: 0.5rem; }

/* Add card */
.add-card {
  display: flex; align-items: stretch; gap: 0;
  border: 1.5px solid var(--c-surface);
  border-radius: 10px; overflow: hidden; margin-bottom: 0.25rem;
  transition: border-color 0.15s;
}
.add-card:focus-within { border-color: var(--c-accent); }
.add-fields { display: flex; flex: 1; gap: 0; }
.pos-input {
  width: 3.5rem; border: none; border-right: 1.5px solid var(--c-surface);
  background: transparent; padding: 0.6rem 0.4rem; text-align: center;
  font-size: 0.9rem; color: var(--c-text); outline: none;
}
.name-input {
  flex: 1; border: none; background: transparent; outline: none;
  padding: 0.6rem 0.75rem; font-size: 0.9rem;
  color: var(--c-text);
}
.name-input::placeholder { color: var(--c-hint); }
.btn-add {
  background: var(--c-accent);
  color: var(--c-accent-text);
  border: none; padding: 0 1rem; font-size: 1.3rem; font-weight: 700; cursor: pointer;
}
.btn-add:disabled { opacity: 0.4; cursor: not-allowed; }

.inline-error { font-size: 0.78rem; color: var(--c-negative); margin: 0.2rem 0 0.5rem; }
.loading-dots { color: var(--c-hint); font-size: 1.25rem; letter-spacing: 0.2em; padding: 1rem 0; }

/* Item list */
.item-list { display: flex; flex-direction: column; gap: 0.375rem; margin-top: 0.5rem; }
.item-row {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--c-surface);
  border-radius: 10px; padding: 0.5rem 0.625rem;
}

/* Position cell — editable number */
.pos-cell {
  width: 2.75rem; text-align: center; border: 1.5px solid transparent;
  border-radius: 6px; background: var(--c-bg);
  padding: 0.2rem 0.25rem; font-size: 0.85rem; font-weight: 600;
  color: var(--c-accent); outline: none;
  transition: border-color 0.15s; flex-shrink: 0;
}
.pos-cell:focus { border-color: var(--c-accent); }
.pos-cell-off {
  width: 2.75rem; text-align: center; font-size: 0.85rem; font-weight: 600;
  color: var(--c-hint); flex-shrink: 0;
}

/* Name cell */
.name-cell { flex: 1; cursor: text; min-width: 0; }
.item-name { font-size: 0.9rem; color: var(--c-text); display: block; }
.item-name-off { color: var(--c-hint); text-decoration: line-through; }
.name-edit {
  width: 100%; background: var(--c-bg);
  border: 1.5px solid var(--c-accent);
  border-radius: 6px; padding: 0.2rem 0.4rem;
  font-size: 0.9rem; color: var(--c-text);
  box-sizing: border-box; outline: none;
}

.deact-btn {
  flex-shrink: 0; border: none; border-radius: 7px;
  padding: 0.25rem 0.55rem; font-size: 0.75rem; font-weight: 600;
  background: var(--c-negative-bg); color: var(--c-negative-dark); cursor: pointer; white-space: nowrap;
}
.act-btn {
  flex-shrink: 0; border: none; border-radius: 7px;
  padding: 0.25rem 0.55rem; font-size: 0.75rem; font-weight: 600;
  background: var(--c-due-ok-bg); color: var(--c-positive); cursor: pointer; white-space: nowrap;
}

/* Archive */
.archive-section { margin-top: 0.75rem; }
.archive-toggle {
  background: none; border: none; font-size: 0.8rem;
  color: var(--c-hint); cursor: pointer; padding: 0.25rem 0;
}
.archive-list { opacity: 0.6; }
.item-row-off { opacity: 0.7; }
.archive-actions { display: flex; gap: 0.375rem; align-items: center; flex-shrink: 0; }
.del-btn {
  border: none; border-radius: 7px; padding: 0.25rem 0.45rem;
  font-size: 0.85rem; background: var(--c-negative-bg); cursor: pointer;
  line-height: 1;
}

/* Confirm modal */
.modal-overlay {
  position: fixed; inset: 0; background: var(--c-overlay);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; padding: 1.5rem;
}
.modal {
  background: var(--c-bg);
  border-radius: 16px; padding: 1.5rem 1.25rem;
  width: 100%; max-width: 320px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-text { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem; color: var(--c-text); text-align: center; }
.modal-warn { font-size: 0.82rem; color: var(--c-negative); margin: 0 0 1.25rem; text-align: center; line-height: 1.4; }
.modal-actions { display: flex; gap: 0.625rem; }
.modal-cancel {
  flex: 1; padding: 0.7rem; border: none; border-radius: 10px;
  background: var(--c-surface);
  color: var(--c-text); font-size: 0.95rem; font-weight: 600; cursor: pointer;
}
.modal-confirm {
  flex: 1; padding: 0.7rem; border: none; border-radius: 10px;
  background: var(--c-negative); color: #fff; font-size: 0.95rem; font-weight: 600; cursor: pointer;
}
.modal-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

.empty-hint { font-size: 0.85rem; color: var(--c-hint); padding: 0.75rem 0; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
