import { createApp } from 'vue'
import App from './App.vue'
import { createAppI18n } from './i18n/index.js'

const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
const initialLocale = (tgLang === 'uz' ? 'uz' : 'ru')

const i18n = createAppI18n(initialLocale)

createApp(App).use(i18n).mount('#app')
