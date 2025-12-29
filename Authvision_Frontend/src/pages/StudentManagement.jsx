import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuthStore } from '../store/authStore'

const StudentManagement = () => {
  const { user } = useAuthStore()
  const [students, setStudents] = useState([])
  const [filteredStudents, setFilteredStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [showStudentModal, setShowStudentModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingStudent, setEditingStudent] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({
    department: '',
    semester: '',
    section: '',
    subject: '',
    attendance_status: ''
  })
  const [subjectOptions, setSubjectOptions] = useState([])
  const [subjectSummaryMap, setSubjectSummaryMap] = useState(null) // { reg_no: percent }
  const [subjectSummaryList, setSubjectSummaryList] = useState(null) // [{ reg, name, percent }]
  const [loadingSubjectSummary, setLoadingSubjectSummary] = useState(false)
  const [departments, setDepartments] = useState(['CSE', 'ECE', 'EEE', 'CE', 'NIL'])

  // 🆕 Enhanced mock data with academic details
  const mockStudents = [
    {
      student_id: '202500568',
      first_name: 'Ishwan',
      last_name: 'Roy',
      full_name: 'Ishwan Roy',
      department: 'CSE',
      section: 'A',
      semester: '3',
      email: 'ishwan@example.com',
      phone: '+91-9876543210',
      registration_date: '2024-01-15',
      is_rejoinee: false,
      subjects: [
        { subjectCode: 'CS101', subjectName: 'Data Structures', attendance_percentage: 88.0 },
        { subjectCode: 'CS102', subjectName: 'Algorithms', attendance_percentage: 92.0 },
        { subjectCode: 'MA101', subjectName: 'Mathematics I', attendance_percentage: 78.5 }
      ],
      attendance: {
        total_classes: 45,
        classes_present: 38,
        classes_absent: 7,
        attendance_percentage: 84.4
      },
      status: 'enrolled',
      last_attendance: '2024-01-15'
    },
    {
      student_id: '202500569',
      first_name: 'John',
      last_name: 'Doe',
      full_name: 'John Doe',
      department: 'ECE',
      section: 'B',
      semester: '4',
      email: 'john@example.com',
      phone: '+91-9876543211',
      registration_date: '2024-01-10',
      is_rejoinee: true,
      subjects: [
        { subjectCode: 'EC101', subjectName: 'Electronics', attendance_percentage: 62.2 },
        { subjectCode: 'EC102', subjectName: 'Signals', attendance_percentage: 58.7 },
        { subjectCode: 'MA201', subjectName: 'Mathematics II', attendance_percentage: 71.4 }
      ],
      attendance: {
        total_classes: 45,
        classes_present: 28,
        classes_absent: 17,
        attendance_percentage: 62.2
      },
      status: 'enrolled',
      last_attendance: '2024-01-15'
    },
    {
      student_id: '202500570',
      first_name: 'Alice',
      last_name: 'Smith',
      full_name: 'Alice Smith',
      department: 'CSE',
      section: 'A',
      semester: '3',
      email: 'alice@example.com',
      phone: '+91-9876543212',
      registration_date: '2024-01-12',
      is_rejoinee: false,
      subjects: [
        { subjectCode: 'CS101', subjectName: 'Data Structures', attendance_percentage: 95.0 },
        { subjectCode: 'CS102', subjectName: 'Algorithms', attendance_percentage: 91.5 },
        { subjectCode: 'PH101', subjectName: 'Physics', attendance_percentage: 89.2 }
      ],
      attendance: {
        total_classes: 45,
        classes_present: 42,
        classes_absent: 3,
        attendance_percentage: 93.3
      },
      status: 'enrolled',
      last_attendance: '2024-01-15'
    }
  ]

  useEffect(() => {
    // reload students when filters change or when subject summary list updates.
    // When a subject is selected, the summary fetch runs async; this ensures
    // loadStudents is called again once the summary list is available.
    loadStudents()
  }, [filters, subjectSummaryList])

  // Load subjects from backend when department or semester changes (or on mount)
  useEffect(() => {
    const fetchSubjects = async () => {
      try {
        let list = []
        if (filters.semester) {
          const resp = await apiClient.getSubjectsBySemester(filters.semester)
          list = Array.isArray(resp) ? resp : (resp.subjects || [])
        } else {
          const resp = await apiClient.getSubjects()
          list = Array.isArray(resp) ? resp : (resp.subjects || [])
        }
        // normalize subject objects to { code, name, department }
        const normalized = (list || []).map(s => {
          if (typeof s === 'string') return { code: s, name: s, department: '' }
          return { code: s.code ?? s.subjectCode ?? s.id ?? s.id_str ?? String(s), name: s.name ?? s.subjectName ?? s.title ?? s.name ?? (s.code || s.subjectCode || ''), department: s.department ?? s.dept ?? '' }
        })
        // filter by department if provided
        const filtered = normalized.filter(s => {
          if (!filters.department) return true
          return (s.department || '') === '' || (s.department || '') === filters.department
        })
        // ensure unique by code
        const uniq = []
        const seen = new Set()
        for (const sub of filtered) {
          if (!seen.has(sub.code)) { seen.add(sub.code); uniq.push(sub) }
        }
        setSubjectOptions(uniq)
      } catch (e) {
        console.warn('Failed to load subjects:', e)
        setSubjectOptions([])
      }
    }
    fetchSubjects()
  }, [filters.semester, filters.department])

  // Load departments on mount
  useEffect(() => {
    let mounted = true
    const fetchDepts = async () => {
      try {
        const resp = await apiClient.getDepartments()
        if (mounted && Array.isArray(resp) && resp.length > 0) {
          // Normalize department values to strings (backend may return objects)
          const normalized = resp.map(d => typeof d === 'string' ? d : (d.code ?? d.id ?? d.name ?? JSON.stringify(d)))
          setDepartments(normalized)
        }
      } catch (e) {
        console.warn('Failed to load departments:', e)
      }
    }
    fetchDepts()
    return () => { mounted = false }
  }, [])

  // When a subject is selected, fetch subject-level attendance summary
  useEffect(() => {
    let cancelled = false
    const fetchSummary = async () => {
      if (!filters.subject) {
        setSubjectSummaryMap(null)
        setSubjectSummaryList(null)
        return
      }
      setLoadingSubjectSummary(true)
      try {
        // Call /reports/subject/{subject}/summary endpoint
        const resp = await apiClient.apiGet(`/reports/subject/${filters.subject}/summary`)
        
        const map = {}
        const list = []
        
        // Parse response format: { subject: {...}, student_stats: [...], ... }
        if (resp && resp.student_stats && Array.isArray(resp.student_stats)) {
          for (const student of resp.student_stats) {
            const reg = student.reg_no || student.regno || student.reg || student.student_id
            const pct = student.percentage ?? student.attendance_percentage ?? null
            const name = student.name || student.student_name || student.full_name || null
            const section = student.section || null
            const presentCount = student.present_count ?? null
            const totalClasses = student.total_classes ?? resp.total_classes ?? null
            
            if (reg) {
              map[String(reg)] = pct !== null && pct !== undefined ? Number(pct) : null
              list.push({ 
                reg: String(reg), 
                name: name || String(reg), 
                percent: pct !== null && pct !== undefined ? Number(pct) : null,
                section: section,
                present_count: presentCount,
                total_classes: totalClasses
              })
            }
          }
        }

        if (!cancelled) {
          setSubjectSummaryMap(map)
          setSubjectSummaryList(list)
        }
      } catch (e) {
        console.warn('Failed to fetch subject summary:', e)
        if (!cancelled) {
          setSubjectSummaryMap(null)
          setSubjectSummaryList(null)
        }
      } finally {
        if (!cancelled) setLoadingSubjectSummary(false)
      }
    }
    fetchSummary()
    return () => { cancelled = true }
  }, [filters.subject])

  useEffect(() => {
    filterStudents()
  }, [students, searchTerm, filters])

  const loadStudents = async () => {
    try {
      setLoading(true)

      // If a subject is selected but the summary is still loading, wait — don't clear results immediately.
      if (filters.subject && loadingSubjectSummary) {
        // keep loading indicator visible until subject summary completes
        return
      }

      // If a subject is selected and we have a server-provided summary list,
      // use that list of registration numbers (and names) to drive which students to show.
      if (filters.subject && subjectSummaryList) {
        // entries: [{ reg, name, percent, section, present_count, total_classes }]
        let entries = Array.isArray(subjectSummaryList) ? subjectSummaryList.slice() : []

        if (entries.length === 0) {
          setStudents([])
          return
        }

        // Filter by attendance status if selected
        if (filters.attendance_status === 'good') {
          entries = entries.filter(e => e.percent !== null && e.percent !== undefined ? Number(e.percent) >= 75 : false)
        } else if (filters.attendance_status === 'low') {
          entries = entries.filter(e => e.percent !== null && e.percent !== undefined ? Number(e.percent) < 75 : false)
        }

        if (entries.length === 0) {
          setStudents([])
          return
        }

        const regs = entries.map(e => e.reg)
        const dataMap = Object.fromEntries(entries.map(e => [String(e.reg), e]))

        // Fetch student details in parallel, but tolerate individual failures.
        const promises = regs.map(reg => apiClient.getStudent(reg).then(res => ({ ok: true, res, reg })).catch(err => ({ ok: false, err, reg })))
        const results = await Promise.all(promises)

        const mapped = results.map(item => {
          const reg = item.reg
          const summaryData = dataMap[String(reg)]
          
          if (!item.ok) {
            // fallback: show the reg and name from summary, minimal info
            return {
              student_id: reg,
              first_name: summaryData?.name?.split(' ')[0] || summaryData?.name || reg,
              last_name: summaryData?.name?.split(' ').slice(1).join(' ') || '',
              full_name: summaryData?.name || reg,
              department: filters.department || '',
              section: summaryData?.section || 'A',
              semester: filters.semester || '',
              email: `${reg}@student.local`,
              phone: '',
              registration_date: null,
              is_rejoinee: false,
              subjects: [],
              attendance: { 
                total_classes: summaryData?.total_classes || 0, 
                classes_present: summaryData?.present_count || 0, 
                classes_absent: (summaryData?.total_classes || 0) - (summaryData?.present_count || 0), 
                attendance_percentage: summaryData?.percent !== null && summaryData?.percent !== undefined ? Number(summaryData.percent) : 0 
              },
              status: 'enrolled',
              last_attendance: null
            }
          }
          
          const s = item.res
          const studentReg = s.reg_no || s.regNo || s.reg || s.username
          return {
            student_id: studentReg,
            first_name: s.name?.split(' ')[0] || summaryData?.name?.split(' ')[0] || s.name || '',
            last_name: s.name?.split(' ').slice(1).join(' ') || summaryData?.name?.split(' ').slice(1).join(' ') || '',
            full_name: s.name || summaryData?.name || studentReg,
            department: s.department || filters.department || '',
            section: s.section || summaryData?.section || 'A',
            semester: s.semester ? String(s.semester) : filters.semester || '',
            email: s.email || `${studentReg}@student.local`,
            phone: s.phone || '',
            registration_date: s.created_at || null,
            is_rejoinee: false,
            subjects: s.subjects || [],
            attendance: { 
              total_classes: summaryData?.total_classes || s.attendance?.total_classes || 0, 
              classes_present: summaryData?.present_count || s.attendance?.classes_present || 0, 
              classes_absent: ((summaryData?.total_classes || s.attendance?.total_classes || 0) - (summaryData?.present_count || s.attendance?.classes_present || 0)), 
              attendance_percentage: summaryData?.percent !== null && summaryData?.percent !== undefined ? Number(summaryData.percent) : (s.attendance?.attendance_percentage || 0)
            },
            status: s.status || 'enrolled',
            last_attendance: s.last_attendance || null
          }
        })
        setStudents(mapped)
        return
      }

      // Otherwise, fall back to loading all students
      try {
        const res = await apiClient.getAllStudents()
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(s => ({
            student_id: s.reg_no || s.regNo || s.reg || s.username,
            first_name: s.name?.split(' ')[0] || s.name || '',
            last_name: s.name?.split(' ').slice(1).join(' ') || '',
            full_name: s.name || s.reg_no || s.username,
            department: s.department || '',
            section: s.section || 'A',
            semester: s.semester ? String(s.semester) : '',
            email: s.email || `${s.reg_no}@student.local`,
            phone: s.phone || '',
            registration_date: s.created_at || null,
            is_rejoinee: false,
            subjects: s.subjects || [],
            attendance: s.attendance || { total_classes: 0, classes_present: 0, classes_absent: 0, attendance_percentage: 0 },
            status: s.status || 'enrolled',
            last_attendance: s.last_attendance || null
          }))
          setStudents(mapped)
          return
        }
      } catch (e) {
        console.warn('Failed to load students from backend, falling back to mock:', e)
      }

      setStudents(mockStudents)
    } catch (error) {
      console.error('Failed to load students:', error)
    } finally {
      setLoading(false)
    }
  }

  // 🆕 Enhanced filtering with multiple criteria
  const filterStudents = () => {
    let filtered = students.filter(student => {
      // Search term filter
      const searchMatch = searchTerm === '' || 
        student.student_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        student.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        student.email.toLowerCase().includes(searchTerm.toLowerCase())
      
      // Department filter
      const deptMatch = !filters.department || student.department === filters.department
      
      // 🆕 Semester filter
      const semesterMatch = !filters.semester || student.semester === filters.semester
      
      // Section filter
      const sectionMatch = !filters.section || student.section === filters.section
      
      // 🆕 Subject filter (match by various possible keys)
      let subjectMatch = true
      let subjectAttendance = null
      if (filters.subject) {
        // Prefer subjectSummaryMap (server data) if available
        if (subjectSummaryMap) {
          // subjectSummaryMap keys are registration numbers
          const regKey = String(student.student_id)
          if (Object.prototype.hasOwnProperty.call(subjectSummaryMap, regKey)) {
            subjectMatch = true
            subjectAttendance = subjectSummaryMap[regKey]
          } else {
            // if not present in summary, try matching student's subject list as fallback
            subjectMatch = (student.subjects || []).some(subj => {
              const code = subj.subjectCode || subj.code || subj.subject_id || subj.id || ''
              return String(code) === String(filters.subject)
            })
          }
        } else {
          subjectMatch = false
          for (const subj of (student.subjects || [])) {
            const code = subj.subjectCode || subj.code || subj.subject_id || subj.id || ''
            if (!code) continue
            if (String(code) === String(filters.subject)) {
              subjectMatch = true
              // determine subject-level attendance if available locally
              subjectAttendance = subj.attendance_percentage ?? subj.attendance ?? subj.attendancePercent ?? subj.percent ?? null
              if (subjectAttendance && typeof subjectAttendance === 'object') {
                subjectAttendance = subjectAttendance.attendance_percentage ?? subjectAttendance.percent ?? null
              }
              if (subjectAttendance !== null) subjectAttendance = Number(subjectAttendance)
              break
            }
          }
        }
      }

      // Attendance status filter: if a subject is selected, apply to subject-level attendance when available,
      // otherwise fall back to overall attendance percentage.
      let attendanceMatch = true
      const overallAttendance = (student.attendance && (student.attendance.attendance_percentage ?? student.attendance.percent ?? student.attendancePercentage)) ? Number(student.attendance.attendance_percentage ?? student.attendance.percent ?? student.attendancePercentage) : null
      if (filters.attendance_status === 'low') {
        if (filters.subject && subjectAttendance !== null) {
          attendanceMatch = subjectAttendance < 75
        } else if (overallAttendance !== null) {
          attendanceMatch = overallAttendance < 75
        }
      } else if (filters.attendance_status === 'good') {
        if (filters.subject && subjectAttendance !== null) {
          attendanceMatch = subjectAttendance >= 75
        } else if (overallAttendance !== null) {
          attendanceMatch = overallAttendance >= 75
        }
      }
      
      return searchMatch && deptMatch && semesterMatch && sectionMatch && subjectMatch && attendanceMatch
    })
    
    setFilteredStudents(filtered)
  }

  // 🆕 Get unique values for filters
  const getUniqueValues = (key) => {
    const values = students.map(student => student[key]).filter(Boolean)
    return [...new Set(values)].sort()
  }

  // 🆕 Get all subjects for filter
  const getAllSubjects = () => {
    // Prefer server-provided subjects if available
    if (subjectOptions && subjectOptions.length > 0) {
      return subjectOptions.map(s => ({ code: s.code || s.subjectCode || s.code, name: s.name || s.subjectName || '' }))
        .filter(Boolean)
        .sort((a, b) => a.name.localeCompare(b.name))
    }

    const allSubjects = students.flatMap(student => 
      student.subjects.map(subject => ({
        code: subject.subjectCode,
        name: subject.subjectName
      }))
    )
    
    const uniqueSubjects = allSubjects.filter((subject, index, self) =>
      index === self.findIndex(s => s.code === subject.code)
    )
    
    return uniqueSubjects.sort((a, b) => a.name.localeCompare(b.name))
  }

  const viewStudentDetails = (student) => {
    setSelectedStudent(student)
    setShowStudentModal(true)
  }

  // 🆕 Operator can edit basic student information
  const handleEditStudent = (student) => {
    setEditingStudent({...student})
    setShowEditModal(true)
  }

  // 🆕 Save edited student information
  const handleSaveEdit = async () => {
    try {
      setLoading(true)
      // Build FormData to match backend /students/modify Form(...) parameters
      const fd = new FormData()
      fd.append('target_reg', String(editingStudent.student_id))
      // name is full name
      if (editingStudent.full_name) fd.append('name', String(editingStudent.full_name))
      if (editingStudent.semester) fd.append('semester', String(editingStudent.semester))
      if (editingStudent.department) fd.append('department', String(editingStudent.department))
      if (editingStudent.section) fd.append('section', String(editingStudent.section))
      if (editingStudent.roll_no !== undefined && editingStudent.roll_no !== null) fd.append('roll_no', String(editingStudent.roll_no))

      // Call backend
      try {
        const resp = await apiClient.apiPostForm('/students/modify', fd)
        // backend returns { reg_no: ... } on success
        // Update local state to reflect saved changes
        setStudents(prev => prev.map(student => (
          student.student_id === editingStudent.student_id ? ({ ...student, ...editingStudent }) : student
        )))
        setShowEditModal(false)
        setEditingStudent(null)
        alert('✅ Student information updated successfully!')
      } catch (err) {
        console.error('API error saving student:', err)
        alert('❌ Failed to update student information: ' + (err.message || err))
      }
    } catch (error) {
      console.error('Failed to update student:', error)
      alert('❌ Failed to update student information')
    } finally {
      setLoading(false)
    }
  }

  // 🆕 Delete student (admin only)
  const handleDeleteStudent = async (student) => {
    if (!window.confirm(`Delete student ${student.full_name} (${student.student_id})? This cannot be undone.`)) return
    try {
      setLoading(true)
      const fd = new FormData()
      fd.append('target_reg', String(student.student_id))
      try {
        const resp = await apiClient.apiPostForm('/students/delete', fd)
        // On success remove from local state
        setStudents(prev => prev.filter(s => s.student_id !== student.student_id))
        alert(`🗑️ Student ${student.full_name} deleted successfully`)
      } catch (err) {
        console.error('API error deleting student:', err)
        alert('❌ Failed to delete student: ' + (err.message || err))
      }
    } finally {
      setLoading(false)
    }
  }

  // 🆕 Export student list for operators
  const exportStudentList = () => {
    const csvContent = [
      ['Registration No', 'Name', 'Department', 'Semester', 'Section', 'Email', 'Phone', 'Attendance %'],
      ...filteredStudents.map(student => [
        student.student_id,
        student.full_name,
        student.department,
        `Sem ${student.semester}`,
        student.section,
        student.email,
        student.phone,
        `${student.attendance.attendance_percentage}%`
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `students_export_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const sendStudentEmail = async (student) => {
    try {
      await apiClient.sendCustomEmail(
        student.email,
        'Attendance Update - 5G Lab',
        `Dear ${student.full_name},\n\nYour current attendance status:\n\nClasses Conducted (CLC): ${student.attendance.total_classes}\nClasses Present (CLP): ${student.attendance.classes_present}\nAttendance Percentage: ${student.attendance.attendance_percentage}%\n\nBest regards,\n5G Lab System`
      )
      alert(`📧 Email sent to ${student.full_name}`)
    } catch (error) {
      console.error('Failed to send email:', error)
      alert('❌ Failed to send email')
    }
  }

  const sections = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'NIL']
  const semesters = ['1', '2', '3', '4', '5', '6', '7', '8']

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-cyan-50/40 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden mb-6">
          <div className="h-1.5 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-cyan-50 text-cyan-600 shadow-sm border border-cyan-100">
                  <span className="material-icons-round text-3xl">school</span>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-slate-800">Student Management</h1>
                  <p className="text-slate-600 mt-1">
                    {user?.role === 'admin' ? 
                      'Full student management with administrative controls' : 
                      'View and manage student accounts with limited editing capabilities'
                    }
                  </p>
                </div>
              </div>
              {/* <div className={`px-4 py-2 rounded-xl font-semibold text-sm border-2 ${
                user?.role === 'admin' 
                  ? 'bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200 text-purple-700' 
                  : 'bg-gradient-to-r from-cyan-50 to-blue-50 border-cyan-200 text-cyan-700'
              }`}>
                <span className="material-icons-round text-lg align-middle mr-1">
                  {user?.role === 'admin' ? 'admin_panel_settings' : 'badge'}
                </span>
                {user?.role === 'admin' ? 'Admin Access' : 'Operator Access'}
              </div> */}
            </div>
          </div>
        </div>

        {/* Search and Filters Section */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden mb-6">
          <div className="h-1 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="material-icons-round text-cyan-600">filter_alt</span>
              <h3 className="text-xl font-bold text-slate-800">Search & Filters</h3>
            </div>

            {/* Search Box */}
            <div className="mb-6">
              <div className="relative">
                <span className="material-icons-round absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">search</span>
                <input
                  type="text"
                  placeholder="Search by Registration ID, Name, or Email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700"
                />
              </div>
            </div>

            {/* Filter Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  <span className="material-icons-round text-sm align-middle mr-1">business</span>
                  Department
                </label>
                <select 
                  value={filters.department} 
                  onChange={(e) => setFilters(prev => ({...prev, department: e.target.value, subject: ''}))}
                  className="w-full px-4 py-2.5 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700 bg-white"
                >
                  <option value="">All Departments</option>
                  {departments.map(dept => (
                    <option key={dept} value={dept}>{dept}</option>
                  ))}
                </select>
              </div>
          
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  <span className="material-icons-round text-sm align-middle mr-1">calendar_today</span>
                  Semester
                </label>
                <select 
                  value={filters.semester} 
                  onChange={(e) => setFilters(prev => ({...prev, semester: e.target.value, subject: ''}))}
                  className="w-full px-4 py-2.5 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700 bg-white"
                >
                  <option value="">All Semesters</option>
                  {semesters.map(sem => (
                    <option key={sem} value={sem}>Semester {sem}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  <span className="material-icons-round text-sm align-middle mr-1">group</span>
                  Section
                </label>
                <select 
                  value={filters.section} 
                  onChange={(e) => setFilters(prev => ({...prev, section: e.target.value}))}
                  className="w-full px-4 py-2.5 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700 bg-white"
                >
                  <option value="">All Sections</option>
                  {sections.map(section => (
                    <option key={section} value={section}>{section}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  <span className="material-icons-round text-sm align-middle mr-1">book</span>
                  Subject
                </label>
                <select 
                  value={filters.subject} 
                  onChange={(e) => setFilters(prev => ({...prev, subject: e.target.value}))}
                  className="w-full px-4 py-2.5 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700 bg-white"
                >
              <option value="">All Subjects</option>
              {(
                // prefer subjectOptions from server, but filter by department if set
                (subjectOptions && subjectOptions.length > 0 ? subjectOptions : getAllSubjects())
                  .filter(s => {
                    const dept = s.department || s.dept || ''
                    if (!filters.department) return true
                    return dept === '' || dept === filters.department
                  })
                  .map(s => ({ code: s.code || s.subjectCode || s.code, name: s.name || s.subjectName || s.name }))
                  .filter((v, i, arr) => i === arr.findIndex(x => x.code === v.code))
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map(subject => (
                    <option key={subject.code} value={subject.code}>
                      {subject.code} - {subject.name}
                    </option>
                  ))
              )}
            </select>
          </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  <span className="material-icons-round text-sm align-middle mr-1">fact_check</span>
                  Attendance Status
                </label>
                <select 
                  value={filters.attendance_status} 
                  onChange={(e) => setFilters(prev => ({...prev, attendance_status: e.target.value}))}
                  className="w-full px-4 py-2.5 border-2 border-slate-200 rounded-xl focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-slate-700 bg-white"
                >
                  <option value="">All Students</option>
                  <option value="good">Good Attendance (≥75%)</option>
                  <option value="low">Low Attendance (&lt;75%)</option>
                </select>
              </div>
          
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3">
              <button 
                onClick={loadStudents} 
                className="bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-2.5 px-6 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
              >
                <span className="material-icons-round text-lg">refresh</span>
                Refresh
              </button>
              <button 
                onClick={() => setFilters({
                  department: '',
                  semester: '',
                  section: '',
                  subject: '',
                  attendance_status: ''
                })}
                className="bg-slate-500 hover:bg-slate-600 text-white font-semibold py-2.5 px-6 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
              >
                <span className="material-icons-round text-lg">clear</span>
                Clear Filters
              </button>
              {user?.role === 'operator' && (
                <button 
                  onClick={exportStudentList} 
                  className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold py-2.5 px-6 rounded-xl transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
                >
                  <span className="material-icons-round text-lg">download</span>
                  Export List
                </button>
              )}
            </div>


            {/* Filter Summary */}
            <div className="mt-6 flex flex-wrap items-center gap-2 text-sm">
              <span className="font-semibold text-slate-700">
                Showing <span className="text-cyan-600 font-bold">{filteredStudents.length}</span> of <span className="text-cyan-600 font-bold">{students.length}</span> students
              </span>
              {filters.department && (
                <span className="px-3 py-1 bg-cyan-50 text-cyan-700 rounded-lg font-medium border border-cyan-200">
                  Department: {filters.department}
                </span>
              )}
              {filters.semester && (
                <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg font-medium border border-blue-200">
                  Semester: {filters.semester}
                </span>
              )}
              {filters.section && (
                <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-lg font-medium border border-purple-200">
                  Section: {filters.section}
                </span>
              )}
              {filters.subject && (
                <span className="px-3 py-1 bg-teal-50 text-teal-700 rounded-lg font-medium border border-teal-200">
                  Subject: {filters.subject}
                </span>
              )}
              {filters.attendance_status && (
                <span className={`px-3 py-1 rounded-lg font-medium border ${filters.attendance_status === 'low' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                  {filters.attendance_status === 'low' ? 'Low Attendance' : 'Good Attendance'}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Students Table Section */}
        <div className="bg-surface-white rounded-2xl border border-slate-200/60 shadow-card overflow-hidden">
          <div className="h-1 w-full bg-gradient-to-r from-cyan-500 via-blue-400 to-teal-400" />
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <span className="material-icons-round text-cyan-600">people</span>
                <h3 className="text-xl font-bold text-slate-800">Students List ({filteredStudents.length})</h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl font-semibold text-sm border border-emerald-200 flex items-center gap-2">
                  <span className="material-icons-round text-lg">check_circle</span>
                  Good: {filteredStudents.filter(s => s.attendance.attendance_percentage >= 75).length}
                </div>
                <div className="px-4 py-2 bg-rose-50 text-rose-700 rounded-xl font-semibold text-sm border border-rose-200 flex items-center gap-2">
                  <span className="material-icons-round text-lg">warning</span>
                  Low: {filteredStudents.filter(s => s.attendance.attendance_percentage < 75).length}
                </div>
              </div>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="w-16 h-16 border-4 border-cyan-200 border-t-cyan-600 rounded-full animate-spin mb-4"></div>
                <p className="text-slate-600 font-medium">Loading students...</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b-2 border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Reg No</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Department</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Semester</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Section</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Attendance</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {filteredStudents.map(student => (
                      <tr key={student.student_id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-4">
                          <span className="font-mono font-semibold text-slate-700">{student.student_id}</span>
                        </td>
                        <td className="px-4 py-4">
                          <div>
                            <div className="font-semibold text-slate-800">{student.full_name}</div>
                            <div className="text-sm text-slate-500">{student.email}</div>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium">{student.department}</span>
                        </td>
                        <td className="px-4 py-4 text-slate-700 font-medium">Sem {student.semester}</td>
                        <td className="px-4 py-4">
                          <span className="px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium">{student.section}</span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-bold text-sm ${student.attendance.attendance_percentage < 75 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                {student.attendance.attendance_percentage}%
                              </span>
                              <span className={`material-icons-round text-sm ${student.attendance.attendance_percentage < 75 ? 'text-rose-500' : 'text-emerald-500'}`}>
                                {student.attendance.attendance_percentage < 75 ? 'trending_down' : 'trending_up'}
                              </span>
                            </div>
                            <div className="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                              <div 
                                className={`h-full rounded-full ${student.attendance.attendance_percentage < 75 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                                style={{ width: `${student.attendance.attendance_percentage}%` }}
                              ></div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-semibold capitalize">
                              {student.status}
                            </span>
                            {student.is_rejoinee && (
                              <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs font-semibold flex items-center gap-1">
                                <span className="material-icons-round text-xs">refresh</span>
                                Rejoin
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <button 
                              className="p-2 text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors" 
                              title="View Full Details"
                              onClick={() => viewStudentDetails(student)}
                            >
                              <span className="material-icons-round text-xl">visibility</span>
                            </button>
                            {user?.role && user?.role !== 'student' && (
                              <button 
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" 
                                title="Edit Student Information"
                                onClick={() => handleEditStudent(student)}
                              >
                                <span className="material-icons-round text-xl">edit</span>
                              </button>
                            )}
                            <button 
                              className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" 
                              title="Send Email"
                              onClick={() => sendStudentEmail(student)}
                            >
                              <span className="material-icons-round text-xl">email</span>
                            </button>
                            {user?.role === 'admin' && (
                              <button
                                className="p-2 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                                title="Delete Student"
                                onClick={() => handleDeleteStudent(student)}
                              >
                                <span className="material-icons-round text-xl">delete</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {filteredStudents.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-16">
                    <span className="material-icons-round text-6xl text-slate-300 mb-4">person_off</span>
                    <h3 className="text-xl font-bold text-slate-700 mb-2">No Students Found</h3>
                    <p className="text-slate-500 text-center max-w-md">No students match your current search criteria. Try adjusting your filters.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>)

    {/* 🆕 Enhanced Student Details Modal */}
    {showStudentModal && selectedStudent && (
        <div className="modal-overlay">
          <div className="modal-content large-modal">
            <div className="modal-header">
              <h3>Student Details - {selectedStudent.full_name}</h3>
              <button onClick={() => setShowStudentModal(false)} className="close-button">×</button>
            </div>
            
            <div className="student-details-enhanced">
              {/* Personal Information */}
              <div className="detail-section">
                <h4>👤 Personal Information</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <label>Registration Number:</label>
                    <span className="detail-value">{selectedStudent.student_id}</span>
                  </div>
                  <div className="detail-item">
                    <label>Full Name:</label>
                    <span className="detail-value">{selectedStudent.full_name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Department:</label>
                    <span className="detail-value">{selectedStudent.department}</span>
                  </div>
                  <div className="detail-item">
                    <label>Semester:</label>
                    <span className="detail-value">Semester {selectedStudent.semester}</span>
                  </div>
                  <div className="detail-item">
                    <label>Section:</label>
                    <span className="detail-value">{selectedStudent.section}</span>
                  </div>
                  <div className="detail-item">
                    <label>Email:</label>
                    <span className="detail-value">{selectedStudent.email}</span>
                  </div>
                  <div className="detail-item">
                    <label>Phone:</label>
                    <span className="detail-value">{selectedStudent.phone}</span>
                  </div>
                  <div className="detail-item">
                    <label>Registration Date:</label>
                    <span className="detail-value">{selectedStudent.registration_date}</span>
                  </div>
                  <div className="detail-item">
                    <label>Student Type:</label>
                    <span className="detail-value">
                      {selectedStudent.is_rejoinee ? '🔄 Rejoining Student' : '🎓 Regular Student'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 🆕 Subject-wise Attendance */}
              <div className="detail-section">
                <h4>📖 Subject-wise Attendance</h4>
                <div className="subjects-attendance-grid">
                  {selectedStudent.subjects.map(subject => (
                    <div key={subject.subjectCode} className="subject-attendance-card">
                      <div className="subject-header">
                        <div className="subject-code">{subject.subjectCode}</div>
                        <div className="subject-name">{subject.subjectName}</div>
                      </div>
                      <div className="attendance-percentage">
                        <span className={`percentage ${subject.attendance_percentage < 75 ? 'low' : 'good'}`}>
                          {subject.attendance_percentage}%
                        </span>
                      </div>
                      <div className="progress-bar">
                        <div 
                          className={`progress-fill ${subject.attendance_percentage < 75 ? 'low' : 'good'}`}
                          style={{ width: `${subject.attendance_percentage}%` }}
                        ></div>
                      </div>
                      <div className="attendance-status">
                        {subject.attendance_percentage < 75 ? '⚠️ Needs Improvement' : '✅ Good'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Overall Attendance */}
              <div className="detail-section">
                <h4>📊 Overall Attendance Summary</h4>
                <div className="attendance-details">
                  <div className="attendance-stats-grid">
                    <div className="stat-card">
                      <span className="stat-label">Classes Conducted (CLC)</span>
                      <span className="stat-value">{selectedStudent.attendance.total_classes}</span>
                    </div>
                    <div className="stat-card">
                      <span className="stat-label">Classes Present (CLP)</span>
                      <span className="stat-value present">{selectedStudent.attendance.classes_present}</span>
                    </div>
                    <div className="stat-card">
                      <span className="stat-label">Classes Absent</span>
                      <span className="stat-value absent">{selectedStudent.attendance.classes_absent}</span>
                    </div>
                    <div className="stat-card highlight">
                      <span className="stat-label">Overall Attendance</span>
                      <span className={`stat-value ${selectedStudent.attendance.attendance_percentage < 75 ? 'low' : 'good'}`}>
                        {selectedStudent.attendance.attendance_percentage}%
                      </span>
                    </div>
                  </div>
                  
                  {selectedStudent.attendance.attendance_percentage < 75 && (
                    <div className="low-attendance-warning">
                      <div className="warning-icon">⚠️</div>
                      <div className="warning-content">
                        <strong>Low Attendance Alert</strong>
                        <p>Student attendance is below 75%. Consider sending an email notification.</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="modal-actions">
              {/* 🆕 Edit button for operators in modal */}
              {user?.role === 'operator' && (
                <button 
                  className="edit-button primary"
                  onClick={() => {
                    setShowStudentModal(false)
                    handleEditStudent(selectedStudent)
                  }}
                >
                  ✏️ Edit Student Information
                </button>
              )}
              <button 
                className="email-button primary"
                onClick={() => sendStudentEmail(selectedStudent)}
              >
                📧 Send Email to Student
              </button>
              <button 
                className="close-modal-button"
                onClick={() => setShowStudentModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🆕 Edit Student Modal for Operators */}
      {showEditModal && editingStudent && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>✏️ Edit Student Information</h3>
              <button onClick={() => setShowEditModal(false)} className="close-button">×</button>
            </div>
            
            <div className="edit-form">
              <div className="form-group">
                <label>Registration Number</label>
                <input 
                  type="text" 
                  value={editingStudent.student_id} 
                  disabled 
                  className="disabled-input"
                />
                <small>Registration number cannot be changed</small>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>First Name *</label>
                  <input 
                    type="text" 
                    value={editingStudent.first_name} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, 
                      first_name: e.target.value,
                      full_name: `${e.target.value} ${prev.last_name}`
                    }))}
                    placeholder="Enter first name"
                  />
                </div>
                
                <div className="form-group">
                  <label>Last Name *</label>
                  <input 
                    type="text" 
                    value={editingStudent.last_name} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, 
                      last_name: e.target.value,
                      full_name: `${prev.first_name} ${e.target.value}`
                    }))}
                    placeholder="Enter last name"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Email Address *</label>
                  <input 
                    type="email" 
                    value={editingStudent.email} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, email: e.target.value
                    }))}
                    placeholder="student@college.edu"
                  />
                </div>
                
                <div className="form-group">
                  <label>Phone Number</label>
                  <input 
                    type="tel" 
                    value={editingStudent.phone} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, phone: e.target.value
                    }))}
                    placeholder="+91-9876543210"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Department</label>
                  <select 
                    value={editingStudent.department} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, department: e.target.value
                    }))}
                  >
                    <option value="">Select Department</option>
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Section</label>
                  <select 
                    value={editingStudent.section} 
                    onChange={(e) => setEditingStudent(prev => ({
                      ...prev, section: e.target.value
                    }))}
                  >
                    <option value="">Select Section</option>
                    {sections.map(section => (
                      <option key={section} value={section}>{section}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="operator-note">
                <div className="note-icon">💡</div>
                <div className="note-content">
                  <strong>Operator Access Note:</strong>
                  <p>You can update basic student information. Academic records and system settings require admin access.</p>
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button 
                className="save-button primary"
                onClick={handleSaveEdit}
                disabled={loading}
              >
                {loading ? '⏳ Saving...' : '💾 Save Changes'}
              </button>
              <button 
                className="cancel-button"
                onClick={() => setShowEditModal(false)}
                disabled={loading}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

    }
export default StudentManagement