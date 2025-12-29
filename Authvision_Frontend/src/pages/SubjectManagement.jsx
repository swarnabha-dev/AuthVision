import React, { useState, useEffect } from 'react';
import { useSubjectsStore } from '../store/subjectsStore';

const SubjectManagement = () => {
  const { 
    subjects, 
    loading, 
    error,
    fetchSubjects,
    addSubject,
    updateSubject,
    deleteSubject 
  } = useSubjectsStore();

  const [departments, setDepartments] = useState([]);

  const [formData, setFormData] = useState({
    subjectCode: '',
    subjectName: '',
    semester: '',
    department: ''
  });
  const [editingId, setEditingId] = useState(null);
  const [isManualEntry, setIsManualEntry] = useState(false);

  useEffect(() => {
    fetchSubjects();
    // fetch department list for dropdown
    (async () => {
      try {
        const list = await (await import('../services/apiClient')).apiClient.getDepartments();
        // Normalize list entries to strings (support [{id,name}] or strings)
        const normalized = Array.isArray(list) ? list.map(item => {
          if (!item) return null;
          if (typeof item === 'string') return item;
          // object: prefer code, then name, then id
          if (item.code) return String(item.code);
          if (item.name) return String(item.name);
          if (item.id) return String(item.id);
          return null;
        }).filter(Boolean) : [];
        setDepartments(normalized.length ? normalized : ['CSE','ECE','ME','EEE']);
      } catch (e) {
        console.error('Failed to load departments', e);
        setDepartments(['CSE','ECE','ME','EEE']);
      }
    })();
  }, [fetchSubjects]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.subjectCode || !formData.subjectName || !formData.semester || !formData.department) {
      alert('Please fill all fields');
      return;
    }

    // Normalize payload to match backend expected fields
    const payload = {
      code: formData.subjectCode,
      name: formData.subjectName,
      department: formData.department,
      semester: Number(formData.semester),
    };

    try {
      if (editingId) {
        await updateSubject(editingId, payload);
        setEditingId(null);
      } else {
        await addSubject(payload);
      }
    } catch (err) {
      // show error and avoid uncaught promise
      console.error('Add/Update subject failed', err);
      alert(err?.message || 'Failed to save subject');
      return;
    }

    setFormData({
      subjectCode: '',
      subjectName: '',
      semester: '',
      department: ''
    });
    setIsManualEntry(false);
  };

  const handleEdit = (subject) => {
    setFormData({
      subjectCode: subject.code ?? subject.subjectCode,
      subjectName: subject.name ?? subject.subjectName,
      semester: subject.semester,
      department: subject.department || ''
    });
    // Use subject code as identifier (DB primary key)
    setEditingId(subject.code ?? subject.subjectCode);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setFormData({
      subjectCode: '',
      subjectName: '',
      semester: '',
      department: ''
    });
    setIsManualEntry(false);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this subject?')) {
      await deleteSubject(id);
    }
  };

  const semesters = [1, 2, 3, 4, 5, 6, 7, 8];

  return (
    <div className="subject-management">
      <div className="page-header">
        <h1>📚 Subject Management</h1>
        <p>Add, edit, or remove subjects from the system</p>
      </div>

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {/* Subject Form */}
      <div className="form-section">
        <h2>{editingId ? 'Edit Subject' : 'Add New Subject'}</h2>
        <form onSubmit={handleSubmit} className="subject-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="semester">Semester *</label>
              <select
                id="semester"
                name="semester"
                value={formData.semester}
                onChange={handleInputChange}
                required
              >
                <option value="">Select Semester</option>
                {semesters.map(sem => (
                  <option key={sem} value={sem}>Semester {sem}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="department">Department *</label>
              <select
                id="department"
                name="department"
                value={formData.department}
                onChange={handleInputChange}
                required
              >
                <option value="">Select department</option>
                {departments.map(dep => (
                  <option key={dep} value={dep}>{dep}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="subjectCode">Subject Code *</label>
              <input
                id="subjectCode"
                type="text"
                name="subjectCode"
                value={formData.subjectCode}
                onChange={handleInputChange}
                placeholder="e.g., CS101"
                required
                disabled={isManualEntry}
              />
            </div>

            <div className="form-group">
              <label htmlFor="subjectName">Subject Name *</label>
              <input
                id="subjectName"
                type="text"
                name="subjectName"
                value={formData.subjectName}
                onChange={handleInputChange}
                placeholder="e.g., Data Structures"
                required
              />
            </div>
          </div>

          <div className="form-actions">
            <button 
              type="submit" 
              className="btn-primary"
              disabled={loading}
            >
              {loading ? 'Saving...' : (editingId ? 'Update Subject' : 'Add Subject')}
            </button>
            
            {editingId && (
              <button 
                type="button" 
                className="btn-secondary"
                onClick={handleCancelEdit}
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Subjects List */}
      <div className="subjects-list-section">
        <h2>Existing Subjects ({subjects.length})</h2>
        
        {loading ? (
          <div className="loading">Loading subjects...</div>
        ) : subjects.length === 0 ? (
          <div className="empty-state">
            📝 No subjects added yet. Start by adding your first subject above.
          </div>
        ) : (
          <div className="subjects-grid">
            {subjects.map((subject, idx) => (
              <div key={subject.code ?? subject.subjectCode ?? idx} className="subject-card">
                <div className="subject-header">
                  <h3>{subject.name ?? subject.subjectName}</h3>
                  <span className="subject-code">{subject.code ?? subject.subjectCode}</span>
                </div>
                <div className="subject-details">
                  <p><strong>Semester:</strong> {subject.semester}</p>
                  <p><strong>Status:</strong> 
                    <span className={`status ${subject.isActive ? 'active' : 'inactive'}`}>
                      {subject.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                </div>
                <div className="subject-actions">
                  <button 
                    onClick={() => handleEdit(subject)}
                    className="btn-edit"
                  >
                    ✏️ Edit
                  </button>
                  <button 
                    onClick={() => handleDelete(subject.code ?? subject.subjectCode)}
                    className="btn-delete"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Entry Option - For Future Use */}
      <div className="manual-entry-section" style={{ display: 'none' }}>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={isManualEntry}
            onChange={(e) => setIsManualEntry(e.target.checked)}
          />
          Manual Subject Entry (Custom Code)
        </label>
        
        {isManualEntry && (
          <div className="manual-entry-fields">
            <input
              type="text"
              placeholder="Enter custom subject code"
              value={formData.subjectCode}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                subjectCode: e.target.value
              }))}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default SubjectManagement;