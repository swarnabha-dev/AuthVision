import React, { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../services/apiClient'

const Login = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const login = useAuthStore((state) => state.login)

  const handlePasswordLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    const result = await login(username, password)
    if (!result.success) setError(result.error)
    setLoading(false)
  }

  // Admin registration (uses backend /auth/register expecting Form fields)
  const [showRegister, setShowRegister] = useState(false)
  const [regUsername, setRegUsername] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('')
  const [regLoading, setRegLoading] = useState(false)
  const [regError, setRegError] = useState('')
  const [regSuccess, setRegSuccess] = useState('')

  const registerAdmin = async (ev) => {
    ev.preventDefault()
    setRegError('')
    setRegSuccess('')
    if (!regUsername || !regPassword) return setRegError('username and password required')
    if (regPassword !== regPasswordConfirm) return setRegError('passwords do not match')
    setRegLoading(true)
    try {
      const fd = new FormData()
      fd.append('username', regUsername)
      fd.append('password', regPassword)
      fd.append('role', 'admin')
      const resp = await apiClient.apiPostForm('/auth/register', fd)
      setRegSuccess('Admin user created. You may now sign in.')
      setShowRegister(false)
      setRegUsername('')
      setRegPassword('')
      setRegPasswordConfirm('')
    } catch (err) {
      console.error('register failed', err)
      setRegError(err?.message || String(err))
    } finally {
      setRegLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card modern">
        <div className="login-header modern">
          <h1>AuthVision</h1>
          <p className="muted">Face recognition attendance — admin console</p>
        </div>

        <form onSubmit={handlePasswordLogin} className="login-form modern">
          {error && <div className="error-message">❌ {error}</div>}

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Enter username"
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter password"
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="login-button modern" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <button type="button" className="outline-button" onClick={() => setShowRegister(s => !s)}>
            {showRegister ? 'Cancel Admin Registration' : 'Register Admin'}
          </button>
        </div>

        {showRegister && (
          <form onSubmit={registerAdmin} className="login-form" style={{ marginTop: 12 }}>
            {regError && <div className="error-message">❌ {regError}</div>}
            {regSuccess && <div className="status-message success">{regSuccess}</div>}
            <div className="form-group">
              <label htmlFor="regUsername">Admin Username</label>
              <input id="regUsername" value={regUsername} onChange={e => setRegUsername(e.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="regPassword">Password</label>
              <input id="regPassword" type="password" value={regPassword} onChange={e => setRegPassword(e.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="regPasswordConfirm">Confirm Password</label>
              <input id="regPasswordConfirm" type="password" value={regPasswordConfirm} onChange={e => setRegPasswordConfirm(e.target.value)} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="login-button" type="submit" disabled={regLoading}>{regLoading ? 'Creating...' : 'Create Admin'}</button>
              <button type="button" className="secondary-button" onClick={() => setShowRegister(false)} disabled={regLoading}>Close</button>
            </div>
          </form>
        )}

        <div className="login-footer modern muted">
          <small>Made with ❤️ for 5G Lab</small>
        </div>
      </div>
    </div>
  )
}

export default Login