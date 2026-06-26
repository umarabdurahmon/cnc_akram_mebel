import { createI18n } from 'vue-i18n'
import ru from './ru.js'
import uz from './uz.js'

const SHOP_TZ = 'Asia/Tashkent'

export function createAppI18n(locale = 'ru') {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'ru',
    messages: { ru, uz },
  })
}

export function formatTime(isoString) {
  if (!isoString) return '--:--'
  const d = new Date(isoString)
  return d.toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: SHOP_TZ,
  })
}

export function formatHours(hours) {
  return Number(hours).toFixed(1)
}
