const tg = window.Telegram?.WebApp ?? null

export function initTelegram() {
  if (!tg) return
  tg.ready()
  tg.expand()
}

export function getInitData() {
  if (tg?.initData) return tg.initData
  if (import.meta.env.DEV) return import.meta.env.VITE_DEV_INIT_DATA ?? ''
  return ''
}

export function getColorScheme() {
  return tg?.colorScheme ?? 'light'
}

export function getThemeParams() {
  return tg?.themeParams ?? {}
}

export function getMainButton() {
  return tg?.MainButton ?? null
}

export function onThemeChange(callback) {
  if (!tg) return
  tg.onEvent('themeChanged', callback)
}

export function showConfirm(message) {
  return new Promise(resolve => {
    if (tg?.showConfirm) {
      tg.showConfirm(message, resolve)
    } else {
      resolve(window.confirm(message))
    }
  })
}

export function showAlert(message) {
  return new Promise(resolve => {
    if (tg?.showAlert) {
      tg.showAlert(message, resolve)
    } else {
      window.alert(message)
      resolve()
    }
  })
}
