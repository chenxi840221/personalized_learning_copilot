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
    return await api.get('/content/', params);
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
    return await api.get('/content/recommendations/', params);
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