import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuthStore } from '../store/authStore'

const Reports = () => {
  const { user } = useAuthStore()
  const [emailSettings, setEmailSettings] = useState({
    trigger_type: 'low_attendance',
    threshold: 75,
    timeframe: 'weekly',
    custom_date: '',
    include_report: true,
    custom_message: ''
  })
  const [reportSettings, setReportSettings] = useState({
    report_type: 'attendance_summary',
    timeframe: 'weekly',
    start_date: '',
    end_date: '',
    selected_month: new Date().toISOString().slice(0, 7), // YYYY-MM
    selected_year: new Date().getFullYear().toString()
  })
  const [sendingEmails, setSendingEmails] = useState(false)
  const [emailStatus, setEmailStatus] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredStudents, setFilteredStudents] = useState([])
  const [loading, setLoading] = useState(false)
  const [reportData, setReportData] = useState(null)
  const [error, setError] = useState(null)
  const [studentsList, setStudentsList] = useState([])
  const [subjectIdentifier, setSubjectIdentifier] = useState('')
  const [studentRegNo, setStudentRegNo] = useState('')

  // keep key fields in reportSettings for compatibility
  useEffect(() => {
    setReportSettings(prev => ({ ...prev, subject_identifier: subjectIdentifier }))
  }, [subjectIdentifier])

  useEffect(() => {
    setReportSettings(prev => ({ ...prev, student_reg_no: studentRegNo }))
  }, [studentRegNo])

  // Initialize dates when component mounts
  useEffect(() => {
    initializeDates()
  }, [])

  useEffect(() => {
    filterStudents()
  }, [studentsList, searchTerm])

  // Initialize date fields with proper values
  const initializeDates = () => {
    const today = new Date()
    const startOfWeek = getStartOfWeek(today)
    const endOfWeek = getEndOfWeek(today)
    
    setReportSettings(prev => ({
      ...prev,
      start_date: startOfWeek.toISOString().split('T')[0],
      end_date: endOfWeek.toISOString().split('T')[0]
    }))
    
    setEmailSettings(prev => ({
      ...prev,
      custom_date: today.toISOString().split('T')[0]
    }))
  }

  const getStartOfWeek = (date) => {
    const d = new Date(date)
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1) // Adjust when Sunday is first day
    return new Date(d.setDate(diff))
  }

  const getEndOfWeek = (date) => {
    const start = getStartOfWeek(date)
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    return end
  }

  // Note: backend does not expose a dedicated "low attendance" list endpoint in `reports.py`.
  // We use available endpoints: /reports/stats, /reports/subject/{id}/summary and /reports/student/{reg_no}/attendance

  const filterStudents = () => {
    const filtered = (studentsList || []).filter(student =>
      searchTerm === '' ||
      (String(student.student_id || student.reg_no || '').toLowerCase().includes(searchTerm.toLowerCase())) ||
      (String(student.full_name || student.name || '').toLowerCase().includes(searchTerm.toLowerCase())) ||
      (String(student.department || '').toLowerCase().includes(searchTerm.toLowerCase()))
    )
    setFilteredStudents(filtered)
  }

  const fetchReport = async () => {
    setReportData(null)
    setError(null)
    setLoading(true)
    try {
      if (reportSettings.report_type === 'attendance_summary') {
        const s = await apiClient.getAttendanceStats(reportSettings.timeframe)
        setReportData({ type: 'attendance_summary', stats: s })
      } else if (reportSettings.report_type === 'low_attendance') {
        if (apiClient.getLowAttendanceStudents) {
          const list = await apiClient.getLowAttendanceStudents(reportSettings.threshold || 75)
          setStudentsList(Array.isArray(list) ? list : [])
        } else {
          setStudentsList([])
        }
        setReportData({ type: 'low_attendance' })
      } else if (reportSettings.report_type === 'subject_summary') {
        const id = subjectIdentifier || reportSettings.subject_identifier
        if (!id) throw new Error('Please enter a subject identifier')
        const summary = await apiClient.getSubjectSummary(id)
        setReportData({ type: 'subject_summary', summary })
        setStudentsList(Array.isArray(summary?.student_stats) ? summary.student_stats : [])
      } else if (reportSettings.report_type === 'student_report') {
        const reg = studentRegNo || reportSettings.student_reg_no
        if (!reg) throw new Error('Please enter a student registration number')
        const attendance = await apiClient.getStudentAttendance(reg)
        setReportData({ type: 'student_report', attendance })
      } else {
        setReportData({ type: reportSettings.report_type, data: null })
      }
    } catch (e) {
      setError('Failed to fetch report')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const downloadBlobFromEndpoint = async (url, filename) => {
    try {
      await apiClient._ensureConfig()
      const base = apiClient.baseURL || ''
      const full = `${base}${url}`
      const headers = {}
      if (apiClient.accessToken) headers['Authorization'] = `Bearer ${apiClient.accessToken}`
      const resp = await fetch(full, { headers })
      if (!resp.ok) throw new Error('Download failed')
      const blob = await resp.blob()
      const href = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = href
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(href)
    } catch (e) {
      console.error('Download error', e)
      alert('Download failed')
    }
  }

  const downloadSubjectCsv = async (id) => {
    const subjectId = id || subjectIdentifier || reportSettings.subject_identifier
    if (!subjectId) return alert('Enter subject identifier')
    await downloadBlobFromEndpoint(`/reports/subject/${encodeURIComponent(subjectId)}/download/csv`, `subject_${subjectId}_summary.csv`)
  }

  const downloadSubjectPdf = async (id) => {
    const subjectId = id || subjectIdentifier || reportSettings.subject_identifier
    if (!subjectId) return alert('Enter subject identifier')
    await downloadBlobFromEndpoint(`/reports/subject/${encodeURIComponent(subjectId)}/download/pdf`, `subject_${subjectId}_summary.pdf`)
  }

  const downloadStudentCsv = async (reg) => {
    const r = reg || studentRegNo || reportSettings.student_reg_no
    if (!r) return alert('Enter student registration number')
    await downloadBlobFromEndpoint(`/reports/student/${encodeURIComponent(r)}/download/csv`, `student_${r}_attendance.csv`)
  }

  const downloadStudentPdf = async (reg) => {
    const r = reg || studentRegNo || reportSettings.student_reg_no
    if (!r) return alert('Enter student registration number')
    await downloadBlobFromEndpoint(`/reports/student/${encodeURIComponent(r)}/download/pdf`, `student_${r}_attendance.pdf`)
  }

  const handleEmailTrigger = async () => {
    setSendingEmails(true)
    setEmailStatus(null)

    try {
      let result
      
      switch(emailSettings.trigger_type) {
        case 'low_attendance':
          result = await apiClient.sendBulkLowAttendanceEmails(emailSettings.threshold)
          break
        case 'weekly':
          result = await apiClient.sendCustomEmail(
            'all',
            `Weekly Attendance Report - ${getCurrentWeekRange()}`,
            `Your weekly attendance report for ${getCurrentWeekRange()} is attached.`,
            emailSettings.include_report ? ['weekly_report'] : []
          )
          break
        case 'monthly':
          result = await apiClient.sendCustomEmail(
            'all',
            `Monthly Attendance Summary - ${reportSettings.selected_month}`,
            `Your monthly attendance summary for ${formatMonth(reportSettings.selected_month)} is attached.`,
            emailSettings.include_report ? ['monthly_report'] : []
          )
          break
        case 'custom':
          // Validate custom date
          if (!emailSettings.custom_date) {
            throw new Error('Please select a custom date')
          }
          result = await apiClient.sendCustomEmail(
            'all',
            `Custom Attendance Report - ${formatDateWithDay(emailSettings.custom_date)}`,
            `Your attendance report for ${formatDateWithDay(emailSettings.custom_date)} is attached.`,
            emailSettings.include_report ? ['custom_report'] : []
          )
          break
        default:
          break
      }

      setEmailStatus({
        type: 'success',
        message: `Emails sent successfully! ${result?.students_notified || 'Multiple'} students notified.`
      })
    } catch (error) {
      console.error('Email trigger failed:', error)
      setEmailStatus({
        type: 'error',
        message: error.message || 'Failed to send emails. Please try again.'
      })
    } finally {
      setSendingEmails(false)
    }
  }

  const sendIndividualEmail = async (student) => {
    try {
      // If backend has a notifications endpoint, `apiClient.sendLowAttendanceEmail` may work.
      if (apiClient.sendLowAttendanceEmail) {
        await apiClient.sendLowAttendanceEmail(student.student_id || student.reg_no, emailSettings.custom_message)
        setEmailStatus({ type: 'success', message: `Email sent to ${student.full_name || student.name}` })
      } else {
        setEmailStatus({ type: 'error', message: 'Email API not available on this backend' })
      }
    } catch (error) {
      setEmailStatus({ type: 'error', message: `Failed to send email to ${student.full_name || student.name}` })
    }
  }

  const exportReport = () => {
    // Validate date range for custom reports
    if (reportSettings.timeframe === 'custom') {
      if (!reportSettings.start_date || !reportSettings.end_date) {
        alert('Please select both start and end dates for custom reports')
        return
      }
      if (new Date(reportSettings.start_date) > new Date(reportSettings.end_date)) {
        alert('Start date cannot be after end date')
        return
      }
    }

    // Export currently filtered students as CSV (backend download endpoints may be added later)
    const timeframeInfo = getTimeframeInfo()
    const csvContent = `Attendance Report - ${timeframeInfo}\n\nStudent ID,Name,Department,Section,Semester,Attendance Percentage,Status\n${filteredStudents.map(student => 
      `${student.student_id || student.reg_no || ''},${student.full_name || student.name || ''},${student.department || ''},${student.section || ''},${student.semester || 'N/A'},${student.attendance_percentage || student.percentage || 0}%,${(student.attendance_percentage || student.percentage || 0) < 75 ? 'Low Attendance' : 'Good Attendance'}`
    ).join('\n')}`
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_report_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  // Enhanced date formatting with day names
  const formatDateWithDay = (dateString) => {
    if (!dateString) return 'Invalid Date'
    const date = new Date(dateString)
    return `${date.toISOString().slice(0, 10)} (${date.toLocaleDateString('en-US', { weekday: 'long' })})`
  }

  const getCurrentWeekRange = () => {
    const now = new Date()
    const startOfWeek = getStartOfWeek(now)
    const endOfWeek = getEndOfWeek(now)
    
    return `${formatDateWithDay(startOfWeek)} to ${formatDateWithDay(endOfWeek)}`
  }

  // Enhanced month formatting
  const formatMonth = (monthString) => {
    if (!monthString) return 'Invalid Month'
    const [year, month] = monthString.split('-')
    const date = new Date(year, month - 1)
    return date.toLocaleString('default', { month: 'long', year: 'numeric' })
  }

  // Enhanced timeframe info with better formatting
  const getTimeframeInfo = () => {
    switch(reportSettings.timeframe) {
      case 'weekly':
        return `Weekly Report - ${getCurrentWeekRange()}`
      case 'monthly':
        return `Monthly Report - ${formatMonth(reportSettings.selected_month)}`
      case 'custom':
        if (!reportSettings.start_date || !reportSettings.end_date) {
          return 'Custom Report - Please select date range'
        }
        return `Custom Report - ${formatDateWithDay(reportSettings.start_date)} to ${formatDateWithDay(reportSettings.end_date)}`
      default:
        return 'Attendance Report'
    }
  }

  // Get weekly dates with day names for display
  const getWeeklyDatesWithDays = () => {
    const dates = []
    const now = new Date()
    const startOfWeek = getStartOfWeek(now)
    
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek)
      date.setDate(startOfWeek.getDate() + i)
      dates.push({
        date: date.toISOString().slice(0, 10),
        day: date.toLocaleDateString('en-US', { weekday: 'long' }),
        fullDate: formatDateWithDay(date),
        isToday: date.toDateString() === new Date().toDateString()
      })
    }
    
    return dates
  }

  const getYears = () => {
    const currentYear = new Date().getFullYear()
    return Array.from({ length: 5 }, (_, i) => (currentYear - i).toString())
  }

  const getMonths = () => {
    return Array.from({ length: 12 }, (_, i) => {
      const month = i + 1
      return `${reportSettings.selected_year}-${month.toString().padStart(2, '0')}`
    })
  }

  // Handle date changes with validation
  const handleStartDateChange = (date) => {
    setReportSettings(prev => {
      const newSettings = { ...prev, start_date: date }
      // If start date is after end date, adjust end date
      if (date && prev.end_date && new Date(date) > new Date(prev.end_date)) {
        newSettings.end_date = date
      }
      return newSettings
    })
  }

  const handleEndDateChange = (date) => {
    setReportSettings(prev => {
      const newSettings = { ...prev, end_date: date }
      // If end date is before start date, adjust start date
      if (date && prev.start_date && new Date(date) < new Date(prev.start_date)) {
        newSettings.start_date = date
      }
      return newSettings
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Attendance Report</h1>
          <p className="text-sm text-gray-500">Generate reports and check attendance</p>
        </div>


        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-medium">Report Configuration</h3>
                  <p className="text-xs text-gray-500">Select report type and timeframe</p>
                </div>
                <div className="flex items-center space-x-2">
                  <button onClick={async ()=>{
                    if (reportSettings.report_type === 'subject_summary') return downloadSubjectCsv()
                    if (reportSettings.report_type === 'student_report') return downloadStudentCsv()
                    return exportReport()
                  }} title="Download CSV" className="inline-flex items-center px-3 py-1.5 bg-green-600 text-white rounded-md shadow">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v12m0 0l4-4m-4 4l-4-4" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    </svg>
                    CSV
                  </button>
                  <button onClick={async ()=>{
                    if (reportSettings.report_type === 'subject_summary') return downloadSubjectPdf()
                    if (reportSettings.report_type === 'student_report') return downloadStudentPdf()
                    alert('PDF export not available for this report type')
                  }} title="Download PDF" className="inline-flex items-center px-3 py-1.5 bg-red-600 text-white rounded-md shadow">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 17l5-5 5 5" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 12V3" />
                    </svg>
                    PDF
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Report Type</label>
                  <select value={reportSettings.report_type} onChange={(e)=>setReportSettings(prev=>({...prev, report_type:e.target.value}))} className="mt-1 block w-full rounded-md border-gray-200 shadow-sm">
                    <option value="attendance_summary">Attendance Summary</option>
                    <option value="low_attendance">Low Attendance</option>
                    
                    <option value="subject_summary">Subject Summary</option>
                    <option value="student_report">Student Report</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Timeframe</label>
                  <select value={reportSettings.timeframe} onChange={(e)=>setReportSettings(prev=>({...prev, timeframe:e.target.value}))} className="mt-1 block w-full rounded-md border-gray-200 shadow-sm">
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button onClick={fetchReport} className="w-full px-4 py-2 bg-green-600 text-white rounded-md">Generate</button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                {reportSettings.report_type === 'subject_summary' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Subject Identifier</label>
                    <input value={subjectIdentifier} onChange={(e)=>{ setSubjectIdentifier(e.target.value) }} placeholder="e.g. CS101" className="mt-1 block w-full rounded-md border-gray-200 shadow-sm p-2" />
                  </div>
                )}

                {reportSettings.report_type === 'student_report' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Student Reg. No.</label>
                    <input value={studentRegNo} onChange={(e)=>{ setStudentRegNo(e.target.value) }} placeholder="e.g. 2022CS001" className="mt-1 block w-full rounded-md border-gray-200 shadow-sm p-2" />
                  </div>
                )}
              </div>

              <div className="mt-6">
                <div className="text-sm text-gray-600">Report Period: <span className="font-medium text-gray-800">{getTimeframeInfo()}</span></div>
              </div>
            </div>

            {/* Results */}
            <div className="bg-white shadow rounded-lg p-6">
              <h4 className="text-md font-medium mb-4">Results</h4>
              {loading && <div className="text-sm text-gray-500">Loading...</div>}
              {error && <div className="text-sm text-red-600">{error}</div>}

              {!loading && reportData && reportData.type === 'attendance_summary' && (
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div className="p-4 bg-indigo-50 rounded-md">
                    <div className="text-xs text-gray-500">Total Students</div>
                    <div className="text-2xl font-bold">{reportData.stats?.students ?? 0}</div>
                  </div>
                  <div className="p-4 bg-amber-50 rounded-md">
                    <div className="text-xs text-gray-500">Total Faculty</div>
                    <div className="text-2xl font-bold">{reportData.stats?.faculty ?? 0}</div>
                  </div>
                  <div className="p-4 bg-green-50 rounded-md">
                    <div className="text-xs text-gray-500">Subjects</div>
                    <div className="text-2xl font-bold">{reportData.stats?.subjects ?? 0}</div>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-md">
                    <div className="text-xs text-gray-500">Active Classes</div>
                    <div className="text-2xl font-bold">{reportData.stats?.active_classes ?? 0}</div>
                  </div>
                </div>
              )}

              {!loading && reportData && reportData.type === 'low_attendance' && (
                <div>
                  <div className="text-sm text-gray-600 mb-3">Found {filteredStudents.length} students below threshold</div>
                  <div className="space-y-3">
                    {filteredStudents.map(s => (
                      <div key={s.student_id || s.reg_no} className="flex items-center justify-between p-3 border rounded-md">
                        <div>
                          <div className="font-medium">{s.full_name || s.name}</div>
                          <div className="text-xs text-gray-500">{s.student_id || s.reg_no} • {s.department} • Sem {s.semester || s.sem}</div>
                        </div>
                        <div className="text-sm font-semibold">{s.attendance_percentage ?? s.percentage}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!loading && reportData && reportData.type === 'subject_summary' && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm text-gray-600">Subject Summary - {reportData.summary?.subject?.code || reportData.summary?.subject?.name || subjectIdentifier}</div>
                    <div className="space-x-2">
                      <button onClick={()=>downloadSubjectCsv(reportData.summary?.subject?.code || reportData.summary?.subject?.name)} className="inline-flex items-center px-3 py-1 bg-green-600 text-white rounded-md">CSV</button>
                      <button onClick={()=>downloadSubjectPdf(reportData.summary?.subject?.code || reportData.summary?.subject?.name)} className="inline-flex items-center px-3 py-1 bg-red-600 text-white rounded-md">PDF</button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {filteredStudents.map(s => (
                      <div key={s.student_id || s.reg_no} className="flex items-center justify-between p-3 border rounded-md">
                        <div>
                          <div className="font-medium">{s.full_name || s.name}</div>
                          <div className="text-xs text-gray-500">{s.student_id || s.reg_no} • {s.department} • Sem {s.semester || s.sem}</div>
                        </div>
                        <div className="text-sm font-semibold">{s.attendance_percentage ?? s.percentage}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!loading && reportData && reportData.type === 'student_report' && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm text-gray-600">Student Report - {studentRegNo || reportSettings.student_reg_no}</div>
                    <div className="space-x-2">
                      <button onClick={()=>downloadStudentCsv(studentRegNo || reportSettings.student_reg_no)} className="inline-flex items-center px-3 py-1 bg-green-600 text-white rounded-md">CSV</button>
                      <button onClick={()=>downloadStudentPdf(studentRegNo || reportSettings.student_reg_no)} className="inline-flex items-center px-3 py-1 bg-red-600 text-white rounded-md">PDF</button>
                    </div>
                  </div>

                  <div className="bg-gray-50 p-4 rounded mb-4">
                    <div className="text-sm font-medium">{reportData.attendance?.student?.name || 'Student'}</div>
                    <div className="text-xs text-gray-500">Reg No: {reportData.attendance?.student?.reg_no || '-' } • Dept: {reportData.attendance?.student?.department || '-'} • Sem: {reportData.attendance?.student?.semester || '-' } • Section: {reportData.attendance?.student?.section || '-'}</div>
                    <div className="text-xs text-gray-400 mt-2">Generated: {reportData.attendance?.generated_at || '-'}</div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm text-left">
                      <thead>
                        <tr className="text-xs text-gray-500">
                          <th className="px-3 py-2">Subject Code</th>
                          <th className="px-3 py-2">Subject Name</th>
                          <th className="px-3 py-2">Present</th>
                          <th className="px-3 py-2">Total</th>
                          <th className="px-3 py-2">Percentage</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(reportData.attendance?.attendance || []).length === 0 ? (
                          <tr><td colSpan={5} className="px-3 py-4 text-gray-500">No attendance records available</td></tr>
                        ) : (
                          (reportData.attendance?.attendance || []).map((r) => (
                            <tr key={r.subject_code} className="border-t">
                              <td className="px-3 py-2">{r.subject_code}</td>
                              <td className="px-3 py-2">{r.subject_name}</td>
                              <td className="px-3 py-2">{r.present_classes}</td>
                              <td className="px-3 py-2">{r.total_classes}</td>
                              <td className="px-3 py-2 font-semibold">{r.percentage}%</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            {/* Email Trigger - Commented Out */}
            {/* <div className="bg-white shadow rounded-lg p-6">
              <h4 className="text-md font-medium mb-3">Email Trigger</h4>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-700">Trigger Type</label>
                  <select value={emailSettings.trigger_type} onChange={(e)=>setEmailSettings(prev=>({...prev, trigger_type:e.target.value}))} className="mt-1 block w-full rounded-md border-gray-200">
                    <option value="low_attendance">Low Attendance Alert</option>
                    <option value="weekly">Weekly Report</option>
                    <option value="monthly">Monthly Summary</option>
                    <option value="custom">Custom Email</option>
                  </select>
                </div>

                {emailSettings.trigger_type === 'low_attendance' && (
                  <div>
                    <label className="block text-sm text-gray-700">Threshold</label>
                    <select value={emailSettings.threshold} onChange={(e)=>setEmailSettings(prev=>({...prev, threshold:parseInt(e.target.value)}))} className="mt-1 block w-full rounded-md border-gray-200">
                      <option value={70}>Below 70%</option>
                      <option value={75}>Below 75%</option>
                      <option value={80}>Below 80%</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm text-gray-700">Message (optional)</label>
                  <textarea value={emailSettings.custom_message} onChange={(e)=>setEmailSettings(prev=>({...prev, custom_message:e.target.value}))} className="mt-1 block w-full rounded-md border-gray-200" rows={3} />
                </div>

                <div>
                  <button onClick={handleEmailTrigger} disabled={sendingEmails} className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md">{sendingEmails ? 'Sending...' : 'Trigger Emails'}</button>
                </div>

                {emailStatus && <div className={`text-sm ${emailStatus.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>{emailStatus.message}</div>}
              </div>
            </div> */}

            <div className="bg-white shadow rounded-lg p-6">
              <h4 className="text-md font-medium mb-3">Quick Actions</h4>
              <div className="space-y-2">
                <button onClick={async () => { setReportSettings(prev=>({...prev, report_type:'low_attendance', timeframe:'weekly'})); await fetchReport(); }} className="w-full px-4 py-2 bg-gray-200 rounded-md">Refresh Low Attendance</button>
                <button onClick={() => { window.location.reload() }} className="w-full px-4 py-2 bg-gray-200 rounded-md">Reload Page</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Reports