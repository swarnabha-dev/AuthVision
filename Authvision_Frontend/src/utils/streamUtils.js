// Utility functions for handling RTSP streams and video configurations

export const streamUtils = {
  // Validate RTSP URL format
  validateRTSPUrl: (url) => {
    if (!url) return false;
    
    try {
      const rtspPattern = /^rtsp:\/\/([a-zA-Z0-9.-]+)(?::(\d+))?(\/.*)?$/;
      const isValid = rtspPattern.test(url);
      
      if (!isValid) {
        console.warn('Invalid RTSP URL format:', url);
      }
      
      return isValid;
    } catch (error) {
      console.error('URL validation error:', error);
      return false;
    }
  },

  // Generate WebSocket URL for video streaming (if backend provides conversion)
  generateStreamWebSocketUrl: (rtspUrl) => {
    if (!rtspUrl) return null;
    
    try {
      // Backend developer should provide the actual conversion endpoint
      // This is a placeholder implementation
      const encodedUrl = encodeURIComponent(rtspUrl);
      return `/api/stream/proxy?url=${encodedUrl}`;
    } catch (error) {
      console.error('Stream URL generation error:', error);
      return null;
    }
  },

  // Extract camera ID from RTSP URL
  extractCameraId: (rtspUrl) => {
    if (!rtspUrl) return 'unknown-camera';
    
    try {
      const url = new URL(rtspUrl);
      const pathParts = url.pathname.split('/').filter(part => part.length > 0);
      
      if (pathParts.length > 0) {
        return pathParts[pathParts.length - 1];
      }
      
      // Fallback to hostname if no path
      return url.hostname || 'unknown-camera';
    } catch (error) {
      console.error('Camera ID extraction error:', error);
      return 'unknown-camera';
    }
  },

  // Format detection data for display
  formatDetection: (detection) => {
    if (!detection) return null;
    
    return {
      id: detection.student_id || `unknown-${Date.now()}-${Math.random()}`,
      studentId: detection.student_id || 'Unknown',
      studentName: detection.student_name || 'Unknown Student',
      confidence: detection.match_confidence ? (detection.match_confidence * 100).toFixed(1) + '%' : '0%',
      modality: detection.match_modality || 'face',
      timestamp: detection.frame_time || new Date().toISOString(),
      bbox: detection.bbox || [0, 0, 100, 100],
      thumbnail: detection.thumbnail_url || '',
      models: detection.models_used || {},
      matched: detection.matched || false
    };
  },

  // Calculate stream health metrics (mock implementation)
  getStreamHealth: async (streamUrl) => {
    // Backend developer would implement actual health check
    // This is a mock implementation for UI development
    
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockHealth = {
          status: Math.random() > 0.2 ? 'healthy' : 'degraded',
          latency: `${Math.floor(Math.random() * 200) + 50}ms`,
          fps: Math.floor(Math.random() * 10) + 20,
          resolution: '1920x1080',
          bitrate: `${Math.floor(Math.random() * 2000) + 1000}kbps`,
          timestamp: new Date().toISOString()
        };
        resolve(mockHealth);
      }, 500);
    });
  },

  // Generate unique session ID
  generateSessionId: () => {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  // Calculate optimal stream quality based on network conditions
  getOptimalStreamQuality: (networkSpeed) => {
    if (networkSpeed > 10) return 'hd'; // >10 Mbps
    if (networkSpeed > 5) return 'sd';  // >5 Mbps
    if (networkSpeed > 2) return 'low'; // >2 Mbps
    return 'very_low'; // <=2 Mbps
  },

  // Parse modality from detection data
  parseModality: (detection) => {
    const modality = detection.match_modality?.toLowerCase() || 'face';
    
    const modalityMap = {
      'face': 'Facial',
      'body': 'Body Shape', 
      'periocular': 'Eye Region',
      'fused': 'Multi-modal',
      'gait': 'Walking Pattern'
    };
    
    return modalityMap[modality] || modality;
  },

  // Format timestamp for display
  formatDetectionTime: (timestamp) => {
    if (!timestamp) return 'Unknown time';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: true,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (error) {
      return 'Invalid time';
    }
  },

  // Check if detection is recent (within last 30 seconds)
  isRecentDetection: (detection, thresholdSeconds = 30) => {
    if (!detection.timestamp && !detection.frame_time) return false;
    
    try {
      const detectionTime = new Date(detection.timestamp || detection.frame_time);
      const now = new Date();
      const diffSeconds = (now - detectionTime) / 1000;
      
      return diffSeconds <= thresholdSeconds;
    } catch (error) {
      return false;
    }
  },

  // Group detections by student
  groupDetectionsByStudent: (detections) => {
    const grouped = {};
    
    detections.forEach(detection => {
      const studentId = detection.student_id || 'unknown';
      
      if (!grouped[studentId]) {
        grouped[studentId] = {
          studentId,
          studentName: detection.student_name || 'Unknown',
          detections: [],
          firstSeen: detection.timestamp || detection.frame_time,
          lastSeen: detection.timestamp || detection.frame_time,
          confidence: 0
        };
      }
      
      grouped[studentId].detections.push(detection);
      grouped[studentId].lastSeen = detection.timestamp || detection.frame_time;
      
      // Update average confidence
      const confidences = grouped[studentId].detections
        .map(d => d.match_confidence || 0)
        .filter(c => c > 0);
      
      if (confidences.length > 0) {
        grouped[studentId].confidence = confidences.reduce((a, b) => a + b) / confidences.length;
      }
    });
    
    return Object.values(grouped);
  }
};

export default streamUtils;