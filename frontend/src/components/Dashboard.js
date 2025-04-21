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
      <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800">
          Welcome, {user?.full_name || user?.username}!
        </h1>
        <p className="text-gray-600 mt-2">
          Your personalized learning dashboard
        </p>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
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

        {/* Progress Bar */}
        {stats.total > 0 && (
          <div className="mt-4">
            <div className="flex justify-between items-center mb-2">
              <p className="text-sm text-gray-600">Overall Progress</p>
              <p className="text-sm font-medium text-gray-900">{stats.percentage}%</p>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className="bg-blue-600 h-2.5 rounded-full" 
                style={{width: `${stats.percentage}%`}}
              ></div>
            </div>
          </div>
        )}
      </div>
      
      {/* Learning Plans Section */}
      <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
          <h2 className="text-xl font-bold text-gray-800">Your Learning Plans</h2>
          
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center w-full sm:w-auto gap-2 sm:gap-0 sm:space-x-2">
            <select
              className="border border-gray-300 rounded-md px-3 py-2 text-sm flex-grow sm:flex-grow-0"
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              disabled={isCreatingPlan}
              aria-label="Select subject"
            >
              <option value="">Select a subject</option>
              {subjects.map(subject => (
                <option key={subject} value={subject}>{subject}</option>
              ))}
            </select>
            
            <button
              onClick={handleCreatePlan}
              disabled={isCreatingPlan || !selectedSubject}
              className="bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {isCreatingPlan ? 'Creating...' : 'Create Plan'}
            </button>
          </div>
        </div>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {isLoadingPlans ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-2 text-gray-500">Loading your learning plans...</p>
          </div>
        ) : learningPlans.length > 0 ? (
          <div className="space-y-4">
            {learningPlans.map(plan => (
              <LearningPlan key={plan.id} plan={plan} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <p className="text-gray-500 mb-2">You don't have any learning plans yet.</p>
            <p className="text-gray-500">Select a subject and click "Create Plan" to get started.</p>
          </div>
        )}
      </div>
      
      {/* Recommendations Section */}
      <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-6">Recommended for You</h2>
        
        {isLoadingRecommendations ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-2 text-gray-500">Loading recommendations...</p>
          </div>
        ) : recommendations.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {recommendations.slice(0, 6).map(content => (
              <ContentRecommendation key={content.id} content={content} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No recommendations available at the moment.</p>
            <p className="text-gray-500 mt-2">
              <Link to="/content" className="text-blue-600 hover:underline">
                Browse all content →
              </Link>
            </p>
          </div>
        )}
        
        {recommendations.length > 6 && (
          <div className="text-center mt-6">
            <Link
              to="/content"
              className="text-blue-600 hover:underline font-medium"
            >
              View all recommendations →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;