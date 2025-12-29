import React, { useState, useCallback } from 'react';
import './ImageUploader.css';

const ImageUploader = ({ 
  onImagesChange, 
  studentId = '',
  maxSize = 5 * 1024 * 1024, // 5MB
  allowedTypes = ['image/jpeg', 'image/png', 'image/jpg']
}) => {
  const [uploads, setUploads] = useState({
    front: { file: null, preview: null, error: null },
    left: { file: null, preview: null, error: null },
    right: { file: null, preview: null, error: null },
    angled_left: { file: null, preview: null, error: null },
    angled_right: { file: null, preview: null, error: null }
  });

  const [uploadProgress, setUploadProgress] = useState({});
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = (file) => {
    if (!allowedTypes.includes(file.type)) {
      return `Invalid file type: ${file.type}. Allowed: JPEG, PNG`;
    }
    
    if (file.size > maxSize) {
      return `File too large: ${(file.size / 1024 / 1024).toFixed(2)}MB. Max: ${maxSize / 1024 / 1024}MB`;
    }
    
    return null;
  };

  const handleFileSelect = useCallback((angle, file) => {
    const error = validateFile(file);
    
    if (error) {
      setUploads(prev => ({
        ...prev,
        [angle]: { ...prev[angle], error }
      }));
      return;
    }

    // Create preview URL
    const previewUrl = URL.createObjectURL(file);
    
    setUploads(prev => ({
      ...prev,
      [angle]: { 
        file, 
        preview: previewUrl, 
        error: null 
      }
    }));

    // Notify parent component
    if (onImagesChange) {
      const allFiles = { ...uploads, [angle]: { file, preview: previewUrl, error: null } };
      onImagesChange(allFiles);
    }
  }, [uploads, onImagesChange, maxSize, allowedTypes]);

  const handleDrop = useCallback((angle, e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(angle, file);
    }
  }, [handleFileSelect]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleInputChange = (angle, e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(angle, file);
    }
  };

  const removeImage = (angle) => {
    // Revoke object URL to prevent memory leaks
    if (uploads[angle].preview) {
      URL.revokeObjectURL(uploads[angle].preview);
    }
    
    setUploads(prev => ({
      ...prev,
      [angle]: { file: null, preview: null, error: null }
    }));

    // Notify parent
    if (onImagesChange) {
      const allFiles = { ...uploads, [angle]: { file: null, preview: null, error: null } };
      onImagesChange(allFiles);
    }
  };

  const getAngleLabel = (angle) => {
    const labels = {
      front: 'Front Face',
      left: 'Left Profile',
      right: 'Right Profile', 
      angled_left: 'Angled Left',
      angled_right: 'Angled Right'
    };
    return labels[angle] || angle;
  };

  const getAngleDescription = (angle) => {
    const descriptions = {
      front: 'Straight frontal view, face clearly visible',
      left: 'Left side profile, ear to chin visible',
      right: 'Right side profile, ear to chin visible',
      angled_left: '45° angle from left side',
      angled_right: '45° angle from right side'
    };
    return descriptions[angle] || '';
  };

  const allImagesUploaded = Object.values(uploads).every(upload => upload.file !== null);
  const hasErrors = Object.values(uploads).some(upload => upload.error);

  // Cleanup object URLs on unmount
  React.useEffect(() => {
    return () => {
      Object.values(uploads).forEach(upload => {
        if (upload.preview) {
          URL.revokeObjectURL(upload.preview);
        }
      });
    };
  }, []);

  return (
    <div className="image-uploader">
      <div className="uploader-header">
        <h3>Student Enrollment - Image Capture</h3>
        <p>Upload 5 different angle photos for comprehensive facial recognition</p>
        
        {studentId && (
          <div className="student-id-badge">
            Student ID: <strong>{studentId}</strong>
          </div>
        )}
      </div>

      <div className="upload-grid">
        {Object.entries(uploads).map(([angle, upload]) => (
          <div key={angle} className="upload-item">
            <div className="upload-label">
              <span className="angle-name">{getAngleLabel(angle)}</span>
              <span className="angle-description">{getAngleDescription(angle)}</span>
            </div>

            <div
              className={`upload-area ${isDragging ? 'dragging' : ''} ${upload.error ? 'error' : ''} ${upload.file ? 'has-file' : ''}`}
              onDrop={(e) => handleDrop(angle, e)}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              {upload.preview ? (
                <div className="image-preview">
                  <img src={upload.preview} alt={getAngleLabel(angle)} />
                  <button
                    type="button"
                    className="remove-btn"
                    onClick={() => removeImage(angle)}
                    title="Remove image"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="upload-placeholder">
                  <div className="upload-icon">📷</div>
                  <span className="upload-text">Drag & drop or click to upload</span>
                  <span className="upload-hint">JPEG or PNG, max 5MB</span>
                  
                  <input
                    type="file"
                    accept={allowedTypes.join(',')}
                    onChange={(e) => handleInputChange(angle, e)}
                    className="file-input"
                  />
                </div>
              )}
            </div>

            {upload.error && (
              <div className="error-message">
                ❌ {upload.error}
              </div>
            )}

            {uploadProgress[angle] !== undefined && (
              <div className="upload-progress">
                <progress value={uploadProgress[angle]} max="100" />
                <span>{uploadProgress[angle]}%</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="upload-status">
        {allImagesUploaded && !hasErrors ? (
          <div className="status-success">
            ✅ All 5 images ready for enrollment
          </div>
        ) : (
          <div className="status-pending">
            ⚠️ {Object.values(uploads).filter(u => u.file).length}/5 images uploaded
          </div>
        )}
      </div>

      <div className="upload-guidelines">
        <h4>📸 Capture Guidelines:</h4>
        <ul>
          <li>Ensure good lighting without shadows</li>
          <li>Face should be clearly visible without obstructions</li>
          <li>Maintain neutral expression</li>
          <li>Remove glasses, hats, or face coverings</li>
          <li>Use high-quality camera for best results</li>
        </ul>
      </div>
    </div>
  );
};

export default ImageUploader;