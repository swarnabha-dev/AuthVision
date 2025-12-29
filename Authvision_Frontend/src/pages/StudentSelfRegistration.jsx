import React, { useState } from 'react'
import { useAuthStore } from '../store/authStore'

const StudentSelfRegistration = () => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    collegeEmail: '',
    phone: '',
    semester: '',
    department: '',
    studentId: ''
  })
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const validateForm = () => {
    if (!formData.firstName.trim()) {
      return 'First name is required'
    }
    if (!formData.lastName.trim()) {
      return 'Last name is required'
    }
    if (!formData.collegeEmail.trim()) {
      return 'College email is required'
    }
    if (!formData.collegeEmail.includes('@smit.smu.edu.in')) {
      return 'Please use your college email address (@smit.smu.edu.in)'
    }
    if (!formData.semester) {
      return 'Please select your semester'
    }
    if (!formData.department) {
      return 'Please select your department'
    }
    if (!formData.studentId.trim()) {
      return 'Student ID is required'
    }
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)

    // Mock API call - replace with actual backend integration
    try {
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Simulate successful submission
      setSubmitted(true)
      
      // In real implementation, this would call:
      // await apiClient.submitStudentRegistration(formData)
      
    } catch (err) {
      setError('Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Department options
  const departments = [
    { value: '', label: 'Select Department' },
    { value: 'CSE', label: 'Computer Science & Engineering' },
    { value: 'ECE', label: 'Electronics & Communication Engineering' },
    { value: 'EEE', label: 'Electrical & Electronics Engineering' },
    { value: 'CE', label: 'Civil Engineering' },
    { value: 'ME', label: 'Mechanical Engineering' }
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

  if (submitted) {
    return (
      <div className="registration-container">
        <div className="registration-success">
          <div className="success-icon">✅</div>
          <h1>Registration Submitted Successfully!</h1>
          <div className="success-details">
            <p>Your registration request has been received and is pending admin approval.</p>
            
            <div className="submission-info">
              <h3>📧 What happens next?</h3>
              <ul>
                <li>✅ Your request will be reviewed by administration</li>
                <li>✅ You'll receive an email at <strong>{formData.collegeEmail}</strong></li>
                <li>✅ Once approved, you can login using OTP</li>
                <li>✅ Approval typically takes 24-48 hours</li>
              </ul>
            </div>

            <div className="student-summary">
              <h3>📋 Your Submission</h3>
              <div className="summary-grid">
                <div className="summary-item">
                  <strong>Name:</strong> {formData.firstName} {formData.lastName}
                </div>
                <div className="summary-item">
                  <strong>Student ID:</strong> {formData.studentId}
                </div>
                <div className="summary-item">
                  <strong>Email:</strong> {formData.collegeEmail}
                </div>
                <div className="summary-item">
                  <strong>Semester:</strong> Semester {formData.semester}
                </div>
                <div className="summary-item">
                  <strong>Department:</strong> {departments.find(d => d.value === formData.department)?.label}
                </div>
              </div>
            </div>
          </div>

          <div className="success-actions">
            <button 
              onClick={() => window.close()}
              className="primary-button"
            >
              Close Window
            </button>
            <button 
              onClick={() => {
                setSubmitted(false)
                setFormData({
                  firstName: '',
                  lastName: '',
                  collegeEmail: '',
                  phone: '',
                  semester: '',
                  department: '',
                  studentId: ''
                })
              }}
              className="secondary-button"
            >
              Register Another Student
            </button>
          </div>

          <div className="support-info">
            <p>📞 Need help? Contact college administration</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="registration-container">
      <div className="registration-card">
        <div className="registration-header">
          <div className="header-content">
            <div className="logo-section">
              <div className="qr-icon">📱</div>
              <div>
                <h1>Student Self-Registration</h1>
                <p>AuthVision - 5G Lab Face Recognition System</p>
              </div>
            </div>
            <div className="registration-badge">
              🔒 Admin Approval Required
            </div>
          </div>
        </div>

        <div className="registration-info">
          <div className="info-card">
            <h3>🎓 Registration Process</h3>
            <div className="process-steps">
              <div className="step">
                <span className="step-number">1</span>
                <div className="step-content">
                  <strong>Fill Details</strong>
                  <p>Provide your information with college email</p>
                </div>
              </div>
              <div className="step">
                <span className="step-number">2</span>
                <div className="step-content">
                  <strong>Admin Review</strong>
                  <p>Administration verifies your details</p>
                </div>
              </div>
              <div className="step">
                <span className="step-number">3</span>
                <div className="step-content">
                  <strong>Get Approved</strong>
                  <p>Receive confirmation email</p>
                </div>
              </div>
              <div className="step">
                <span className="step-number">4</span>
                <div className="step-content">
                  <strong>OTP Login</strong>
                  <p>Use college email for OTP login</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="registration-form">
          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          <div className="form-section">
            <h3>👤 Personal Information</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="firstName">First Name *</label>
                <input
                  id="firstName"
                  name="firstName"
                  type="text"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your first name"
                  disabled={loading}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="lastName">Last Name *</label>
                <input
                  id="lastName"
                  name="lastName"
                  type="text"
                  value={formData.lastName}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your last name"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="collegeEmail">College Email *</label>
                <input
                  id="collegeEmail"
                  name="collegeEmail"
                  type="email"
                  value={formData.collegeEmail}
                  onChange={handleInputChange}
                  required
                  placeholder="your_id@smit.smu.edu.in"
                  disabled={loading}
                />
                <div className="input-hint">
                  💡 Must be your official college email address
                </div>
              </div>
              
              <div className="form-group">
                <label htmlFor="phone">Phone Number</label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="Enter phone number"
                  disabled={loading}
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>🎓 Academic Information</h3>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="studentId">Student ID *</label>
                <input
                  id="studentId"
                  name="studentId"
                  type="text"
                  value={formData.studentId}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g., 202200085"
                  disabled={loading}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="semester">Semester *</label>
                <select
                  id="semester"
                  name="semester"
                  value={formData.semester}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  className="form-select"
                >
                  {semesters.map(sem => (
                    <option key={sem.value} value={sem.value}>
                      {sem.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group full-width">
                <label htmlFor="department">Department *</label>
                <select
                  id="department"
                  name="department"
                  value={formData.department}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  className="form-select"
                >
                  {departments.map(dept => (
                    <option key={dept.value} value={dept.value}>
                      {dept.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="form-notes">
            <div className="note-card">
              <h4>📝 Important Notes</h4>
              <ul>
                <li>All fields marked with * are mandatory</li>
                <li>Use your official college email address only</li>
                <li>Admin approval is required before you can use the system</li>
                <li>You'll receive email notifications about your approval status</li>
                <li>After approval, use OTP login with your college email</li>
              </ul>
            </div>
          </div>

          <div className="form-actions">
            <button 
              type="submit" 
              className="submit-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinning">⏳</span>
                  Submitting Registration...
                </>
              ) : (
                '📧 Submit for Approval'
              )}
            </button>
          </div>
        </form>

        <div className="registration-footer">
          <p>Made with ❤️ for 5G Lab by ArpanCodec</p>
          <p className="footer-note">
            This registration requires admin approval. You'll be notified via email.
          </p>
        </div>
      </div>
    </div>
  )
}

export default StudentSelfRegistration