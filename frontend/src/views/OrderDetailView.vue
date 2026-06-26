<template>
  <div class="detail-view">
    <div v-if="loading" class="loading-state">
      <span class="loading-dots">···</span>
    </div>
    <div v-else-if="!order" class="hint">{{ t('errors.server_error') }}</div>

    <template v-else>
      <!-- ===== ШАПКА ===== -->
      <div class="order-hero">
        <div class="hero-top">
          <div class="hero-badges">
            <span class="badge-num">#{{ order.internal_number }}</span>
            <button class="badge-code-btn" @click.stop="shareCode" :title="t('orders.share_code')">
              {{ order.public_code }} 📤
            </button>
          </div>
          <!-- Дедлайн — правый верхний угол -->
          <div v-if="order.deadline" class="deadline-top">
            <span class="days-badge" :class="daysClass(order.deadline)">{{ daysLabel(order.deadline) }}</span>
            <span class="deadline-date">{{ formatDate(order.deadline) }}</span>
          </div>
        </div>

        <h1 class="hero-title">{{ order.title }}</h1>

        <!-- Закрыт — баннер -->
        <div v-if="order.is_closed" class="closed-banner">
          🔒 {{ t('orders.closed') }}
          <span v-if="order.closed_at" class="closed-date">{{ formatDateTime(order.closed_at) }}</span>
        </div>

        <!-- Этап — кликабельный если можно менять -->
        <div v-else class="stage-section">
          <div
            class="stage-pill"
            :class="[order.current_stage_name ? 'stage-active' : 'stage-none', order.can_change_status_for_me ? 'stage-clickable' : '']"
            @click="order.can_change_status_for_me && (showStageModal = true)"
          >
            {{ order.current_stage_name || t('orders.no_stage') }}
            <span v-if="order.can_change_status_for_me" class="stage-tap-hint">↕</span>
          </div>
        </div>

        <!-- Финансовая сводка (только менеджеру, только если есть сумма) -->
        <div v-if="isManager && order.total_amount" class="hero-finance">
          <div class="hf-item">
            <div class="hf-label">{{ t('orders.total_amount_short') }}</div>
            <div class="hf-value">{{ fmtAmount(order.total_amount) }}</div>
          </div>
          <div class="hf-divider" />
          <div class="hf-item">
            <div class="hf-label">{{ t('orders.paid_short') }}</div>
            <div class="hf-value hf-paid">{{ fmtAmount(order.total_paid) }}</div>
          </div>
          <div class="hf-divider" />
          <div class="hf-item">
            <div class="hf-label">{{ t('orders.balance_short') }}</div>
            <div class="hf-value" :class="Number(order.balance) > 0 ? 'hf-debt' : 'hf-ok'">
              {{ fmtAmount(order.balance) }}
            </div>
          </div>
        </div>
      </div>

      <!-- ===== ТАБЫ ===== -->
      <div class="tabs">
        <button
          v-for="tab in visibleTabs" :key="tab"
          :class="['tab', { active: activeTab === tab }]"
          @click="switchTab(tab)"
        >
          {{ tabLabel(tab) }}
        </button>
      </div>

      <!-- ===== INFO ===== -->
      <div v-if="activeTab === 'info'" class="tab-content">

        <!-- Шапка таба с карандашом -->
        <div v-if="isManager && !order.is_closed" class="info-tab-header">
          <span v-if="!editMode" class="info-tab-hint">{{ t('orders.tap_to_edit') }}</span>
          <div v-if="editMode" class="edit-actions">
            <button class="btn-cancel-edit" @click="cancelEdit" :disabled="saving">{{ t('orders.cancel') }}</button>
            <button class="btn-save-edit" @click="saveEdit" :disabled="saving">
              {{ saving ? '…' : t('orders.save') }}
            </button>
          </div>
          <button class="pencil-btn" :class="{ active: editMode }" @click="toggleEdit">✏️</button>
        </div>

        <!-- Клиент -->
        <div class="info-card">
          <div class="info-card-label">{{ t('orders.customer') }}</div>
          <input v-if="editMode" v-model="editForm.customer_name" class="info-input" />
          <div v-else class="info-card-value">{{ order.customer_name }}</div>
        </div>

        <!-- Название -->
        <div class="info-card">
          <div class="info-card-label">{{ t('orders.order_title') }}</div>
          <input v-if="editMode" v-model="editForm.title" class="info-input" />
          <div v-else class="info-card-value">{{ order.title }}</div>
        </div>

        <!-- Этап -->
        <div class="info-card" v-if="isManager">
          <div class="info-card-label">{{ t('orders.stage') }}</div>
          <select v-if="editMode" v-model="editForm.current_stage_id" class="info-input">
            <option :value="null">{{ t('orders.no_stage') }}</option>
            <option v-for="s in stages.filter(s => s.is_active)" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <div v-else class="info-card-value">{{ order.current_stage_name || t('orders.no_stage') }}</div>
        </div>

        <!-- Контакт -->
        <div class="info-card" v-if="editMode ? isManager : order.customer_contact">
          <div class="info-card-label">{{ t('orders.contact') }}</div>
          <input v-if="editMode && isManager" v-model="editForm.customer_contact" class="info-input" :placeholder="t('orders.contact_placeholder')" />
          <a v-else :href="`tel:${order.customer_contact}`" class="info-card-value link">{{ order.customer_contact }}</a>
        </div>

        <!-- Срок -->
        <div class="info-card" v-if="editMode || order.deadline">
          <div class="info-card-label">{{ t('orders.deadline') }}</div>
          <input v-if="editMode" v-model="editForm.deadline" type="date" class="info-input" />
          <div v-else class="info-card-value">{{ formatDate(order.deadline) }}</div>
        </div>

        <!-- Сумма -->
        <div class="info-card" v-if="isManager && (editMode || order.total_amount)">
          <div class="info-card-label">{{ t('orders.amount') }}</div>
          <div v-if="editMode" class="info-input-suffix">
            <input v-model="editForm.total_amount" type="number" min="0" step="1000" class="info-input" />
            <span class="input-suffix">сум</span>
          </div>
          <div v-else class="info-card-value">{{ fmtAmount(order.total_amount) }}</div>
        </div>

        <!-- Описание -->
        <div class="info-card" v-if="editMode || order.description">
          <div class="info-card-label">{{ t('orders.description') }}</div>
          <textarea v-if="editMode" v-model="editForm.description" rows="3" class="info-input info-textarea" :placeholder="t('orders.description_placeholder')" />
          <div v-else class="info-card-value multiline">{{ order.description }}</div>
        </div>

        <!-- Примечание клиенту -->
        <div class="info-card info-card-note" v-if="editMode || order.public_note">
          <div class="info-card-label">💬 {{ t('orders.public_note') }}</div>
          <textarea v-if="editMode" v-model="editForm.public_note" rows="2" class="info-input info-textarea" :placeholder="t('orders.public_note_placeholder')" />
          <div v-else class="info-card-value multiline">{{ order.public_note }}</div>
        </div>

        <!-- Геолокация доставки -->
        <div class="info-card" v-if="isManager && editMode">
          <div class="info-card-label">📍 {{ t('orders.location') }}</div>
          <LocationPicker
            v-if="editForm.delivery_lat != null"
            :lat="editForm.delivery_lat"
            :lon="editForm.delivery_lon"
            @update:lat="editForm.delivery_lat = $event"
            @update:lon="editForm.delivery_lon = $event"
          />
          <button v-if="editForm.delivery_lat != null" class="btn-map-clear" @click="editForm.delivery_lat = null; editForm.delivery_lon = null">
            ✕ {{ t('orders.remove_location') }}
          </button>
          <button v-else class="btn-map" @click="editForm.delivery_lat = 41.2995; editForm.delivery_lon = 69.2401">
            📍 {{ t('orders.add_location') }}
          </button>
        </div>
        <div class="info-card" v-else-if="order.delivery_lat != null">
          <div class="info-card-label">📍 {{ t('orders.location') }}</div>
          <div class="location-actions">
            <button class="btn-as-link" @click="showMapSheet = true">{{ t('orders.open_map') }}</button>
            <button class="btn-send-location" :disabled="sendingLocation" @click="shareLocation">
              {{ sendingLocation ? '…' : t('orders.send_to_bot') }}
            </button>
          </div>
        </div>

        <div v-if="saveError" class="save-error">{{ saveError }}</div>

        <!-- Закрыть заказ -->
        <button
          v-if="isManager && !order.is_closed && !editMode"
          class="btn-close-order"
          :disabled="closing"
          @click="closeOrder"
        >
          {{ closing ? '…' : t('orders.close_order') }}
        </button>
      </div>

      <!-- ===== HISTORY ===== -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div v-if="historyLoading" class="hint-sm">…</div>
        <div v-else-if="history.length === 0" class="tl-empty">
          <div class="tl-empty-icon">📋</div>
          <div class="tl-empty-text">{{ t('orders.no_history') }}</div>
        </div>
        <div v-else class="timeline">
          <div v-for="(h, idx) in history" :key="h.id" class="timeline-item">
            <div class="tl-left">
              <div class="tl-dot" :class="idx === 0 ? 'tl-dot-active' : ''" />
              <div class="tl-connector" v-if="idx < history.length - 1" />
            </div>
            <div class="tl-card" :class="{ 'tl-card-latest': idx === 0 }">
              <div class="tl-top">
                <span class="tl-stage">{{ stageName(h.stage_id) }}</span>
                <span class="tl-time">{{ relativeDate(h.changed_at) }}</span>
              </div>
              <div v-if="employeeName(h.changed_by)" class="tl-who">
                {{ employeeName(h.changed_by) }}
              </div>
              <div v-if="h.comment" class="tl-comment">{{ h.comment }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== FILES ===== -->
      <div v-if="activeTab === 'files'" class="tab-content">

        <!-- Кнопка загрузки вверху -->
        <div v-if="isManager" class="upload-area">
          <label class="upload-drop" :class="{ uploading: !!uploadStatus }">
            <input type="file" ref="fileInput" class="file-input"
              accept="image/*,.pdf,.dwg,.dxf"
              multiple
              @change="handleFileChange"
              :disabled="!!uploadStatus"
            />
            <span v-if="uploadStatus" class="upload-progress">
              <span class="upload-progress-bar" :style="{ width: uploadPct + '%' }" />
              <span class="upload-progress-text">{{ uploadStatus }}</span>
            </span>
            <span v-else class="upload-drop-label">
              <span class="upload-icon">📎</span>
              {{ t('orders.upload_file') }}
            </span>
          </label>
          <p v-if="fileError" class="upload-error">{{ fileError }}</p>
        </div>

        <div v-if="filesLoading" class="files-loading">
          <span class="loading-dots">···</span>
        </div>

        <template v-else-if="files.length">
          <!-- Галерея изображений -->
          <div v-if="imageFiles.length" class="images-section">
            <div class="files-section-label">{{ t('orders.files_images') }} ({{ imageFiles.length }})</div>
            <div class="image-gallery">
              <div
                v-for="f in imageFiles" :key="f.id"
                class="gallery-item"
                @click="openFile(f)"
              >
                <img v-if="thumbUrls[f.id]" :src="thumbUrls[f.id]" class="gallery-thumb" alt="" />
                <div v-else class="gallery-placeholder">🖼️</div>
                <div v-if="fileLoading[f.id]" class="gallery-loading">⏳</div>
                <button
                  v-if="isManager"
                  class="gallery-del"
                  @click.stop="deleteFile(f)"
                >✕</button>
              </div>
            </div>
          </div>

          <!-- Список документов -->
          <div v-if="docFiles.length" class="docs-section">
            <div class="files-section-label">{{ t('orders.files_docs') }} ({{ docFiles.length }})</div>
            <div class="doc-list">
              <div v-for="f in docFiles" :key="f.id" class="doc-row">
                <div class="doc-icon">{{ fileIcon(f) }}</div>
                <div class="doc-info" @click="openFile(f)">
                  <div class="doc-name">{{ f.original_filename }}</div>
                  <div class="doc-size">{{ fmtSize(f.size_bytes) }}</div>
                </div>
                <div class="doc-actions">
                  <button
                    class="doc-btn doc-btn-open"
                    :disabled="fileLoading[f.id]"
                    @click="openFile(f)"
                  >
                    {{ fileLoading[f.id] ? '…' : '⬇' }}
                  </button>
                  <button
                    v-if="isManager"
                    class="doc-btn doc-btn-del"
                    @click="deleteFile(f)"
                  >✕</button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div v-else-if="!filesLoading" class="files-empty">
          <div class="files-empty-icon">📂</div>
          <div class="files-empty-text">{{ t('orders.no_files') }}</div>
        </div>
      </div>

      <!-- ===== IMAGE PREVIEW MODAL ===== -->
      <transition name="fade">
        <div v-if="previewUrl" class="img-preview-overlay" @click="closePreview">
          <img :src="previewUrl" class="img-preview" alt="" @click.stop />
          <button class="img-preview-close" @click="closePreview">✕</button>
        </div>
      </transition>

      <!-- ===== TEAM ===== -->
      <div v-if="activeTab === 'team'" class="tab-content">
        <div v-if="teamLoading" class="hint-sm">…</div>

        <template v-else>
          <!-- Section header with add toggle (always visible) -->
          <div class="team-header" @click="showAttachForm = !showAttachForm">
            <span class="team-header-title">{{ t('orders.attach') }}</span>
            <button class="team-add-btn" :class="{ open: showAttachForm }">+</button>
          </div>

          <!-- Add form -->
          <transition name="slide">
            <div v-if="showAttachForm" class="attach-form">
              <p v-if="!availableEmployees.length" class="hint-sm">Все сотрудники уже в команде</p>
              <select v-else v-model="attachEmpId" class="input-select">
                <option value="">{{ t('orders.select_employee') }}</option>
                <option v-for="e in availableEmployees" :key="e.id" :value="e.id">{{ e.full_name }}</option>
              </select>
              <label class="attach-check">
                <span class="attach-check-label">{{ t('orders.can_change_status') }}</span>
                <div class="toggle-switch" :class="{ on: attachCanChange }" @click="attachCanChange = !attachCanChange">
                  <div class="toggle-thumb" />
                </div>
              </label>
              <button v-if="availableEmployees.length" class="btn-attach" :disabled="!attachEmpId" @click="attachEmployee">
                {{ t('orders.attach') }}
              </button>
            </div>
          </transition>

          <!-- Empty state -->
          <div v-if="!attachments.length" class="team-empty">
            <div class="team-empty-icon">👥</div>
            <div class="team-empty-text">{{ t('orders.no_team') }}</div>
          </div>

          <!-- Team list -->
          <div v-else class="team-list">
            <div v-for="a in attachments" :key="a.id" class="team-card">
              <div class="team-avatar">{{ initials(employeeName(a.employee_id)) }}</div>
              <div class="team-info">
                <div class="team-name">{{ employeeName(a.employee_id) }}</div>
                <div class="team-perm" :class="a.can_change_status ? 'perm-yes' : 'perm-no'">
                  {{ a.can_change_status ? t('orders.can_change_status') : t('orders.no_change_status') }}
                </div>
              </div>
              <div class="team-controls">
                <div class="toggle-switch sm" :class="{ on: a.can_change_status }" @click="toggleFlag(a)" :title="t('orders.can_change_status')">
                  <div class="toggle-thumb" />
                </div>
                <button class="team-del-btn" @click="detachEmployee(a)">✕</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- ===== FINANCE ===== -->
      <div v-if="activeTab === 'finance'" class="tab-content">
        <OrderFinanceTab :order-id="orderId" />
      </div>
    </template>

    <StageChangeModal
      v-if="showStageModal"
      :order-id="orderId"
      :current-stage-id="order?.current_stage_id"
      @close="showStageModal = false"
      @saved="onStageSaved"
    />

    <!-- Map app chooser -->
    <Transition name="sheet-fade">
      <div v-if="showMapSheet" class="map-sheet-overlay" @click.self="showMapSheet = false">
        <div class="map-sheet">
          <div class="map-sheet-handle" />
          <div class="map-sheet-title">{{ t('orders.open_in') }}</div>
          <a
            v-for="app in mapApps"
            :key="app.id"
            :href="app.url"
            target="_blank"
            rel="noopener noreferrer"
            class="map-app-row"
            @click="showMapSheet = false"
          >
            <span class="map-app-icon">{{ app.icon }}</span>
            <span class="map-app-name">{{ app.name }}</span>
            <span class="map-app-chevron">›</span>
          </a>
          <button class="map-sheet-cancel" @click="showMapSheet = false">
            {{ t('orders.cancel') }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showConfirm, showAlert } from '../telegram.js'
import StageChangeModal from './StageChangeModal.vue'
import OrderFinanceTab from './OrderFinanceTab.vue'
import LocationPicker from '../components/LocationPicker.vue'

const BOT_USERNAME = import.meta.env.VITE_BOT_USERNAME ?? ''

const props = defineProps({
  orderId: { type: Number, required: true },
  isManager: { type: Boolean, required: true },
})
defineEmits(['edit', 'back'])
const { t, locale } = useI18n()

const order = ref(null)
const loading = ref(false)
const showMapSheet = ref(false)
const sendingLocation = ref(false)
const mapApps = computed(() => {
  const lat = order.value?.delivery_lat
  const lon = order.value?.delivery_lon
  if (lat == null) return []
  return [
    {
      id: 'gmaps',
      icon: '🗺️',
      name: 'Google Maps',
      url: `https://maps.google.com/?q=${lat},${lon}`,
    },
    {
      id: 'ymaps',
      icon: '🗺️',
      name: 'Яндекс Карты',
      url: `https://yandex.com/maps/?pt=${lon},${lat}&z=16`,
    },
  ]
})
const stages = ref([])
const history = ref([])
const historyLoading = ref(false)
const files = ref([])
const filesLoading = ref(false)
const thumbUrls = ref({})
const attachments = ref([])
const allEmployees = ref([])
const teamLoading = ref(false)
const activeTab = ref('info')
const showStageModal = ref(false)
const closing = ref(false)
const uploadStatus = ref('')
const uploadPct = ref(0)
const fileLoading = ref({})
const previewUrl = ref(null)

const imageFiles = computed(() => files.value.filter(f => isImage(f)))
const docFiles = computed(() => files.value.filter(f => !isImage(f)))
const editMode = ref(false)
const saving = ref(false)
const saveError = ref('')
const editForm = ref({})
const fileError = ref('')
const fileInput = ref(null)
const attachEmpId = ref('')
const attachCanChange = ref(false)
const showAttachForm = ref(false)

const visibleTabs = computed(() => {
  const tabs = ['info', 'files']
  if (props.isManager) tabs.push('finance', 'team')
  tabs.push('history')
  return tabs
})

const availableEmployees = computed(() => {
  const attached = new Set(attachments.value.map(a => a.employee_id))
  return allEmployees.value.filter(e => !attached.has(e.id))
})

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

function tabLabel(tab) {
  if (tab === 'finance') return t('finance.title')
  return t(`orders.tab_${tab}`)
}

function stageName(stageId) {
  return stages.value.find(s => s.id === stageId)?.name ?? `#${stageId}`
}

function employeeName(empId) {
  return allEmployees.value.find(e => e.id === empId)?.full_name ?? ''
}

function initials(name) {
  if (!name) return '?'
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function fmtAmount(val) {
  if (val === null || val === undefined) return '—'
  return Number(val).toLocaleString('ru-RU') + ' сум'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function relativeDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / 86400000)
  const timeStr = d.toLocaleTimeString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 0) return `сегодня, ${timeStr}`
  if (diffDays === 1) return `вчера, ${timeStr}`
  if (diffDays < 7) return `${diffDays} дн. назад`
  return d.toLocaleDateString(locale.value === 'uz' ? 'uz-UZ' : 'ru-RU', { day: 'numeric', month: 'short' })
}

function fileIcon(f) {
  const ext = f.original_filename?.split('.').pop()?.toLowerCase()
  if (['jpg','jpeg','png','webp','gif'].includes(ext)) return '🖼️'
  if (ext === 'pdf') return '📄'
  if (['dwg','dxf'].includes(ext)) return '📐'
  return '📎'
}

async function loadOrder() {
  loading.value = true
  try {
    const stagesUrl = props.isManager ? '/api/stages?include_inactive=true' : '/api/stages'
    const [ord, stgs] = await Promise.all([
      api.get(`/api/orders/${props.orderId}`),
      api.get(stagesUrl),
    ])
    order.value = ord
    stages.value = stgs
    if (props.isManager) {
      api.get('/api/employees').then(e => { allEmployees.value = e }).catch(() => {})
    }
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    history.value = await api.get(`/api/orders/${props.orderId}/history`)
  } catch { /* silent */ } finally {
    historyLoading.value = false
  }
}

async function loadFiles() {
  filesLoading.value = true
  try {
    files.value = await api.get(`/api/orders/${props.orderId}/files`)
    for (const f of files.value) {
      if (f.thumbnail_key) {
        api.fetchBlobUrl(`/api/orders/${props.orderId}/files/${f.id}/thumbnail`)
          .then(url => { if (url) thumbUrls.value[f.id] = url })
          .catch(() => {})
      }
    }
  } catch { /* silent */ } finally {
    filesLoading.value = false
  }
}

async function loadTeam() {
  if (!props.isManager) return
  teamLoading.value = true
  try {
    const [att, emps] = await Promise.all([
      api.get(`/api/orders/${props.orderId}/employees`),
      api.get('/api/employees'),
    ])
    attachments.value = att
    allEmployees.value = emps
  } catch { /* silent */ } finally {
    teamLoading.value = false
  }
}

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'history' && history.value.length === 0) loadHistory()
  if (tab === 'files' && files.value.length === 0) loadFiles()
  if (tab === 'team' && attachments.value.length === 0) loadTeam()
}

async function handleFileChange(e) {
  const fileList = [...(e.target.files ?? [])]
  if (!fileList.length) return
  fileError.value = ''

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]
    const prefix = fileList.length > 1 ? `${i + 1}/${fileList.length} · ` : ''
    uploadPct.value = 0
    uploadStatus.value = prefix + t('orders.uploading', { pct: 0 })
    try {
      const record = await api.uploadFile(
        `/api/orders/${props.orderId}/files`, file, {},
        pct => {
          uploadPct.value = pct
          uploadStatus.value = prefix + t('orders.uploading', { pct })
        },
      )
      files.value.push(record)
      if (record.thumbnail_key) {
        api.fetchBlobUrl(`/api/orders/${props.orderId}/files/${record.id}/thumbnail`)
          .then(url => { if (url) thumbUrls.value[record.id] = url }).catch(() => {})
      }
    } catch (err) {
      fileError.value = err.code === 'file_too_large' ? t('orders.file_too_large')
        : err.code === 'file_type' ? t('orders.file_type_error')
        : t('errors.server_error')
      uploadStatus.value = ''
      if (fileInput.value) fileInput.value.value = ''
      return
    }
  }

  uploadStatus.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function isImage(f) {
  const ext = f.original_filename?.split('.').pop()?.toLowerCase()
  return ['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)
}

function fmtSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} КБ`
  return `${(bytes / 1048576).toFixed(1)} МБ`
}

function closePreview() {
  if (previewUrl.value) { URL.revokeObjectURL(previewUrl.value); previewUrl.value = null }
}

async function openFile(f) {
  if (fileLoading.value[f.id]) return
  fileLoading.value = { ...fileLoading.value, [f.id]: true }
  try {
    if (isImage(f)) {
      const url = await api.fetchBlobUrl(`/api/orders/${props.orderId}/files/${f.id}/download`)
      if (!url) return
      closePreview()
      previewUrl.value = url
    } else {
      // Get a short-lived token so the download URL can be used without auth headers
      const { token, filename } = await api.post(`/api/orders/${props.orderId}/files/${f.id}/token`)
      const dlUrl = `${window.location.origin}/api/dl/${token}`
      const tg = window.Telegram?.WebApp
      // Open in the system browser — Telegram WebView itself can't handle downloads,
      // but the external browser will see Content-Disposition: attachment and save the file.
      if (tg?.openLink) {
        tg.openLink(dlUrl, { try_browser: 'system' })
      } else {
        // Fallback for browser/desktop testing
        const a = document.createElement('a')
        a.href = dlUrl
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      }
    }
  } finally {
    fileLoading.value = { ...fileLoading.value, [f.id]: false }
  }
}

async function deleteFile(f) {
  const ok = await showConfirm(t('orders.confirm_delete_file'))
  if (!ok) return
  try {
    await api.delete(`/api/orders/${props.orderId}/files/${f.id}`)
    files.value = files.value.filter(x => x.id !== f.id)
    if (thumbUrls.value[f.id]) { URL.revokeObjectURL(thumbUrls.value[f.id]); delete thumbUrls.value[f.id] }
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

async function attachEmployee() {
  if (!attachEmpId.value) return
  try {
    const row = await api.post(`/api/orders/${props.orderId}/employees`, {
      employee_id: Number(attachEmpId.value),
      can_change_status: attachCanChange.value,
    })
    attachments.value.push(row)
    attachEmpId.value = ''; attachCanChange.value = false; showAttachForm.value = false
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

async function detachEmployee(a) {
  const ok = await showConfirm(t('orders.confirm_detach'))
  if (!ok) return
  try {
    await api.delete(`/api/orders/${props.orderId}/employees/${a.employee_id}`)
    attachments.value = attachments.value.filter(x => x.id !== a.id)
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

async function toggleFlag(a) {
  try {
    const updated = await api.post(`/api/orders/${props.orderId}/employees`, {
      employee_id: a.employee_id,
      can_change_status: !a.can_change_status,
    })
    const idx = attachments.value.findIndex(x => x.id === a.id)
    if (idx !== -1) attachments.value[idx] = updated
  } catch (err) { await showAlert(t(`errors.${err.code ?? 'unknown'}`)) }
}

function onStageSaved(updated) {
  showStageModal.value = false
  order.value = updated
}

function toggleEdit() {
  if (editMode.value) { cancelEdit(); return }
  editForm.value = {
    customer_name: order.value.customer_name,
    title: order.value.title,
    current_stage_id: order.value.current_stage_id ?? null,
    customer_contact: order.value.customer_contact ?? '',
    deadline: order.value.deadline ?? '',
    total_amount: order.value.total_amount ?? '',
    description: order.value.description ?? '',
    public_note: order.value.public_note ?? '',
    delivery_lat: order.value.delivery_lat ?? null,
    delivery_lon: order.value.delivery_lon ?? null,
  }
  editMode.value = true
  saveError.value = ''
}

function cancelEdit() {
  editMode.value = false
  saveError.value = ''
}

async function saveEdit() {
  if (saving.value) return
  saving.value = true
  saveError.value = ''
  const f = editForm.value
  const body = {
    customer_name: f.customer_name?.trim(),
    title: f.title?.trim(),
    current_stage_id: f.current_stage_id || null,
    customer_contact: f.customer_contact?.trim() || null,
    deadline: f.deadline || null,
    total_amount: f.total_amount !== '' && f.total_amount !== null ? Number(f.total_amount) : null,
    description: f.description?.trim() || null,
    public_note: f.public_note?.trim() || null,
    delivery_lat: f.delivery_lat ?? null,
    delivery_lon: f.delivery_lon ?? null,
  }
  try {
    const updated = await api.patch(`/api/orders/${props.orderId}`, body)
    order.value = updated
    editMode.value = false
  } catch (err) {
    saveError.value = t(`errors.${err.code ?? 'unknown'}`)
  } finally {
    saving.value = false
  }
}

async function closeOrder() {
  const balance = order.value?.balance
  const hasDebt = balance !== null && balance !== undefined && Number(balance) > 0
  const msg = hasDebt
    ? t('orders.confirm_close_debt', { amount: fmtAmount(balance) })
    : t('orders.confirm_close')
  const ok = await showConfirm(msg)
  if (!ok) return
  closing.value = true
  try {
    const updated = await api.post(`/api/orders/${props.orderId}/close`, null)
    order.value = updated
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    closing.value = false
  }
}

async function shareLocation() {
  if (sendingLocation.value) return
  sendingLocation.value = true
  try {
    await api.post(`/api/orders/${props.orderId}/share-location`, null)
    await showAlert(t('orders.location_sent'))
  } catch (err) {
    await showAlert(t(`errors.${err.code ?? 'unknown'}`))
  } finally {
    sendingLocation.value = false
  }
}

async function shareCode() {
  const code = order.value?.public_code
  if (!code) return
  const botLink = BOT_USERNAME ? `https://t.me/${BOT_USERNAME}` : ''
  const msg = botLink
    ? t('orders.share_msg', { code, link: botLink })
    : t('orders.share_msg_no_link', { code })
  try {
    if (navigator.share) {
      await navigator.share({ text: msg })
    } else {
      await navigator.clipboard.writeText(msg)
      await showAlert(t('orders.code_copied'))
    }
  } catch { /* user cancelled */ }
}

onMounted(loadOrder)
</script>

<style scoped>
.detail-view { padding: 0 1rem 5rem; max-width: 600px; margin: 0 auto; }
.loading-state { display: flex; justify-content: center; padding: 3rem 0; }
.loading-dots { font-size: 1.5rem; letter-spacing: 0.2em; color: var(--c-hint); }
.hint { color: var(--c-hint); text-align: center; padding: 2rem 0; font-size: 0.9rem; }
.hint-sm { color: var(--c-hint); font-size: 0.9rem; padding: 0.5rem 0; }
.error-msg { color: var(--c-negative); font-size: 0.82rem; margin-top: 0.25rem; }

.btn-close-order {
  width: 100%; margin-top: 1.5rem; padding: 0.8rem;
  border: 1.5px solid #e74c3c; border-radius: 12px;
  background: transparent; color: var(--c-negative);
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.btn-close-order:hover { background: var(--c-negative); color: #fff; }
.btn-close-order:disabled { opacity: 0.5; cursor: not-allowed; }

/* ===== HERO ===== */
.order-hero {
  background: var(--c-surface);
  border-radius: 16px; padding: 1rem 1.1rem 1.1rem;
  margin: 0.75rem 0 0;
}
.hero-top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 0.5rem; gap: 0.5rem; }
.hero-badges { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }

/* Дедлайн — правый верхний угол */
.deadline-top { display: flex; flex-direction: column; align-items: flex-end; gap: 0.2rem; flex-shrink: 0; }
.deadline-date { font-size: 0.7rem; color: rgba(255,255,255,0.55); white-space: nowrap; }
.badge-num {
  background: var(--c-accent);
  color: var(--c-accent-text);
  font-size: 0.75rem; font-weight: 700; border-radius: 6px; padding: 0.15rem 0.5rem;
}
.badge-code-btn {
  font-size: 0.72rem; font-family: monospace;
  color: var(--c-accent);
  background: var(--c-bg);
  border: none; border-radius: 6px; padding: 0.15rem 0.5rem;
  cursor: pointer; display: flex; align-items: center; gap: 0.2rem;
}
.edit-icon-btn {
  background: none; border: none; font-size: 1rem; cursor: pointer; padding: 0.2rem;
  opacity: 0.7;
}
.hero-title {
  font-size: 1.2rem; font-weight: 700; margin: 0 0 0.2rem;
  color: var(--c-text); line-height: 1.3;
}
.hero-customer { font-size: 0.9rem; color: var(--c-hint); margin-bottom: 0.75rem; }

/* Finance summary in hero */
.hero-finance {
  display: flex; align-items: center; gap: 0;
  background: rgba(0,0,0,0.2); border-radius: 10px;
  margin-top: 0.75rem; overflow: hidden;
}
.hf-item { flex: 1; padding: 0.6rem 0.75rem; text-align: center; }
.hf-label { font-size: 0.68rem; color: rgba(255,255,255,0.55); font-weight: 500; margin-bottom: 0.2rem; text-transform: uppercase; letter-spacing: 0.04em; }
.hf-value { font-size: 0.9rem; font-weight: 700; color: #fff; }
.hf-paid { color: #a5d6a7; }
.hf-debt { color: #ef9a9a; }
.hf-ok   { color: #a5d6a7; }
.hf-divider { width: 1px; height: 2.5rem; background: rgba(255,255,255,0.15); flex-shrink: 0; }

.closed-banner {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  background: rgba(0,0,0,0.25); border-radius: 8px; padding: 0.4rem 0.75rem;
  font-size: 0.85rem; font-weight: 700; color: rgba(255,255,255,0.8);
  margin-bottom: 0.5rem;
}
.closed-date { font-weight: 400; font-size: 0.75rem; opacity: 0.7; }

.stage-section { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.stage-pill {
  border-radius: 8px; padding: 0.3rem 0.75rem; font-size: 0.85rem; font-weight: 600;
  display: flex; align-items: center; gap: 0.35rem;
}
.stage-active { background: #e3f2fd; color: #1565c0; }
.stage-none { background: var(--tg-theme-bg-color, #e8e8e8); color: var(--c-hint); }
.stage-clickable { cursor: pointer; }
.stage-clickable:active { opacity: 0.75; }
.stage-tap-hint { font-size: 0.75rem; opacity: 0.6; }

/* .deadline-row убран — дедлайн теперь в hero-top */
.days-badge { font-size: 0.72rem; font-weight: 700; border-radius: 5px; padding: 0.1rem 0.4rem; }
.days-overdue { background: rgba(255,80,80,0.2); color: #ff8a80; }
.days-urgent  { background: rgba(255,160,0,0.2); color: #ffcc02; }
.days-soon    { background: rgba(255,220,0,0.15); color: #ffe57f; }
.days-ok      { background: rgba(100,255,150,0.15); color: #a5d6a7; }

/* ===== TABS ===== */
.tabs {
  display: flex; overflow-x: auto; gap: 0;
  border-bottom: 1.5px solid var(--c-surface);
  margin: 1rem 0 0; scrollbar-width: none;
}
.tabs::-webkit-scrollbar { display: none; }
.tab {
  background: none; border: none;
  border-bottom: 2.5px solid transparent;
  padding: 0.6rem 0.875rem; font-size: 0.85rem; white-space: nowrap;
  cursor: pointer; color: var(--c-hint);
  transition: color 0.15s; flex-shrink: 0;
}
.tab.active {
  border-bottom-color: var(--c-accent);
  color: var(--c-accent); font-weight: 600;
}

.tab-content { padding-top: 1rem; }


/* ===== INFO TAB HEADER ===== */
.info-tab-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.75rem;
}
.info-tab-hint { font-size: 0.78rem; color: var(--c-hint); }
.edit-actions { display: flex; gap: 0.5rem; }
.pencil-btn {
  background: var(--c-surface);
  border: none; border-radius: 50%; width: 2rem; height: 2rem;
  font-size: 0.95rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.pencil-btn.active { background: var(--c-accent); }
.btn-cancel-edit {
  padding: 0.4rem 0.875rem; border: none; border-radius: 8px;
  background: var(--c-surface);
  color: var(--c-hint);
  font-size: 0.82rem; font-weight: 600; cursor: pointer;
}
.btn-save-edit {
  padding: 0.4rem 0.875rem; border: none; border-radius: 8px;
  background: var(--c-accent);
  color: var(--c-accent-text);
  font-size: 0.82rem; font-weight: 600; cursor: pointer;
}
.btn-save-edit:disabled, .btn-cancel-edit:disabled { opacity: 0.5; cursor: not-allowed; }

/* Inline edit inputs */
.info-input {
  width: 100%; background: var(--c-bg);
  border: 1.5px solid var(--c-accent);
  border-radius: 8px; padding: 0.45rem 0.625rem;
  font-size: 0.92rem; color: var(--c-text);
  box-sizing: border-box; outline: none; font-family: inherit;
}
.info-textarea { resize: vertical; }
.info-input-suffix { position: relative; }
.info-input-suffix .info-input { padding-right: 2.75rem; }
.input-suffix {
  position: absolute; right: 0.625rem; top: 50%; transform: translateY(-50%);
  font-size: 0.78rem; color: var(--c-hint); pointer-events: none;
}
.save-error { font-size: 0.8rem; color: var(--c-negative); text-align: center; margin: 0.25rem 0; }

/* ===== INFO CARDS ===== */
.info-card {
  background: var(--c-surface);
  border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
}
.info-card-note { border-left: 3px solid var(--c-accent); }
.info-card-label { font-size: 0.75rem; font-weight: 600; color: var(--c-hint); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.3rem; }
.info-card-value { font-size: 0.95rem; color: var(--c-text); }
.info-card-value.multiline { white-space: pre-wrap; line-height: 1.5; }
.info-card-value.link { color: var(--c-accent); text-decoration: none; display: block; }

/* ===== TIMELINE ===== */
.tl-empty { display: flex; flex-direction: column; align-items: center; padding: 2.5rem 1rem; gap: 0.5rem; }
.tl-empty-icon { font-size: 2.5rem; }
.tl-empty-text { font-size: 0.9rem; color: var(--c-hint); }

.timeline { display: flex; flex-direction: column; }
.timeline-item { display: flex; gap: 0.75rem; }

.tl-left { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 1rem; }
.tl-dot {
  width: 0.75rem; height: 0.75rem; border-radius: 50%; flex-shrink: 0;
  background: var(--c-hint);
  border: 2px solid var(--c-bg);
  box-shadow: 0 0 0 2px var(--c-hint);
  margin-top: 0.875rem;
}
.tl-dot-active {
  width: 0.875rem; height: 0.875rem;
  background: var(--c-accent);
  box-shadow: 0 0 0 2px var(--c-accent);
}
.tl-connector { flex: 1; width: 2px; background: var(--c-surface); margin: 0.25rem 0; min-height: 0.5rem; }

.tl-card {
  flex: 1; background: var(--c-surface);
  border-radius: 12px; padding: 0.625rem 0.875rem;
  margin-bottom: 0.5rem;
}
.tl-card-latest {
  background: var(--c-surface);
  border-left: 3px solid var(--c-accent);
}
.tl-top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
.tl-stage { font-weight: 600; font-size: 0.9rem; color: var(--c-text); }
.tl-time { font-size: 0.72rem; color: var(--c-hint); flex-shrink: 0; }
.tl-who { font-size: 0.75rem; color: var(--c-hint); margin-top: 0.2rem; }
.tl-comment {
  font-size: 0.82rem; color: var(--c-text);
  background: var(--c-bg);
  border-radius: 6px; padding: 0.35rem 0.6rem; margin-top: 0.4rem;
  border-left: 2px solid var(--c-hint);
  opacity: 0.85;
}

/* ===== FILES ===== */

/* Upload */
.upload-area { margin-bottom: 1rem; }
.upload-drop {
  display: flex; align-items: center; justify-content: center;
  border: 2px dashed var(--c-accent);
  border-radius: 14px; padding: 1rem 1.25rem;
  width: 100%; box-sizing: border-box;
  cursor: pointer; position: relative; overflow: hidden; min-height: 3.25rem;
  transition: background 0.15s;
}
.upload-drop:not(.uploading):active { background: rgba(36,129,204,0.08); }
.upload-drop.uploading { cursor: not-allowed; border-style: solid; }
.upload-drop-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; font-weight: 600; color: var(--c-accent); }
.upload-icon { font-size: 1.1rem; }
.upload-progress { width: 100%; display: flex; flex-direction: column; gap: 0.35rem; }
.upload-progress-bar {
  height: 4px; border-radius: 2px;
  background: var(--c-accent);
  transition: width 0.2s; min-width: 4px;
}
.upload-progress-text { font-size: 0.8rem; color: var(--c-hint); text-align: center; }
.upload-error { font-size: 0.78rem; color: var(--c-negative); margin: 0.25rem 0 0; }
.file-input { display: none; }

.files-loading { text-align: center; padding: 1.5rem 0; color: var(--c-hint); font-size: 1.5rem; letter-spacing: 0.2em; }
.files-section-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-hint); margin-bottom: 0.625rem; }

/* Image gallery */
.images-section { margin-bottom: 1.25rem; }
.image-gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.375rem; }
.gallery-item {
  position: relative; aspect-ratio: 1; border-radius: 10px; overflow: hidden;
  background: var(--c-surface);
  cursor: pointer;
}
.gallery-item:active { opacity: 0.8; }
.gallery-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.gallery-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 2rem; }
.gallery-loading {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.4); font-size: 1.5rem;
}
.gallery-del {
  position: absolute; top: 0.3rem; right: 0.3rem;
  background: rgba(0,0,0,0.55); border: none; border-radius: 50%;
  width: 1.5rem; height: 1.5rem; font-size: 0.65rem; color: #fff;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  line-height: 1;
}

/* Document list */
.docs-section { margin-bottom: 0.5rem; }
.doc-list { display: flex; flex-direction: column; gap: 0.375rem; }
.doc-row {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--c-surface);
  border-radius: 12px; padding: 0.75rem 0.875rem;
}
.doc-icon { font-size: 1.75rem; flex-shrink: 0; line-height: 1; }
.doc-info { flex: 1; min-width: 0; cursor: pointer; }
.doc-name { font-size: 0.875rem; font-weight: 500; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-size { font-size: 0.72rem; color: var(--c-hint); margin-top: 0.15rem; }
.doc-actions { display: flex; gap: 0.375rem; flex-shrink: 0; }
.doc-btn {
  border: none; border-radius: 8px; width: 2rem; height: 2rem;
  font-size: 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.doc-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.doc-btn-open { background: var(--tg-theme-bg-color, #e8e8e8); color: var(--c-text); }
.doc-btn-del { background: var(--c-negative-bg); color: var(--c-negative-dark); }

/* Empty */
.files-empty { text-align: center; padding: 2rem 0; }
.files-empty-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.files-empty-text { font-size: 0.9rem; color: var(--c-hint); }

/* ===== TEAM ===== */
/* ── Team tab ── */
.team-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.25rem 0 0.5rem; cursor: pointer; user-select: none;
}
.team-header-title {
  font-size: 0.8rem; font-weight: 600; color: var(--c-hint);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.team-add-btn {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--c-accent); color: var(--c-accent-text);
  border: none; cursor: pointer; font-size: 1.1rem; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s; flex-shrink: 0;
}
.team-add-btn.open { transform: rotate(45deg); }

.team-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 2.5rem 1rem; gap: 0.5rem;
}
.team-empty-icon { font-size: 2.5rem; }
.team-empty-text { font-size: 0.9rem; color: var(--c-hint); }

.team-list { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.25rem; }
.team-card {
  display: flex; align-items: center; gap: 0.875rem;
  background: var(--c-surface);
  border-radius: 14px; padding: 0.75rem 1rem;
}
.team-avatar {
  width: 2.75rem; height: 2.75rem; border-radius: 50%; flex-shrink: 0;
  background: var(--c-accent);
  color: var(--c-accent-text);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.875rem; font-weight: 700;
}
.team-info { flex: 1; min-width: 0; }
.team-name { font-size: 0.95rem; font-weight: 600; color: var(--c-text); }
.team-perm { font-size: 0.73rem; margin-top: 0.15rem; font-weight: 500; }
.perm-yes { color: var(--c-positive); }
.perm-no  { color: var(--c-hint); }

.team-controls { display: flex; align-items: center; gap: 0.625rem; flex-shrink: 0; }
.team-del-btn {
  background: none; border: none; color: var(--c-hint);
  font-size: 0.85rem; cursor: pointer; padding: 0.25rem; line-height: 1;
  opacity: 0.5; transition: opacity 0.15s;
}
.team-del-btn:hover { opacity: 1; color: var(--c-negative); }

/* Toggle switch */
.toggle-switch {
  width: 2.75rem; height: 1.5rem; border-radius: 99px;
  background: var(--c-surface); position: relative; cursor: pointer;
  transition: background 0.2s; flex-shrink: 0;
  border: 1.5px solid var(--c-hint);
  box-sizing: border-box;
}
.toggle-switch.on { background: var(--c-positive); border-color: var(--c-positive); }
.toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: calc(1.5rem - 8px); height: calc(1.5rem - 8px);
  border-radius: 50%; background: var(--c-hint);
  transition: transform 0.2s, background 0.2s;
}
.toggle-switch.on .toggle-thumb { transform: translateX(1.25rem); background: #fff; }
.toggle-switch.sm { width: 2.25rem; height: 1.25rem; }
.toggle-switch.sm .toggle-thumb { width: calc(1.25rem - 8px); height: calc(1.25rem - 8px); }
.toggle-switch.sm.on .toggle-thumb { transform: translateX(1rem); }

/* Attach form */
.attach-form {
  background: var(--c-surface);
  border-radius: 14px; padding: 0.875rem; display: flex; flex-direction: column; gap: 0.625rem;
  margin-bottom: 0.5rem;
}
.input-select {
  background: var(--c-bg); border: none;
  border-radius: 8px; padding: 0.55rem 0.75rem; font-size: 0.9rem;
  color: var(--c-text); width: 100%;
}
.attach-check {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.25rem 0;
}
.attach-check-label { font-size: 0.875rem; color: var(--c-text); }
.btn-attach {
  background: var(--c-accent);
  color: var(--c-accent-text);
  border: none; border-radius: 10px; padding: 0.65rem; font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.btn-attach:disabled { opacity: 0.5; cursor: not-allowed; }

/* Slide transition (shared) */
.slide-enter-active, .slide-leave-active { transition: max-height 0.22s ease, opacity 0.2s ease; max-height: 400px; overflow: hidden; }
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; }

/* ===== IMAGE PREVIEW ===== */
.img-preview-overlay {
  position: fixed; inset: 0; z-index: 300;
  background: var(--c-overlay-dark);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.img-preview {
  max-width: 100%; max-height: 90vh;
  border-radius: 8px; object-fit: contain;
}
.img-preview-close {
  position: absolute; top: 1rem; right: 1rem;
  background: rgba(255,255,255,0.15); border: none; border-radius: 50%;
  width: 2.25rem; height: 2.25rem; font-size: 0.9rem; color: #fff;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}

/* ── btn as link ─────────────────────────────────── */
.btn-as-link {
  background: none; border: none; padding: 0;
  color: var(--c-accent); font-size: inherit;
  cursor: pointer; text-align: left;
}

/* ── Location actions row ────────────────────────── */
.location-actions {
  display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
}
.btn-send-location {
  background: none; border: 1px solid var(--c-accent); border-radius: 8px;
  padding: 0.2rem 0.6rem; font-size: 0.82rem;
  color: var(--c-accent); cursor: pointer;
}
.btn-send-location:disabled { opacity: 0.5; cursor: default; }

/* ── Map app chooser sheet ───────────────────────── */
.map-sheet-overlay {
  position: fixed; inset: 0;
  background: var(--c-overlay-dark);
  z-index: 200;
  display: flex; align-items: flex-end;
}
.map-sheet {
  background: var(--c-bg);
  border-radius: 20px 20px 0 0;
  width: 100%; padding: 0 0 1.5rem;
}
.map-sheet-handle {
  width: 2.5rem; height: 4px; border-radius: 2px;
  background: var(--c-hint); opacity: 0.4;
  margin: 0.6rem auto 0.25rem;
}
.map-sheet-title {
  font-size: 0.78rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--c-hint);
  padding: 0.5rem 1.25rem 0.75rem;
}
.map-app-row {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  text-decoration: none; color: var(--c-text);
  border-top: 1px solid var(--c-surface);
}
.map-app-row:active { background: var(--c-surface); }
.map-app-icon { font-size: 1.3rem; width: 1.75rem; text-align: center; }
.map-app-name { flex: 1; font-size: 1rem; }
.map-app-chevron { color: var(--c-hint); font-size: 1.2rem; }
.map-sheet-cancel {
  display: block; width: calc(100% - 2.5rem);
  margin: 0.75rem 1.25rem 0;
  padding: 0.8rem; border: none; border-radius: 12px;
  background: var(--c-surface); color: var(--c-text);
  font-size: 0.95rem; font-weight: 600; cursor: pointer;
}

/* Sheet animation */
.sheet-fade-enter-active, .sheet-fade-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-fade-enter-active .map-sheet,
.sheet-fade-leave-active .map-sheet {
  transition: transform 0.25s ease;
}
.sheet-fade-enter-from, .sheet-fade-leave-to { opacity: 0; }
.sheet-fade-enter-from .map-sheet,
.sheet-fade-leave-to .map-sheet { transform: translateY(100%); }
</style>
