import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../services/apiClient'

export const useSubjectsStore = create(
  persist(
    (set, get) => ({
      // State
      subjects: [],
      loading: false,
      error: null,
      lastFetched: null,

      // 🆕 SIMPLIFIED STATE - REMOVED CLASS SCHEDULES
      activeSessions: [],
      todayAttendance: [], // Today's attendance records

      // 🆕 FETCH STUDENTS BY SEMESTER
      fetchStudentsBySemester: async (semester) => {
        set({ loading: true, error: null });
        
        try {
          // Try to fetch from API using apiClient helper
          const response = await apiClient.getStudentsBySemester(semester);
          
          if (response && Array.isArray(response)) {
            return response;
          } else if (response && response.students) {
            return response.students;
          } else {
            // Fallback to mock data
            const mockStudents = [
              {
                id: 'stu1',
                studentId: '2024001',
                firstName: 'Alice',
                lastName: 'Brown',
                semester: semester,
                department: 'CSE',
                email: 'alice@college.edu',
                isActive: true
              },
              {
                id: 'stu2',
                studentId: '2024002', 
                firstName: 'Bob',
                lastName: 'Johnson',
                semester: semester,
                department: 'CSE',
                email: 'bob@college.edu',
                isActive: true
              },
              {
                id: 'stu3',
                studentId: '2024003',
                firstName: 'Carol',
                lastName: 'Davis',
                semester: semester,
                department: 'ECE',
                email: 'carol@college.edu',
                isActive: true
              },
              {
                id: 'stu4',
                studentId: '2024004',
                firstName: 'John',
                lastName: 'Doe',
                semester: semester,
                department: 'CSE',
                email: 'john@college.edu',
                isActive: true
              }
            ];
            
            return mockStudents;
          }
        } catch (error) {
          set({ 
            error: error.message || 'Failed to fetch students',
            loading: false 
          });
          throw error;
        }
      },

      // 🆕 CREATE SUBJECT ATTENDANCE SESSION
      createAttendanceSession: async (semester, subject) => {
        set({ loading: true, error: null });
        
        try {
          const sessionData = {
            semester: semester,
            subjectId: subject.id,
            subjectCode: subject.subjectCode,
            subjectName: subject.subjectName,
            timestamp: new Date().toISOString(),
            sessionToken: `ATTEND_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            startTime: new Date(),
            status: 'active'
          };

          // Try to create session via API (backend: POST /attendance/start)
          try {
            const response = await apiClient.createAttendanceSession(sessionData);
            // apiClient.createAttendanceSession returns backend response or throws
            if (response) {
              // backend returns started session info
              set(state => ({
                activeSessions: [...state.activeSessions, response],
                loading: false
              }));
              return response;
            }
          } catch (e) {
            // continue to fallback
            console.warn('createAttendanceSession API failed, falling back to local', e);
          }

          // Fallback to local state
          set(state => ({
            activeSessions: [...state.activeSessions, sessionData],
            loading: false
          }));
          return sessionData;
        } catch (error) {
          set({ 
            error: error.message || 'Failed to create attendance session',
            loading: false 
          });
          throw error;
        }
      },

      // 🆕 MARK SUBJECT ATTENDANCE
      markSubjectAttendance: async (sessionToken, studentId, subjectId, recognitionData = {}) => {
        set({ loading: true, error: null });
        
        try {
          const attendanceRecord = {
            sessionToken,
            studentId,
            subjectId,
            timestamp: new Date().toISOString(),
            status: 'present',
            recognitionData: {
              confidence: recognitionData.confidence || 0,
              method: recognitionData.method || 'face_recognition',
              ...recognitionData
            }
          };

          // Try to mark attendance via API
          const response = await apiClient.apiPost('/attendance/mark-subject', attendanceRecord);
          
          if (response && response.attendance) {
            // Update today's attendance locally
            set(state => ({
              todayAttendance: [...state.todayAttendance, response.attendance],
              loading: false
            }));
            return response.attendance;
          } else {
            // Fallback to local state
            const mockAttendance = {
              id: `att_${Date.now()}`,
              ...attendanceRecord,
              studentName: `Student ${studentId}`,
              subjectName: 'Current Subject'
            };
            
            set(state => ({
              todayAttendance: [...state.todayAttendance, mockAttendance],
              loading: false
            }));
            return mockAttendance;
          }
        } catch (error) {
          set({ 
            error: error.message || 'Failed to mark attendance',
            loading: false 
          });
          throw error;
        }
      },

      // 🆕 END ATTENDANCE SESSION
      endAttendanceSession: async (sessionToken) => {
        set({ loading: true, error: null });
        
        try {
          // Try to end session via API (backend: POST /attendance/stop)
          await apiClient.endAttendanceSession();
          
          // Update local state
          set(state => ({
            activeSessions: state.activeSessions.filter(session => 
              session.sessionToken !== sessionToken
            ),
            loading: false
          }));
          return true;
        } catch (error) {
          // Fallback to local state update
          set(state => ({
            activeSessions: state.activeSessions.filter(session => 
              session.sessionToken !== sessionToken
            ),
            loading: false
          }));
          return true;
        }
      },

      // 🆕 GET ACTIVE SESSION
      getActiveSession: (sessionToken) => {
        const { activeSessions } = get();
        return activeSessions.find(session => session.sessionToken === sessionToken);
      },

      // 🆕 GET TODAY'S SUBJECT ATTENDANCE
      getTodaySubjectAttendance: (subjectId) => {
        const { todayAttendance } = get();
        return todayAttendance.filter(record => 
          record.subjectId === subjectId
        );
      },

      // 🆕 VALIDATE STUDENT FOR SEMESTER
      validateStudentForSemester: async (studentId, semester) => {
        try {
          // Check if student belongs to the selected semester
          const response = await apiClient.apiGet(`/students/${studentId}/validate-semester?semester=${semester}`);
          
          if (response && response.valid !== undefined) {
            return response.valid;
          } else {
            // Mock validation - in real app, this would check student's semester
            return true; // For demo purposes
          }
        } catch (error) {
          console.error('Validation failed:', error);
          return false;
        }
      },

      // ========== EXISTING SUBJECT METHODS (PRESERVED) ==========

      // FETCH ALL SUBJECTS
      fetchSubjects: async () => {
        set({ loading: true, error: null });
        
        try {
          const response = await apiClient.getSubjects();
          
          if (response && Array.isArray(response)) {
            set({
              subjects: response,
              loading: false,
              lastFetched: new Date().toISOString()
            });
            return response;
          } else if (response && response.subjects) {
            set({
              subjects: response.subjects,
              loading: false,
              lastFetched: new Date().toISOString()
            });
            return response.subjects;
          } else {
            throw new Error('No subjects data received');
          }
        } catch (error) {
          const mockSubjects = [
            {
              id: '1',
              subjectCode: 'CS101',
              subjectName: 'Data Structures',
              semester: '3',
              isActive: true,
              createdAt: '2024-01-01'
            },
            {
              id: '2', 
              subjectCode: 'CS102',
              subjectName: 'Algorithms',
              semester: '3',
              isActive: true,
              createdAt: '2024-01-01'
            },
            {
              id: '3',
              subjectCode: 'MA101',
              subjectName: 'Mathematics I',
              semester: '1',
              isActive: true,
              createdAt: '2024-01-01'
            },
            {
              id: '4',
              subjectCode: 'PH101',
              subjectName: 'Physics',
              semester: '1',
              isActive: true,
              createdAt: '2024-01-01'
            },
            {
              id: '5',
              subjectCode: 'CS201',
              subjectName: 'Database Systems',
              semester: '4',
              isActive: true,
              createdAt: '2024-01-01'
            },
            {
              id: '6',
              subjectCode: 'CS202',
              subjectName: 'Operating Systems',
              semester: '4',
              isActive: true,
              createdAt: '2024-01-01'
            }
          ];
          
          set({
            subjects: mockSubjects,
            loading: false,
            lastFetched: new Date().toISOString()
          });
          return mockSubjects;
        }
      },

      // ADD NEW SUBJECT
      addSubject: async (subjectData) => {
        set({ loading: true, error: null });

        try {
          // Normalize incoming shapes: support { code,name } or legacy { subjectCode,subjectName }
          const code = (subjectData.code ?? subjectData.subjectCode ?? '').toString().trim();
          const name = (subjectData.name ?? subjectData.subjectName ?? '').toString().trim();
          const semester = subjectData.semester;
          const department = subjectData.department ?? subjectData.dept ?? '';

          if (!code || !name || !semester) {
            throw new Error('Subject code, name, and semester are required');
          }

          const { subjects } = get();
          const duplicate = subjects.find(subject => 
            (subject.code ?? subject.subjectCode)?.toString().toUpperCase() === code.toUpperCase()
          );

          if (duplicate) {
            throw new Error(`Subject with code ${code} already exists`);
          }

          const newSubject = {
            // use code as primary identifier when persisting locally
            code: code.toUpperCase(),
            name,
            department,
            semester: semester,
            isActive: true,
            createdAt: new Date().toISOString()
          };

          const response = await apiClient.createSubject(newSubject);

          if (response && response.subject) {
            set(state => ({
              subjects: [...state.subjects, response.subject],
              loading: false
            }));
            return response.subject;
          } else if (response && Array.isArray(response.subjects)) {
            const added = response.subjects[0];
            set(state => ({
              subjects: [...state.subjects, added],
              loading: false
            }));
            return added;
          } else {
            set(state => ({
              subjects: [...state.subjects, newSubject],
              loading: false
            }));
            return newSubject;
          }
        } catch (error) {
          set({ 
            error: error.message || 'Failed to add subject',
            loading: false 
          });
          throw error;
        }
      },

      // UPDATE EXISTING SUBJECT
      updateSubject: async (subjectId, updatedData) => {
        set({ loading: true, error: null });
        
        try {
          const response = await apiClient.updateSubject(subjectId, updatedData);
          
          if (response && response.subject) {
            set(state => ({
              subjects: state.subjects.map(subject =>
                // match by id or code
                (subject.id === subjectId || subject.code === subjectId || subject.subjectCode === subjectId) ? response.subject : subject
              ),
              loading: false
            }));
            return response.subject;
          } else if (response && response.updated) {
            // backend returned confirmation
            set(state => ({
              subjects: state.subjects.map(subject =>
                (subject.id === subjectId || subject.code === subjectId || subject.subjectCode === subjectId) ? { ...subject, ...updatedData } : subject
              ),
              loading: false
            }));
            return updatedData;
          } else {
            set(state => ({
              subjects: state.subjects.map(subject =>
                (subject.id === subjectId || subject.code === subjectId || subject.subjectCode === subjectId) ? { ...subject, ...updatedData } : subject
              ),
              loading: false
            }));
            return updatedData;
          }
        } catch (error) {
          set({ 
            error: error.message || 'Failed to update subject',
            loading: false 
          });
          throw error;
        }
      },

      // DELETE SUBJECT
      deleteSubject: async (subjectId) => {
        set({ loading: true, error: null });
        
        try {
          await apiClient.deleteSubject(subjectId);
          
          set(state => ({
            subjects: state.subjects.filter(subject => !(subject.id === subjectId || subject.code === subjectId || subject.subjectCode === subjectId)),
            loading: false
          }));
          return true;
        } catch (error) {
          set(state => ({
            subjects: state.subjects.filter(subject => !(subject.id === subjectId || subject.code === subjectId || subject.subjectCode === subjectId)),
            loading: false
          }));
          return true;
        }
      },

      // TOGGLE SUBJECT ACTIVE STATUS
      toggleSubjectStatus: async (subjectId) => {
        const { subjects } = get();
        const subject = subjects.find(s => s.id === subjectId);
        
        if (!subject) {
          set({ error: 'Subject not found' });
          return;
        }

        const updatedData = { isActive: !subject.isActive };
        return get().updateSubject(subjectId, updatedData);
      },

      // GET SUBJECTS BY SEMESTER
      getSubjectsBySemester: (semester) => {
        const { subjects } = get();
        return subjects.filter(subject => 
          subject.semester === semester && subject.isActive
        );
      },

      // GET SUBJECT BY ID
      getSubjectById: (subjectId) => {
        const { subjects } = get();
        return subjects.find(subject => subject.id === subjectId);
      },

      // GET SUBJECT BY CODE
      getSubjectByCode: (subjectCode) => {
        const { subjects } = get();
        return subjects.find(subject => 
          subject.subjectCode === subjectCode.toUpperCase()
        );
      },

      // SEARCH SUBJECTS
      searchSubjects: (query) => {
        const { subjects } = get();
        const searchTerm = query.toLowerCase();
        
        return subjects.filter(subject =>
          subject.subjectCode.toLowerCase().includes(searchTerm) ||
          subject.subjectName.toLowerCase().includes(searchTerm) ||
          subject.semester.includes(searchTerm)
        );
      },

      // GET ALL ACTIVE SUBJECTS
      getActiveSubjects: () => {
        const { subjects } = get();
        return subjects.filter(subject => subject.isActive);
      },

      // GET SUBJECT COUNT BY SEMESTER
      getSubjectCountBySemester: () => {
        const { subjects } = get();
        const countBySemester = {};
        
        subjects.forEach(subject => {
          countBySemester[subject.semester] = (countBySemester[subject.semester] || 0) + 1;
        });
        
        return countBySemester;
      },

      // CLEAR ERROR
      clearError: () => set({ error: null }),

      // REFRESH SUBJECTS
      refreshSubjects: () => {
        return get().fetchSubjects();
      },

      // RESET STORE
      resetStore: () => {
        set({
          subjects: [],
          loading: false,
          error: null,
          lastFetched: null,
          activeSessions: [],
          todayAttendance: []
        });
      }
    }),
    {
      name: 'subjects-storage',
      partialize: (state) => ({
        subjects: state.subjects,
        lastFetched: state.lastFetched
      }),
      version: 3, // Increased version for simplified structure
      
      migrate: (persistedState, version) => {
        if (version === 0) {
          return {
            ...persistedState,
            lastFetched: null
          };
        }
        if (version === 1 || version === 2) {
          // Remove teacherClasses and simplify structure
          const { teacherClasses, ...cleanState } = persistedState;
          return {
            ...cleanState,
            activeSessions: [],
            todayAttendance: []
          };
        }
        return persistedState;
      }
    }
  )
);