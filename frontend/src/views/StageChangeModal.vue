<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h2 class="modal-title">{{ t('orders.stage_change') }}</h2>

      <div class="field">
        <label>{{ t('orders.stage_select') }}</label>
        <select v-model="selectedStageId" class="input-select">
          <option v-for="s in stages" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <div class="field">
        <label>{{ t('orders.comment') }}</label>
        <textarea v-model="comment" rows="2" class="input-note" :placeholder="t('orders.comment_placeholder')" />
      </div>

      <div class="modal-actions">
        <button class="btn-cancel" @click="$emit('close')" :disabled="saving">{{ t('orders.cancel') }}</button>
        <button class="btn-save" @click="save" :disabled="saving || !selectedStageId">
          {{ saving ? '…' : t('orders.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import { showAlert } from '../telegram.js'

const props = defineProps({
  orderId: { type: Number, required: true },
  currentStageId: { type: Number, default: null },
})
const emit = defineEmits(['close', 'saved'])
const { t } = useI18n()

const stages = ref([])
const selectedStageId = ref(props.currentStageId)
const comment = ref('')
const saving = ref(false)

onMounted(async () => {
  try {
    stages.value = await api.get('/api/stages')
  } catch { /* ignore — user can't select */ }
})

async function save() {
  if (!selectedStageId.value || saving.value) return
  saving.value = true
  try {
    const updated = await api.post(`/api/orders/${props.orderId}/stage`, {
      stage_id: selectedStageId.value,
      comment: comment.value || null,
    })
    emit('saved', updated)
  } catch (err) {
    await showAlert(err.status === 403 ? t('errors.forbidden') : t('errors.server_error'))
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
}
.modal-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 1rem;
  color: var(--c-text);
}
.field { margin-bottom: 0.875rem; }
.field label {
  display: block;
  font-size: 0.8rem;
  color: var(--c-hint);
  margin-bottom: 0.25rem;
}
.input-select, .input-note {
  background: var(--c-surface);
  border: none;
  border-radius: 8px;
  padding: 0.5rem 0.625rem;
  font-size: 0.9rem;
  color: var(--c-text);
  width: 100%;
  box-sizing: border-box;
}
.input-note { resize: vertical; font-family: inherit; }
.modal-actions { display: flex; gap: 0.75rem; }
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
.btn-save:disabled, .btn-cancel:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
