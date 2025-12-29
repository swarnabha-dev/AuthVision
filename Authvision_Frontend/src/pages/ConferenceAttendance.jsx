import React, { useState, useEffect } from 'react'
import { 
  Users, 
  UserCheck, 
  UserX, 
  Shield,
  ShieldOff,
  Camera,
  RefreshCw,
  Download
} from 'lucide-react'
import { recognitionClient } from '../services/recognitionClient'
import { apiClient } from '../services/apiClient'

const ConferenceAttendance = () => {
  const [conferenceData, setConferenceData] = useState(null)
  const [isScanning, setIsScanning] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)

  const mockConferenceData = {
    totalAttendees: 127,
    authorized: 118,
    unauthorized: 9,
    guests: 15,
    participants: [
      { id: 1, name: 'Dr. Sarah Chen', type: 'authorized', time: '10:00 AM' },
      { id: 2, name: 'Unknown Person', type: 'unauthorized', time: '10:05 AM' },
      { id: 3, name: 'Mark Wilson (Guest)', type: 'guest', time: '10:10 AM' },
      { id: 4, name: 'Prof. James Brown', type: 'authorized', time: '10:15 AM' },
    ],
    trends: {
      hourly: [25, 48, 76, 95, 112, 127],
      authorizedRate: 93
    }
  }

  useEffect(() => {
    (async () => {
      try {
        // Try backend endpoints for conference attendance
        const resp = await apiClient.apiGet('/conferences/current')
        if (resp) {
          setConferenceData(resp)
          return
        }
      } catch (e) {
        try {
          const resp2 = await apiClient.apiGet('/conference/attendance')
          if (resp2) {
            setConferenceData(resp2)
            return
          }
        } catch (e2) {
          // ignore and fall back
        }
      }

      setConferenceData(mockConferenceData)
    })()
  }, [])

  const startConferenceScan = async () => {
    setIsScanning(true)
    setCameraActive(true)
    
    try {
      const result = await recognitionClient.recognizeFace('mock-conference-image')
      
      if (result.recognized) {
        console.log('Attendee recognized:', result.userId)
      } else {
        console.log('Unknown attendee - checking authorization')
      }
    } catch (error) {
      console.error('Conference scan failed:', error)
    } finally {
      setIsScanning(false)
      // Keep camera active for continuous scanning in real implementation
    }
  }

  const stopConferenceScan = () => {
    setIsScanning(false)
    setCameraActive(false)
  }

  const getAttendeeIcon = (type) => {
    switch (type) {
      case 'authorized': return <Shield className="status-authorized" />
      case 'unauthorized': return <ShieldOff className="status-unauthorized" />
      case 'guest': return <UserCheck className="status-guest" />
      default: return <Users />
    }
  }

  const exportAttendance = () => {
    // Mock export functionality
    console.log('Exporting conference attendance...')
  }

  if (!conferenceData) {
    return <div className="loading">Loading conference data...</div>
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Conference Attendance</h1>
        <p>Access control and participant tracking</p>
      </div>

      {/* Conference Controls */}
      <div className="action-section">
        <div className="conference-controls">
          <div className="camera-section">
            <div className="camera-placeholder conference-camera">
              {cameraActive ? (
                <div className="camera-feed">
                  <div className="scanning-overlay">
                    <RefreshCw className="spinning" />
                    <p>Monitoring conference entrance...</p>
                  </div>
                  <div className="camera-frame">
                    [Conference Camera Feed - Recognition algo will be plugged here]
                  </div>
                </div>
              ) : (
                <div className="camera-prompt">
                  <Camera size={48} />
                  <p>Start monitoring to track conference attendees</p>
                </div>
              )}
            </div>
            
            <div className="control-buttons">
              <button 
                onClick={startConferenceScan}
                disabled={isScanning}
                className={`primary-button ${isScanning ? 'loading' : ''}`}
              >
                {isScanning ? 'Monitoring...' : 'Start Monitoring'}
              </button>
              
              {cameraActive && (
                <button 
                  onClick={stopConferenceScan}
                  className="secondary-button"
                >
                  Stop Monitoring
                </button>
              )}
              
              <button 
                onClick={exportAttendance}
                className="outline-button"
              >
                <Download size={16} />
                Export Report
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Conference Statistics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <Users className="stat-icon" />
            <span>Total Attendees</span>
          </div>
          <div className="stat-value">{conferenceData.totalAttendees}</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-header">
            <Shield className="stat-icon authorized" />
            <span>Authorized</span>
          </div>
          <div className="stat-value">{conferenceData.authorized}</div>
          <div className="stat-percentage">
            {conferenceData.trends.authorizedRate}%
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-header">
            <ShieldOff className="stat-icon unauthorized" />
            <span>Unauthorized</span>
          </div>
          <div className="stat-value">{conferenceData.unauthorized}</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-header">
            <UserCheck className="stat-icon guest" />
            <span>Guests</span>
          </div>
          <div className="stat-value">{conferenceData.guests}</div>
        </div>
      </div>

      {/* Real-time Attendee List */}
      <div className="attendance-list-section">
        <div className="section-header">
          <h3>Recent Attendees</h3>
          <span className="badge">{conferenceData.participants.length} entries</span>
        </div>
        
        <div className="conference-list">
          {conferenceData.participants.map((attendee) => (
            <div key={attendee.id} className="conference-item">
              <div className="attendee-info">
                {getAttendeeIcon(attendee.type)}
                <div>
                  <div className="attendee-name">{attendee.name}</div>
                  <div className="attendee-time">{attendee.time}</div>
                </div>
              </div>
              
              <div className={`attendee-type type-${attendee.type}`}>
                {attendee.type.toUpperCase()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Security Alerts */}
      {conferenceData.unauthorized > 0 && (
        <div className="security-alert">
          <div className="alert-header">
            <ShieldOff className="alert-icon" />
            <h3>Security Notice</h3>
          </div>
          <p>
            {conferenceData.unauthorized} unauthorized person(s) detected. 
            Please review the attendee list and take appropriate action.
          </p>
        </div>
      )}
    </div>
  )
}

export default ConferenceAttendance