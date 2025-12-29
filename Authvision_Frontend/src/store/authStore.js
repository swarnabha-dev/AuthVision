import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../services/apiClient'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      hasHydrated: false,

      setHasHydrated: (state) => {
        set({ hasHydrated: state });
      },

      // 🆕 OTP Authentication
      sendOtp: async (collegeEmail) => {
        set({ isLoading: true });
        
        // Mock OTP sending - replace with actual API call
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Validate college email domain
        const validDomains = ['smit.smu.edu.in', 'smu.edu.in'];
        const emailDomain = collegeEmail.split('@')[1];
        
        if (!validDomains.includes(emailDomain)) {
          set({ isLoading: false });
          return { 
            success: false, 
            error: 'Please use your college email address (@smit.smu.edu.in)' 
          };
        }
        
        // Mock: Check if student is approved
        const approvedStudents = [
          'arpan_202200085@smit.smu.edu.in',
          'student1@smit.smu.edu.in', 
          'student2@smit.smu.edu.in'
        ];
        
        if (!approvedStudents.includes(collegeEmail)) {
          set({ isLoading: false });
          return { 
            success: false, 
            error: 'Student not found or registration pending approval' 
          };
        }
        
        // Mock successful OTP send
        set({ isLoading: false });
        return { 
          success: true, 
          message: 'OTP sent to your college email (valid for 24 hours)' 
        };
      },

      verifyOtp: async (collegeEmail, otp) => {
        set({ isLoading: true });
        
        // Mock OTP verification - replace with actual API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock OTP validation (in real app, this would verify against backend)
        if (otp.length !== 6 || !/^\d+$/.test(otp)) {
          set({ isLoading: false });
          return { 
            success: false, 
            error: 'Invalid OTP format' 
          };
        }
        
        // Mock student data based on email
        const studentData = {
          'arpan_202200085@smit.smu.edu.in': {
            id: 'student-uuid-202200085',
            username: 'arpan_202200085',
            role: 'student',
            name: 'Arpan Majumdar',
            email: 'arpan_202200085@smit.smu.edu.in',
            student_id: '202200085',
            semester: '3',
            department: 'CSE',
            registration_status: 'approved',
            approved_at: '2024-01-10'
          },
          'student1@smit.smu.edu.in': {
            id: 'student-uuid-1001',
            username: 'student1',
            role: 'student', 
            name: 'Student One',
            email: 'student1@smit.smu.edu.in',
            student_id: '202400001',
            semester: '2',
            department: 'ECE',
            registration_status: 'approved',
            approved_at: '2024-01-12'
          }
        };
        
        const student = studentData[collegeEmail];
        
        if (student) {
          set({
            accessToken: `mock-jwt-otp-${student.id}`,
            refreshToken: `mock-jwt-refresh-otp-${student.id}`,
            user: student,
            isAuthenticated: true,
            isLoading: false,
          });

          apiClient.setAccessToken(`mock-jwt-otp-${student.id}`);
          return { success: true };
        }
        
        set({ isLoading: false });
        return { 
          success: false, 
          error: 'Invalid OTP or student not found' 
        };
      },

      // 🆕 Enhanced login to support both password and OTP
      login: async (username, password, isOtpLogin = false) => {
        set({ isLoading: true });

        try {
          // OTP Login flow uses existing verifyOtp mock for now
          if (isOtpLogin) {
            const otpResult = await get().verifyOtp(username, password);
            set({ isLoading: false });
            return otpResult;
          }

          // Prepare form data for backend login (FastAPI expects form fields)
          const form = new FormData();
          form.append('username', username);
          form.append('password', password);

          const resp = await apiClient.apiPostForm('/auth/login', form);

          if (resp && resp.access_token) {
            const access = resp.access_token;
            const refresh = resp.refresh_token || null;

            // Parse JWT payload to extract basic user info (sub, role)
            const parseJwt = (token) => {
              try {
                const parts = token.split('.');
                if (parts.length !== 3) return null;
                const payload = parts[1];
                const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
                return JSON.parse(decodeURIComponent(escape(decoded)));
              } catch (e) {
                return null;
              }
            };

            const payload = parseJwt(access) || {};
            const user = {
              username: payload.sub || username,
              role: payload.role || 'student',
            };

            set({
              accessToken: access,
              refreshToken: refresh,
              user,
              isAuthenticated: true,
              isLoading: false,
            });

            apiClient.setAccessToken(access);
            // After obtaining tokens, attempt to fetch full user profile
            let fullUser = user;
            try {
              if (user.role === 'student') {
                // Try fetching student profile by reg_no/username
                const studentResp = await apiClient.getStudent(user.username);
                if (studentResp && studentResp.reg_no) {
                  fullUser = { ...studentResp, username: user.username, role: 'student' };
                }
              } else {
                // For non-students, try /auth/me
                try {
                  const me = await apiClient.apiGet('/auth/me');
                  if (me && me.username) {
                    fullUser = { ...me };
                  }
                } catch (e) {
                  // ignore
                }
              }
            } catch (e) {
              console.warn('failed to fetch full profile after login', e);
            }

            set({
              accessToken: access,
              refreshToken: refresh,
              user: fullUser,
              isAuthenticated: true,
              isLoading: false,
            });

            apiClient.setAccessToken(access);
            return { success: true };
          }

          set({ isLoading: false });
          return { success: false, error: 'Invalid login response' };
        } catch (error) {
          set({ isLoading: false });
          return { success: false, error: error?.message || 'Login failed' };
        }
      },

      logout: async () => {
        // Call backend logout endpoint to revoke tokens
        try {
          const { refreshToken } = get();
          if (refreshToken) {
            await apiClient.logout(refreshToken);
          }
        } catch (error) {
          console.warn('Backend logout failed:', error);
          // Continue with frontend logout even if backend fails
        }
        
        // Clear frontend state
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
        
        apiClient.setAccessToken(null);
      },

      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken });
        apiClient.setAccessToken(accessToken);
      },

      refreshTokens: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return false;

        try {
          const form = new FormData();
          form.append('refresh_token', refreshToken);

          const resp = await apiClient.apiPostForm('/auth/refresh', form);
          if (resp && resp.access_token) {
            const access = resp.access_token;
            const refresh = resp.refresh_token || refreshToken;

            // update store and apiClient
            set({ accessToken: access, refreshToken: refresh });
            apiClient.setAccessToken(access);
            return true;
          }
          return false;
        } catch (e) {
          console.warn('token refresh failed', e);
          // token refresh failed -> logout
          get().logout();
          return false;
        }
      },

      // 🆕 Student Registration Status Check
      checkRegistrationStatus: async (collegeEmail) => {
        // Mock registration status check
        await new Promise(resolve => setTimeout(resolve, 800));
        
        const registrationStatus = {
          'pending_student@smit.smu.edu.in': 'pending',
          'rejected_student@smit.smu.edu.in': 'rejected',
          'arpan_202200085@smit.smu.edu.in': 'approved',
          'student1@smit.smu.edu.in': 'approved'
        };
        
        return registrationStatus[collegeEmail] || 'not_found';
      },

      // 🆕 Get current user's registration status
      getRegistrationStatus: () => {
        const { user } = get();
        return user?.registration_status || 'unknown';
      },

      // Check if user has specific role
      hasRole: (role) => {
        const { user } = get();
        return user?.role === role;
      },

      // Check if user has any of the specified roles
      hasAnyRole: (roles) => {
        const { user } = get();
        return roles.includes(user?.role);
      },

      // Check if user is admin
      isAdmin: () => {
        const { user } = get();
        return user?.role === 'admin';
      },

      // Check if user is operator
      isOperator: () => {
        const { user } = get();
        return user?.role === 'operator';
      },

      // Check if user is student
      isStudent: () => {
        const { user } = get();
        return user?.role === 'student';
      },

      // 🆕 Check if student registration is approved
      isStudentApproved: () => {
        const { user } = get();
        return user?.role === 'student' && user?.registration_status === 'approved';
      },

      // 🆕 Get student details
      getStudentDetails: () => {
        const { user } = get();
        if (user?.role === 'student') {
          return {
            name: user.name,
            studentId: user.student_id,
            email: user.email,
            semester: user.semester,
            department: user.department,
            registrationStatus: user.registration_status
          };
        }
        return null;
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken, 
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      version: 3, // Increased version to persist isAuthenticated
      
      // 🆕 Migration for existing users
      migrate: (persistedState, version) => {
        if (version === 0 || version === 1) {
          // Add registration_status to existing student user
          if (persistedState.user?.role === 'student') {
            persistedState = {
              ...persistedState,
              user: {
                ...persistedState.user,
                registration_status: 'approved' // Assume existing students are approved
              }
            };
          }
        }
        if (version < 3) {
          // Ensure isAuthenticated is properly set from tokens
          persistedState = {
            ...persistedState,
            isAuthenticated: !!(persistedState.accessToken && persistedState.user)
          };
        }
        return persistedState;
      },
      onRehydrateStorage: () => (state) => {
        // Called after state is rehydrated from storage
        if (state) {
          state.hasHydrated = true;
          // Restore access token to apiClient if it exists
          if (state.accessToken) {
            apiClient.setAccessToken(state.accessToken);
          }
        }
      }
    }
  )
);

// Helper to wait for hydration
useAuthStore.subscribe(
  (state) => state.hasHydrated,
  (hasHydrated) => {
    if (hasHydrated) {
      console.log('Auth store rehydrated');
    }
  }
);