// Update your frontend/src/services/content.js file
import { api } from './api';

// Get all content with optional filters
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

// Get recommended content - in our simple backend this is just filtered content
export const getRecommendations = async (subject = null) => {
  try {
    // Get general content or subject-specific content
    return await getContent(subject);
  } catch (error) {
    console.error('Failed to fetch recommendations:', error);
    throw error;
  }
};

// Get learning plans for current user
export const getLearningPlans = async () => {
  try {
    return await api.get('/learning-plans/');
  } catch (error) {
    console.error('Failed to fetch learning plans:', error);
    throw error;
  }
};

// Create a new learning plan
export const createLearningPlan = async (subject) => {
  try {
    return await api.post('/learning-plans/', { subject });
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