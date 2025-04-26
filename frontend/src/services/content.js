// frontend/src/services/content.js
import { api } from './api';

// Get all content with optional filters
export const getContent = async (subject = null, contentType = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) params.subject = subject;
    if (contentType) params.content_type = contentType;
    
    // Make API request
    const response = await api.get('/content/', params);
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from content API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch content:', error);
    return []; // Return empty array instead of throwing to prevent UI breaks
  }
};

// Get recommended content based on user profile
export const getRecommendations = async (subject = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) params.subject = subject;
    
    // Make API request
    const response = await api.get('/content/recommendations/', params);
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from recommendations API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch recommendations:', error);
    return []; // Return empty array instead of throwing
  }
};

// Use the new personalized recommendations if available
export const getPersonalizedRecommendations = async (subject = null, limit = 10) => {
  try {
    // Check for auth token - personalized recommendations require authentication
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('No auth token available, falling back to standard recommendations');
      return await getRecommendations(subject);
    }
    
    // Build query parameters
    const params = {
      limit: limit
    };
    if (subject) params.subject = subject;
    
    // Try the enhanced endpoint first
    try {
      const response = await api.get('/ai/personalized-recommendations/', params);
      console.log('Using AI personalized recommendations:', response);
      return response;
    } catch (err) {
      console.log('AI recommendations not available, falling back to standard recommendations');
      return await getRecommendations(subject);
    }
  } catch (error) {
    console.error('Failed to fetch personalized recommendations:', error);
    return [];
  }
};

// Get learning plans for current user
export const getLearningPlans = async () => {
  try {
    // Check for auth token - learning plans require authentication
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('No auth token available for fetching learning plans');
      return [];
    }
    
    const response = await api.get('/learning-plans/');
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from learning plans API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch learning plans:', error);
    return []; // Return empty array to avoid UI breaks
  }
};

// Create a new learning plan
export const createLearningPlan = async (subject) => {
  try {
    // Verify authentication is available
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('Authentication required to create learning plans');
      throw new Error('Please log in to create learning plans');
    }
    
    // First try AI-generated learning plan endpoint
    try {
      console.log('Attempting to create AI learning plan for subject:', subject);
      const response = await api.post('/ai/learning-plan', { subject });
      console.log('Successfully created AI learning plan:', response);
      return response;
    } catch (err) {
      console.warn('AI learning plan creation failed, error:', err);
      console.log('Falling back to standard learning plan endpoint');
      
      // Fall back to regular endpoint
      try {
        const response = await api.post('/learning-plans/', { subject });
        console.log('Successfully created standard learning plan:', response);
        return response;
      } catch (fallbackErr) {
        console.error('Standard learning plan creation also failed:', fallbackErr);
        throw fallbackErr;
      }
    }
  } catch (error) {
    console.error('Failed to create learning plan:', error);
    throw error; // Re-throw to allow UI to handle the error
  }
};

// Update learning activity status
export const updateActivityStatus = async (planId, activityId, status, completedAt = null) => {
  try {
    return await api.put(`/learning-plans/${planId}/activities/${activityId}`, {
      status,
      completed_at: completedAt
    });
  } catch (error) {
    console.error('Failed to update activity status:', error);
    throw error;
  }
};

// Get content by topic
export const getContentByTopic = async (topic, limit = 5) => {
  try {
    const params = {
      topic: topic,
      limit: limit
    };
    
    const response = await api.get('/content/by-topic/', params);
    return response;
  } catch (error) {
    console.error(`Failed to fetch content for topic ${topic}:`, error);
    return [];
  }
};

// Get similar content
export const getSimilarContent = async (contentId, limit = 3) => {
  try {
    const params = {
      limit: limit
    };
    
    const response = await api.get(`/content/similar/${contentId}`, params);
    return response;
  } catch (error) {
    console.error(`Failed to fetch similar content for ID ${contentId}:`, error);
    return [];
  }
};

// Search content with query
export const searchContent = async (query, subject = null, contentType = null, limit = 10) => {
  try {
    // Use POST for search to handle complex queries
    const data = {
      query: query,
      limit: limit
    };
    
    if (subject) data.subject = subject;
    if (contentType) data.content_type = contentType;
    
    const response = await api.post('/content/search', data);
    return response;
  } catch (error) {
    console.error('Failed to search content:', error);
    return [];
  }
};