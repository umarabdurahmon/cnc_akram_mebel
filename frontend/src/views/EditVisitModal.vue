<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2 class="modal-title">{{ t('manager.edit_title') }}</h2>
      <p class="modal-meta">{{ employeeName }} · {{ visit.work_date }}</p>

      <div class="field">
        <label>{{ t('manager.edit_check_in_label') }}</label>
        <div class="time-row">
          <input type="date" v-model="inDate" class="input-date" />
          <input type="time" v-model="inTime" class="input-time" />
        </div>
        <p v-if="workDateChanged" class="date-warn">
          {{ t('manager.edit_work_date_changed', { date: inDate }) }}
        </p>
      </div>

      <div class="field">
        <label>{{ t('manager.edit_check_out_label') }}</label>
        <div class="time-row">
          <input type="date" v-model="outDate" class="input-date" />
          <input type="time" v-model="outTime" class="input-time" />
          <button v-if="outDate || outTime" class="btn-clear" @click="clearCheckOut">✕</button>
        </div>
      </div>

      <div class="field">
        <label>{{ t('manager.edit_note_label') }}</label>
        <textarea v-model="note" rows="2" class="input-note" />
      </div>

      <div class="hours-preview">
        {{ t('manager.edit_hours_preview', { before: formatHours(totalHours), after: formatHours(newTotalHours) }) }}
      </div>

      <div class="modal-actions">
        <button class="btn-cancel" @click="$emit('close')" :disabled="saving">
          {{ t('manager.edit_cancel') }}
        </button>
        <button class="btn-save" @click="save" :disabled="saving">
          {{ saving ? '…' : t('manager.edit_save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showConfirm, showAlert } from '../telegram.js'
import { formatHours } from '../i18n/index.js'

const props = defineProps({
  visit: { type: Object, required: true },
  employeeName: { type: String, required: true },
  totalHours: { type: Number, required: true },
})

const emit = defineEmits(['close', 'saved'])
const { t } = useI18n()
const saving = ref(false)

function utcToTashkentParts(isoStr) {
  if (!isoStr) return { date: '', time: '' }
  const d = new Date(isoStr)
  return {
    date: d.toLocaleDateString('sv', { timeZone: 'Asia/Tashkent' }),
    time: d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Tashkent' }),
  }
}

function tashkentPartsToUtcIso(date, time) {
  if (!date || !time) return null
  return new Date(`${date}T${time}:00+05:00`).toISOString()
}

const inParts = utcToTashkentParts(props.visit.check_in_at)
const outParts = utcToTashkentParts(props.visit.check_out_at)

const inDate = ref(inParts.date)
const inTime = ref(inParts.time)
const outDate = ref(outParts.date)
const outTime = ref(outParts.time)
const note = ref(props.visit.note ?? '')

function clearCheckOut() {
  outDate.value = ''
  outTime.value = ''
}

const workDateChanged = computed(() => inDate.value && inDate.value !== props.visit.work_date)

function visitDurationHours(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0
  return (new Date(checkOut) - new Date(checkIn)) / 3600000
}

const oldDuration = visitDurationHours(props.visit.check_in_at, props.visit.check_out_at)

const newTotalHours = computed(() => {
  const newIn = tashkentPartsToUtcIso(inDate.value, inTime.value)
  const newOut = tashkentPartsToUtcIso(outDate.value, outTime.value)
  const newDuration = visitDurationHours(newIn, newOut)
  return Math.max(0, props.totalHours - oldDuration + newDuration)
})

async function save() {
  if (saving.value) return

  const newIn = tashkentPartsToUtcIso(inDate.value, inTime.value)
  if (!newIn) {
    await showAlert(t('manager.edit_error_400'))
    return
  }

  const newOut = (outDate.value && outTime.value)
    ? tashkentPartsToUtcIso(outDate.value, outTime.value)
    : null

  const confirmMsg = t('manager.edit_confirm_msg', {
    before: formatHours(props.totalHours),
    after: formatHours(newTotalHours.value),
  })
  const ok = await showConfirm(confirmMsg)
  if (!ok) return

  saving.value = true
  try {
    const body = { check_in_at: newIn, note: note.value || null }
    if (outDate.value || outTime.value || props.visit.check_out_at !== null) {
      body.check_out_at = newOut
    }

    const updated = await api.patch(`/api/attendance/${props.visit.id}`, body)
    emit('saved', updated)
  } catch (err) {
    let msg = t('errors.server_error')
    if (err.status === 400) msg = t('manager.edit_error_400')
    else if (err.status === 409) msg = t('manager.edit_error_409')
    await showAlert(msg)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--c-overlay);
  display: flex;
  align-items: flex-end;
  z-index: 100;
}

.modal {
  background: var(--c-bg);
  border-radius: 16px 16px 0 0;
  padding: 1.25rem 1rem 2rem;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.25rem;
  color: var(--c-text);
}

.modal-meta {
  font-size: 0.875rem;
  color: var(--c-hint);
  margin: 0 0 1rem;
}

.field {
  margin-bottom: 0.875rem;
}

.field label {
  display: block;
  font-size: 0.8rem;
  color: var(--c-hint);
  margin-bottom: 0.25rem;
}

.time-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.input-date, .input-time, .input-note {
  background: var(--c-surface);
  border: none;
  border-radius: 8px;
  padding: 0.5rem 0.625rem;
  font-size: 0.9rem;
  color: var(--c-text);
  width: 100%;
  box-sizing: border-box;
}

.input-date { flex: 1.5; }
.input-time { flex: 1; }

.input-note {
  resize: vertical;
  font-family: inherit;
}

.btn-clear {
  background: none;
  border: none;
  color: var(--c-hint);
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  flex-shrink: 0;
}

.date-warn {
  font-size: 0.8rem;
  color: var(--c-warning);
  margin: 0.25rem 0 0;
}

.hours-preview {
  font-size: 0.875rem;
  color: var(--c-hint);
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--c-surface);
  border-radius: 8px;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-cancel, .btn-save {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  background: var(--c-surface);
  color: var(--c-text);
}

.btn-save {
  background: var(--c-accent);
  color: var(--c-accent-text);
}

.btn-save:disabled, .btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
