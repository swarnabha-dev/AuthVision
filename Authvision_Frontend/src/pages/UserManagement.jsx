import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/apiClient'
import { useAuthStore } from '../store/authStore'

const UserManagement = () => {
  const { user } = useAuthStore()
  const [users, setUsers] = useState([])
  const [filteredUsers, setFilteredUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('operators') // operators, pending_students, all_users
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState({
    status: '',
    role: '',
    department: ''
  })
  const [selectedUser, setSelectedUser] = useState(null)
  const [showUserModal, setShowUserModal] = useState(false)
  const [showCreateOperatorModal, setShowCreateOperatorModal] = useState(false)
  const [newOperatorData, setNewOperatorData] = useState({
    username: '',
    email: '',
    name: '',
    password: '',
    confirmPassword: ''
  })

  // Local fallback mock users (used only if backend is unreachable)
  const mockUsers = [
    {
      id: '1',
      username: 'operator1',
      email: 'operator1@5glab.com',
      name: 'John Operator',
      role: 'operator',
      status: 'active',
      department: 'CSE',
      created_at: '2024-01-10',
      last_login: '2024-01-15',
      students_registered: 45,
      attendance_marked: 120
    },
    {
      id: '4',
      username: 'student_pending_001',
      email: 'pending1@student.com',
      name: 'Alice Johnson',
      role: 'student',
      status: 'pending',
      department: 'CSE',
      semester: '3',
      section: 'A',
      created_at: '2024-01-15',
      registration_type: 'self',
      subjects: ['CS101', 'CS102', 'MA101']
    }
  ]

  useEffect(() => {
    loadUsers()
  }, [activeTab])

  useEffect(() => {
    filterUsers()
  }, [users, searchTerm, filters, activeTab])

  const loadUsers = async () => {
    try {
      setLoading(true)

      // Try backend first
      try {
        const resp = await apiClient.getAllStudents()
        // backend may return array or { students: [] }
        const list = Array.isArray(resp) ? resp : (resp && resp.students ? resp.students : [])

        // Map backend fields to UI shape if necessary
        const mapped = list.map(u => ({
          id: u.id || u._id || u.username || `${u.username || 'user'}_${Math.random()}`,
          username: u.username || u.reg_no || u.studentId || '',
          email: u.email || u.contact_email || '',
          name: u.name || `${u.firstName || ''} ${u.lastName || ''}`.trim() || u.username,
          role: u.role || (u.registration_type ? 'student' : 'operator') || 'student',
          status: u.status || (u.isActive ? 'active' : 'inactive') || 'pending',
          department: u.department || u.dept || '',
          semester: u.semester || u.sem || '',
          section: u.section || '',
          created_at: u.created_at || u.createdAt || '',
          last_login: u.last_login || u.lastLogin || '' ,
          subjects: u.subjects || u.registeredSubjects || [] ,
          attendance_percentage: u.attendance_percentage || u.attendance || null,
          students_registered: u.students_registered || 0,
          attendance_marked: u.attendance_marked || 0
        }))

        // Filter by activeTab
        let filteredData = mapped
        switch(activeTab) {
          case 'operators':
            filteredData = mapped.filter(u => u.role === 'operator')
            break
          case 'pending_students':
            filteredData = mapped.filter(u => u.role === 'student' && u.status === 'pending')
            break
          case 'all_users':
            filteredData = mapped
            break
          default:
            break
        }

        setUsers(filteredData)
        return
      } catch (err) {
        console.warn('Backend users fetch failed, falling back to local mock:', err)
      }

      // Fallback: use local mock data
      let filteredData = mockUsers
      switch(activeTab) {
        case 'operators':
          filteredData = mockUsers.filter(u => u.role === 'operator')
          break
        case 'pending_students':
          filteredData = mockUsers.filter(u => u.role === 'student' && u.status === 'pending')
          break
        case 'all_users':
          filteredData = mockUsers
          break
        default:
          break
      }

      setUsers(filteredData)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterUsers = () => {
    let filtered = users.filter(user => {
      // Search term filter
      const searchMatch = searchTerm === '' || 
        user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.department?.toLowerCase().includes(searchTerm.toLowerCase())
      
      // Status filter
      const statusMatch = !filters.status || user.status === filters.status
      
      // Role filter
      const roleMatch = !filters.role || user.role === filters.role
      
      // Department filter
      const deptMatch = !filters.department || user.department === filters.department
      
      return searchMatch && statusMatch && roleMatch && deptMatch
    })
    
    setFilteredUsers(filtered)
  }

  const viewUserDetails = (user) => {
    setSelectedUser(user)
    setShowUserModal(true)
  }

  const approveStudent = async (studentId) => {
    try {
      // API call to approve student
      await apiClient.apiPost(`/students/${studentId}/approve`)
      setRegistrationStatus({ 
        type: 'success', 
        message: 'Student registration approved successfully!' 
      })
      loadUsers() // Reload users
      setShowUserModal(false)
    } catch (error) {
      console.error('Failed to approve student:', error)
      setRegistrationStatus({ 
        type: 'error', 
        message: 'Failed to approve student registration' 
      })
    }
  }

  const rejectStudent = async (studentId) => {
    if (window.confirm('Are you sure you want to reject this student registration?')) {
      try {
        // API call to reject student
        await apiClient.apiPost(`/students/${studentId}/reject`)
        setRegistrationStatus({ 
          type: 'success', 
          message: 'Student registration rejected!' 
        })
        loadUsers() // Reload users
        setShowUserModal(false)
      } catch (error) {
        console.error('Failed to reject student:', error)
        setRegistrationStatus({ 
          type: 'error', 
          message: 'Failed to reject student registration' 
        })
      }
    }
  }

  const toggleOperatorStatus = async (operatorId, currentStatus) => {
    try {
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active'
      await apiClient.apiPost(`/operators/${operatorId}/status`, { status: newStatus })
      setRegistrationStatus({ 
        type: 'success', 
        message: `Operator ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully!` 
      })
      loadUsers() // Reload users
    } catch (error) {
      console.error('Failed to update operator status:', error)
      setRegistrationStatus({ 
        type: 'error', 
        message: 'Failed to update operator status' 
      })
    }
  }

  const createNewOperator = async (e) => {
    e.preventDefault()
    
    if (newOperatorData.password !== newOperatorData.confirmPassword) {
      setRegistrationStatus({ type: 'error', message: 'Passwords do not match!' })
      return
    }

    try {
      await apiClient.apiPost('/operators', {
        username: newOperatorData.username,
        email: newOperatorData.email,
        name: newOperatorData.name,
        password: newOperatorData.password,
        role: 'operator'
      })
      
      setRegistrationStatus({ 
        type: 'success', 
        message: 'New operator created successfully!' 
      })
      
      setNewOperatorData({
        username: '',
        email: '',
        name: '',
        password: '',
        confirmPassword: ''
      })
      setShowCreateOperatorModal(false)
      loadUsers() // Reload users
    } catch (error) {
      console.error('Failed to create operator:', error)
      setRegistrationStatus({ 
        type: 'error', 
        message: 'Failed to create operator' 
      })
    }
  }

  const getStats = () => {
    const totalOperators = users.filter(u => u.role === 'operator').length
    const activeOperators = users.filter(u => u.role === 'operator' && u.status === 'active').length
    const pendingStudents = users.filter(u => u.role === 'student' && u.status === 'pending').length
    const totalStudents = users.filter(u => u.role === 'student').length

    return { totalOperators, activeOperators, pendingStudents, totalStudents }
  }

  const stats = getStats()

  const departments = ['CSE', 'ECE', 'EEE', 'CE', 'NIL']
  const statusOptions = [
    { value: '', label: 'All Status' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' },
    { value: 'pending', label: 'Pending' }
  ]
  const roleOptions = [
    { value: '', label: 'All Roles' },
    { value: 'admin', label: 'Admin' },
    { value: 'operator', label: 'Operator' },
    { value: 'student', label: 'Student' }
  ]

  const [registrationStatus, setRegistrationStatus] = useState(null)

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>User Management</h1>
        <p>Manage operators, approve student registrations, and monitor system users</p>
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card primary">
          <div className="stat-icon">👨‍💼</div>
          <div className="stat-info">
            <span className="stat-value">{stats.totalOperators}</span>
            <span className="stat-label">Total Operators</span>
          </div>
        </div>
        <div className="stat-card success">
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <span className="stat-value">{stats.activeOperators}</span>
            <span className="stat-label">Active Operators</span>
          </div>
        </div>
        <div className="stat-card warning">
          <div className="stat-icon">⏳</div>
          <div className="stat-info">
            <span className="stat-value">{stats.pendingStudents}</span>
            <span className="stat-label">Pending Students</span>
          </div>
        </div>
        <div className="stat-card info">
          <div className="stat-icon">🎓</div>
          <div className="stat-info">
            <span className="stat-value">{stats.totalStudents}</span>
            <span className="stat-label">Total Students</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="tabs-navigation">
        <button 
          className={`tab-button ${activeTab === 'operators' ? 'active' : ''}`}
          onClick={() => setActiveTab('operators')}
        >
          👨‍💼 Operators ({stats.totalOperators})
        </button>
        <button 
          className={`tab-button ${activeTab === 'pending_students' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending_students')}
        >
          ⏳ Pending Students ({stats.pendingStudents})
        </button>
        <button 
          className={`tab-button ${activeTab === 'all_users' ? 'active' : ''}`}
          onClick={() => setActiveTab('all_users')}
        >
          👥 All Users ({users.length})
        </button>
        
        {activeTab === 'operators' && (
          <button 
            className="create-operator-button"
            onClick={() => setShowCreateOperatorModal(true)}
          >
            ➕ Create New Operator
          </button>
        )}
      </div>

      {/* Search and Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search by name, username, or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="filter-row">
          <div className="filter-group">
            <label>Status</label>
            <select 
              value={filters.status} 
              onChange={(e) => setFilters(prev => ({...prev, status: e.target.value}))}
            >
              {statusOptions.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>Role</label>
            <select 
              value={filters.role} 
              onChange={(e) => setFilters(prev => ({...prev, role: e.target.value}))}
            >
              {roleOptions.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Department</label>
            <select 
              value={filters.department} 
              onChange={(e) => setFilters(prev => ({...prev, department: e.target.value}))}
            >
              <option value="">All Departments</option>
              {departments.map(dept => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>
          
          <button onClick={loadUsers} className="refresh-button">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Users Table */}
      <div className="users-table-section">
        <div className="section-header">
          <h3>
            {activeTab === 'operators' && 'Operators Management'}
            {activeTab === 'pending_students' && 'Pending Student Approvals'}
            {activeTab === 'all_users' && 'All System Users'}
          </h3>
          <div className="results-count">
            Showing {filteredUsers.length} of {users.length} users
          </div>
        </div>
        
        {loading ? (
          <div className="loading">Loading users...</div>
        ) : (
          <div className="table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Department</th>
                  <th>Created</th>
                  <th>Last Activity</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(user => (
                  <tr key={user.id} className={`user-row ${user.status}`}>
                    <td className="user-info">
                      <div className="user-avatar">
                        {user.role === 'operator' ? '👨‍💼' : user.role === 'admin' ? '👑' : '🎓'}
                      </div>
                      <div className="user-details">
                        <div className="user-name">{user.name}</div>
                        <div className="user-credentials">
                          {user.username} • {user.email}
                        </div>
                        {user.role === 'student' && user.semester && (
                          <div className="student-info">
                            Sem {user.semester} • Sec {user.section}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="user-role">
                      <span className={`role-badge ${user.role}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="user-status">
                      <span className={`status-badge ${user.status}`}>
                        {user.status}
                      </span>
                    </td>
                    <td className="user-department">
                      {user.department || 'N/A'}
                    </td>
                    <td className="user-created">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="user-activity">
                      {user.last_login ? 
                        new Date(user.last_login).toLocaleDateString() : 
                        'Never'
                      }
                    </td>
                    <td className="user-actions">
                      <button 
                        className="action-button view" 
                        title="View Details"
                        onClick={() => viewUserDetails(user)}
                      >
                        👁️ Details
                      </button>
                      
                      {user.role === 'operator' && (
                        <button 
                          className={`action-button ${user.status === 'active' ? 'deactivate' : 'activate'}`}
                          title={user.status === 'active' ? 'Deactivate' : 'Activate'}
                          onClick={() => toggleOperatorStatus(user.id, user.status)}
                        >
                          {user.status === 'active' ? '⏸️ Deactivate' : '▶️ Activate'}
                        </button>
                      )}
                      
                      {user.role === 'student' && user.status === 'pending' && (
                        <>
                          <button 
                            className="action-button approve"
                            title="Approve Registration"
                            onClick={() => approveStudent(user.id)}
                          >
                            ✅ Approve
                          </button>
                          <button 
                            className="action-button reject"
                            title="Reject Registration"
                            onClick={() => rejectStudent(user.id)}
                          >
                            ❌ Reject
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {filteredUsers.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">
                  {activeTab === 'pending_students' ? '🎉' : '📝'}
                </div>
                <h3>
                  {activeTab === 'pending_students' ? 
                    'No Pending Approvals' : 
                    'No Users Found'
                  }
                </h3>
                <p>
                  {activeTab === 'pending_students' ? 
                    'All student registrations have been processed. Great work!' : 
                    'No users match your current search criteria. Try adjusting your filters.'
                  }
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Status Message */}
      {registrationStatus && (
        <div className={`status-message ${registrationStatus.type}`}>
          <div className="status-icon">
            {registrationStatus.type === 'success' ? '✅' : '❌'}
          </div>
          <div className="status-content">
            {registrationStatus.message}
          </div>
        </div>
      )}

      {/* User Details Modal */}
      {showUserModal && selectedUser && (
        <div className="modal-overlay">
          <div className="modal-content large-modal">
            <div className="modal-header">
              <h3>User Details - {selectedUser.name}</h3>
              <button onClick={() => setShowUserModal(false)} className="close-button">×</button>
            </div>
            
            <div className="user-details-enhanced">
              <div className="detail-section">
                <h4>👤 Basic Information</h4>
                <div className="detail-grid">
                  <div className="detail-item">
                    <label>Full Name:</label>
                    <span className="detail-value">{selectedUser.name}</span>
                  </div>
                  <div className="detail-item">
                    <label>Username:</label>
                    <span className="detail-value">{selectedUser.username}</span>
                  </div>
                  <div className="detail-item">
                    <label>Email:</label>
                    <span className="detail-value">{selectedUser.email}</span>
                  </div>
                  <div className="detail-item">
                    <label>Role:</label>
                    <span className={`detail-value role ${selectedUser.role}`}>
                      {selectedUser.role}
                    </span>
                  </div>
                  <div className="detail-item">
                    <label>Status:</label>
                    <span className={`detail-value status ${selectedUser.status}`}>
                      {selectedUser.status}
                    </span>
                  </div>
                  <div className="detail-item">
                    <label>Department:</label>
                    <span className="detail-value">{selectedUser.department || 'N/A'}</span>
                  </div>
                  <div className="detail-item">
                    <label>Created:</label>
                    <span className="detail-value">
                      {new Date(selectedUser.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="detail-item">
                    <label>Last Login:</label>
                    <span className="detail-value">
                      {selectedUser.last_login ? 
                        new Date(selectedUser.last_login).toLocaleDateString() : 
                        'Never'
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Additional Info based on role */}
              {selectedUser.role === 'operator' && (
                <div className="detail-section">
                  <h4>📊 Operator Performance</h4>
                  <div className="performance-stats">
                    <div className="performance-card">
                      <span className="performance-value">{selectedUser.students_registered || 0}</span>
                      <span className="performance-label">Students Registered</span>
                    </div>
                    <div className="performance-card">
                      <span className="performance-value">{selectedUser.attendance_marked || 0}</span>
                      <span className="performance-label">Attendance Records</span>
                    </div>
                  </div>
                </div>
              )}

              {selectedUser.role === 'student' && (
                <div className="detail-section">
                  <h4>🎓 Academic Information</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <label>Semester:</label>
                      <span className="detail-value">{selectedUser.semester || 'N/A'}</span>
                    </div>
                    <div className="detail-item">
                      <label>Section:</label>
                      <span className="detail-value">{selectedUser.section || 'N/A'}</span>
                    </div>
                    <div className="detail-item">
                      <label>Registration Type:</label>
                      <span className="detail-value">{selectedUser.registration_type || 'N/A'}</span>
                    </div>
                    {selectedUser.attendance_percentage && (
                      <div className="detail-item">
                        <label>Attendance:</label>
                        <span className="detail-value">{selectedUser.attendance_percentage}%</span>
                      </div>
                    )}
                  </div>
                  
                  {selectedUser.subjects && (
                    <div className="subjects-list">
                      <strong>Registered Subjects:</strong>
                      <div className="subject-tags">
                        {selectedUser.subjects.map(subject => (
                          <span key={subject} className="subject-tag">{subject}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-actions">
              {selectedUser.role === 'student' && selectedUser.status === 'pending' && (
                <>
                  <button 
                    className="action-button approve large"
                    onClick={() => approveStudent(selectedUser.id)}
                  >
                    ✅ Approve Registration
                  </button>
                  <button 
                    className="action-button reject large"
                    onClick={() => rejectStudent(selectedUser.id)}
                  >
                    ❌ Reject Registration
                  </button>
                </>
              )}
              
              {selectedUser.role === 'operator' && (
                <button 
                  className={`action-button ${selectedUser.status === 'active' ? 'deactivate' : 'activate'} large`}
                  onClick={() => toggleOperatorStatus(selectedUser.id, selectedUser.status)}
                >
                  {selectedUser.status === 'active' ? '⏸️ Deactivate Operator' : '▶️ Activate Operator'}
                </button>
              )}
              
              <button 
                className="close-modal-button"
                onClick={() => setShowUserModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Operator Modal */}
      {showCreateOperatorModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Create New Operator</h3>
              <button onClick={() => setShowCreateOperatorModal(false)} className="close-button">×</button>
            </div>
            
            <form onSubmit={createNewOperator} className="operator-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    value={newOperatorData.name}
                    onChange={(e) => setNewOperatorData(prev => ({...prev, name: e.target.value}))}
                    required
                    placeholder="Enter operator's full name"
                  />
                </div>
                <div className="form-group">
                  <label>Username *</label>
                  <input
                    type="text"
                    value={newOperatorData.username}
                    onChange={(e) => setNewOperatorData(prev => ({...prev, username: e.target.value}))}
                    required
                    placeholder="Choose a username"
                  />
                </div>
              </div>
              
              <div className="form-group">
                <label>Email Address *</label>
                <input
                  type="email"
                  value={newOperatorData.email}
                  onChange={(e) => setNewOperatorData(prev => ({...prev, email: e.target.value}))}
                  required
                  placeholder="operator@5glab.com"
                />
              </div>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Password *</label>
                  <input
                    type="password"
                    value={newOperatorData.password}
                    onChange={(e) => setNewOperatorData(prev => ({...prev, password: e.target.value}))}
                    required
                    placeholder="Enter password"
                  />
                </div>
                <div className="form-group">
                  <label>Confirm Password *</label>
                  <input
                    type="password"
                    value={newOperatorData.confirmPassword}
                    onChange={(e) => setNewOperatorData(prev => ({...prev, confirmPassword: e.target.value}))}
                    required
                    placeholder="Confirm password"
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  👨‍💼 Create Operator
                </button>
                <button 
                  type="button" 
                  className="btn-secondary"
                  onClick={() => setShowCreateOperatorModal(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserManagement