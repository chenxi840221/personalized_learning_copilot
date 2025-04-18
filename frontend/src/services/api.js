import axios from 'axios';

// Create axios instance with base URL
export const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 10000,
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
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle common errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle 401 Unauthorized errors (token expired, etc)
    if (error.response && error.response.status === 401) {
      // Clear the token and redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
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

// Generic API methods with enhanced error handling
export const api = {
  get: async (url, params = {}) => {
    try {
      const response = await apiClient.get(url, { params });
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },
  
  post: async (url, data = {}) => {
    try {
      const response = await apiClient.post(url, data);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },
  
  put: async (url, data = {}) => {
    try {
      const response = await apiClient.put(url, data);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },
  
  delete: async (url) => {
    try {
      const response = await apiClient.delete(url);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  },
  
  // Method with retry capability for unstable connections
  withRetry: async (method, url, data = {}, retries = 3, delay = 1000) => {
    let lastError;
    
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        let response;
        
        switch (method.toLowerCase()) {
          case 'get':
            response = await apiClient.get(url, { params: data });
            break;
          case 'post':
            response = await apiClient.post(url, data);
            break;
          case 'put':
            response = await apiClient.put(url, data);
            break;
          case 'delete':
            response = await apiClient.delete(url);
            break;
          default:
            throw new Error(`Invalid method: ${method}`);
        }
        
        return response.data;
      } catch (error) {
        lastError = error;
        
        // Don't retry for client errors (4xx) except for 429 (too many requests)
        if (error.status && error.status >= 400 && error.status < 500 && error.status !== 429) {
          break;
        }
        
        // Wait before retry
        if (attempt < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay * (attempt + 1)));
        }
      }
    }
    
    // All retries failed
    handleApiError(lastError);
  }
};