import React, { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { apiClient } from '../services/apiClient'

const Topbar = () => {
  const { user, logout } = useAuthStore()
  const [cameraStatus, setCameraStatus] = useState('checking')

  useEffect(() => {
    checkCameraStatus()
  }, [])

  const checkCameraStatus = async () => {
    try {
      // Query active streams from backend; if any stream is running, mark camera connected
      const streams = await apiClient.listStreams()
      // streams may be array of { name, url, status } or names; handle both
      const running = Array.isArray(streams) && streams.some(s => {
        if (!s) return false
        if (typeof s === 'string') return true
        return s.status === 'running' || s.is_active || s.active === true
      })
      setCameraStatus(running ? 'connected' : 'disconnected')
    } catch (error) {
      console.error('Camera status check failed:', error)
      setCameraStatus('error')
    }
  }

  const getCameraStatusIcon = () => {
    switch (cameraStatus) {
      case 'connected': return '🟢'
      case 'disconnected': return '🔴'
      case 'error': return '🟡'
      default: return '⚪'
    }
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h2>AuthVision - 5G Lab</h2>
      </div>
      
      <div className="topbar-right">
        <div className="camera-status">
          <span className={`status-indicator ${cameraStatus}`}>
            {getCameraStatusIcon()} Camera
          </span>
          <button 
            onClick={checkCameraStatus}
            className="status-refresh-button"
            title="Refresh camera status"
          >
            🔄
          </button>
        </div>
        
        <div className="lab-credit">
          <span>5G Lab | ArpanCodec</span>
        </div>
        
        <div className="user-info">
          <span className="user-icon">👤</span>
          <span>{user?.name} ({user?.role})</span>
        </div>
        
        <button 
          onClick={async () => {
            await logout();
            window.location.href = '/login';
          }}
          className="logout-button"
          title="Logout"
        >
          <span className="logout-icon">🚪</span>
        </button>
      </div>
    </header>
  )
}

export default Topbar