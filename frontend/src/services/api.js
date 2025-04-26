// frontend/src/services/api.js
import axios from 'axios';

// Create axios instance with base URL
export const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 15000, // Increased timeout for slow API responses
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add request interceptor to add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.warn('No authentication token found. Request may fail if authentication is required.');
    }
    
    // Log requests for debugging
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, 
      config.params || config.data || {});
      
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle common errors
apiClient.interceptors.response.use(
  (response) => {
    // Log successful responses for debugging
    console.log(`API Response (${response.status}):`, response.data);
    return response.data; // Return data directly for easier usage
  },
  async (error) => {
    // Enhanced error handling with token refresh attempts
    const originalRequest = error.config;
    
    // Handle 401 Unauthorized errors (token expired, etc)
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      // Mark this request as retried to prevent infinite loops
      originalRequest._retry = true;
      
      try {
        // Try to refresh token or re-login
        // For now, we'll just handle token expiry by redirecting to login
        console.warn('Authentication failed. Redirecting to login page.');
        localStorage.removeItem('token');
        window.location.href = '/login';
        return Promise.reject(error);
      } catch (refreshError) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    // Create a more detailed error object
    const enhancedError = new Error(
      error.response?.data?.detail || error.message || 'An unknown error occurred'
    );
    
    // Add additional properties for debugging
    enhancedError.status = error.response?.status;
    enhancedError.statusText = error.response?.statusText;
    enhancedError.data = error.response?.data;
    enhancedError.originalError = error;
    
    // Log detailed error for debugging
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    
    return Promise.reject(enhancedError);
  }
);

// Format and log API errors
const handleApiError = (error) => {
  // Get error details
  const status = error.status || 'N/A';
  const message = error.message || 'Unknown error';
  const endpoint = error.originalError?.config?.url || 'Unknown endpoint';
  
  // Create detailed error message
  const logMessage = `API Error: [${status}] ${message} - Endpoint: ${endpoint}`;
  
  // Log error details to console
  console.error(logMessage, error);
  
  // Re-throw error with cleaned up message
  throw new Error(message);
};

// Helper to handle empty responses gracefully
const handleEmptyResponse = (data, defaultValue = []) => {
  if (data === null || data === undefined) {
    console.warn('API returned null or undefined data');
    return defaultValue;
  }
  return data;
};

// Generic API methods with enhanced error handling
export const api = {
  get: async (url, params = {}) => {
    try {
      const response = await apiClient.get(url, { params });
      return response; // Already returns data via interceptor
    } catch (error) {
      // Try again once with a delay for transient errors
      if (error.status === 503 || error.status === 429 || error.status === 504) {
        console.log(`Retrying ${url} after transient error...`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        try {
          const retryResponse = await apiClient.get(url, { params });
          return retryResponse;
        } catch (retryError) {
          handleApiError(retryError);
        }
      } else {
        handleApiError(error);
      }
    }
  },
  
  post: async (url, data = {}) => {
    try {
      const response = await apiClient.post(url, data);
      return response;
    } catch (error) {
      if (error.status === 401) {
        console.error('Authentication failed when calling ' + url);
        // Check if token exists
        const token = localStorage.getItem('token');
        if (!token) {
          console.error('No token found in localStorage');
        } else {
          console.log('Token exists but may be invalid or expired');
        }
      }
      handleApiError(error);
    }
  },
  
  put: async (url, data = {}) => {
    try {
      const response = await apiClient.put(url, data);
      return response;
    } catch (error) {
      handleApiError(error);
    }
  },
  
  delete: async (url) => {
    try {
      const response = await apiClient.delete(url);
      return response;
    } catch (error) {
      handleApiError(error);
    }
  }
};