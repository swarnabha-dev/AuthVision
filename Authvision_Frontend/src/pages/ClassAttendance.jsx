import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../store/authStore'
import { useSubjectsStore } from '../store/subjectsStore'
import { apiClient } from '../services/apiClient'
import StreamViewer from '../components/StreamViewer'
import '../styles/ui.css'
import { websocketClient } from '../services/websocketClient'

const ClassAttendance = () => {
  const { user } = useAuthStore()
  // Use selectors to avoid stale/undefined function references
  const subjects = useSubjectsStore(state => state.subjects)
  const fetchSubjects = useSubjectsStore(state => state.fetchSubjects)
  const getSubjectsBySemester = useSubjectsStore(state => state.getSubjectsBySemester)
  const subjectsLoading = useSubjectsStore(state => state.loading)
  
  const [attendanceData, setAttendanceData] = useState(null)
  const [isScanning, setIsScanning] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)
  const [currentMode, setCurrentMode] = useState('selection') // selection, face_recognition
  const [selectedSemester, setSelectedSemester] = useState('')
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedDepartment, setSelectedDepartment] = useState('')
  const [selectedStream, setSelectedStream] = useState('')
  const [activeSession, setActiveSession] = useState(null)
  const [scanningStatus, setScanningStatus] = useState('')
  const [recentAttendance, setRecentAttendance] = useState([])
  // Live recognition feed (real-time) - keeps events persistent in UI
  const [liveRecognition, setLiveRecognition] = useState([])
  const [departments, setDepartments] = useState([])
  const [streams, setStreams] = useState([])
  const [liveFrameSrc, setLiveFrameSrc] = useState(null)
  const [liveConnected, setLiveConnected] = useState(false)
  const liveObjectUrlRef = useRef(null)
  const liveTimeoutRef = useRef(null)
  const [attendanceConnected, setAttendanceConnected] = useState(false)
  const [streamSocketConnected, setStreamSocketConnected] = useState(false)
  
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [stream, setStream] = useState(null)

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

  useEffect(() => {
    // Load subjects and try to fetch attendance stats from backend, fallback to mock
    try {
      if (typeof fetchSubjects === 'function') {
        fetchSubjects()
      } else {
        console.warn('fetchSubjects not available on subjects store')
      }
    } catch (e) {
      console.warn('fetchSubjects invocation failed', e)
    }
    
    // Check for persisted session and offer resume option
    try {
      const savedSession = localStorage.getItem('active_attendance_session')
      if (savedSession) {
        const parsed = JSON.parse(savedSession)
        console.log('Found persisted session:', parsed)
        // Could auto-populate form fields or show a "Resume Session" button
        // For now, just log it - implement resume UI later if needed
      }
    } catch (e) {
      console.warn('Failed to load persisted session', e)
    }
    (async () => {
      try {
        const stats = await apiClient.getAttendanceStats('week')
        const recent = await apiClient.getRecentAttendance().catch(() => null)

        setAttendanceData({
          total: stats?.total_students ?? 0,
          present: stats?.present ?? 0,
          absent: stats?.absent ?? 0,
          late: stats?.late ?? 0,
          lowAttendance: Array.isArray(stats?.low_attendance) ? stats.low_attendance : [],
          weeklyTrend: Array.isArray(stats?.weekly_trend) ? stats.weekly_trend : [],
          raw: stats ?? null
        })

        if (Array.isArray(recent)) setRecentAttendance(recent.slice(0, 10))
      } catch (e) {
        console.warn('Failed to fetch attendance stats from backend:', e)
        setAttendanceData({ total: 0, present: 0, absent: 0, late: 0, lowAttendance: [], weeklyTrend: [] })
      }
    })()

    // Load departments and available RTSP streams
    ;(async () => {
      try {
        const depts = await apiClient.getDepartments().catch(() => [])
        setDepartments(Array.isArray(depts) ? depts : [])
      } catch (e) {
        console.warn('Failed to load departments', e)
      }

      try {
        const s = await apiClient.listStreams().catch(() => [])
        // streams are objects { name, url, running }
        setStreams(Array.isArray(s) ? s : [])
      } catch (e) {
        console.warn('Failed to load streams', e)
      }
    })()
  }, [fetchSubjects])

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      stopCamera()
      try { websocketClient.disconnect(); } catch (e) {}
      if (liveObjectUrlRef.current) {
        try { URL.revokeObjectURL(liveObjectUrlRef.current) } catch (e) {}
        liveObjectUrlRef.current = null
      }
    }
  }, [])

  // Get filtered subjects based on selected semester and department
  const filteredSubjects = subjects
    .filter(s => {
      if (selectedSemester && String(s.semester) !== String(selectedSemester)) return false
      if (selectedDepartment && (s.department || '').toString() !== selectedDepartment) return false
      return true
    })

  // Start camera for face recognition
  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 } 
      })
      setStream(mediaStream)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
      setCameraActive(true)
    } catch (error) {
      console.error('Camera access denied:', error)
      setScanningStatus('❌ Camera access denied. Please allow camera permissions.')
    }
  }

  // Stop camera
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setCameraActive(false)
  }

  // Handle semester change
  const handleSemesterChange = (e) => {
    setSelectedSemester(e.target.value)
    setSelectedSubject('') // Reset subject when semester changes
  }

  // Handle subject change
  const handleSubjectChange = (e) => {
    setSelectedSubject(e.target.value)
  }

  // Start attendance session
  const startAttendanceSession = async () => {
    console.log('startAttendanceSession invoked', { selectedDepartment, selectedSemester, selectedSubject, selectedStream })
    if (!selectedDepartment || !selectedSemester || !selectedSubject || !selectedStream) {
      setScanningStatus('❌ Please select Department, Semester, Subject and Stream')
      return
    }

    // Find subject by common identifiers; if not found, proceed with provided selectedSubject
    const subject = subjects.find(s => (
      String(s.id) === String(selectedSubject) ||
      String(s.code) === String(selectedSubject) ||
      String(s.subjectCode) === String(selectedSubject) ||
      String(s.subjectName) === String(selectedSubject) ||
      String(s.name) === String(selectedSubject)
    ))
    if (!subject) {
      console.warn('Selected subject not found in store, proceeding with provided identifier:', selectedSubject)
    }

    try {
      // Check backend for any active session to avoid 400 "Session already running"
      try {
        const status = await apiClient.getActiveSessions().catch(() => null)
        let running = false
        if (status) {
          if (typeof status === 'object') {
            running = Boolean(status.running || status.active || status.is_running || status.session || status.id)
            if (!running && Array.isArray(status) && status.length > 0) running = true
          }
        }
        if (running) {
          setScanningStatus('❌ A session is already running on the server. Stop it before starting a new one.')
          return
        }
      } catch (e) {
        // ignore status check errors and proceed to start; server will respond if session exists
        console.warn('Failed to query active session status', e)
      }
      const payload = {
        subject: selectedSubject,
        department: selectedDepartment,
        semester: selectedSemester,
        section: 'A',
        stream_name: selectedStream
      }
      console.log('Calling POST /attendance/start with payload:', payload)
      // Build FormData and call the API POST directly to ensure the request is sent
      const fd = new FormData()
      fd.append('subject', String(payload.subject))
      fd.append('department', String(payload.department))
      fd.append('semester', String(payload.semester))
      fd.append('section', String(payload.section))
      fd.append('stream_name', String(payload.stream_name))

      let created = null
      try {
        created = await apiClient.apiPostForm('/attendance/start', fd)
        console.log('/attendance/start response:', created)
      } catch (apiErr) {
        console.error('/attendance/start failed:', apiErr)
        // Interpret known backend message
        try {
          const msg = (apiErr?.message || '').toString()
          if (msg.includes('Session already running') || msg.includes('session already running')) {
            setScanningStatus('❌ Session already running on server. Stop that session first.')
            return
          }
        } catch (e) {}
        setScanningStatus('❌ Failed to create attendance session — see console')
        throw apiErr
      }

      const session = {
        sessionId: created?.session_id || null,
        sessionToken: created?.sessionToken || created?.token || created?.id || null,
        subjectId: selectedSubject,
        subjectName: subject.subjectName || subject.name || subject.title || String(selectedSubject),
        semester: selectedSemester,
        department: selectedDepartment,
        section: 'A',
        streamName: selectedStream,
        startTime: created?.start_time ? new Date(created.start_time) : (created?.startTime ? new Date(created.startTime) : new Date()),
        raw: created
      }

      setActiveSession(session)
      // Persist session to localStorage for resume capability
      try {
        localStorage.setItem('active_attendance_session', JSON.stringify({
          sessionId: session.sessionId,
          subjectId: selectedSubject,
          department: selectedDepartment,
          semester: selectedSemester,
          section: 'A',
          streamName: selectedStream,
          startTime: session.startTime.toISOString()
        }))
      } catch (e) {
        console.warn('Failed to persist session to localStorage', e)
      }
      // Clear local recent attendance (frontend-only) when a new session starts
      try { setRecentAttendance([]) } catch (e) { console.warn('Failed to clear recentAttendance', e) }
      setCurrentMode('face_recognition')
      setScanningStatus('👁️ Session started — connecting live feed...')

      try {
        // Ensure any previous sockets/listeners are cleared
        try { websocketClient.disconnect(); } catch (e) {}
        try { websocketClient.clearListeners('attendance'); websocketClient.clearListeners('binary'); websocketClient.clearListeners('message'); } catch (e) {}

        // Connect to attendance websocket for recognition/attendance events
        websocketClient.connectAttendanceLive()
        // Update UI when sockets connect
        websocketClient.on('connected', ({ key, connected }) => {
          try {
            if (key === 'attendance') {
              setAttendanceConnected(Boolean(connected))
              if (connected) setScanningStatus('👁️ Live recognition connected')
            }
            if (key === `stream:${selectedStream}`) {
              setStreamSocketConnected(Boolean(connected))
              setLiveConnected(Boolean(connected))
              if (connected) setScanningStatus('👁️ Live feed connected')
              try { if (liveTimeoutRef.current) { clearTimeout(liveTimeoutRef.current); liveTimeoutRef.current = null } } catch (e) {}
            }
          } catch (e) {
            console.warn('connected handler error', e)
          }
        })
        websocketClient.on('attendance', (payload) => {
          // payload may be { key, data } or raw
          const data = payload && payload.data ? payload.data : payload
          console.log('attendance websocket payload:', data)

          // Normalize timestamp
          let ts = data.timestamp || data.time || data.t || data.detected_at || null
          let displayTs = new Date().toLocaleTimeString()
          try {
            if (ts) {
              const parsed = new Date(ts)
              if (!isNaN(parsed.getTime())) displayTs = parsed.toLocaleString()
            }
          } catch (e) {}

          const info = extractStudentInfo(data)

          const record = {
            studentName: info.name || data.studentName || data.name || 'Unknown',
            regNo: info.reg || data.student_reg || data.reg || data.reg_no || '—',
            timestamp: displayTs,
            status: data.status || 'present',
            subject: data.subject || data.subject_code || ''
          }

          // Add to live feed (persist in UI). If same student recognized again, update timestamp and move to top.
          try {
            setLiveRecognition(prev => {
              // try to find existing by regNo (or name if reg missing)
              const keyMatch = record.regNo || record.studentName
              const idx = prev.findIndex(r => (r.regNo || r.studentName) === keyMatch)
              let next = [...prev]
              if (idx !== -1) {
                // update existing record timestamp and move to front
                const existing = { ...next[idx], timestamp: record.timestamp, status: record.status }
                next.splice(idx, 1)
                next.unshift(existing)
              } else {
                next.unshift({ ...record, _id: `${Date.now()}-${Math.random().toString(36).slice(2,8)}` })
              }
              // cap list size to reasonable number
              return next.slice(0, 50)
            })
          } catch (e) {
            console.warn('Failed to add live recognition', e)
          }

          // Also keep a short recent history if desired
          setRecentAttendance(prev => [record, ...prev].slice(0, 50))
          // ensure UI reflects incoming recognition events
          setScanningStatus('👁️ Live recognition running — events arriving')
        })

        // Also connect to stream websocket for live frames
        if (selectedStream) {
          websocketClient.connectStream(selectedStream)
          websocketClient.on('binary', (payload) => {
            // payload { key, data }
            try {
              const key = payload && payload.key ? payload.key : null
              if (key !== `stream:${selectedStream}`) return
              const blob = payload.data instanceof Blob ? payload.data : new Blob([payload.data])
              if (liveObjectUrlRef.current) {
                try { URL.revokeObjectURL(liveObjectUrlRef.current) } catch (e) {}
              }
              const url = URL.createObjectURL(blob)
              liveObjectUrlRef.current = url
              setLiveFrameSrc(url)
              setLiveConnected(true)
              setScanningStatus('👁️ Live feed connected')
              setStreamSocketConnected(true)
              try { if (liveTimeoutRef.current) { clearTimeout(liveTimeoutRef.current); liveTimeoutRef.current = null } } catch (e) {}
            } catch (e) {
              console.warn('Failed to render stream binary frame', e)
            }
          })
          websocketClient.on('message', (payload) => {
            const key = payload && payload.key ? payload.key : null
            const data = payload && payload.data ? payload.data : payload
            if (key !== `stream:${selectedStream}`) return
            if (data && data.frame_base64) {
              // accept base64 frame strings
              setLiveFrameSrc(data.frame_base64.startsWith('data:') ? data.frame_base64 : `data:image/jpeg;base64,${data.frame_base64}`)
              setLiveConnected(true)
              setStreamSocketConnected(true)
              try { if (liveTimeoutRef.current) { clearTimeout(liveTimeoutRef.current); liveTimeoutRef.current = null } } catch (e) {}
              setScanningStatus('👁️ Live feed connected')
            }
          })
          // fallback: if no frames arrive within 5s, show waiting status
          try { if (liveTimeoutRef.current) clearTimeout(liveTimeoutRef.current) } catch (e) {}
          liveTimeoutRef.current = setTimeout(() => {
            if (!liveConnected) setScanningStatus('⌛ Waiting for live frames...')
          }, 5000)
        }
      } catch (e) {
        console.warn('Failed to connect attendance websocket:', e)
      }

    } catch (e) {
      console.error('Failed to start attendance session:', e)
      setScanningStatus('❌ Failed to start attendance session. See console for details.')
    }
  }

  // Helper: extract name and reg no from various possible payload shapes
  const extractStudentInfo = (data) => {
    if (!data || typeof data !== 'object') return { name: null, reg: null };

    const tryKeys = (obj, keys) => {
      for (const k of keys) {
        if (obj[k] !== undefined && obj[k] !== null && String(obj[k]).trim() !== '') return obj[k];
      }
      return null;
    };

    // Top-level direct fields
    const name = tryKeys(data, ['student_name', 'studentName', 'name', 'full_name', 'fullname', 'display_name'])
      || (data.student && tryKeys(data.student, ['name', 'full_name', 'registration_name']))
      || (data.person && tryKeys(data.person, ['name']))
      || null;

    const reg = tryKeys(data, ['student_reg', 'reg', 'reg_no', 'registration_no', 'student_id', 'id'])
      || (data.student && tryKeys(data.student, ['reg', 'reg_no', 'registration_no', 'student_id']))
      || (data.person && tryKeys(data.person, ['reg_no', 'registration_no', 'id']))
      || null;

    return { name: name ? String(name) : null, reg: reg ? String(reg) : null };
  }

  // Start face recognition
  const startFaceRecognition = async () => {
    if (!activeSession) {
      setScanningStatus('❌ No active session. Please start an attendance session first.')
      return
    }

    // Recognition is driven by the backend model service and websocket events.
    // This button can be used to show a message or to trigger a manual one-off capture in future.
    setScanningStatus('👁️ Live recognition running — events appear in Recent Attendance')
  }

  // Preview selected stream via websocket (one-off preview)
  const previewStream = async () => {
    if (!selectedStream) return setScanningStatus('❌ Select a stream to preview')
    try {
      // clear any previous preview socket/listeners for this stream
      try { websocketClient.disconnect(`stream:${selectedStream}`) } catch (e) {}
      try { websocketClient.clearListeners('binary'); websocketClient.clearListeners('message'); } catch (e) {}
      websocketClient.connectStream(selectedStream)
      websocketClient.on('binary', (payload) => {
        try {
          const key = payload && payload.key ? payload.key : null
          if (key !== `stream:${selectedStream}`) return
          const blob = payload.data instanceof Blob ? payload.data : new Blob([payload.data])
          if (liveObjectUrlRef.current) {
            try { URL.revokeObjectURL(liveObjectUrlRef.current) } catch (e) {}
          }
          const url = URL.createObjectURL(blob)
          liveObjectUrlRef.current = url
          setLiveFrameSrc(url)
          setLiveConnected(true)
        } catch (e) {
          console.warn('Preview frame error', e)
        }
      })
      websocketClient.on('message', (payload) => {
        const key = payload && payload.key ? payload.key : null
        const data = payload && payload.data ? payload.data : payload
        if (key !== `stream:${selectedStream}`) return
        if (data && data.frame_base64) {
          setLiveFrameSrc(data.frame_base64.startsWith('data:') ? data.frame_base64 : `data:image/jpeg;base64,${data.frame_base64}`)
          setLiveConnected(true)
        }
      })
      setScanningStatus('🔌 Previewing stream...')
    } catch (e) {
      console.warn('Preview failed', e)
      setScanningStatus('❌ Preview failed')
    }
  }

  // Stop attendance session
  const stopAttendanceSession = async () => {
    try {
      console.log('Calling POST /attendance/stop')
      const resp = await apiClient.endAttendanceSession()
      console.log('/attendance/stop response:', resp)
    } catch (e) {
      console.warn('Failed to call endAttendanceSession:', e)
    }

    try {
      websocketClient.disconnect()
    } catch (e) {
      console.warn('Failed to disconnect websocket client', e)
    }

    // Clear persisted session from localStorage
    try {
      localStorage.removeItem('active_attendance_session')
    } catch (e) {
      console.warn('Failed to remove session from localStorage', e)
    }

    stopCamera()
    setCurrentMode('selection')
    setActiveSession(null)
    setScanningStatus('')
    setIsScanning(false)
    setLiveFrameSrc(null)
    setLiveConnected(false)
  }

  // Render Semester & Subject Selection
  const renderSelection = () => {
    return (
      <div className="attendance-selection">
        <h2>🎓 Take Subject Attendance</h2>
        <p>Select semester and subject to start face recognition attendance</p>
        
        <div className="selection-form">
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Department *</label>
              <select value={selectedDepartment} onChange={(e) => { setSelectedDepartment(e.target.value); setSelectedSubject('') }} className="form-select">
                <option value="">Select Department</option>
                {departments.map(d => {
                  const val = (typeof d === 'string') ? d : (d.id ?? d.name ?? JSON.stringify(d))
                  const label = (typeof d === 'string') ? d : (d.name ?? d.label ?? String(val))
                  return (
                    <option key={String(val)} value={String(val)}>{label}</option>
                  )
                })}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="semester" className="form-label">
                <span className="label-icon">📚</span>
                Semester *
              </label>
              <select
                id="semester"
                value={selectedSemester}
                onChange={handleSemesterChange}
                className="form-select"
                required
              >
                {semesters.map(sem => (
                  <option key={String(sem.value)} value={String(sem.value)}>
                    {sem.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="subject" className="form-label">
                <span className="label-icon">📖</span>
                Subject *
              </label>
              <select
                id="subject"
                value={selectedSubject}
                onChange={handleSubjectChange}
                disabled={!selectedSemester || !selectedDepartment || subjectsLoading}
                className="form-select"
                required
              >
                <option value="">{subjectsLoading ? 'Loading subjects...' : 'Select Subject'}</option>
                {filteredSubjects.map(subject => {
                  const id = subject?.id ?? subject?.code ?? JSON.stringify(subject)
                  const code = subject?.subjectCode ?? subject?.code ?? subject?.id ?? ''
                  const name = subject?.subjectName ?? subject?.name ?? subject?.title ?? ''
                  return (
                    <option key={String(id)} value={String(id)}>
                      {`${code}${code && name ? ' - ' : ''}${name}`}
                    </option>
                  )
                })}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Section</label>
              <select value={activeSession?.section || 'A'} onChange={(e) => {/* no-op for now */}} className="form-select">
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Stream</label>
              <select value={selectedStream} onChange={(e) => setSelectedStream(e.target.value)} className="form-select">
                <option value="">Select Stream</option>
                {streams.map(s => {
                  const name = (typeof s === 'string') ? s : (s.name ?? s.id ?? JSON.stringify(s))
                  return (<option key={String(name)} value={String(name)}>{String(name)}</option>)
                })}
              </select>
              <div className="preview-controls">
                <button className="btn btn-ghost" onClick={previewStream} disabled={!selectedStream}><span className="icon icon-camera" /> Preview</button>
                <span className="preview-status">{liveConnected ? 'Preview connected' : 'Preview not connected'}</span>
              </div>
              {liveFrameSrc && (
                <div style={{ marginTop: 8 }}>
                  <div className="stream-thumb">
                    <img src={liveFrameSrc} alt="Live Preview" />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="form-actions">
            <button 
              onClick={startAttendanceSession}
              disabled={!selectedDepartment || !selectedSemester || !selectedSubject || !selectedStream || subjectsLoading}
              className="primary-button large"
            >
              🎬 Start Attendance Session
            </button>
          </div>
        </div>

        {/* Quick Stats removed as requested */}
      </div>
    )
  }

  // Render Face Recognition
  const renderFaceRecognition = () => {
    const subject = subjects.find(s => s.id === activeSession?.subjectId)
    const displaySubjectCode = subject?.subjectCode || subject?.code || activeSession?.subjectName || ''
    const displaySubjectName = subject?.subjectName || subject?.name || activeSession?.subjectName || '-'
    
    return (
      <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden">
        <div className="h-1.5 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
        
        {/* Session Header with Info and Stop Button */}
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-cyan-50 text-cyan-600 shadow-sm border border-cyan-100">
                <span className="material-icons-round text-2xl">face_retouching_natural</span>
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-800">Live Face Recognition Attendance</h3>
                <p className="text-sm text-slate-400 mt-0.5">Real-time student identification and attendance marking</p>
              </div>
            </div>
          </div>
          
          {/* Session Info and Stop Button */}
          <div className="mt-6 flex items-start justify-between gap-6">
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 flex-1">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Session ID</p>
                <p className="text-lg font-bold text-slate-800">{activeSession?.sessionId || 'N/A'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Semester</p>
                <p className="text-lg font-bold text-slate-800">{activeSession?.semester}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Subject</p>
                <p className="text-lg font-bold text-slate-800">{displaySubjectCode}{displaySubjectCode && displaySubjectName ? ' - ' : ''}{displaySubjectName}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Started</p>
                <p className="text-lg font-bold text-slate-800">{activeSession?.startTime?.toLocaleTimeString()}</p>
              </div>
            </div>
            
            {/* Stop Button */}
            <button onClick={stopAttendanceSession} className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2">
              <span className="material-icons-round">stop_circle</span>
              Stop Session
            </button>
          </div>
        </div>

        {/* Main Content: Live Feed and Recognition Results */}
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Feed Section - Takes 2 columns (major area) */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <span className="material-icons-round text-cyan-600">videocam</span>
                <h4 className="text-lg font-bold text-slate-800">Live Camera Feed</h4>
                {(attendanceConnected && (liveConnected || streamSocketConnected)) && (
                  <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 rounded-lg">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Live
                  </span>
                )}
              </div>
              
              <div className="bg-slate-900 rounded-xl overflow-hidden shadow-lg border-2 border-slate-700" style={{ aspectRatio: '16/9' }}>
                {activeSession ? (
                  (() => {
                    const streamObj = streams.find(s => s.name === selectedStream) || streams.find(s => s.name === activeSession?.raw?.stream_name)
                    const url = streamObj?.url || ''
                    const isSafeStreamUrl = url && (String(url).startsWith('http') || String(url).startsWith('data:') || String(url).startsWith('blob:'))
                    return (
                      <>
                        {isSafeStreamUrl ? (
                          <div className="w-full h-full">
                            <StreamViewer streamUrl={url} streamName={streamObj?.name || selectedStream || activeSession?.raw?.stream_name} autoStart={true} showControls={false} onDetection={(d) => { }} />
                          </div>
                        ) : (
                          <>
                            {liveFrameSrc ? (
                              <img src={liveFrameSrc} alt="Live frame" className="w-full h-full object-contain" />
                            ) : (
                              <div className="flex flex-col items-center justify-center h-full text-slate-400 p-8">
                                <span className="material-icons-round text-6xl mb-4 text-slate-600">videocam_off</span>
                                <p className="text-lg font-semibold text-slate-300">RTSP Stream</p>
                                <p className="text-sm text-center mt-2 max-w-md">Browser cannot load RTSP directly — click "Preview Stream" or ensure backend provides an HTTP/MJPEG endpoint.</p>
                              </div>
                            )}
                          </>
                        )}
                      </>
                    )
                  })()
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 p-8">
                    <span className="material-icons-round text-6xl mb-4 text-slate-600">camera_alt</span>
                    <p className="text-lg font-semibold text-slate-300">No Active Session</p>
                    <p className="text-sm text-center mt-2">Start a session to view live RTSP feed and recognition results</p>
                  </div>
                )}
              </div>
              
              {/* Status Panel */}
              {!(attendanceConnected && (liveConnected || streamSocketConnected)) && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
                  <span className="material-icons-round text-amber-600 animate-spin">refresh</span>
                  <p className="text-sm font-semibold text-amber-800">{scanningStatus || 'Connecting...'}</p>
                </div>
              )}
            </div>

            {/* Recognition Results Section - Takes 1 column */}
            <div className="lg:col-span-1">
              <div className="flex items-center gap-3 mb-4">
                <span className="material-icons-round text-emerald-600">person_search</span>
                <h4 className="text-lg font-bold text-slate-800">Live Recognition</h4>
              </div>
              
              <div className="bg-slate-50 rounded-xl border border-slate-200 overflow-hidden shadow-sm" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                {liveRecognition.length === 0 ? (
                  <div className="p-8 text-center">
                    <span className="material-icons-round text-5xl text-slate-300 mb-3">person_off</span>
                    <p className="text-sm text-slate-500">No live recognitions yet</p>
                    <p className="text-xs text-slate-400 mt-1">Faces recognized will appear here in realtime</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-200">
                    {liveRecognition.map((record) => (
                      <div key={record._id} className="p-4 hover:bg-white transition-colors">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3 flex-1">
                            <span className="text-2xl mt-0.5">{getStatusIcon(record.status)}</span>
                            <div className="flex-1 min-w-0">
                              <p className="font-bold text-slate-800 truncate">{record.studentName}</p>
                              <p className="text-xs text-slate-500 mt-0.5">{record.regNo}</p>
                              <p className="text-xs text-cyan-600 font-semibold mt-1">{record.timestamp}</p>
                            </div>
                          </div>
                          <span className="text-xs bg-cyan-100 text-cyan-700 px-2 py-1 rounded-md font-medium whitespace-nowrap">
                            {record.subject}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'present': return '✅'
      case 'absent': return '❌'
      case 'late': return '⏰'
      default: return '👤'
    }
  }

  if (!attendanceData) {
    return <div className="loading">Loading attendance system...</div>
  }

  return (
    <div className="min-h-screen bg-background-light text-slate-600">
      <div className="p-8 lg:p-12">
        <header className="mb-10">
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mb-3">Subject Attendance</h1>
          <p className="text-lg text-slate-500 max-w-3xl leading-relaxed font-light">Take attendance by semester and subject using advanced face recognition technology.
            <span className="block mt-1 text-sm text-slate-400 font-medium">Made with <span className="text-rose-500 animate-pulse">❤</span> for 5G Lab by ArpanCodec</span>
          </p>
        </header>

        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden relative">
          <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 via-cyan-400 to-teal-400" />
          <div className="p-8 lg:p-12 relative z-10">
            <div className="flex items-center gap-4 mb-8 pb-6 border-b border-slate-100">
              <div className="p-3 rounded-xl bg-cyan-50 text-cyan-600 shadow-sm border border-cyan-100">
                <span className="material-icons-round text-2xl">school</span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-800">Session Configuration</h2>
                <p className="text-sm text-slate-400 mt-0.5">Configure the class details to start monitoring</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
              <div className="space-y-2 group">
                <label className="block text-sm font-semibold text-slate-700">Department <span className="text-cyan-500">*</span></label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-icons-round text-slate-400 text-lg">business</span>
                  </span>
                  <select value={selectedDepartment} onChange={(e) => { setSelectedDepartment(e.target.value); setSelectedSubject('') }} className="block w-full pl-10 pr-10 py-3 text-base border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white text-slate-700 transition-all shadow-sm hover:border-slate-300 cursor-pointer">
                    <option value="">Select Department</option>
                    {departments.map(d => {
                      const val = (typeof d === 'string') ? d : (d.id ?? d.name ?? JSON.stringify(d))
                      const label = (typeof d === 'string') ? d : (d.name ?? d.label ?? String(val))
                      return (<option key={String(val)} value={String(val)}>{label}</option>)
                    })}
                  </select>
                </div>
              </div>

              <div className="space-y-2 group">
                <label className="block text-sm font-semibold text-slate-700 flex items-center gap-2"><span className="material-icons-round text-xs text-rose-400">layers</span> Semester <span className="text-cyan-500">*</span></label>
                <div className="relative">
                  <select className="block w-full px-4 py-3 text-base border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white text-slate-700 transition-all shadow-sm hover:border-slate-300 cursor-pointer appearance-none" value={selectedSemester} onChange={handleSemesterChange}>
                    {semesters.map(sem => (<option key={String(sem.value)} value={String(sem.value)}>{sem.label}</option>))}
                  </select>
                </div>
              </div>

              <div className="space-y-2 group md:col-span-1">
                <label className="block text-sm font-semibold text-slate-700 flex items-center gap-2"><span className="material-icons-round text-xs text-blue-400">menu_book</span> Subject <span className="text-cyan-500">*</span></label>
                <div className="relative">
                  <select className="block w-full px-4 py-3 text-base border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white text-slate-700 transition-all shadow-sm hover:border-slate-300 cursor-pointer appearance-none" value={selectedSubject} onChange={handleSubjectChange} disabled={!selectedSemester || !selectedDepartment || subjectsLoading}>
                    <option value="">{subjectsLoading ? 'Loading subjects...' : 'Select Subject'}</option>
                    {filteredSubjects.map(subject => {
                      const id = subject?.id ?? subject?.code ?? JSON.stringify(subject)
                      const code = subject?.subjectCode ?? subject?.code ?? subject?.id ?? ''
                      const name = subject?.subjectName ?? subject?.name ?? subject?.title ?? ''
                      return (<option key={String(id)} value={String(id)}>{`${code}${code && name ? ' - ' : ''}${name}`}</option>)
                    })}
                  </select>
                </div>
              </div>

              <div className="space-y-2 group md:col-span-1">
                <label className="block text-sm font-semibold text-slate-700">Section</label>
                <div className="relative">
                  <select className="block w-full px-4 py-3 text-base border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white text-slate-700 transition-all shadow-sm hover:border-slate-300 cursor-pointer appearance-none" value={activeSession?.section || 'A'} onChange={(e) => {/* no-op for now */}}>
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2 group md:col-span-2">
                <label className="block text-sm font-semibold text-slate-700">Stream Source ID</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="material-icons-round text-slate-400 text-lg">settings_input_hdmi</span>
                  </span>
                  <select className="block w-full pl-10 pr-10 py-3 text-base border-slate-200 rounded-xl focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white text-slate-700 transition-all shadow-sm hover:border-slate-300 cursor-pointer appearance-none" value={selectedStream} onChange={(e) => setSelectedStream(e.target.value)}>
                    <option value="">Select Stream</option>
                    {streams.map(s => { const name = (typeof s === 'string') ? s : (s.name ?? s.id ?? JSON.stringify(s)); return (<option key={String(name)} value={String(name)}>{String(name)}</option>) })}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 mt-8 pt-6 border-t border-slate-100">
              <button onClick={previewStream} className="relative overflow-hidden group bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold py-2.5 px-6 rounded-xl transition-all flex items-center gap-2 shadow-sm hover:shadow-md">
                <span className="material-icons-round text-xl group-hover:scale-110 transition-transform text-slate-500 group-hover:text-slate-700">camera_enhance</span>
                <span>Preview</span>
              </button>
              <span className="text-sm text-emerald-600 font-semibold flex items-center gap-2 px-3 py-1 bg-emerald-50 rounded-lg animate-pulse">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Preview {liveConnected ? 'connected' : 'not connected'}
              </span>
              <button onClick={startAttendanceSession} className="ml-auto bg-accent hover:bg-cyan-400 text-slate-900 font-bold py-3 px-8 rounded-xl transition-all shadow-glow hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2">
                <span className="material-icons-round">face_retouching_natural</span>
                Start Recognition
              </button>
            </div>
          </div>
          <div className="absolute bottom-0 right-0 w-80 h-80 bg-cyan-50/50 rounded-full blur-3xl -z-0 pointer-events-none translate-x-1/3 translate-y-1/3" />
          <div className="absolute top-0 left-0 w-64 h-64 bg-blue-50/50 rounded-full blur-3xl -z-0 pointer-events-none -translate-x-1/3 -translate-y-1/3" />
        </div>

        {/* Face recognition view */}
        {currentMode === 'face_recognition' && (
          <div className="mt-8">
            {renderFaceRecognition()}
          </div>
        )}

        <canvas ref={canvasRef} style={{ display: 'none' }} />
      </div>
    </div>
  )
}

export default ClassAttendance