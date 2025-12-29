// recognitionClient - lightweight wrapper that delegates HTTP to apiClient
// Posts image data to backend endpoints using apiClient so Authorization and baseURL are consistent.
import { apiClient } from './apiClient'

class RecognitionClient {
  constructor(options = {}) {
    // default relative endpoints (apiClient will prefix with /api/v1/backend via its request normalization)
    this.endpointPath = options.endpoint || '/recognition/attend'
    this.enrollPath = options.enrollPath || '/students/enroll'
    this.timeoutMs = options.timeoutMs || 10000
    this.isInitialized = false
  }

  // set or update auth token (Bearer)
  setAuthToken(token) {
    this.authToken = token
    try { if (typeof localStorage !== 'undefined' && token) localStorage.setItem('access_token', token) } catch (e) {}
  }

  // build relative endpoint path (apiClient will turn into full URL)
  _endpoint(path) { return path || this.endpointPath }

  // convert dataURL/base64 to Blob
  _dataURLToBlob(dataURL) {
    const parts = dataURL.split(',')
    const meta = parts[0] || ''
    const data = parts[1] || ''
    const isBase64 = meta.indexOf(';base64') !== -1
    const contentType = (meta.split(':')[1] || 'image/jpeg').split(';')[0]
    if (isBase64) {
      const byteChars = atob(data)
      const byteNumbers = new Array(byteChars.length)
      for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i)
      const byteArray = new Uint8Array(byteNumbers)
      return new Blob([byteArray], { type: contentType })
    }
    // URL-encoded fallback
    const decoded = decodeURIComponent(data)
    const arr = new Uint8Array(decoded.length)
    for (let i = 0; i < decoded.length; i++) arr[i] = decoded.charCodeAt(i)
    return new Blob([arr], { type: contentType })
  }

  // fetch wrapper with AbortController timeout
  async _fetchWithTimeout(url, opts = {}, timeoutMs = this.timeoutMs) {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), timeoutMs)
    opts.signal = controller.signal
    try {
      const res = await fetch(url, opts)
      clearTimeout(id)
      return res
    } catch (err) {
      clearTimeout(id)
      throw err
    }
  }

  // initialize by optionally pinging health; refresh token from localStorage
  async initialize() {
    if (this.isInitialized) return { success: true }
    if (!this.authToken && typeof localStorage !== 'undefined') {
      this.authToken = localStorage.getItem('access_token')
    }
    // ping health via apiClient (best-effort)
    try {
      const res = await apiClient.apiGet('/health')
      this.isInitialized = true
      return { success: true, message: 'recognition endpoint reachable', info: res }
    } catch (e) {
      this.isInitialized = true
      return { success: true, message: 'initialized (health check skipped/unavailable)' }
    }
  }

  // Recognize face: accepts File/Blob, dataURL, base64(with contentType via options), or { file }
  async recognizeFace(imageData, options = {}) {
    if (!this.isInitialized) await this.initialize()

    let fileBlob = null
    if (imageData instanceof Blob) fileBlob = imageData
    else if (typeof imageData === 'string') {
      if (imageData.startsWith('data:')) fileBlob = this._dataURLToBlob(imageData)
      else if (/^[A-Za-z0-9+/=\s]+$/.test(imageData) && options.contentType) {
        fileBlob = this._dataURLToBlob(`data:${options.contentType};base64,${imageData}`)
      } else throw new Error('Unsupported imageData string; provide dataURL or raw base64 with contentType')
    } else if (imageData && imageData.file) fileBlob = imageData.file
    else throw new Error('Unsupported imageData type')

    const form = new FormData()
    form.append('image', fileBlob, options.filename || 'frame.jpg')
    if (options.metadata) form.append('metadata', JSON.stringify(options.metadata))

    try {
      return await apiClient.apiPostForm(options.endpoint || this._endpoint(this.endpointPath), form)
    } catch (err) {
      return { error: true, message: err.message || String(err) }
    }
  }

  // Enroll a new face
  async registerNewFace(imageData, userData = {}, options = {}) {
    if (!this.isInitialized) await this.initialize()
    let fileBlob = null
    if (imageData instanceof Blob) fileBlob = imageData
    else if (typeof imageData === 'string' && imageData.startsWith('data:')) fileBlob = this._dataURLToBlob(imageData)
    else if (imageData && imageData.file) fileBlob = imageData.file
    else throw new Error('Unsupported imageData for enrollment')

    const form = new FormData()
    form.append('image', fileBlob, options.filename || 'enroll.jpg')
    form.append('user', JSON.stringify(userData || {}))

    try {
      return await apiClient.apiPostForm(options.enrollEndpoint || this.enrollPath, form)
    } catch (err) {
      return { error: true, message: err.message || String(err) }
    }
  }

  // Batch recognition: posts multiple images as 'images' fields
  async recognizeMultipleFaces(images = [], options = {}) {
    if (!this.isInitialized) await this.initialize()
    const form = new FormData()
    images.forEach((img, idx) => {
      if (img instanceof Blob) form.append('images', img, options.filenames ? options.filenames[idx] : `frame_${idx}.jpg`)
      else if (typeof img === 'string' && img.startsWith('data:')) form.append('images', this._dataURLToBlob(img), options.filenames ? options.filenames[idx] : `frame_${idx}.jpg`)
      else if (img && img.file) form.append('images', img.file, options.filenames ? options.filenames[idx] : `frame_${idx}.jpg`)
      else throw new Error('Unsupported image type in images array')
    })

    try {
      return await apiClient.apiPostForm(options.endpoint || (this.endpointPath + '/batch'), form)
    } catch (err) {
      return { error: true, message: err.message || String(err) }
    }
  }

  // Health/status helper
  async getSystemStatus() {
    try {
      const json = await apiClient.apiGet('/system/status')
      return { initialized: this.isInitialized, status: 'ok', info: json }
    } catch (err) {
      return { initialized: this.isInitialized, status: 'error', message: err.message }
    }
  }
}

export const recognitionClient = new RecognitionClient({ allowPlaceholder: true })
export default recognitionClient





