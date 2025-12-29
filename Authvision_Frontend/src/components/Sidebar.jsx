import React, { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../services/apiClient'

const Sidebar = () => {
  const { user } = useAuthStore()

  const menuItems = [
    // 🆕 ADMIN DASHBOARD - ADMIN ONLY
    {
      path: '/admin',
      material: 'dashboard',
      label: 'Admin Dashboard',
      roles: ['admin'],
      description: 'Manage registrations and users',
      isNew: true
    },
    {
      path: '/class',
      material: 'class',
      label: 'Class Attendance',
      roles: ['admin', 'operator'],
      description: 'Real-time class monitoring'
    },
    {
      path: '/registration',
      material: 'person_add',
      label: 'Student Registration',
      roles: ['admin', 'operator'],
      description: 'Register new students'
    },
    {
      path: '/streams',
      material: 'videocam',
      label: 'Camera Streams',
      roles: ['admin', 'operator'],
      description: 'Manage RTSP / camera streams'
    },
    {
      path: '/students',
      material: 'manage_accounts',
      label: 'Student Management',
      roles: ['admin', 'operator'],
      description: 'View and manage students'
    },
    {
      path: '/reports',
      material: 'analytics',
      label: 'Reports & Analytics',
      roles: ['admin', 'operator'],
      description: 'Attendance reports and insights'
    },
    {
      path: '/subjects',
      material: 'menu_book',
      label: 'Subject Management',
      roles: ['admin'],
      description: 'Manage subjects and curriculum'
    },
    {
      path: '/faculty/register',
      material: 'person_add',
      label: 'Faculty Registration',
      roles: ['admin'],
      description: 'Create faculty accounts'
    },
    {
      path: '/student-dashboard',
      material: 'school',
      label: 'My Attendance',
      roles: ['student'],
      description: 'View your attendance records'
    }
  ]

  const filteredMenuItems = menuItems.filter(item => item.roles.includes(user?.role))
  const location = useLocation()
  const [me, setMe] = useState(null)

  const getRoleBadge = () => {
    switch (user?.role) {
      case 'admin':
        return 'System Admin'
      case 'operator':
        return 'Attendance Operator'
      case 'student':
        return 'Student'
      default:
        return 'User'
    }
  }

  const getRolePermissions = () => {
    switch(user?.role) {
      case 'admin':
        return 'Full system access • Manage operators • All features'
      case 'operator':
        return 'Student management • Attendance tracking • Basic reports'
      case 'student':
        return 'View attendance only • Personal dashboard'
      default:
        return 'Limited access'
    }
  }

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const resp = await apiClient.getMe().catch(() => null)
        if (mounted && resp) setMe(resp)
      } catch (e) {
        // ignore
      }
    })()
    return () => { mounted = false }
  }, [])

  return (
    <aside className="w-72 bg-surface-white border-r border-slate-200 flex flex-col fixed h-full z-20 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.05)]">
      <div className="p-4 border-b border-slate-100">
        <div className="text-sm font-bold text-slate-900">AuthVision - 5G Lab</div>
      </div>
      <div className="p-6 border-b border-slate-100">
        <div className="flex items-center gap-4 mb-4">
          <div className="relative">
            <img
              alt="User"
              className="w-12 h-12 rounded-full ring-2 ring-accent ring-offset-2 ring-offset-white object-cover"
              src={user?.avatar || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user?.name || 'User')}
            />
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800">Welcome,</h2>
            <p className="text-xs text-primary font-semibold flex items-center gap-1">
              <span className="material-icons-round text-sm">verified</span>
              {me?.name || user?.name || getRoleBadge()}
            </p>
          </div>
        </div>
        <div className="text-xs text-slate-500 space-y-1">
          <p className="flex items-center gap-2">
            <span className="material-icons-round text-amber-500 text-sm">military_tech</span>
            {getRoleBadge()}
          </p>
          <p className="pl-6">{getRolePermissions()}</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {filteredMenuItems.map((item) => {
          const active = location.pathname === item.path || location.pathname.startsWith(item.path + '/')
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`group flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${active ? 'bg-cyan-50 text-cyan-700 border border-cyan-100 shadow-sm' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
              title={item.description}
            >
              {item.material ? (
                <span className="material-icons-round text-slate-400 group-hover:text-primary transition-colors" aria-hidden>{item.material}</span>
              ) : (
                <span className="text-slate-400">{item.icon}</span>
              )}

              <div className="flex-1">
                <p className={`sidebar-label ${active ? 'font-bold' : ''}`}>{item.label}</p>
                <p className="text-[10px] text-slate-400 font-normal">{item.description}</p>
              </div>

              {active && <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-slate-100">
        <button 
          onClick={async () => {
            const { logout } = useAuthStore.getState();
            await logout();
            window.location.href = '/login';
          }}
          className="flex items-center gap-2 text-xs font-medium text-slate-500 hover:text-red-600 transition-colors w-full px-2 py-2 rounded-lg hover:bg-red-50"
        >
          <span className="material-icons-round text-base">logout</span> Sign Out
        </button>
      </div>
    </aside>
  )
}

export default Sidebar