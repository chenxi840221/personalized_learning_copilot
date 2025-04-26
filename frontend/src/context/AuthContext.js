// frontend/src/context/AuthContext.js
import React, { createContext, useState, useEffect } from 'react';
import { login as apiLogin, register as apiRegister, getCurrentUser, logout as apiLogout } from '../services/auth';

// Create the Auth Context
export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [authInitialized, setAuthInitialized] = useState(false);

  // Check if user is already logged in on initial load
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Get token from local storage
        const token = localStorage.getItem('token');
        
        if (token) {
          console.log('Token found in localStorage, checking user info');
          
          try {
            // Get current user if token exists
            const userData = await getCurrentUser();
            console.log('User data retrieved successfully:', userData);
            setUser(userData);
          } catch (userError) {
            console.error('Error getting user data:', userError);
            // Don't clear token yet, just log the error
            setError('Error getting user profile. Token may be invalid.');
          }
        } else {
          console.log('No authentication token found');
        }
      } catch (err) {
        console.error('Auth check failed:', err);
      } finally {
        setLoading(false);
        setAuthInitialized(true);
      }
    };

    checkAuthStatus();
  }, []);

  // Login function with enhanced error handling
  const handleLogin = async (username, password) => {
    setLoading(true);
    setError(null);
    
    try {
      console.log(`Attempting login for user: ${username}`);
      const response = await apiLogin(username, password);
      
      if (!response || !response.access_token) {
        throw new Error('Invalid response from authentication server');
      }
      
      const token = response.access_token;
      console.log('Login successful, token received');
      
      // Store token in local storage
      localStorage.setItem('token', token);
      
      // Try to get user data
      try {
        // Get user data
        const userData = await getCurrentUser();
        
        if (!userData) {
          throw new Error('Failed to retrieve user data after login');
        }
        
        console.log('User data retrieved successfully after login');
        setUser(userData);
        return userData;
      } catch (userDataError) {
        console.error('Error fetching user data after login:', userDataError);
        // We still have a token, so consider login successful
        // but with incomplete user data
        setUser({ username: username });
        return { username: username };
      }
    } catch (err) {
      console.error('Login failed:', err);
      
      // Extract more specific error message if available
      let errorMessage = 'Login failed';
      if (err.message) {
        errorMessage = err.message;
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const handleRegister = async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      // Validate password match before sending to API
      if (userData.password !== userData.confirm_password) {
        setError('Passwords do not match');
        setLoading(false);
        throw new Error('Passwords do not match');
      }
      
      await apiRegister(userData);
      
      // After registration, log the user in
      return await handleLogin(userData.username, userData.password);
    } catch (err) {
      console.error('Registration failed:', err);
      
      // Extract more specific error message if available
      let errorMessage = 'Registration failed';
      if (err.message) {
        errorMessage = err.message;
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const handleLogout = () => {
    // Remove token from local storage
    localStorage.removeItem('token');
    
    // Clear user state
    setUser(null);
    
    // Call logout service
    apiLogout();
    
    console.log('User logged out successfully');
  };

  // Check token validity
  const checkTokenValidity = () => {
    const token = localStorage.getItem('token');
    
    if (!token) {
      return false;
    }
    
    try {
      // Basic check: is the token formatted like a JWT?
      const parts = token.split('.');
      if (parts.length !== 3) {
        return false;
      }
      
      // Parse the payload
      const payload = JSON.parse(atob(parts[1]));
      
      // Check if expired
      if (payload.exp) {
        const expiry = new Date(payload.exp * 1000);
        return new Date() < expiry;
      }
      
      // If no expiry, assume valid
      return true;
    } catch (e) {
      console.error('Error checking token validity:', e);
      return false;
    }
  };

  // Context value
  const value = {
    user,
    loading,
    error,
    authInitialized,
    isAuthenticated: !!user,
    isTokenValid: checkTokenValidity,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};