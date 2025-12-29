import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../store/authStore'
import { useSubjectsStore } from '../store/subjectsStore'
import { recognitionClient } from '../services/recognitionClient'
import { apiClient } from './apiClient'

const ClassAttendance = () => {
  const { user } = useAuthStore()
  const { 
    subjects, 
    fetchSubjects, 
    getSubjectsBySemester,
    loading: subjectsLoading 
  } = useSubjectsStore()
  
  const [attendanceData, setAttendanceData] = useState(null)
  const [isScanning, setIsScanning] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)
  const [currentMode, setCurrentMode] = useState('selection') // selection, face_recognition
  const [selectedSemester, setSelectedSemester] = useState('')
  const [selectedSubject, setSelectedSubject] = useState('')
  const [activeSession, setActiveSession] = useState(null)
  const [scanningStatus, setScanningStatus] = useState('')
  const [recentAttendance, setRecentAttendance] = useState([])
  
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

  // attendanceData will be populated from backend via apiClient.getAttendanceStats()

  useEffect(() => {
    // Load subjects (store) and real attendance stats from backend
    fetchSubjects()
    let mounted = true
    ;(async () => {
      try {
        // Initialize apiClient with a baseURL (use explicit global or window.location.origin)
        const base = (typeof window !== 'undefined' && window.__API_BASE__) ? window.__API_BASE__ : window.location.origin
        await apiClient.init({ api: { baseURL: base, defaultAdmin: { username: 'admin@local.test', password: 'Admin@123', role: 'admin' } } })

        const stats = await apiClient.getAttendanceStats('month').catch(() => null)
        if (!mounted) return
        if (stats) {
          // Map backend stats to the component shape used previously
          setAttendanceData({
            total: stats.total_students ?? 0,
            present: stats.present_today ?? 0,
            absent: stats.absent_today ?? 0,
            late: stats.late ?? 0,
            lowAttendance: stats.low_attendance ?? [],
            weeklyTrend: stats.weekly_trend ?? []
          })
        } else {
          setAttendanceData(null)
        }
      } catch (err) {
        console.error('Failed to load attendance stats', err)
      }
    })()
    return () => { mounted = false }
  }, [fetchSubjects])

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      stopCamera()
    }
  }, [])

  // Get filtered subjects based on selected semester
  const filteredSubjects = selectedSemester ? getSubjectsBySemester(selectedSemester) : []

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
    if (!selectedSemester || !selectedSubject) {
      setScanningStatus('❌ Please select both semester and subject')
      return
    }

    const subject = subjects.find(s => s.id === selectedSubject)
    if (!subject) {
      setScanningStatus('❌ Invalid subject selected')
      return
    }

    // Create active session
    const session = {
      semester: selectedSemester,
      subjectId: selectedSubject,
      subjectCode: subject.subjectCode,
      subjectName: subject.subjectName,
      teacherId: user?.id,
      timestamp: new Date().toISOString(),
      sessionToken: `ATTEND_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      startTime: new Date()
    }

    setActiveSession(session)
    setCurrentMode('face_recognition')
    setScanningStatus('👁️ Starting face recognition...')
    await startCamera()
  }

  // Start face recognition
  const startFaceRecognition = async () => {
    if (!activeSession) {
      setScanningStatus('❌ No active session. Please select semester and subject first.')
      return
    }

    setIsScanning(true)
    setScanningStatus('👁️ Scanning for faces...')
    
    try {
      // Simulate face recognition - replace with actual recognitionClient call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Mock recognition result
      const mockResult = {
        recognized: true,
        studentId: `STU${Math.floor(Math.random() * 1000)}`,
        studentName: `Student ${Math.floor(Math.random() * 100)}`,
        confidence: 0.92,
        regNo: `2024${Math.floor(Math.random() * 1000)}`
      }
      
      if (mockResult.recognized) {
        const attendanceRecord = {
          studentId: mockResult.studentId,
          studentName: mockResult.studentName,
          regNo: mockResult.regNo,
          subject: activeSession.subjectName,
          semester: activeSession.semester,
          timestamp: new Date().toLocaleTimeString(),
          confidence: mockResult.confidence
        }

        // Add to recent attendance
        setRecentAttendance(prev => [attendanceRecord, ...prev.slice(0, 9)]) // Keep last 10 records
        
        setScanningStatus(`✅ ${mockResult.studentName} (${mockResult.regNo}) - Attendance marked for ${activeSession.subjectName}`)
        
        // Here you would call API to mark attendance
        console.log(`Attendance marked:`, attendanceRecord)
      } else {
        setScanningStatus('❓ Unknown face detected - Student not enrolled in this semester')
      }
    } catch (error) {
      console.error('Recognition failed:', error)
      setScanningStatus('❌ Recognition failed. Please try again.')
    } finally {
      setIsScanning(false)
    }
  }

  // Stop attendance session
  const stopAttendanceSession = () => {
    stopCamera()
    setCurrentMode('selection')
    setSelectedSubject('')
    setActiveSession(null)
    setScanningStatus('')
    setIsScanning(false)
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
                  <option key={sem.value} value={sem.value}>
                    {sem.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="subject" className="form-label">
                <span className="label-icon">📖</span>
                Subject *
              </label>
              <select
                id="subject"
                value={selectedSubject}
                onChange={handleSubjectChange}
                disabled={!selectedSemester || subjectsLoading}
                className="form-select"
                required
              >
                <option value="">{subjectsLoading ? 'Loading subjects...' : 'Select Subject'}</option>
                {filteredSubjects.map(subject => (
                  <option key={subject.id} value={subject.id}>
                    {subject.subjectCode} - {subject.subjectName}
                  </option>
                ))}
              </select>
              {!selectedSemester && (
                <div className="hint-text">Please select a semester first</div>
              )}
              {selectedSemester && filteredSubjects.length === 0 && !subjectsLoading && (
                <div className="hint-text warning">No subjects available for this semester</div>
              )}
            </div>
          </div>

          <div className="form-actions">
            <button 
              onClick={startAttendanceSession}
              disabled={!selectedSemester || !selectedSubject || subjectsLoading}
              className="primary-button large"
            >
              🎬 Start Attendance Session
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        {selectedSemester && (
          <div className="quick-stats">
            <h3>📊 Semester {selectedSemester} Overview</h3>
            <div className="stats-cards">
              <div className="stat-card mini">
                <div className="stat-value">{filteredSubjects.length}</div>
                <div className="stat-label">Subjects</div>
              </div>
              <div className="stat-card mini">
                <div className="stat-value">~45</div>
                <div className="stat-label">Enrolled Students</div>
              </div>
              <div className="stat-card mini">
                <div className="stat-value">85%</div>
                <div className="stat-label">Avg Attendance</div>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Render Face Recognition
  const renderFaceRecognition = () => {
    const subject = subjects.find(s => s.id === activeSession?.subjectId)
    
    return (
      <div className="face-recognition">
        <div className="session-header">
          <h3>👁️ Face Recognition Attendance</h3>
          <div className="session-info">
            <p><strong>Semester:</strong> {activeSession?.semester}</p>
            <p><strong>Subject:</strong> {subject?.subjectCode} - {subject?.subjectName}</p>
            <p><strong>Started:</strong> {activeSession?.startTime?.toLocaleTimeString()}</p>
          </div>
        </div>

        <div className="recognition-container">
          <div className="camera-section">
            <div className="camera-feed">
              {cameraActive ? (
                <>
                  <video 
                    ref={videoRef} 
                    autoPlay 
                    muted 
                    playsInline
                    className="live-camera-feed"
                  />
                  <div className="scanning-overlay">
                    <span className="spinning">⏳</span>
                    <p>{scanningStatus}</p>
                  </div>
                </>
              ) : (
                <div className="camera-prompt">
                  <span className="camera-icon">📷</span>
                  <p>Camera ready for face recognition</p>
                </div>
              )}
            </div>
            
            <div className="recognition-actions">
              <button 
                onClick={startFaceRecognition}
                disabled={isScanning || !cameraActive}
                className={`primary-button ${isScanning ? 'loading' : ''}`}
              >
                {isScanning ? '🔍 Scanning...' : '👁️ Recognize Face'}
              </button>
              <button onClick={stopAttendanceSession} className="secondary-button">
                🏁 End Session
              </button>
            </div>
          </div>

          {/* Recent Attendance */}
          <div className="recent-attendance">
            <h4>✅ Recent Attendance</h4>
            {recentAttendance.length === 0 ? (
              <div className="empty-state">
                <p>No attendance records yet. Faces recognized will appear here.</p>
              </div>
            ) : (
              <div className="attendance-list compact">
                {recentAttendance.map((record, index) => (
                  <div key={index} className="attendance-item compact">
                    <div className="student-info">
                      <span className="status-icon">✅</span>
                      <div>
                        <strong>{record.studentName}</strong>
                        <div className="student-details">
                          {record.regNo} • {record.timestamp}
                        </div>
                      </div>
                    </div>
                    <div className="subject-tag">
                      {record.subject}
                    </div>
                  </div>
                ))}
              </div>
            )}
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

  const attendanceRate = Math.round((attendanceData.present / attendanceData.total) * 100)

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Subject Attendance</h1>
        <p>Take attendance by semester and subject using face recognition</p>
        <div className="page-credit">Made with ❤️ for 5G Lab by ArpanCodec</div>
      </div>

      {/* Main Attendance Interface */}
      <div className="attendance-interface">
        {currentMode === 'selection' && renderSelection()}
        {currentMode === 'face_recognition' && renderFaceRecognition()}
      </div>

      {/* Statistics Cards (shown only when no active session) */}
      {!activeSession && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-icon">👥</span>
                <span>Total Students</span>
              </div>
              <div className="stat-value">{attendanceData.total}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-icon present">✅</span>
                <span>Present Today</span>
              </div>
              <div className="stat-value">{attendanceData.present}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-header">
                <span className="stat-icon absent">❌</span>
                <span>Absent Today</span>
              </div>
              <div className="stat-value">{attendanceData.absent}</div>
            </div>
            
            <div className="stat-card">
              <div className="stat-header">
                <div className="attendance-rate">{attendanceRate}%</div>
                <span>Overall Rate</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${attendanceRate}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Low Attendance Alert */}
          {attendanceData.lowAttendance.length > 0 && (
            <div className="alert-section">
              <div className="alert-header">
                <span className="alert-icon">⚠️</span>
                <h3>Students Needing Attention</h3>
              </div>
              <div className="alert-list">
                {attendanceData.lowAttendance.map((student, index) => (
                  <span key={index} className="alert-item">{student}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  )
}

export default ClassAttendance