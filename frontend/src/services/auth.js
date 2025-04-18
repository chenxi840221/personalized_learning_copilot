import { apiClient } from './api';

// Login function
export const login = async (username, password) => {
  try {
    // Use URLSearchParams to format data as form data
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await apiClient.post('/token', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to login';
    throw new Error(message);
  }
};

// Register function
export const register = async (userData) => {
  try {
    const response = await apiClient.post('/users/', userData);
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to register';
    throw new Error(message);
  }
};

// Get current user
export const getCurrentUser = async () => {
  try {
    const response = await apiClient.get('/users/me/');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to get user data';
    throw new Error(message);
  }
};

// Logout (client-side only)
export const logout = () => {
  // Nothing to do on server side for JWT auth
  // Token invalidation would be handled by the server
};