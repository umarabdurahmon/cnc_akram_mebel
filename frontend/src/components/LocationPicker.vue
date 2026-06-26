<template>
  <div ref="mapEl" class="location-picker" />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Vite bundler fix: leaflet can't resolve its own marker images at runtime
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
})

const props = defineProps({
  lat: { type: Number, default: null },
  lon: { type: Number, default: null },
})
const emit = defineEmits(['update:lat', 'update:lon'])

const TASHKENT = [41.2995, 69.2401]
const mapEl = ref(null)
let map = null
let marker = null

onMounted(() => {
  const center = props.lat != null ? [props.lat, props.lon] : TASHKENT
  map = L.map(mapEl.value).setView(center, 13)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map)
  marker = L.marker(center, { draggable: true }).addTo(map)

  const update = ({ lat, lng }) => {
    emit('update:lat', lat)
    emit('update:lon', lng)
  }
  marker.on('dragend', () => update(marker.getLatLng()))
  map.on('click', (e) => {
    marker.setLatLng(e.latlng)
    update(e.latlng)
  })

  // emit initial center so form.delivery_lat/lon are populated immediately
  if (props.lat == null) update({ lat: TASHKENT[0], lng: TASHKENT[1] })
})

onUnmounted(() => {
  map?.remove()
})
</script>

<style scoped>
.location-picker {
  height: 200px;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 0.25rem;
}
</style>
