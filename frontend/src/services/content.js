// frontend/src/services/content.js
import { api } from './api';

/**
 * Get all content with optional filters
 * @param {string|null} subject - Optional subject filter
 * @param {string|null} contentType - Optional content type filter
 * @returns {Promise<Array>} Array of content items
 */
export const getContent = async (subject = null, contentType = null) => {
  try {
    // Build query parameters
    const params = {};
    if (subject) params.subject = subject;
    if (contentType) params.content_type = contentType;
    
    // Make API request
    return await api.get('/content/', params);
  } catch (error) {
    console.error('Failed to fetch content:', error);
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
    // Build query parameters
    const params = {};
    if (subject) params.subject = subject;
    
    // Make API request
    return await api.get('/content/recommendations/', params);
  } catch (error) {
    console.error('Failed to fetch recommendations:', error);
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
    if (subject) params.subject = subject;
    
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
    if (subject) params.subject = subject;
    
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