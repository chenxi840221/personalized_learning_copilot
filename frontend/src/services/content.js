// services/content.js
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
    
    // Log the response for debugging
    console.log('Content API response:', response);
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from content API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch content:', error);
    throw error;
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
    
    // Log the response for debugging
    console.log('Recommendations API response:', response);
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from recommendations API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch recommendations:', error);
    // Return empty array instead of throwing to avoid breaking the UI
    return [];
  }
};

// Use the new personalized recommendations if available
export const getPersonalizedRecommendations = async (subject = null, limit = 10) => {
  try {
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
    const response = await api.get('/learning-plans/');
    
    // Log the response for debugging
    console.log('Learning plans API response:', response);
    
    // Ensure the response is in the expected format
    if (!Array.isArray(response)) {
      console.error('Invalid response format from learning plans API:', response);
      return [];
    }
    
    return response;
  } catch (error) {
    console.error('Failed to fetch learning plans:', error);
    throw error;
  }
};

// Create a new learning plan
export const createLearningPlan = async (subject) => {
  try {
    // Check if AI-generated learning plan endpoint is available
    try {
      const response = await api.post('/ai/learning-plan/', { subject });
      console.log('Created AI learning plan:', response);
      return response;
    } catch (err) {
      console.log('AI learning plan not available, using standard endpoint');
      // Fall back to regular endpoint
      return await api.post('/learning-plans/', { subject });
    }
  } catch (error) {
    console.error('Failed to create learning plan:', error);
    throw error;
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