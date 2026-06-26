<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-handle" />
      <div class="modal-head">
        <h2 class="modal-title">{{ t('orders.create') }}</h2>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- Обязательные поля -->
      <div class="section-label">{{ t('orders.required_fields') }}</div>

      <div class="field" :class="{ error: errors.customer_name }">
        <label>{{ t('orders.customer') }}</label>
        <input
          v-model="form.customer_name"
          class="input-text"
          type="text"
          :placeholder="t('orders.customer_placeholder')"
          @input="errors.customer_name = ''"
        />
        <span v-if="errors.customer_name" class="error-text">{{ errors.customer_name }}</span>
      </div>

      <div class="field" :class="{ error: errors.title }">
        <label>{{ t('orders.order_title') }}</label>
        <input
          v-model="form.title"
          class="input-text"
          type="text"
          :placeholder="t('orders.order_title_placeholder')"
          @input="errors.title = ''"
        />
        <span v-if="errors.title" class="error-text">{{ errors.title }}</span>
      </div>

      <!-- Этап -->
      <div class="field">
        <label>{{ t('orders.stage') }}</label>
        <select v-model="form.current_stage_id" class="input-text">
          <option :value="null">{{ t('orders.no_stage') }}</option>
          <option v-for="s in stages" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <!-- Дополнительные поля — раскрываются -->
      <button class="expand-btn" @click="showExtra = !showExtra">
        {{ showExtra ? '▾' : '▸' }} {{ t('orders.extra_fields') }}
        <span v-if="extraFilled" class="extra-badge">{{ extraFilled }}</span>
      </button>

      <transition name="slide">
        <div v-if="showExtra" class="extra-fields">
          <div class="field">
            <label>{{ t('orders.deadline') }}</label>
            <input v-model="form.deadline" class="input-text" type="date" />
          </div>

          <div class="field">
            <label>{{ t('orders.contact') }}</label>
            <input
              v-model="form.customer_contact"
              class="input-text"
              type="text"
              :placeholder="t('orders.contact_placeholder')"
            />
          </div>

          <div class="field">
            <label>{{ t('orders.amount') }}</label>
            <div class="input-with-suffix">
              <input
                v-model="form.total_amount"
                class="input-text"
                type="number"
                step="1000"
                min="0"
                placeholder="0"
              />
              <span class="suffix">сум</span>
            </div>
          </div>

          <div class="field">
            <label>{{ t('orders.description') }}</label>
            <textarea
              v-model="form.description"
              rows="2"
              class="input-note"
              :placeholder="t('orders.description_placeholder')"
            />
          </div>

          <div class="field">
            <label>{{ t('orders.public_note') }}</label>
            <textarea
              v-model="form.public_note"
              rows="2"
              class="input-note"
              :placeholder="t('orders.public_note_placeholder')"
            />
          </div>

          <div class="field">
            <label>{{ t('orders.location') }}</label>
            <button v-if="!showMap" class="btn-map" @click="showMap = true">
              📍 {{ t('orders.add_location') }}
            </button>
            <template v-else>
              <LocationPicker
                :lat="form.delivery_lat"
                :lon="form.delivery_lon"
                @update:lat="form.delivery_lat = $event"
                @update:lon="form.delivery_lon = $event"
              />
              <button class="btn-map-clear" @click="clearLocation">
                ✕ {{ t('orders.remove_location') }}
              </button>
            </template>
            <span v-if="form.delivery_lat != null" class="coord-hint">
              {{ form.delivery_lat.toFixed(5) }}, {{ form.delivery_lon.toFixed(5) }}
            </span>
          </div>
        </div>
      </transition>

      <div v-if="generalError" class="general-error">{{ generalError }}</div>

      <div class="modal-actions">
        <button class="btn-cancel" @click="$emit('close')" :disabled="saving">
          {{ t('orders.cancel') }}
        </button>
        <button class="btn-save" @click="save" :disabled="saving">
          <span v-if="saving" class="spinner">…</span>
          <span v-else>{{ t('orders.create_btn') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api.js'
import LocationPicker from '../components/LocationPicker.vue'

const emit = defineEmits(['close', 'saved'])
const { t } = useI18n()

const saving = ref(false)
const showExtra = ref(true)
const showMap = ref(false)
const generalError = ref('')
const stages = ref([])
const errors = ref({ customer_name: '', title: '' })

const form = ref({
  customer_name: '', title: '', current_stage_id: null,
  customer_contact: '',
  description: '', deadline: '', total_amount: '', public_note: '',
  delivery_lat: null, delivery_lon: null,
})

const extraFilled = computed(() => {
  const f = form.value
  return [f.customer_contact, f.description, f.deadline, f.total_amount, f.public_note, f.delivery_lat]
    .filter(v => v !== '' && v !== null && v !== undefined).length || 0
})

onMounted(async () => {
  try {
    stages.value = await api.get('/api/stages')
  } catch { /* silent */ }
})

function clean(val) {
  return val === '' ? null : val
}

function clearLocation() {
  form.value.delivery_lat = null
  form.value.delivery_lon = null
  showMap.value = false
}

function validate() {
  let ok = true
  errors.value = { customer_name: '', title: '' }
  if (!form.value.customer_name.trim()) {
    errors.value.customer_name = t('orders.err_required')
    ok = false
  }
  if (!form.value.title.trim()) {
    errors.value.title = t('orders.err_required')
    ok = false
  }
  return ok
}

async function save() {
  if (saving.value || !validate()) return
  saving.value = true
  generalError.value = ''
  const body = {
    customer_name: form.value.customer_name.trim(),
    title: form.value.title.trim(),
    current_stage_id: form.value.current_stage_id,
    customer_contact: clean(form.value.customer_contact),
    description: clean(form.value.description),
    deadline: clean(form.value.deadline),
    total_amount: form.value.total_amount ? Number(form.value.total_amount) : null,
    public_note: clean(form.value.public_note),
    delivery_lat: form.value.delivery_lat,
    delivery_lon: form.value.delivery_lon,
  }
  try {
    const result = await api.post('/api/orders', body)
    emit('saved', result)
  } catch (err) {
    generalError.value = t(`errors.${err.code ?? 'unknown'}`) + (err.detail ? ` (${err.detail})` : '')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: var(--c-overlay);
  display: flex; align-items: flex-end; z-index: 100;
}
.modal {
  background: var(--c-bg);
  border-radius: 20px 20px 0 0;
  padding: 0.5rem 1rem 2rem;
  width: 100%; max-height: 92vh; overflow-y: auto;
}

.modal-handle {
  width: 2.5rem; height: 4px; border-radius: 2px;
  background: var(--c-hint);
  margin: 0.5rem auto 0.75rem; opacity: 0.4;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem;
}
.modal-title { font-size: 1.1rem; font-weight: 700; margin: 0; color: var(--c-text); }
.close-btn {
  background: var(--c-surface);
  border: none; border-radius: 50%; width: 1.75rem; height: 1.75rem;
  font-size: 0.75rem; color: var(--c-hint);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}

.section-label {
  font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--c-hint);
  margin-bottom: 0.625rem;
}

.field { margin-bottom: 0.75rem; }
.field.error .input-text,
.field.error .input-note { border-color: var(--c-negative); }
.field label {
  display: block; font-size: 0.8rem; font-weight: 500;
  color: var(--c-hint); margin-bottom: 0.25rem;
}
.input-text, .input-note {
  background: var(--c-surface);
  border: 1.5px solid transparent; border-radius: 10px;
  padding: 0.6rem 0.75rem; font-size: 0.95rem;
  color: var(--c-text);
  width: 100%; box-sizing: border-box; transition: border-color 0.15s;
}
.input-text:focus, .input-note:focus {
  outline: none; border-color: var(--c-accent);
}
.input-note { resize: vertical; font-family: inherit; }
.error-text { display: block; font-size: 0.76rem; color: var(--c-negative); margin-top: 0.2rem; }

.input-with-suffix { position: relative; }
.input-with-suffix .input-text { padding-right: 3rem; }
.suffix {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  font-size: 0.8rem; color: var(--c-hint); pointer-events: none;
}

/* Expand button */
.expand-btn {
  display: flex; align-items: center; gap: 0.4rem;
  background: none; border: none; font-size: 0.88rem; font-weight: 600;
  color: var(--c-accent);
  cursor: pointer; padding: 0.25rem 0; margin-bottom: 0.75rem;
}
.extra-badge {
  background: var(--c-accent);
  color: var(--c-accent-text);
  font-size: 0.68rem; font-weight: 700; border-radius: 99px;
  padding: 0.05rem 0.4rem; line-height: 1.5;
}

.extra-fields { margin-bottom: 0.25rem; }

.field-row { display: flex; gap: 0.625rem; }
.field.half { flex: 1; min-width: 0; }

.general-error {
  font-size: 0.82rem; color: var(--c-negative);
  text-align: center; margin-bottom: 0.75rem;
}

.modal-actions { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
.btn-cancel, .btn-save {
  flex: 1; padding: 0.8rem; border: none; border-radius: 12px;
  font-size: 0.95rem; font-weight: 600; cursor: pointer;
}
.btn-cancel {
  background: var(--c-surface);
  color: var(--c-text);
}
.btn-save {
  background: var(--c-accent);
  color: var(--c-accent-text);
}
.btn-save:disabled, .btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-map {
  background: var(--c-surface);
  border: 1.5px dashed var(--c-accent);
  border-radius: 10px;
  color: var(--c-accent);
  font-size: 0.9rem; font-weight: 500;
  padding: 0.55rem 0.75rem;
  width: 100%; cursor: pointer; text-align: left;
}
.btn-map-clear {
  background: none; border: none;
  color: var(--c-negative);
  font-size: 0.8rem; cursor: pointer;
  padding: 0.3rem 0; margin-top: 0.3rem;
}
.coord-hint {
  display: block;
  font-size: 0.74rem; color: var(--c-hint);
  margin-top: 0.25rem; font-variant-numeric: tabular-nums;
}

/* Transition */
.slide-enter-active, .slide-leave-active {
  transition: all 0.25s ease; overflow: hidden; max-height: 600px;
}
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; }
</style>
