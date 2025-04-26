// frontend/src/services/auth.js
import { api, apiClient } from './api';

// Login function with enhanced error handling
export const login = async (username, password) => {
  try {
    console.log(`Login attempt for ${username}`);
    
    // Use URLSearchParams to format data as form data
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    // Use direct apiClient to get full response with status
    const response = await apiClient.post('/token', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    // Check if we have a valid response
    if (!response.data || !response.data.access_token) {
      console.error('Invalid login response:', response);
      throw new Error('Invalid response from authentication server');
    }
    
    // Store token in local storage
    localStorage.setItem('token', response.data.access_token);
    
    console.log('Login successful, token received');
    return response.data;
  } catch (error) {
    console.error('Login failed:', error);
    
    // Create a more user-friendly error message
    let errorMsg = 'Failed to login';
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      const status = error.response.status;
      const detail = error.response.data?.detail;
      
      if (status === 401) {
        errorMsg = detail || 'Invalid username or password';
      } else if (status === 403) {
        errorMsg = 'Access forbidden';
      } else if (status === 422) {
        errorMsg = detail || 'Invalid input data';
      } else {
        errorMsg = detail || `Error: ${status}`;
      }
    } else if (error.request) {
      // The request was made but no response was received
      errorMsg = 'No response from server. Please check your internet connection.';
    }
    
    // Throw a new error with the appropriate message
    throw new Error(errorMsg);
  }
};

// Register function with enhanced validation
export const register = async (userData) => {
  try {
    // Perform client-side validation
    if (!userData.username || !userData.email || !userData.password) {
      throw new Error('Username, email, and password are required');
    }
    
    if (userData.password !== userData.confirm_password) {
      throw new Error('Passwords do not match');
    }
    
    // Convert learning_style enum format if needed
    if (userData.learning_style) {
      // Our backend expects simple strings, not objects
      userData.learning_style = userData.learning_style.value || userData.learning_style;
    }
    
    // Make the API call
    const response = await api.post('/users/', userData);
    
    console.log('Registration successful', response);
    return response;
  } catch (error) {
    console.error('Registration failed:', error);
    
    // Create a more user-friendly error message
    let errorMsg = 'Failed to register';
    
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail;
      
      if (status === 400) {
        if (detail?.includes('already registered')) {
          errorMsg = 'This username is already taken. Please choose another one.';
        } else {
          errorMsg = detail || 'Invalid registration data';
        }
      } else if (status === 422) {
        errorMsg = detail || 'Missing or invalid registration information';
      } else {
        errorMsg = detail || `Error: ${status}`;
      }
    } else if (error.request) {
      errorMsg = 'No response from server. Please check your internet connection.';
    } else {
      // Client-side validation error
      errorMsg = error.message;
    }
    
    throw new Error(errorMsg);
  }
};

// Get current user with retry mechanism
export const getCurrentUser = async () => {
  try {
    // Check if token exists
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('No token available for getCurrentUser');
      return null;
    }
    
    // First attempt
    try {
      const response = await api.get('/users/me/');
      console.log('User data retrieved successfully', response);
      return response;
    } catch (firstAttemptError) {
      console.warn('First attempt to get user data failed:', firstAttemptError);
      
      // If first attempt fails with 401, the token might be invalid
      if (firstAttemptError.status === 401) {
        console.warn('Token appears to be invalid or expired');
        return null;
      }
      
      // For other errors, try once more after a short delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try {
        const retryResponse = await api.get('/users/me/');
        console.log('Retry successful, user data retrieved');
        return retryResponse;
      } catch (retryError) {
        console.error('Retry also failed, giving up:', retryError);
        throw retryError;
      }
    }
  } catch (error) {
    console.error('Error getting user data:', error);
    
    // Create a more user-friendly error message
    let errorMsg = 'Failed to get user data';
    
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail;
      
      if (status === 401) {
        errorMsg = 'Your session has expired. Please log in again.';
        // Clear invalid token
        localStorage.removeItem('token');
      } else {
        errorMsg = detail || `Error: ${status}`;
      }
    } else if (error.request) {
      errorMsg = 'No response from server. Please check your internet connection.';
    }
    
    throw new Error(errorMsg);
  }
};

// Logout (client-side only)
export const logout = () => {
  // Remove token from local storage
  localStorage.removeItem('token');
  console.log('Logged out - token removed');
};

// Check if token exists and is valid (client-side only)
export const isAuthenticated = () => {
  const token = localStorage.getItem('token');
  if (!token) {
    return false;
  }
  
  try {
    // Basic validation: check if token is a valid JWT format
    const parts = token.split('.');
    if (parts.length !== 3) {
      return false;
    }
    
    // Decode the token payload
    const payload = JSON.parse(atob(parts[1]));
    
    // Check expiration
    if (payload.exp) {
      return new Date(payload.exp * 1000) > new Date();
    }
    
    // If no expiration, assume it's valid
    return true;
  } catch (e) {
    console.error('Error checking token validity:', e);
    return false;
  }
};