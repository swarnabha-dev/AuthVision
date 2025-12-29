import React, { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../services/apiClient'
import '../styles/ui.css'

const AdminDashboard = () => {
  const { user } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')

  const [faculty, setFaculty] = useState([])
  const [students, setStudents] = useState([])
  const [subjects, setSubjects] = useState([])

  const [analytics, setAnalytics] = useState({
    totalStudents: 0,
    totalFaculty: 0,
    totalSubjects: 0,
    totalStreams: 0,
    runningStreams: 0,
    activeSessions: 0
  })

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      const studentsResp = await apiClient.getAllStudents().catch(() => [])
      const facultyResp = await apiClient.getFacultyList().catch(() => [])
      const subjectsResp = await apiClient.getSubjects().catch(() => [])

      const streams = await apiClient.listStreams().catch(() => [])
      const sessions = await apiClient.getActiveSessions().catch(() => null)

      const streamCount = Array.isArray(streams) ? streams.length : (streams?.length || 0)
      const runningStreams = Array.isArray(streams) ? streams.filter(s => s.running || s.active).length : 0
      const activeSessions = (sessions && (Array.isArray(sessions) ? sessions.length : (sessions.running ? 1 : 0))) || 0

      setStudents(Array.isArray(studentsResp) ? studentsResp : [])
      setFaculty(Array.isArray(facultyResp) ? facultyResp : [])
      setSubjects(Array.isArray(subjectsResp) ? subjectsResp : (subjectsResp.subjects || []))

      setAnalytics({
        totalStudents: Array.isArray(studentsResp) ? studentsResp.length : 0,
        totalFaculty: Array.isArray(facultyResp) ? facultyResp.length : 0,
        totalSubjects: Array.isArray(subjectsResp) ? subjectsResp.length : (subjectsResp.subjects || 0),
        totalStreams: streamCount,
        runningStreams,
        activeSessions
      })
    } catch (error) {
      // Backend endpoints may not exist in older deployments; keep UI usable
      console.warn('Failed to load dashboard data from backend:', error)
    }
    setLoading(false)
  }

  // Status toggling removed: backend/UI doesn't require per-user status control here

  const filteredFaculty = faculty.filter(f => (f.name || '').toLowerCase().includes(searchTerm.toLowerCase()) || (f.email || '').toLowerCase().includes(searchTerm.toLowerCase()))

  return (
    <div className="min-h-screen bg-background-light text-slate-700">
      <div className="p-8 lg:p-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-amber-50 flex items-center justify-center">👥</div>
              <div>
                <div className="text-2xl font-bold">{analytics.totalStudents ?? 0}</div>
                <div className="text-sm text-muted">Total Students</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-green-50 flex items-center justify-center">📚</div>
              <div>
                <div className="text-2xl font-bold">{analytics.totalSubjects ?? analytics.totalSubjects === 0 ? analytics.totalSubjects : analytics.totalSubjects}</div>
                <div className="text-sm text-muted">Total Subjects</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-indigo-50 flex items-center justify-center">👩‍🏫</div>
              <div>
                <div className="text-2xl font-bold">{analytics.totalFaculty ?? 0}</div>
                <div className="text-sm text-muted">Total Faculty</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-slate-50 flex items-center justify-center">📹</div>
              <div>
                <div className="text-2xl font-bold">{analytics.totalStreams ?? 0}</div>
                <div className="text-sm text-muted">Total Streams ({analytics.runningStreams ?? 0} running)</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="col-span-2">
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Subjects</h3>
              {subjects.length === 0 ? (
                <div className="text-sm text-muted">No subjects available</div>
              ) : (
                <ul className="space-y-2">
                  {subjects.slice(0, 12).map((s, idx) => (
                    <li key={s.code || s.id || idx} className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{s.name || s.title || s.code}</div>
                        <div className="text-xs text-muted">{s.code ? `Code: ${s.code}` : s.department || ''}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <div className="card mb-6">
              <h3 className="text-lg font-semibold mb-3">Faculty</h3>
              <div className="space-y-3">
                {faculty.slice(0,6).map((f, idx) => (
                  <div key={f.username || f.id || idx} className="flex items-center">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-md bg-indigo-50 flex items-center justify-center">{(f.name || '').split(' ').map(s=>s[0]).slice(0,2).join('')}</div>
                      <div>
                        <div className="font-medium">{f.name}</div>
                        <div className="text-xs text-muted">{f.email || f.username || ''}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold mb-3">System Summary</h3>
              <div className="text-sm text-muted space-y-2">
                <div>Active Sessions: <strong className="text-slate-900">{analytics.activeSessions ?? 0}</strong></div>
                <div>Running Streams: <strong className="text-slate-900">{analytics.runningStreams ?? 0}</strong></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Registration Card Component
const RegistrationCard = ({ registration, onApprove, onReject, loading }) => {
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const handleRejectClick = () => {
    setShowRejectModal(true)
  }

  const handleRejectConfirm = () => {
    onReject(registration.id, rejectReason)
    setShowRejectModal(false)
    setRejectReason('')
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="registration-card">
      <div className="card-header">
        <div className="student-info">
          <h4>{registration.firstName} {registration.lastName}</h4>
          <p className="student-email">{registration.collegeEmail}</p>
        </div>
        <div className="registration-meta">
          <span className="submission-date">
            Submitted: {formatDate(registration.submittedAt)}
          </span>
        </div>
      </div>

      <div className="card-content">
        <div className="student-details">
          <div className="detail-item">
            <strong>Student ID:</strong> {registration.studentId}
          </div>
          <div className="detail-item">
            <strong>Semester:</strong> {registration.semester}
          </div>
          <div className="detail-item">
            <strong>Department:</strong> {registration.department}
          </div>
          <div className="detail-item">
            <strong>Phone:</strong> {registration.phone}
          </div>
        </div>
      </div>

      <div className="card-actions">
        <button 
          onClick={() => onApprove(registration.id)}
          disabled={loading}
          className="approve-button"
        >
          ✅ Approve
        </button>
        <button 
          onClick={handleRejectClick}
          disabled={loading}
          className="reject-button"
        >
          ❌ Reject
        </button>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h4>Reject Registration</h4>
            <p>Please provide a reason for rejecting {registration.firstName}'s registration:</p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason..."
              rows="4"
              className="reason-textarea"
            />
            <div className="modal-actions">
              <button 
                onClick={handleRejectConfirm}
                disabled={!rejectReason.trim()}
                className="confirm-reject-button"
              >
                Confirm Reject
              </button>
              <button 
                onClick={() => setShowRejectModal(false)}
                className="cancel-button"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// User Row Component
const UserRow = ({ user, loading }) => {
  return (
    <div className="user-row">
      <div className="col-name">
        <div className="user-avatar">
          {user.name.split(' ').map(n => n[0]).join('')}
        </div>
        <div className="user-details">
          <strong>{user.name}</strong>
          <span>{user.email}</span>
        </div>
      </div>
      
      <div className="col-role">
        <span className={`role-badge ${user.role || ''}`}>
          {user.role || 'N/A'}
        </span>
      </div>
    </div>
  )
}

export default AdminDashboard