import { create } from 'zustand';
import { websocketClient } from '../services/websocketClient';

export const useAttendanceStore = create((set, get) => ({
  // Real-time detection data
  detections: [],
  isStreaming: false,
  currentStream: null,
  connectionStatus: 'disconnected',
  
  // Session management
  activeSessions: [],
  currentSession: null,
  
  // Statistics
  stats: {
    totalDetections: 0,
    recognizedStudents: 0,
    unknownFaces: 0,
    confidence: 0
  },

  // Initialize WebSocket connection
  initializeWebSocket: () => {
    console.log('🔄 Initializing WebSocket for attendance...');
    
    websocketClient.on('connected', (status) => {
      set({ connectionStatus: status ? 'connected' : 'disconnected' });
    });

    websocketClient.on('recognition', (data) => {
      console.log('🎯 Recognition event received:', data);
      
      const newDetections = data.detections || [];
      const currentDetections = get().detections;
      
      // Update statistics
      const stats = get().calculateStats([...newDetections, ...currentDetections]);
      
      set((state) => ({
        detections: [...newDetections, ...state.detections.slice(0, 99)], // Keep last 100
        stats: { ...state.stats, ...stats }
      }));

      // Emit custom event for components to listen to
      window.dispatchEvent(new CustomEvent('new_recognition', { detail: newDetections }));
    });

    websocketClient.on('attendance', (data) => {
      console.log('✅ Attendance marked:', data);
      // Handle attendance confirmation
    });

    websocketClient.on('error', (error) => {
      console.error('❌ WebSocket error in store:', error);
      set({ connectionStatus: 'error' });
    });

    // Connect WebSocket
    websocketClient.connect();
  },

  // Start recognition on a stream
  startRecognition: (streamUrl, modality = 'face') => {
    websocketClient.startRecognition(streamUrl, modality);
    set({ 
      isStreaming: true, 
      currentStream: streamUrl,
      detections: [] // Clear previous detections
    });
  },

  // Stop recognition
  stopRecognition: () => {
    if (get().currentStream) {
      websocketClient.stopRecognition(get().currentStream);
    }
    set({ 
      isStreaming: false, 
      currentStream: null 
    });
  },

  // Add manual detection (for testing)
  addDetection: (detection) => {
    set((state) => ({
      detections: [detection, ...state.detections.slice(0, 99)]
    }));
  },

  // Clear all detections
  clearDetections: () => set({ detections: [] }),

  // Get recent detections
  getRecentDetections: (limit = 10) => {
    return get().detections.slice(0, limit);
  },

  // Calculate statistics
  calculateStats: (detections) => {
    const recognized = detections.filter(d => d.matched).length;
    const total = detections.length;
    
    return {
      totalDetections: total,
      recognizedStudents: recognized,
      unknownFaces: total - recognized,
      confidence: total > 0 ? detections.reduce((sum, d) => sum + (d.match_confidence || 0), 0) / total : 0
    };
  },

  // Session management
  setActiveSessions: (sessions) => set({ activeSessions: sessions }),
  setCurrentSession: (session) => set({ currentSession: session }),

  // Cleanup
  cleanup: () => {
    websocketClient.disconnect();
    set({
      detections: [],
      isStreaming: false,
      currentStream: null,
      connectionStatus: 'disconnected'
    });
  }
}));