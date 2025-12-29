import { useEffect, useRef } from 'react';
import { useAttendanceStore } from '../store/attendanceStore';

export const useWebSocket = () => {
  const initialized = useRef(false);
  const {
    initializeWebSocket,
    cleanup,
    connectionStatus,
    detections,
    isStreaming,
    stats
  } = useAttendanceStore();

  useEffect(() => {
    if (!initialized.current) {
      console.log('🔌 Initializing WebSocket hook...');
      initializeWebSocket();
      initialized.current = true;
    }

    return () => {
      console.log('🧹 Cleaning up WebSocket hook...');
      // Don't cleanup here - let the store handle persistent connection
      // cleanup();
    };
  }, [initializeWebSocket]);

  return {
    connectionStatus,
    detections,
    isStreaming,
    stats,
    startRecognition: useAttendanceStore.getState().startRecognition,
    stopRecognition: useAttendanceStore.getState().stopRecognition,
    clearDetections: useAttendanceStore.getState().clearDetections,
    getRecentDetections: useAttendanceStore.getState().getRecentDetections
  };
};