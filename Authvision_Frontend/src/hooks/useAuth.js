import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { authService } from '../services/authService';

export const useAuth = () => {
  const [loading, setLoading] = useState(false);
  const { user, isAuthenticated, login, logout, updateUser } = useAuthStore();

  // Check for existing token on app start
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token && !user) {
        // Token exists but user not in store, validate it
        try {
          const currentUser = authService.getCurrentUser();
          if (currentUser) {
            updateUser(currentUser);
          }
        } catch (error) {
          console.error('Auth validation failed:', error);
          await logout();
        }
      }
    };

    checkAuth();
  }, [user, updateUser, logout]);

  const handleLogin = async (username, password) => {
    setLoading(true);
    try {
      const result = await login(username, password);
      return result;
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error.message || 'Login failed' 
      };
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await logout();
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const refreshAuth = async () => {
    try {
      await authService.refreshToken();
      const currentUser = authService.getCurrentUser();
      updateUser(currentUser);
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      await logout();
      return false;
    }
  };

  const hasRole = (requiredRole) => {
    if (!user) return false;
    return user.role === requiredRole;
  };

  const hasAnyRole = (requiredRoles) => {
    if (!user) return false;
    return requiredRoles.includes(user.role);
  };

  return {
    user,
    isAuthenticated,
    loading,
    login: handleLogin,
    logout: handleLogout,
    refreshToken: refreshAuth,
    hasRole,
    hasAnyRole,
    isAdmin: user?.role === 'admin',
    isOperator: user?.role === 'operator'
  };
};