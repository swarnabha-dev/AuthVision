import { create } from 'zustand';
import { apiClient } from '../services/apiClient';

export const useStreamStore = create((set, get) => ({
  // Available RTSP streams
  availableStreams: [],
  
  // Active stream sessions
  activeSessions: [],
  
  // Stream health monitoring
  streamHealth: {},
  
  // Stream configuration
  streamConfig: {
    quality: 'hd',
    fps: 25,
    modality: 'face',
    confidenceThreshold: 0.7
  },

  // Load available streams from backend
  loadAvailableStreams: async () => {
    try {
      set({ loading: true });
      
      // This endpoint should be provided by backend developer
      // Backend exposes /stream/list
      const streams = await apiClient.listStreams();
      
      set({ 
        availableStreams: streams,
        loading: false 
      });
      
      return streams;
    } catch (error) {
      console.error('Failed to load streams:', error);
      set({ loading: false, error: error.message });
      return [];
    }
  },

  // Create new stream session
  createStreamSession: async (streamData) => {
    try {
      // Start stream via backend: POST /stream/start
      const session = await apiClient.startStream(streamData);

      set((state) => ({
        activeSessions: [...state.activeSessions, session]
      }));

      return session;
    } catch (error) {
      console.error('Failed to create stream session:', error);
      throw error;
    }
  },

  // End stream session
  endStreamSession: async (sessionId) => {
    try {
      // Stop stream via backend: POST /stream/stop with { name }
      await apiClient.stopStream(sessionId);

      set((state) => ({
        activeSessions: state.activeSessions.filter(s => s.id !== sessionId)
      }));

      return true;
    } catch (error) {
      console.error('Failed to end stream session:', error);
      throw error;
    }
  },

  // Update stream configuration
  updateStreamConfig: (newConfig) => {
    set((state) => ({
      streamConfig: { ...state.streamConfig, ...newConfig }
    }));
  },

  // Check stream health
  checkStreamHealth: async (streamUrl) => {
    try {
      // No explicit health endpoint; try getting a snapshot to verify availability
      const name = encodeURIComponent(streamUrl);
      const health = await apiClient.getStreamSnapshotImage(name).catch(err => ({ status: 'error', error: err.message }));
      
      set((state) => ({
        streamHealth: {
          ...state.streamHealth,
          [streamUrl]: health
        }
      }));
      
      return health;
    } catch (error) {
      console.error('Stream health check failed:', error);
      
      set((state) => ({
        streamHealth: {
          ...state.streamHealth,
          [streamUrl]: { status: 'error', error: error.message }
        }
      }));
      
      return { status: 'error', error: error.message };
    }
  },

  // Add manual stream
  addManualStream: (streamUrl, name = '') => {
    const streamName = name || `Camera-${Date.now()}`;
    const newStream = {
      id: `manual-${Date.now()}`,
      url: streamUrl,
      name: streamName,
      type: 'manual',
      status: 'unknown'
    };

    set((state) => ({
      availableStreams: [...state.availableStreams, newStream]
    }));

    return newStream;
  },

  // Remove stream
  removeStream: (streamId) => {
    set((state) => ({
      availableStreams: state.availableStreams.filter(s => s.id !== streamId),
      activeSessions: state.activeSessions.filter(s => s.stream_id !== streamId)
    }));
  },

  // Get stream by ID
  getStreamById: (streamId) => {
    return get().availableStreams.find(s => s.id === streamId);
  },

  // Get active session for stream
  getSessionForStream: (streamId) => {
    return get().activeSessions.find(s => s.stream_id === streamId);
  },

  // Clear all streams and sessions
  clearAll: () => {
    set({
      availableStreams: [],
      activeSessions: [],
      streamHealth: {}
    });
  }
}));