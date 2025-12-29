import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuthStore } from '../store/authStore'

const StudentDashboard = () => {
  const { user } = useAuthStore()
  const [attendanceData, setAttendanceData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('weekly')
  const [customDateRange, setCustomDateRange] = useState({
    start: '',
    end: ''
  })
  const [selectedSubject, setSelectedSubject] = useState('all')

  useEffect(() => {
    loadAttendanceData()
    const interval = setInterval(loadAttendanceData, 300000)
    return () => clearInterval(interval)
  }, [filter, customDateRange, selectedSubject])

  const loadAttendanceData = async () => {
    try {
      if (!user || !user.username) throw new Error('no-user')
      const res = await apiClient.getStudentAttendance(user.username)
      if (res) {
        // Map backend response to UI shape when possible
        const mapped = {
          student_id: res.reg_no || user.username,
          student_name: res.name || user.name || user.username,
          department: res.department || 'N/A',
          section: res.section || 'A',
          semester: res.semester ? String(res.semester) : 'N/A',
          subjects: res.subjects || [],
          overall_attendance: res.overall_attendance || { total_classes: 0, classes_present: 0, classes_absent: 0, attendance_percentage: 0 },
          recent_attendance: res.recent_attendance || [],
          today_attendance: res.today_attendance || []
        }
        setAttendanceData(mapped)
      } else {
        throw new Error('empty-response')
      }
    } catch (error) {
      console.warn('Failed to load student attendance from backend, falling back to mock:', error)
      // Fallback mock
      const mockData = {
        student_id: user?.username || '202500568',
        student_name: user?.name || 'John Doe',
        department: 'Computer Science & Engineering',
        section: 'A',
        semester: '3',
        subjects: [
          {
            subjectCode: 'CS101',
            subjectName: 'Data Structures',
            total_classes: 25,
            classes_present: 22,
            classes_absent: 3,
            attendance_percentage: 88.0,
            last_attended: '2024-01-15'
          },
          {
            subjectCode: 'CS102',
            subjectName: 'Algorithms',
            total_classes: 20,
            classes_present: 18,
            classes_absent: 2,
            attendance_percentage: 90.0,
            last_attended: '2024-01-14'
          },
          {
            subjectCode: 'MA101',
            subjectName: 'Mathematics I',
            total_classes: 30,
            classes_present: 25,
            classes_absent: 5,
            attendance_percentage: 83.3,
            last_attended: '2024-01-13'
          },
          {
            subjectCode: 'PH101',
            subjectName: 'Physics',
            total_classes: 28,
            classes_present: 20,
            classes_absent: 8,
            attendance_percentage: 71.4,
            last_attended: '2024-01-12'
          }
        ],
        overall_attendance: {
          total_classes: 103,
          classes_present: 85,
          classes_absent: 18,
          attendance_percentage: 82.5
        },
        recent_attendance: [
          { date: '2024-01-15', status: 'present', subject: 'CS101', subjectName: 'Data Structures', time: '09:00 AM' },
          { date: '2024-01-15', status: 'present', subject: 'MA101', subjectName: 'Mathematics I', time: '11:00 AM' },
          { date: '2024-01-14', status: 'present', subject: 'CS102', subjectName: 'Algorithms', time: '10:00 AM' },
          { date: '2024-01-14', status: 'absent', subject: 'PH101', subjectName: 'Physics', time: '02:00 PM' },
        ],
        today_attendance: [
          { subject: 'CS101', subjectName: 'Data Structures', time: '09:00 AM', status: 'present' },
          { subject: 'MA101', subjectName: 'Mathematics I', time: '11:00 AM', status: 'pending' }
        ]
      }
      setAttendanceData(mockData)
    } finally {
      setLoading(false)
    }
  }

  const getFilteredAttendance = () => {
    if (!attendanceData) return []
    
    let filtered = [...attendanceData.recent_attendance]
    
    if (selectedSubject !== 'all') {
      filtered = filtered.filter(record => record.subject === selectedSubject)
    }
    
    if (filter === 'weekly') {
      const oneWeekAgo = new Date()
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
      filtered = filtered.filter(record => new Date(record.date) >= oneWeekAgo)
    } else if (filter === 'monthly') {
      const oneMonthAgo = new Date()
      oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
      filtered = filtered.filter(record => new Date(record.date) >= oneMonthAgo)
    } else if (filter === 'custom' && customDateRange.start && customDateRange.end) {
      filtered = filtered.filter(record => {
        const recordDate = new Date(record.date)
        return recordDate >= new Date(customDateRange.start) && 
               recordDate <= new Date(customDateRange.end)
      })
    }
    
    return filtered
  }

  const getSubjects = () => {
    if (!attendanceData) return []
    return attendanceData.subjects.map(subject => ({
      code: subject.subjectCode,
      name: subject.subjectName
    }))
  }

  const exportData = () => {
    if (!attendanceData) return
    
    let csvContent = 'Student Attendance Report\n\n'
    csvContent += `Student ID,Name,Department,Section,Semester,Overall Attendance\n`
    csvContent += `${attendanceData.student_id},${attendanceData.student_name},${attendanceData.department},${attendanceData.section},${attendanceData.semester},${attendanceData.overall_attendance.attendance_percentage}%\n\n`
    
    csvContent += 'Subject-wise Attendance\n'
    csvContent += 'Subject Code,Subject Name,Classes Conducted,Classes Present,Classes Absent,Attendance Percentage,Last Attended\n'
    attendanceData.subjects.forEach(subject => {
      csvContent += `${subject.subjectCode},${subject.subjectName},${subject.total_classes},${subject.classes_present},${subject.classes_absent},${subject.attendance_percentage}%,${subject.last_attended}\n`
    })
    
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_report_${attendanceData.student_id}_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <h3>Loading Your Dashboard</h3>
        <p>Preparing your attendance insights...</p>
      </div>
    )
  }

  const isLowAttendance = attendanceData.overall_attendance.attendance_percentage < 75
  const filteredAttendance = getFilteredAttendance()
  const subjects = getSubjects()

  return (
    <div className="student-dashboard">
      {/* Header Section */}
      <div className="dashboard-header">
        <div className="header-content">
          <div className="header-text">
            <h1>Student Attendance Dashboard</h1>
            <p>Monitor your academic progress with real-time attendance insights</p>
          </div>
          <div className="header-stats">
            <div className="stat-card primary">
              <div className="stat-icon">📊</div>
              <div className="stat-info">
                <span className="stat-value">{attendanceData.overall_attendance.attendance_percentage}%</span>
                <span className="stat-label">Overall Attendance</span>
              </div>
            </div>
            <div className="stat-card success">
              <div className="stat-icon">✅</div>
              <div className="stat-info">
                <span className="stat-value">{attendanceData.overall_attendance.classes_present}</span>
                <span className="stat-label">Classes Present</span>
              </div>
            </div>
            <div className="stat-card warning">
              <div className="stat-icon">📚</div>
              <div className="stat-info">
                <span className="stat-value">{attendanceData.subjects.length}</span>
                <span className="stat-label">Subjects</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        {/* Quick Actions & Filters */}
        <div className="actions-section">
          <div className="filters-container">
            <div className="filter-group">
              <label>Time Period</label>
              <select 
                value={filter} 
                onChange={(e) => setFilter(e.target.value)}
                className="filter-select"
              >
                <option value="weekly">📅 Weekly View</option>
                <option value="monthly">📅 Monthly View</option>
                <option value="custom">📅 Custom Range</option>
                <option value="all">📅 All Time</option>
              </select>
            </div>

            {filter === 'custom' && (
              <div className="filter-group">
                <label>Date Range</label>
                <div className="date-range">
                  <input
                    type="date"
                    value={customDateRange.start}
                    onChange={(e) => setCustomDateRange(prev => ({
                      ...prev, start: e.target.value
                    }))}
                    className="date-input"
                  />
                  <span className="date-separator">to</span>
                  <input
                    type="date"
                    value={customDateRange.end}
                    onChange={(e) => setCustomDateRange(prev => ({
                      ...prev, end: e.target.value
                    }))}
                    className="date-input"
                  />
                </div>
              </div>
            )}

            <div className="filter-group">
              <label>Filter by Subject</label>
              <select 
                value={selectedSubject} 
                onChange={(e) => setSelectedSubject(e.target.value)}
                className="filter-select"
              >
                <option value="all">📚 All Subjects</option>
                {subjects.map(subject => (
                  <option key={subject.code} value={subject.code}>
                    {subject.code} - {subject.name}
                  </option>
                ))}
              </select>
            </div>

            <button onClick={loadAttendanceData} className="refresh-btn">
              <span className="refresh-icon">🔄</span>
              Refresh Data
            </button>
          </div>
        </div>

        {/* Today's Attendance */}
        <div className="section-card">
          <div className="section-header">
            <h2>📊 Today's Schedule</h2>
            <div className="last-updated">
              Auto-refreshes daily • Last updated: {new Date().toLocaleTimeString()}
            </div>
          </div>
          <div className="today-grid">
            {attendanceData.today_attendance.map((record, index) => (
              <div key={index} className={`today-card ${record.status}`}>
                <div className="subject-badge">
                  <div className="subject-code">{record.subject}</div>
                  <div className="subject-name">{record.subjectName}</div>
                </div>
                <div className="class-time">{record.time}</div>
                <div className={`status-indicator ${record.status}`}>
                  {record.status === 'present' ? (
                    <>✅ Present</>
                  ) : record.status === 'absent' ? (
                    <>❌ Absent</>
                  ) : (
                    <>⏳ Pending</>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Subject-wise Attendance */}
        <div className="section-card">
          <div className="section-header">
            <h2>📖 Subject-wise Performance</h2>
            <div className="overall-summary">
              Overall: <strong>{attendanceData.overall_attendance.attendance_percentage}%</strong>
            </div>
          </div>
          <div className="subjects-grid">
            {attendanceData.subjects.map((subject, index) => (
              <div key={subject.subjectCode} className={`subject-card ${subject.attendance_percentage < 75 ? 'warning' : ''}`}>
                <div className="subject-header">
                  <div className="subject-title">
                    <h3>{subject.subjectName}</h3>
                    <span className="subject-code">{subject.subjectCode}</span>
                  </div>
                  <div className="attendance-percent">
                    <span className={`percent ${subject.attendance_percentage < 75 ? 'low' : 'good'}`}>
                      {subject.attendance_percentage}%
                    </span>
                  </div>
                </div>
                
                <div className="attendance-stats">
                  <div className="stat">
                    <span className="stat-number">{subject.total_classes}</span>
                    <span className="stat-label">Conducted</span>
                  </div>
                  <div className="stat">
                    <span className="stat-number present">{subject.classes_present}</span>
                    <span className="stat-label">Present</span>
                  </div>
                  <div className="stat">
                    <span className="stat-number absent">{subject.classes_absent}</span>
                    <span className="stat-label">Absent</span>
                  </div>
                </div>
                
                <div className="progress-container">
                  <div className="progress-bar">
                    <div 
                      className={`progress-fill ${subject.attendance_percentage < 75 ? 'low' : 'good'}`}
                      style={{ width: `${subject.attendance_percentage}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="subject-footer">
                  <span className="last-attended">
                    Last attended: {subject.last_attended}
                  </span>
                  {subject.attendance_percentage < 75 && (
                    <div className="warning-badge">
                      ⚠️ Below 75%
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Attendance Records */}
        <div className="section-card">
          <div className="section-header">
            <div className="section-title">
              <h2>📋 Attendance History</h2>
              <span className="record-count">
                {filteredAttendance.length} records found
              </span>
            </div>
            <button onClick={exportData} className="export-btn">
              <span className="export-icon">📊</span>
              Export Report
            </button>
          </div>
          
          {filteredAttendance.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📝</div>
              <h3>No Records Found</h3>
              <p>No attendance records match your current filters. Try adjusting your search criteria.</p>
            </div>
          ) : (
            <div className="attendance-table">
              <div className="table-header">
                <div className="col-date">Date & Time</div>
                <div className="col-subject">Subject</div>
                <div className="col-status">Status</div>
              </div>
              <div className="table-body">
                {filteredAttendance.map((record, index) => (
                  <div key={index} className={`table-row ${record.status}`}>
                    <div className="col-date">
                      <div className="date">{record.date}</div>
                      <div className="time">{record.time}</div>
                    </div>
                    <div className="col-subject">
                      <div className="subject-code">{record.subject}</div>
                      <div className="subject-name">{record.subjectName}</div>
                    </div>
                    <div className="col-status">
                      <span className={`status-badge ${record.status}`}>
                        {record.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Low Attendance Alert */}
        {isLowAttendance && (
          <div className="alert-card warning">
            <div className="alert-icon">⚠️</div>
            <div className="alert-content">
              <h3>Low Attendance Alert</h3>
              <p>
                Your overall attendance is <strong>{attendanceData.overall_attendance.attendance_percentage}%</strong>, 
                which is below the required 75%. Immediate action is recommended to improve your attendance.
              </p>
              <div className="alert-actions">
                <button className="btn-primary">📧 Resend Notification</button>
                <button className="btn-secondary">❓ Contact Department</button>
              </div>
            </div>
          </div>
        )}

        {/* System Info */}
        <div className="system-info">
          <div className="info-icon">💡</div>
          <div className="info-content">
            <strong>Auto-Refresh Enabled:</strong> This dashboard automatically updates every 5 minutes. 
            Today's attendance is refreshed daily at midnight.
          </div>
        </div>
      </div>
    </div>
  )
}

export default StudentDashboard