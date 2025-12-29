import React, { useState, useRef, useEffect } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuthStore } from '../store/authStore'

const Registration = () => {
  const { user, accessToken } = useAuthStore()
  
  // Core form state (NO is_rejoinee field)
  const [formData, setFormData] = useState({
    student_id: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    section: '',
    department: '',
    semester: '',
    password: ''
  })

  // Image files state
  const [imageFiles, setImageFiles] = useState({
    front: null,
    left: null,
    right: null,
    angled_left: null,
    angled_right: null
  })

  // Image preview URLs state
  const [imagePreviewUrls, setImagePreviewUrls] = useState({
    front: null,
    left: null,
    right: null,
    angled_left: null,
    angled_right: null
  })

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [registrationStatus, setRegistrationStatus] = useState(null)
  
  // Capture mode: upload or webcam ONLY (NO bullet_cam)
  const [captureMode, setCaptureMode] = useState('upload')
  const [currentCapture, setCurrentCapture] = useState(null)
  const [cameraStarted, setCameraStarted] = useState(false)
  
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [stream, setStream] = useState(null)

  // Department options
  const [departmentsList, setDepartmentsList] = useState([
    { id: '', name: 'Select Department' }
  ])

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        const deps = await apiClient.getDepartments()
        if (!mounted) return
        const list = (Array.isArray(deps) ? deps : (deps?.departments || [])).map(d => 
          typeof d === 'string' ? { id: d, name: d } : ({ id: d.id || d.name, name: d.name || d.id })
        )
        setDepartmentsList([
          { id: '', name: 'Select Department' },
          ...list,
          { id: 'OTHER', name: 'Type Your Own' }
        ])
      } catch (e) {
        setDepartmentsList([
          { id: '', name: 'Select Department' },
          { id: 'CSE', name: 'Computer Science & Engineering (CSE)' },
          { id: 'ECE', name: 'Electronics & Communication Engineering (ECE)' },
          { id: 'EEE', name: 'Electrical & Electronics Engineering (EEE)' },
          { id: 'CE', name: 'Civil Engineering (CE)' },
          { id: 'OTHER', name: 'Type Your Own' }
        ])
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  // Cleanup preview URLs only on component unmount
  useEffect(() => {
    return () => {
      // Revoke all object URLs when component unmounts
      Object.values(imagePreviewUrls).forEach(url => {
        if (url) URL.revokeObjectURL(url)
      })
    }
  }, []) // Empty dependency array - only runs on unmount

  // Section options
  const sections = [
    { value: '', label: 'Select Section' },
    { value: 'A', label: 'A' },
    { value: 'B', label: 'B' },
    { value: 'C', label: 'C' },
    { value: 'D', label: 'D' },
    { value: 'E', label: 'E' },
    { value: 'F', label: 'F' },
    { value: 'G', label: 'G' },
    { value: 'H', label: 'H' },
    { value: 'NIL', label: 'NIL' },
    { value: 'OTHER', label: 'Type Your Own' }
  ]

  // Semester options
  const semesters = [
    { value: '', label: 'Select Semester' },
    { value: '1', label: 'Semester 1' },
    { value: '2', label: 'Semester 2' },
    { value: '3', label: 'Semester 3' },
    { value: '4', label: 'Semester 4' },
    { value: '5', label: 'Semester 5' },
    { value: '6', label: 'Semester 6' },
    { value: '7', label: 'Semester 7' },
    { value: '8', label: 'Semester 8' }
  ]

  // Webcam control
  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 } 
      })
      setStream(mediaStream)
      setCameraStarted(true)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch (error) {
      console.error('Webcam error:', error)
      setRegistrationStatus({ 
        type: 'error', 
        message: 'Webcam access denied. Please use upload option.' 
      })
      setCaptureMode('upload')
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
      setCameraStarted(false)
    }
  }

  // Capture from webcam
  const captureImage = (position) => {
    if (captureMode !== 'webcam' || !videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob((blob) => {
      const file = new File([blob], `${position}_webcam.jpg`, { type: 'image/jpeg' })
      
      // Clean up old preview URL if exists
      if (imagePreviewUrls[position]) {
        URL.revokeObjectURL(imagePreviewUrls[position])
      }
      
      // Create new preview URL
      const previewUrl = URL.createObjectURL(file)
      
      setImageFiles(prev => ({ ...prev, [position]: file }))
      setImagePreviewUrls(prev => ({ ...prev, [position]: previewUrl }))
      setCurrentCapture(position)
      setTimeout(() => setCurrentCapture(null), 2000)
    }, 'image/jpeg', 0.8)
  }

  // Capture from RTSP stream using snapshot API
  const captureFromRTSP = async (position) => {
    if (captureMode !== 'rtsp' || !selectedStream) {
      setEnrollmentStatus({ type: 'error', message: 'Please select an RTSP stream first' })
      return
    }

    try {
      // Use the snapshot API endpoint
      const baseURL = apiClient.baseURL || 'http://localhost:8002'
      const snapshotUrl = `${baseURL}/stream/${encodeURIComponent(selectedStream)}/snapshot_image`
      
      const response = await fetch(snapshotUrl, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to capture snapshot: ${response.status}`)
      }
      
      const blob = await response.blob()
      const file = new File([blob], `${position}_rtsp.jpg`, { type: 'image/jpeg' })
      
      // Clean up old preview URL if exists
      if (imagePreviewUrls[position]) {
        URL.revokeObjectURL(imagePreviewUrls[position])
      }
      
      // Create new preview URL
      const previewUrl = URL.createObjectURL(file)
      
      setImageFiles(prev => ({ ...prev, [position]: file }))
      setImagePreviewUrls(prev => ({ ...prev, [position]: previewUrl }))
      setCurrentCapture(position)
      setTimeout(() => setCurrentCapture(null), 2000)
    } catch (error) {
      console.error('RTSP capture failed:', error)
      setEnrollmentStatus({ type: 'error', message: `Failed to capture from RTSP stream: ${error.message}` })
    }
  }

  // Handle capture mode change
  const handleCaptureModeChange = (mode) => {
    if (captureMode === 'webcam') {
      stopCamera()
    }
    setCaptureMode(mode)
    if (mode === 'webcam' && !cameraStarted) {
      startWebcam()
    }
    if (mode === 'rtsp') {
      setEnrollmentStatus(null)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera()
    }
  }, [])

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleFileChange = (position, file) => {
    if (file) {
      // Clean up old preview URL if exists
      if (imagePreviewUrls[position]) {
        URL.revokeObjectURL(imagePreviewUrls[position])
      }
      
      // Create new preview URL
      const previewUrl = URL.createObjectURL(file)
      
      setImageFiles(prev => ({ ...prev, [position]: file }))
      setImagePreviewUrls(prev => ({ ...prev, [position]: previewUrl }))
    }
  }

  // Validation
  const validateForm = () => {
    if (!formData.student_id.trim()) return 'Registration Number is required'
    if (!formData.first_name.trim()) return 'First Name is required'
    if (!formData.last_name.trim()) return 'Last Name is required'
    if (!formData.department) return 'Department is required'
    if (formData.department === 'OTHER' && !formData.custom_department) return 'Please specify your department'
    if (formData.section === 'OTHER' && !formData.custom_section) return 'Please specify your section'
    if (!formData.password) return 'Initial password is required'
    if (!formData.semester) return 'Semester selection is required'
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    const validationError = validateForm()
    if (validationError) {
      setRegistrationStatus({ type: 'error', message: validationError })
      return
    }

    setIsSubmitting(true)
    setRegistrationStatus(null)

    try {
      const finalDepartment = formData.department === 'OTHER' ? formData.custom_department : formData.department
      const finalSection = formData.section === 'OTHER' ? formData.custom_section : formData.section

      const fd = new FormData()
      fd.append('reg_no', formData.student_id)
      const fullName = `${formData.first_name}${formData.middle_name ? ' ' + formData.middle_name : ''} ${formData.last_name}`.trim()
      fd.append('name', fullName)
      fd.append('department', finalDepartment)
      fd.append('section', finalSection)
      fd.append('semester', String(formData.semester || ''))
      if (formData.roll_no) fd.append('roll_no', String(formData.roll_no))
      fd.append('password', String(formData.password || ''))

      const studentResponse = await apiClient.apiPostForm('/students/create', fd)

      if (!studentResponse || studentResponse.status === 'error') {
        throw new Error(studentResponse?.message || 'Failed to create student record')
      }

      setRegistrationStatus({ 
        type: 'success', 
        message: `Student ${formData.first_name} ${formData.last_name} created successfully! Proceed to Enrollment to upload photos.` 
      })

      setFormData(prev => ({
        ...prev,
        student_id: '',
        first_name: '',
        middle_name: '',
        last_name: '',
        section: '',
        department: '',
        semester: '',
        password: ''
      }))

    } catch (error) {
      console.error('Registration failed:', error)
      setRegistrationStatus({ 
        type: 'error', 
        message: error.message || 'Registration failed. Please try again.' 
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  // Enrollment state
  const [enrollRegNo, setEnrollRegNo] = useState('')
  const [verifiedStudent, setVerifiedStudent] = useState(null)
  const [streamsList, setStreamsList] = useState([])
  const [selectedStream, setSelectedStream] = useState('')
  const [enrollLoading, setEnrollLoading] = useState(false)
  const [liveFrameUrl, setLiveFrameUrl] = useState(null)
  const wsRef = useRef(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [capturePosition, setCapturePosition] = useState('front')
  const [enrollmentStatus, setEnrollmentStatus] = useState(null)

  const verifyStudent = async () => {
    if (!enrollRegNo) {
      setEnrollmentStatus({ type: 'error', message: 'Enter registration number to verify' })
      return
    }
    try {
      setEnrollmentStatus(null)
      const resp = await apiClient.getStudent(enrollRegNo)
      setVerifiedStudent(resp)
      setEnrollmentStatus({ type: 'success', message: 'Student verified — proceed to upload or capture photos.' })
    } catch (e) {
      console.error('Verify failed', e)
      setEnrollmentStatus({ type: 'error', message: 'Student not found or API error' })
      setVerifiedStudent(null)
    }
  }

  const loadStreams = async () => {
    try {
      const list = await apiClient.listStreams()
      setStreamsList(Array.isArray(list) ? list.map(s => s.name || s) : [])
    } catch (e) {
      console.error('Failed to load streams', e)
      setStreamsList([])
    }
  }

  useEffect(() => { loadStreams() }, [])

  // Websocket for live preview
  useEffect(() => {
    const openWs = async () => {
      if (!selectedStream) return
      try {
        setPreviewLoading(true)
        await apiClient._ensureConfig()
        const token = useAuthStore.getState().accessToken
        const base = apiClient.baseURL || window.location.origin
        const wsBase = base.replace(/^http/, 'ws').replace(/\/api\/?$/, '')
        const wsUrl = `${wsBase}/stream/ws/${encodeURIComponent(selectedStream)}?token=${encodeURIComponent(token || '')}`
        
        if (wsRef.current) {
          try { wsRef.current.close() } catch (e) {}
          wsRef.current = null
        }

        const ws = new WebSocket(wsUrl)
        ws.binaryType = 'arraybuffer'
        ws.onopen = () => { setPreviewLoading(false) }
        ws.onmessage = (msg) => {
          try {
            const ab = msg.data
            const blob = new Blob([ab], { type: 'image/jpeg' })
            const url = URL.createObjectURL(blob)
            if (liveFrameUrl) URL.revokeObjectURL(liveFrameUrl)
            setLiveFrameUrl(url)
          } catch (e) {
            console.error('Failed to process ws frame', e)
          }
        }
        ws.onerror = (e) => { console.error('WS error', e); setPreviewLoading(false) }
        ws.onclose = () => { setPreviewLoading(false) }
        wsRef.current = ws
      } catch (e) {
        console.error('Failed to open WS', e)
        setPreviewLoading(false)
      }
    }

    openWs()

    return () => {
      if (wsRef.current) try { wsRef.current.close() } catch (e) {}
      if (liveFrameUrl) try { URL.revokeObjectURL(liveFrameUrl) } catch (e) {}
      setLiveFrameUrl(null)
    }
  }, [selectedStream])

  const submitEnrollment = async () => {
    if (!verifiedStudent || !verifiedStudent.reg_no && !enrollRegNo) {
      setEnrollmentStatus({ type: 'error', message: 'Verify student registration number first' })
      return
    }
    const reg = verifiedStudent?.reg_no || enrollRegNo
    setEnrollLoading(true)
    try {
      const fd = new FormData()
      Object.entries(imageFiles).forEach(([pos, f]) => { if (f) fd.append('files', f, f.name) })
      fd.append('metadata', JSON.stringify({ uploaded_by: user?.id || 'web', timestamp: new Date().toISOString() }))
      
      const resp = await apiClient.enrollStudent(reg, fd)
      const ok = resp && (
        (resp.status && Number(resp.status) >= 200 && Number(resp.status) < 300) ||
        resp.status === 'enrolled' || resp.status === 'success' ||
        resp === 'ok' || resp === 'OK'
      )
      
      if (ok) {
        setEnrollmentStatus({ type: 'success', message: 'Enrollment photos uploaded successfully' })
      } else {
        setEnrollmentStatus({ type: 'error', message: resp?.message || JSON.stringify(resp) || 'Enrollment failed' })
      }
    } catch (e) {
      console.error('Enroll failed', e)
      setEnrollmentStatus({ type: 'error', message: 'Enrollment API failed' })
    } finally {
      setEnrollLoading(false)
    }
  }

  // Image capture field component
  const ImageCaptureField = ({ position, label, description }) => (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <label className="text-sm font-medium text-gray-700">
          {label} {imageFiles[position] && <span className="text-green-600 ml-2">✓</span>}
        </label>
        <span className="text-xs text-gray-500">{description}</span>
      </div>
      
      {captureMode === 'upload' ? (
        <div>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => handleFileChange(position, e.target.files[0])}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
          {imageFiles[position] && (
            <span className="text-xs text-green-600 mt-2 block">{imageFiles[position].name}</span>
          )}
        </div>
      ) : (
        <div>
          <button
            type="button"
            onClick={() => captureMode === 'rtsp' ? captureFromRTSP(position) : captureImage(position)}
            className={`w-full px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center ${
              currentCapture === position
                ? 'bg-green-600 text-white'
                : 'bg-cyan-600 text-white hover:bg-cyan-700'
            }`}
            disabled={captureMode === 'webcam' ? !cameraStarted : (captureMode === 'rtsp' ? !selectedStream : false)}
          >
            <span className="material-icons-round text-sm mr-1">camera_alt</span>
            {currentCapture === position ? 'Captured!' : `Capture ${label}`}
          </button>
          {imageFiles[position] && (
            <div className="mt-3">
              <div className="flex items-center mb-2">
                <span className="material-icons-round text-sm text-green-600 mr-1">check_circle</span>
                <span className="text-xs text-green-600">Image Captured</span>
              </div>
              <div className="w-full border-2 border-green-300 rounded-lg overflow-hidden bg-gray-50">
                <img 
                  src={imagePreviewUrls[position]} 
                  alt={`${label} capture`}
                  className="w-full h-40 object-cover"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Page Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="bg-gradient-to-r from-cyan-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
          <h1 className="text-3xl font-bold mb-2">New Student Registration</h1>
          <p className="text-cyan-50">Complete student enrollment with academic details and facial recognition</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Registration Form */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Student Information Card */}
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <span className="material-icons-round text-cyan-600 mr-2">person</span>
                  Student Information
                </h3>
                <span className="px-3 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full">Required</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Registration Number *
                  </label>
                  <input
                    name="student_id"
                    type="text"
                    value={formData.student_id}
                    onChange={handleInputChange}
                    required
                    placeholder="e.g., 202500568"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    First Name *
                  </label>
                  <input
                    name="first_name"
                    type="text"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter first name"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Middle Name
                  </label>
                  <input
                    name="middle_name"
                    type="text"
                    value={formData.middle_name}
                    onChange={handleInputChange}
                    placeholder="Optional"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Last Name *
                  </label>
                  <input
                    name="last_name"
                    type="text"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    required
                    placeholder="Enter last name"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Department *
                  </label>
                  <select
                    name="department"
                    value={formData.department}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    {departmentsList.map(dept => (
                      <option key={dept.id} value={dept.id}>{dept.name}</option>
                    ))}
                  </select>
                  {formData.department === 'OTHER' && (
                    <input
                      type="text"
                      name="custom_department"
                      placeholder="Enter department name"
                      value={formData.custom_department || ''}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent mt-2"
                    />
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Section
                  </label>
                  <select
                    name="section"
                    value={formData.section}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    {sections.map(section => (
                      <option key={section.value} value={section.value}>{section.label}</option>
                    ))}
                  </select>
                  {formData.section === 'OTHER' && (
                    <input
                      type="text"
                      name="custom_section"
                      placeholder="Enter section"
                      value={formData.custom_section || ''}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent mt-2"
                    />
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Semester *
                  </label>
                  <select
                    name="semester"
                    value={formData.semester}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    {semesters.map(sem => (
                      <option key={sem.value} value={sem.value}>{sem.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Initial Password *
                  </label>
                  <input
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                    placeholder="Set initial password"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            {/* Status Message */}
            {registrationStatus && (
              <div className={`rounded-lg p-4 ${
                registrationStatus.type === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : 'bg-red-50 border border-red-200 text-red-800'
              }`}>
                <div className="flex items-center">
                  <span className="material-icons-round mr-2">
                    {registrationStatus.type === 'success' ? 'check_circle' : 'error'}
                  </span>
                  {registrationStatus.message}
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <span className="animate-spin material-icons-round mr-2">hourglass_empty</span>
                  Registering Student...
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <span className="material-icons-round mr-2">check_circle</span>
                  Complete Registration
                </span>
              )}
            </button>
          </form>
        </div>

        {/* Enrollment Panel */}
        <div className="space-y-6">
          {/* Verify Student Card */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center mb-4">
              <span className="material-icons-round text-cyan-600 mr-2">verified_user</span>
              Verify Student
            </h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Enter registration number"
                value={enrollRegNo}
                onChange={(e) => setEnrollRegNo(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
              <button 
                type="button" 
                onClick={verifyStudent}
                className="w-full px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
              >
                <span className="material-icons-round text-sm mr-1">search</span>
                Verify
              </button>
              
              {/* Enrollment Status Message */}
              {enrollmentStatus && (
                <div className={`rounded-lg p-3 ${
                  enrollmentStatus.type === 'success'
                    ? 'bg-green-50 border border-green-200 text-green-800'
                    : 'bg-red-50 border border-red-200 text-red-800'
                }`}>
                  <div className="flex items-center text-sm">
                    <span className="material-icons-round text-sm mr-2">
                      {enrollmentStatus.type === 'success' ? 'check_circle' : 'error'}
                    </span>
                    {enrollmentStatus.message}
                  </div>
                </div>
              )}
              
              {verifiedStudent && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="font-semibold text-green-900">{verifiedStudent.first_name} {verifiedStudent.last_name}</div>
                  <div className="text-sm text-green-700">Reg No: {verifiedStudent.reg_no || enrollRegNo}</div>
                </div>
              )}
            </div>
          </div>

          {/* Capture Mode Card */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center mb-4">
              <span className="material-icons-round text-cyan-600 mr-2">camera_alt</span>
              Image Capture Method
            </h3>
            <div className="grid grid-cols-3 gap-2 mb-4">
              <button
                type="button"
                onClick={() => handleCaptureModeChange('upload')}
                className={`px-3 py-3 rounded-lg font-medium transition-all text-sm ${
                  captureMode === 'upload'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="material-icons-round text-sm block mb-1">upload_file</span>
                Upload
              </button>
              <button
                type="button"
                onClick={() => handleCaptureModeChange('webcam')}
                className={`px-3 py-3 rounded-lg font-medium transition-all text-sm ${
                  captureMode === 'webcam'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="material-icons-round text-sm block mb-1">videocam</span>
                Webcam
              </button>
              <button
                type="button"
                onClick={() => handleCaptureModeChange('rtsp')}
                className={`px-3 py-3 rounded-lg font-medium transition-all text-sm ${
                  captureMode === 'rtsp'
                    ? 'bg-cyan-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="material-icons-round text-sm block mb-1">stream</span>
                RTSP
              </button>
            </div>

            {captureMode === 'webcam' && (
              <div className="border border-gray-300 rounded-lg overflow-hidden">
                <video 
                  ref={videoRef} 
                  autoPlay 
                  muted 
                  playsInline 
                  className="w-full h-auto"
                />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
              </div>
            )}

            {captureMode === 'rtsp' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select RTSP Stream
                  </label>
                  <select
                    value={selectedStream}
                    onChange={(e) => setSelectedStream(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    <option value="">Choose a stream...</option>
                    {streamsList.map(stream => (
                      <option key={stream} value={stream}>{stream}</option>
                    ))}
                  </select>
                </div>
                
                {selectedStream && (
                  <div className="border border-gray-300 rounded-lg overflow-hidden bg-gray-900 relative">
                    {previewLoading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75 z-10">
                        <div className="text-white text-sm">Loading stream...</div>
                      </div>
                    )}
                    {liveFrameUrl ? (
                      <img src={liveFrameUrl} alt="Live RTSP Feed" className="w-full h-auto" />
                    ) : (
                      <div className="flex items-center justify-center py-12 text-gray-400">
                        <span className="material-icons-round mr-2">videocam_off</span>
                        Waiting for stream...
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Image Capture Grid */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center mb-4">
              <span className="material-icons-round text-cyan-600 mr-2">photo_library</span>
              Capture Images
            </h3>
            <div className="space-y-3">
              <ImageCaptureField position="front" label="Front View" description="Straight face" />
              <ImageCaptureField position="left" label="Left Profile" description="Left side" />
              <ImageCaptureField position="right" label="Right Profile" description="Right side" />
              <ImageCaptureField position="angled_left" label="Angled Left" description="45° left" />
              <ImageCaptureField position="angled_right" label="Angled Right" description="45° right" />
            </div>
            <button
              type="button"
              onClick={submitEnrollment}
              disabled={enrollLoading}
              className="w-full mt-4 px-4 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {enrollLoading ? (
                <span className="flex items-center justify-center">
                  <span className="animate-spin material-icons-round mr-2">hourglass_empty</span>
                  Uploading...
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <span className="material-icons-round mr-2">cloud_upload</span>
                  Submit Enrollment
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Registration
