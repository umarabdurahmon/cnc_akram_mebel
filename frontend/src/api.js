import { getInitData } from './telegram.js'

function authHeaders() {
  const initData = getInitData()
  return initData ? { Authorization: `tma ${initData}` } : {}
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...options.headers,
  }

  const res = await fetch(path, { ...options, headers })

  if (!res.ok) {
    const err = new Error()
    err.status = res.status
    const body = await res.json().catch(() => ({}))
    console.error('[api] error', res.status, path, body)
    if (res.status === 401) {
      err.code = 'auth_required'
    } else if (res.status === 403) {
      err.code =
        body.detail === 'Employee not found' || body.detail === 'Employee is inactive'
          ? 'not_registered'
          : 'forbidden'
      err.detail = body.detail
    } else {
      err.code = 'server_error'
      err.detail = body.detail ?? JSON.stringify(body)
    }
    throw err
  }

  if (res.status === 204) return null
  return res.json()
}

/** Upload a file with XHR so we get upload progress events. */
function uploadFile(path, file, extraFields = {}, onProgress = null) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)
    for (const [k, v] of Object.entries(extraFields)) {
      if (v != null) formData.append(k, v)
    }

    const xhr = new XMLHttpRequest()
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        const err = new Error()
        err.status = xhr.status
        err.code = xhr.status === 413 ? 'file_too_large' : xhr.status === 415 ? 'file_type' : 'server_error'
        try { err.detail = JSON.parse(xhr.responseText).detail } catch { /* ignore */ }
        reject(err)
      }
    }
    xhr.onerror = () => {
      const err = new Error()
      err.code = 'network'
      reject(err)
    }

    const hdrs = authHeaders()
    xhr.open('POST', path)
    for (const [k, v] of Object.entries(hdrs)) xhr.setRequestHeader(k, v)
    xhr.send(formData)
  })
}

/** Fetch a binary resource (thumbnail, download) and return a Blob URL. */
async function fetchBlobUrl(path) {
  const res = await fetch(path, { headers: authHeaders() })
  if (!res.ok) return null
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

async function fetchBlob(path) {
  const res = await fetch(path, { headers: authHeaders() })
  if (!res.ok) {
    const err = new Error()
    err.code = 'server_error'
    throw err
  }
  return res.blob()
}

export const api = {
  get: (path) => request(path),
  fetchBlob,
  post: (path, body) =>
    request(path, {
      method: 'POST',
      body: body != null ? JSON.stringify(body) : undefined,
    }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
  uploadFile,
  fetchBlobUrl,
}
