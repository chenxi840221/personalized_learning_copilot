import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getLearningPlans, getRecommendations, createLearningPlan } from '../services/content';

// Components
import LearningPlan from './LearningPlan';
import ContentRecommendation from './ContentRecommendation';

const Dashboard = () => {
  const { user } = useAuth();
  const [learningPlans, setLearningPlans] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(true);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(true);
  const [error, setError] = useState('');
  const [isCreatingPlan, setIsCreatingPlan] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState('');
  
  // Available subjects
  const subjects = ['Mathematics', 'Science', 'English'];
  
  // Fetch learning plans and recommendations on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch learning plans
        const plans = await getLearningPlans();
        setLearningPlans(plans);
      } catch (err) {
        console.error('Error fetching learning plans:', err);
        setError('Failed to load learning plans');
      } finally {
        setIsLoadingPlans(false);
      }
      
      try {
        // Fetch recommendations based on student profile
        const recs = await getRecommendations();
        setRecommendations(recs);
      } catch (err) {
        console.error('Error fetching recommendations:', err);
        // Don't set error for recommendations to avoid blocking the UI
      } finally {
        setIsLoadingRecommendations(false);
      }
    };
    
    fetchData();
  }, []);
  
  // Handle creating a new learning plan
  const handleCreatePlan = async () => {
    if (!selectedSubject) {
      setError('Please select a subject');
      return;
    }
    
    setIsCreatingPlan(true);
    setError('');
    
    try {
      // Create new learning plan
      const newPlan = await createLearningPlan(selectedSubject);
      
      // Add new plan to state
      setLearningPlans([newPlan, ...learningPlans]);
      
      // Reset selection
      setSelectedSubject('');
    } catch (err) {
      console.error('Error creating learning plan:', err);
      setError('Failed to create learning plan');
    } finally {
      setIsCreatingPlan(false);
    }
  };
  
  // Calculate completion stats
  const calculateStats = () => {
    if (learningPlans.length === 0) {
      return { total: 0, completed: 0, inProgress: 0, percentage: 0 };
    }
    
    const total = learningPlans.length;
    const completed = learningPlans.filter(plan => plan.status === 'completed').length;
    const inProgress = learningPlans.filter(plan => plan.status === 'in_progress').length;
    const percentage = Math.round((completed / total) * 100);
    
    return { total, completed, inProgress, percentage };
  };
  
  const stats = calculateStats();
  
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Welcome Section */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h1 className="text-2xl font-bold text-gray-800">
          Welcome, {user?.full_name || user?.username}!
        </h1>
        <p className="text-gray-600 mt-2">
          Your personalized learning dashboard
        </p>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
            <p className="text-sm text-blue-700 font-medium">Learning Plans</p>
            <p className="text-2xl font-bold text-blue-800">{stats.total}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg border border-green-100">
            <p className="text-sm text-green-700 font-medium">Completed</p>
            <p className="text-2xl font-bold text-green-800">{stats.completed}</p>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100">
            <p className="text-sm text-yellow-700 font-medium">In Progress</p>
            <p className="text-2xl font-bold text-yellow-800">{stats.inProgress}</p>
          </div>
        </div>