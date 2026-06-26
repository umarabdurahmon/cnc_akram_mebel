/**
 * Float-safe money handling.
 *
 * Rule: amounts travel as STRINGS from input to API. Never parseFloat → number → API.
 * parseFloat is only used for display (Intl.NumberFormat), never for computation or wire.
 */

/** Normalise a user-typed string to a clean decimal string, or return null if invalid. */
export function parseAmount(raw) {
  if (!raw) return null
  // Accept spaces as thousands separators; comma or dot as decimal separator
  const s = raw.replace(/\s/g, '').replace(',', '.')
  if (!/^\d+(\.\d{0,2})?$/.test(s)) return null
  if (s === '0' || s === '0.00' || s === '0.0') return null
  return s
}

/** Display a decimal string with thousands separators (float used only here, for display). */
export function displayAmount(str, currency = 'сум') {
  if (str === null || str === undefined || str === '') return '—'
  const n = parseFloat(str)
  if (isNaN(n)) return str
  return new Intl.NumberFormat('ru-RU').format(n) + (currency ? ' ' + currency : '')
}

/** Determine CSS class based on profit sign. */
export function profitClass(str) {
  if (!str) return ''
  const n = parseFloat(str)
  if (isNaN(n)) return ''
  return n >= 0 ? 'positive' : 'negative'
}
