// frontend/src/services/api.js
import axios from 'axios';

// Create axios instance with base URL
// Log the API URL to help diagnose connection issues
const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
console.log('🔌 API Client initializing with base URL:', apiUrl);

export const apiClient = axios.create({
  baseURL: apiUrl,
  timeout: 120000, // Increased timeout to 2 minutes since document processing can take time
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add request interceptor to add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    // Get token from storage (MSAL will handle this internally)
    // We don't need to do anything here as EntraAuthContext already sets the token
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
      // Redirect to login page if unauthorized
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
  
  // Form data post (for file uploads)
  postFormData: async (url, formData) => {
    try {
      const response = await apiClient.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 180000, // 3 minutes timeout for file uploads (overrides the default timeout)
        onUploadProgress: (progressEvent) => {
          // Optional: Log progress
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log(`Upload progress: ${percentCompleted}%`);
        }
      });
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }
};

// Get auth token (for use in raw fetch calls)
export const getToken = () => {
  // Get token from localStorage or sessionStorage
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token') || '';
};

// Student Reports API
export const uploadReport = async (formData) => {
  try {
    return await api.postFormData('/student-reports/upload', formData);
  } catch (error) {
    console.error('Error uploading report:', error);
    throw error;
  }
};

export const getReports = async (queryParams) => {
  try {
    console.log('🔍 API Service: Requesting student reports from backend');
    
    // Add direct axios call check to diagnose connection issues
    try {
      const directResponse = await apiClient.get('/student-reports', { timeout: 5000 });
      console.log('🔧 Direct axios test worked! Status:', directResponse.status);
    } catch (directError) {
      // If the direct call fails, log detailed information
      console.error('🔧 Direct axios test failed:', directError.message);
      console.error('🔧 Request URL:', directError.config?.url);
      console.error('🔧 Is network error:', directError.isAxiosError && !directError.response);
    }
    
    // Proceed with regular API call
    const result = await api.get('/student-reports', queryParams);
    console.log('📊 API Service: Received', result?.length || 0, 'reports from backend');
    return result;
  } catch (error) {
    console.error('❌ API Service Error fetching reports:', error);
    console.error('❌ Error details:', {
      message: error.message,
      isAxiosError: error.isAxiosError || false,
      status: error.response?.status || 'No response',
      statusText: error.response?.statusText || 'No response text'
    });
    throw error;
  }
};

export const getReport = async (reportId) => {
  try {
    return await api.get(`/student-reports/${reportId}`);
  } catch (error) {
    console.error('Error fetching report:', error);
    throw error;
  }
};

export const deleteReport = async (reportId) => {
  try {
    return await api.delete(`/student-reports/${reportId}`);
  } catch (error) {
    console.error('Error deleting report:', error);
    throw error;
  }
};