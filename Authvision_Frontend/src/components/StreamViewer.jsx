import React, { useRef, useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useStreamStore } from '../store/streamStore';

// Inline minimal styles for StreamViewer (keeps styling self-contained)
const _streamViewerStyles = `
.stream-viewer { display:block; background:transparent; padding:8px; border-radius:8px }
.stream-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px }
.stream-status { display:flex; gap:8px; align-items:center }
.status-indicator { font-size:12px; padding:4px 8px; border-radius:999px; background:#111827; color:#fff }
.status-indicator.connected { background:#10b981 }
.status-indicator.disconnected { background:#f97316 }
.video-container { position:relative; background:#000; border-radius:8px; overflow:hidden }
.video-element { width:100%; height:360px; object-fit:cover; background:#000 }
.detection-overlay { position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none }
.stream-loading, .stream-error { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:#fff; background:rgba(0,0,0,0.45) }
.stream-controls { display:flex; gap:8px; margin-top:8px; justify-content:flex-end }
.btn { padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06); background:#111827; color:#fff; cursor:pointer }
.btn:disabled { opacity:0.5; cursor:not-allowed }
.btn.btn-outline { background:transparent; border:1px solid rgba(255,255,255,0.08) }
.detection-stats { margin-top:10px; background:rgba(255,255,255,0.02); padding:8px; border-radius:8px }
.stats-grid { display:flex; gap:12px }
.stat-item { text-align:center }
.stat-value { font-weight:700; font-size:18px }
.stat-label { font-size:12px; color:rgba(255,255,255,0.6) }
`;

const StreamViewer = ({ 
  streamUrl, 
  streamName = 'Live Camera Feed',
  showControls = true,
  autoStart = false,
  onDetection = null 
}) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState(null);
  const [detectionOverlays, setDetectionOverlays] = useState([]);

  const { 
    startRecognition, 
    stopRecognition, 
    isStreaming, 
    detections,
    connectionStatus 
  } = useWebSocket();

  const { streamConfig } = useStreamStore();

  // Initialize video stream
  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;

    const initializeStream = async () => {
      try {
        setError(null);
        
        // For RTSP streams, we typically need a backend proxy or conversion to HLS
        // Backend developer should provide the actual stream URL format
        const videoElement = videoRef.current;
        
        // This is a simplified implementation
        // Backend developer should provide proper stream handling
        videoElement.src = streamUrl;
        
        videoElement.onloadeddata = () => {
          console.log('Stream loaded successfully');
          setIsPlaying(true);
          
          if (autoStart) {
            handleStartRecognition();
          }
        };

        videoElement.onerror = () => {
          setError('Failed to load video stream');
          setIsPlaying(false);
        };

        videoElement.onplay = () => setIsPlaying(true);
        videoElement.onpause = () => setIsPlaying(false);

      } catch (err) {
        setError(`Stream initialization failed: ${err.message}`);
        console.error('Stream error:', err);
      }
    };

    initializeStream();

    return () => {
      if (videoRef.current) {
        videoRef.current.src = '';
      }
      if (isStreaming) {
        stopRecognition();
      }
    };
  }, [streamUrl, autoStart]);

  // Handle real-time detection overlays
  useEffect(() => {
    if (!canvasRef.current || !videoRef.current || detections.length === 0) return;

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext('2d');

    // Match canvas size to video
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw detection bounding boxes and labels
    detections.forEach((detection, index) => {
      if (!detection.bbox) return;

      const [x, y, width, height] = detection.bbox;
      const confidence = detection.match_confidence || 0;
      
      // Draw bounding box
      ctx.strokeStyle = confidence > 0.8 ? '#00ff00' : confidence > 0.6 ? '#ffff00' : '#ff0000';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);

      // Draw label background
      const label = detection.student_name || 'Unknown';
      const confidenceText = `${(confidence * 100).toFixed(1)}%`;
      
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      const textWidth = Math.max(
        ctx.measureText(label).width,
        ctx.measureText(confidenceText).width
      ) + 10;
      
      ctx.fillRect(x, y - 40, textWidth, 40);

      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.font = '12px Arial';
      ctx.fillText(label, x + 5, y - 25);
      ctx.fillText(confidenceText, x + 5, y - 10);

      // Call detection callback if provided
      if (onDetection) {
        onDetection(detection);
      }
    });

    setDetectionOverlays(detections);
  }, [detections, onDetection]);

  const handleStartRecognition = () => {
    if (!streamUrl) {
      setError('No stream URL provided');
      return;
    }

    startRecognition(streamUrl, streamConfig.modality);
    setError(null);
  };

  const handleStopRecognition = () => {
    stopRecognition();
  };

  const handleFullscreen = () => {
    if (videoRef.current) {
      if (videoRef.current.requestFullscreen) {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const handleSnapshot = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Draw current frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to data URL and trigger download
    const dataUrl = canvas.toDataURL('image/jpeg');
    const link = document.createElement('a');
    link.download = `snapshot-${Date.now()}.jpg`;
    link.href = dataUrl;
    link.click();
  };

  return (
    <div className="stream-viewer">
      <style dangerouslySetInnerHTML={{ __html: _streamViewerStyles }} />
      <div className="stream-header">
        <h3>{streamName}</h3>
        <div className="stream-status">
          <span className={`status-indicator ${connectionStatus}`}>
            {connectionStatus}
          </span>
          {isStreaming && (
            <span className="recording-indicator">● REC</span>
          )}
        </div>
      </div>

      <div className="video-container">
        <video
          ref={videoRef}
          controls={false}
          autoPlay
          muted
          playsInline
          className="video-element"
        />
        <canvas
          ref={canvasRef}
          className="detection-overlay"
        />
        
        {error && (
          <div className="stream-error">
            <span>❌ {error}</span>
          </div>
        )}

        {!isPlaying && !error && (
          <div className="stream-loading">
            <span>Loading stream...</span>
          </div>
        )}
      </div>

      {showControls && (
        <div className="stream-controls">
          <button
            onClick={handleStartRecognition}
            disabled={isStreaming || !isPlaying}
            className="btn btn-primary"
          >
            ▶ Start Recognition
          </button>
          
          <button
            onClick={handleStopRecognition}
            disabled={!isStreaming}
            className="btn btn-secondary"
          >
            ⏹ Stop Recognition
          </button>
          
          <button
            onClick={handleSnapshot}
            disabled={!isPlaying}
            className="btn btn-outline"
          >
            📸 Snapshot
          </button>
          
          <button
            onClick={handleFullscreen}
            className="btn btn-outline"
          >
            ⛶ Fullscreen
          </button>
        </div>
      )}

      {/* Detection Statistics */}
      {isStreaming && detectionOverlays.length > 0 && (
        <div className="detection-stats">
          <h4>Real-time Detections</h4>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-value">{detectionOverlays.length}</span>
              <span className="stat-label">Total</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">
                {detectionOverlays.filter(d => d.matched).length}
              </span>
              <span className="stat-label">Recognized</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">
                {detectionOverlays.filter(d => !d.matched).length}
              </span>
              <span className="stat-label">Unknown</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StreamViewer;