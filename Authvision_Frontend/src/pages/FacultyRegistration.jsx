import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import '../styles/ui.css'

const FacultyRegistration = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [name, setName] = useState('')
  const [department, setDepartment] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const depts = await apiClient.getDepartments().catch(() => [])
        if (!mounted) return
        setDepartments(Array.isArray(depts) ? depts : [])
      } catch (e) {
        console.warn('Failed to load departments', e)
      }
    })()
    return () => { mounted = false }
  }, [])

  const validate = () => {
    setError(null)
    if (!username.trim()) return setError('Username is required')
    if (!name.trim()) return setError('Name is required')
    if (!department) return setError('Department is required')
    if (!password) return setError('Password is required')
    if (password !== confirmPassword) return setError('Passwords do not match')
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setMessage(null)
    try {
      const payload = { username: username.trim(), name: name.trim(), department, password }
      const resp = await apiClient.createFaculty(payload)
      setMessage('Faculty created successfully')
      setError(null)
      // Optional: redirect to faculty list
      setTimeout(() => navigate('/faculty'), 800)
    } catch (err) {
      console.error('Failed to create faculty', err)
      setError(err?.message || 'Failed to create faculty')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-800 dark:text-text-dark font-sans min-h-screen transition-colors duration-300 flex items-center justify-center p-6">
      <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        <div className="lg:col-span-2 bg-surface-light dark:bg-surface-dark rounded-xl shadow-subtle border border-border-light dark:border-border-dark p-8 md:p-12 transition-all duration-300">
          <header className="mb-10">
            <h1 style={{color: '#0f172a'}} className="text-3xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <span style={{backgroundColor: 'rgba(14,165,233,0.08)'}} className="p-2 rounded-lg flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="12" cy="12" r="12" fill="rgba(14,165,233,0.08)" />
                  <path d="M12 12c1.657 0 3-1.567 3-3.5S13.657 5 12 5s-3 1.567-3 3.5S10.343 12 12 12zm0 1.5c-2.33 0-7 1.17-7 3.5V19h14v-1c0-2.33-4.67-3.5-7-3.5z" fill="#0ea5e9" />
                </svg>
              </span>
              Register Faculty
            </h1>
            <p style={{color: '#475569'}} className="text-lg leading-relaxed">
              Create a new faculty account for the system. Ensure all details are accurate for face recognition integration.
            </p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-8" method="POST">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label style={{color: '#0f172a'}} className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="username">Username</label>
                <input id="username" name="username" value={username} onChange={e => setUsername(e.target.value)} style={{backgroundColor: '#ffffff', color: '#0f172a'}} className="block w-full px-3 py-3 h-12 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm transition-all" placeholder="eg. faculty01" type="text" />
              </div>

              <div className="space-y-2">
                <label style={{color: '#0f172a'}} className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="fullname">Full Name</label>
                <input id="fullname" name="name" value={name} onChange={e => setName(e.target.value)} style={{backgroundColor: '#ffffff', color: '#0f172a'}} className="block w-full px-3 py-3 h-12 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm transition-all" placeholder="John Doe" type="text" />
              </div>
            </div>

            <div className="space-y-2 group">
                <label style={{color: '#0f172a'}} className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="department">Department</label>
              <div>
                <select id="department" name="department" value={department} onChange={e => setDepartment(e.target.value)} style={{backgroundColor: '#ffffff', color: '#0f172a'}} className="block w-full px-3 py-3 h-12 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm transition-all">
                  <option disabled value="">Select Department</option>
                  {departments.map((d, idx) => {
                    const isString = typeof d === 'string' || typeof d === 'number'
                    const val = isString ? String(d) : (d.code || d.id || d.department || d.name || JSON.stringify(d))
                    const label = isString ? String(d) : (d.name || d.department || d.code || String(d))
                    return <option key={`${val}_${idx}`} value={val}>{label}</option>
                  })}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label style={{color: '#0f172a'}} className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="password">Password</label>
                <input id="password" name="password" type="password" value={password} onChange={e => setPassword(e.target.value)} style={{backgroundColor: '#ffffff', color: '#0f172a'}} className="block w-full px-3 py-3 h-12 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm transition-all" />
              </div>

              <div className="space-y-2">
                <label style={{color: '#0f172a'}} className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="confirm_password">Confirm Password</label>
                <input id="confirm_password" name="confirm_password" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} style={{backgroundColor: '#ffffff', color: '#0f172a'}} className="block w-full px-3 py-3 h-12 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary sm:text-sm transition-all" />
              </div>
            </div>

            <div className="pt-6 flex items-center justify-between border-t border-border-light dark:border-border-dark mt-8">
              <button type="button" onClick={() => navigate(-1)} className="text-slate-600 dark:text-subtext-dark hover:text-slate-900 dark:hover:text-white font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2">Cancel</button>
              <button
                type="submit"
                aria-label="Create Faculty"
                style={{ backgroundColor: '#0ea5e9', color: '#ffffff', boxShadow: '0 8px 24px rgba(14,165,233,0.18)' }}
                className="font-semibold py-3 px-8 rounded-lg transform hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-2"
                disabled={loading}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                {loading ? 'Creating...' : 'Create Faculty'}
              </button>
            </div>
          </form>
        </div>

        <div className="lg:col-span-1 space-y-6">
          <div className="bg-surface-light dark:bg-surface-dark rounded-xl shadow-subtle border border-border-light dark:border-border-dark p-6 transition-all duration-300">
            {/* <h2 className="text-xl font-semibold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-primary"><circle cx="12" cy="12" r="10" stroke="#0ea5e9" strokeWidth="1.5" fill="rgba(14,165,233,0.04)"/><path d="M12 8v4" stroke="#0ea5e9" strokeWidth="1.6" strokeLinecap="round"/><circle cx="12" cy="16" r="0.5" fill="#0ea5e9"/></svg>
              About Faculty
            </h2> */}
            {/* <p className="text-slate-600 dark:text-subtext-dark text-sm leading-relaxed mb-6">
              Faculty profiles grant access to the attendance operator features. Provide a unique username and assign the correct department to ensure proper access controls within the university system.
            </p> */}
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-gray-300 mb-4 opacity-80">Available Departments</h3>
            <ul className="space-y-3">
              {departments.length === 0 ? (
                <li className="text-xs text-muted">No departments available</li>
              ) : (
                departments.map((d, idx) => {
                  const label = typeof d === 'string' ? d : (d.department || d.name || d.code || JSON.stringify(d))
                  const abbr = (label || '').split(' ').map(x => x[0]).join('').slice(0,2).toUpperCase()
                  return (
                    <li key={`dept_${idx}`} className="flex items-center gap-3 p-3 rounded-lg bg-background-light dark:bg-slate-800/50 hover:bg-white dark:hover:bg-slate-700 hover:shadow-sm transition-all cursor-default group border border-transparent hover:border-border-light dark:hover:border-border-dark">
                      <span className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xs font-bold group-hover:scale-110 transition-transform">{abbr}</span>
                      <span className="text-sm font-medium text-slate-800 dark:text-gray-300">{label}</span>
                    </li>
                  )
                })
              )}
            </ul>
          </div>

          {/* <div className="bg-gradient-to-br from-primary to-primary_hover rounded-xl shadow-lg p-6 text-white relative overflow-hidden">
            <div className="relative z-10">
              <h3 className="font-bold text-lg mb-2">Face Recognition Ready</h3>
              <p className="text-blue-50 text-sm mb-4">Upon registration, faculty will be prompted to set up their biometric profile for automated attendance tracking.</p>
              <a className="inline-flex items-center text-xs font-bold uppercase tracking-wide bg-white/20 hover:bg-white/30 backdrop-blur-sm px-3 py-1.5 rounded-full transition-colors" href="#">
                Learn more
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="ml-1"><path d="M5 12h14M13 5l7 7-7 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </a>
            </div>
          </div> */}
        </div>
      </div>
    </div>
  )
}

export default FacultyRegistration
