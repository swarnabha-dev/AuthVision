import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { apiClient } from './services/apiClient'
import Login from './pages/Login'
import ClassAttendance from './pages/ClassAttendance'
import ConferenceAttendance from './pages/ConferenceAttendance'
import Registration from './pages/Registration'
import StudentManagement from './pages/StudentManagement'
import Reports from './pages/Reports'
import StudentDashboard from './pages/StudentDashboard'
import SubjectManagement from './pages/SubjectManagement'
import StudentSelfRegistration from './pages/StudentSelfRegistration' // 🆕 NEW
import AdminDashboard from './pages/AdminDashboard' // 🆕 NEW
import FacultyRegistration from './pages/FacultyRegistration'
import StreamsSettings from './pages/StreamsSettings'
import Sidebar from './components/Sidebar'

function App() {
  const { isAuthenticated, user, initializeAuth, hasHydrated } = useAuthStore()

  // Initialize API client with config
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch('/config.json')
        const config = await response.json()
        // Expose config globally for services that read it directly
        window.__APP_CONFIG__ = config
        apiClient.init(config)
        if (initializeAuth) {
          initializeAuth(config)
        }
      } catch (error) {
        console.error('Failed to load config:', error)
        // Fallback to default config
        const defaultConfig = {
          api: {
            baseURL: 'http://localhost:5000/api',
            timeout: 10000
          },
          websocket: {
            url: 'ws://localhost:5000/ws',
            reconnectInterval: 3000
          },
          features: {
            useMocks: false,
            enableWebSocket: true,
            enableFileUpload: true
          }
        }
        window.__APP_CONFIG__ = defaultConfig
        apiClient.init(defaultConfig)
      }
    }

    loadConfig()
  }, [initializeAuth])

  // Determine default route based on user role
  const getDefaultRoute = () => {
    if (!user) return '/class'
    
    switch (user.role) {
      case 'student':
        return '/student-dashboard'
      case 'admin':
        return '/admin' // 🆕 Admin now starts at Admin Dashboard
      case 'operator':
        return '/class' // Operator starts at Class Attendance
      default:
        return '/class'
    }
  }

  // Wait for store to rehydrate from localStorage before checking auth
  if (!hasHydrated) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#f8fafc' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
          <div style={{ fontSize: '18px', color: '#64748b', fontWeight: '600' }}>Loading...</div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/register" element={<StudentSelfRegistration />} />
        <Route path="*" element={<Login />} />
      </Routes>
    )
  }

  return (
    <div className="app">
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            {/* Default route based on user role */}
            <Route path="/" element={<Navigate to={getDefaultRoute()} replace />} />
            
            {/* ==================== */}
            {/* PUBLIC ROUTES (No Auth Required) */}
            {/* ==================== */}
            <Route path="/register" element={<StudentSelfRegistration />} />
            
            {/* ==================== */}
            {/* ADMIN ONLY ROUTES */}
            {/* ==================== */}
            <Route path="/admin" element={
              user?.role === 'admin' ? 
                <AdminDashboard /> : 
                <Navigate to="/class" replace />
            } />
            
            <Route path="/subjects" element={
              user?.role === 'admin' ? 
                <SubjectManagement /> : 
                <Navigate to="/class" replace />
            } />

            <Route path="/faculty/register" element={
              user?.role === 'admin' ?
                <FacultyRegistration /> :
                <Navigate to="/class" replace />
            } />
            
            {/* ==================== */}
            {/* ADMIN & OPERATOR ROUTES */}
            {/* ==================== */}
            <Route path="/class" element={
              user?.role === 'admin' || user?.role === 'operator' ? 
                <ClassAttendance /> : 
                <Navigate to="/student-dashboard" replace />
            } />
            
            <Route path="/conference" element={
              user?.role === 'admin' || user?.role === 'operator' ? 
                <ConferenceAttendance /> : 
                <Navigate to="/student-dashboard" replace />
            } />
            
            <Route path="/registration" element={
              user?.role === 'admin' || user?.role === 'operator' ? 
                <Registration /> : 
                <Navigate to="/class" replace />
            } />

            <Route path="/streams" element={
              user?.role === 'admin' || user?.role === 'operator' ?
                <StreamsSettings /> :
                <Navigate to="/class" replace />
            } />
            
            <Route path="/students" element={
              user?.role === 'admin' || user?.role === 'operator' ? 
                <StudentManagement /> : 
                <Navigate to="/class" replace />
            } />
            
            <Route path="/reports" element={
              user?.role === 'admin' || user?.role === 'operator' ? 
                <Reports /> : 
                <Navigate to="/student-dashboard" replace />
            } />
            
            {/* ==================== */}
            {/* STUDENT ONLY ROUTES */}
            {/* ==================== */}
            <Route path="/student-dashboard" element={
              user?.role === 'student' ? 
                <StudentDashboard /> : 
                <Navigate to="/class" replace />
            } />
            
            {/* Catch all route - redirect to appropriate default */}
            <Route path="*" element={<Navigate to={getDefaultRoute()} replace />} />
          </Routes>
        </main>
      </div>
      
      {/* Global Footer */}
      <footer className="global-footer">
        <p>Made with ❤️ for 5G Lab by ArpanCodec</p>
        {user && (
          <div className="user-role-badge">
            Logged in as: <span className={`role ${user.role}`}>{user.role}</span>
          </div>
        )}
      </footer>
    </div>
  )
}

export default App