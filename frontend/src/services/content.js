// frontend/src/services/content.js
import { api } from './api';

/**
 * Get all content with optional filters
 * @param {string|null} subject - Optional subject filter
 * @param {string|null} contentType - Optional content type filter
 * @param {string|null} difficulty - Optional difficulty filter
 * @param {number|null} gradeLevel - Optional grade level filter
 * @returns {Promise<Array>} Array of content items
 */
export const getContent = async (subject = null, contentType = null, difficulty = null, gradeLevel = null) => {
  try {
    console.log(`🔍 Fetching content with filters - Subject: ${subject}, Type: ${contentType}`);
    
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    if (contentType) params.content_type = contentType;
    if (difficulty) params.difficulty = difficulty;
    if (gradeLevel) params.grade_level = gradeLevel;
    
    // Make API request
    const result = await api.get('/content', params);
    console.log(`📚 Received ${result?.length || 0} content items from API`);
    return result;
  } catch (error) {
    console.error('❌ Failed to fetch content:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    throw error;
  }
};

/**
 * Get recommended content based on user profile
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of recommended content items
 */
export const getRecommendations = async (subject = null) => {
  try {
    console.log(`🔍 Fetching personalized recommendations${subject ? ` for ${subject}` : ''}`);
    
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    try {
      // First try the recommendations endpoint
      const result = await api.get('/content/recommendations', params);
      console.log(`📚 Received ${result?.length || 0} recommended items from API`);
      return result;
    } catch (recommendationError) {
      // If recommendations endpoint fails, fallback to main content endpoint
      console.log('⚠️ Recommendations endpoint failed, falling back to content endpoint');
      console.error(recommendationError);
      
      // Fallback to the regular content endpoint
      const fallbackResult = await api.get('/content', params);
      console.log(`📚 Received ${fallbackResult?.length || 0} content items from fallback API`);
      return fallbackResult;
    }
  } catch (error) {
    console.error('❌ Failed to fetch recommendations:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    
    // Return empty array instead of throwing to provide graceful degradation
    return [];
  }
};

/**
 * Search for content using text and vector search
 * @param {string} query - Search query
 * @param {string|null} subject - Optional subject filter
 * @param {string|null} contentType - Optional content type filter
 * @returns {Promise<Array>} Array of content items matching the search
 */
export const searchContent = async (query, subject = null, contentType = null) => {
  try {
    console.log(`🔍 Searching for content with query: "${query}"${subject ? `, subject: ${subject}` : ''}${contentType ? `, type: ${contentType}` : ''}`);
    
    // Build query parameters
    const params = { query };
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    if (contentType) params.content_type = contentType;
    
    // Make API request using GET as defined in the backend
    const result = await api.get('/content/search', params);
    console.log(`🔎 Found ${result?.length || 0} search results`);
    return result;
  } catch (error) {
    console.error('❌ Failed to search content:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    
    // Return empty array instead of throwing to provide graceful degradation
    return [];
  }
};

/**
 * Get content by ID
 * @param {string} contentId - Content ID
 * @returns {Promise<Object>} Content item 
 */
export const getContentById = async (contentId) => {
  try {
    console.log(`🔍 Fetching content with ID: ${contentId}`);
    
    // Make API request
    const result = await api.get(`/content/${contentId}`);
    console.log(`📚 Received content item from API:`, result);
    return result;
  } catch (error) {
    console.error(`❌ Failed to fetch content with ID ${contentId}:`, error);
    console.error('Error details:', {
      message: error.message,
      status: error.status || 'N/A',
      data: error.data || 'N/A'
    });
    throw error;
  }
};

/**
 * Get learning plans for current user
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of learning plans
 */
export const getLearningPlans = async (subject = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    // Make API request
    return await api.get('/learning-plans/', params);
  } catch (error) {
    console.error('Failed to fetch learning plans:', error);
    throw error;
  }
};

/**
 * Create a new learning plan
 * @param {string} subject - Subject for the learning plan
 * @returns {Promise<Object>} Created learning plan
 */
export const createLearningPlan = async (subject) => {
  try {
    return await api.post('/learning-plans/', { subject });
  } catch (error) {
    console.error('Failed to create learning plan:', error);
    throw error;
  }
};

/**
 * Update learning activity status
 * @param {string} planId - Learning plan ID
 * @param {string} activityId - Activity ID
 * @param {string} status - New status (not_started, in_progress, completed)
 * @param {string|null} completedAt - Optional ISO date string when the activity was completed
 * @returns {Promise<Object>} Update result
 */
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

/**
 * Get AI-generated personalized recommendations
 * @param {string|null} subject - Optional subject filter
 * @returns {Promise<Array>} Array of AI-recommended content items
 */
export const getAIRecommendations = async (subject = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) {
      // Map "Maths" in frontend to what the backend expects
      if (subject === "Maths") {
        params.subject = "Maths";
      } else {
        params.subject = subject;
      }
    }
    
    // Make API request to AI endpoint
    return await api.get('/ai/personalized-recommendations', params);
  } catch (error) {
    console.error('Failed to fetch AI recommendations:', error);
    // Fall back to regular recommendations
    return await getRecommendations(subject);
  }
};

/**
 * Create an AI-generated learning plan
 * @param {string} subject - Subject for the learning plan
 * @returns {Promise<Object>} Created learning plan
 */
export const createAILearningPlan = async (subject) => {
  try {
    return await api.post('/ai/learning-plan', { subject });
  } catch (error) {
    console.error('Failed to create AI learning plan:', error);
    // Fall back to regular plan creation
    return await createLearningPlan(subject);
  }
};