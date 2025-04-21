import React, { useState } from 'react';
import { updateActivityStatus } from '../services/content';

const LearningPlan = ({ plan }) => {
  const [expandedPlan, setExpandedPlan] = useState(false);
  const [localPlan, setLocalPlan] = useState(plan);
  const [updating, setUpdating] = useState(false);
  
  // Toggle expansion of plan details
  const toggleExpand = () => {
    setExpandedPlan(!expandedPlan);
  };
  
  // Handle updating activity status
  const handleStatusChange = async (activityId, newStatus) => {
    setUpdating(true);
    
    try {
      // Update on server
      await updateActivityStatus(localPlan.id, activityId, newStatus, 
        newStatus === 'completed' ? new Date().toISOString() : null);
      
      // Update local state
      const updatedActivities = localPlan.activities.map(activity => {
        if (activity.id === activityId) {
          return {
            ...activity,
            status: newStatus,
            completed_at: newStatus === 'completed' ? new Date().toISOString() : null
          };
        }
        return activity;
      });
      
      // Calculate new progress percentage
      const totalActivities = updatedActivities.length;
      const completedActivities = updatedActivities.filter(a => a.status === 'completed').length;
      const newProgressPercentage = totalActivities > 0 
        ? Math.round((completedActivities / totalActivities) * 100) 
        : 0;
      
      // Update plan status if all activities are completed
      const newPlanStatus = completedActivities === totalActivities ? 'completed' 
        : completedActivities > 0 ? 'in_progress' : 'not_started';
      
      // Update local plan
      setLocalPlan({
        ...localPlan,
        activities: updatedActivities,
        progress_percentage: newProgressPercentage,
        status: newPlanStatus
      });
    } catch (error) {
      console.error('Failed to update activity status:', error);
      // You could show an error toast here
    } finally {
      setUpdating(false);
    }
  };
  
  // Get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };
  
  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Not started';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };
  
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Plan Header */}
      <div 
        className="flex flex-wrap items-center justify-between p-4 bg-gray-50 cursor-pointer gap-2"
        onClick={toggleExpand}
      >
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-medium text-gray-900 truncate">{localPlan.title}</h3>
          <p className="text-sm text-gray-500">{localPlan.subject}</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 mt-2 sm:mt-0">
          {/* Progress Badge */}
          <div className="text-sm font-medium">
            {localPlan.progress_percentage}% Complete
          </div>
          
          {/* Status Badge */}
          <span className={`px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(localPlan.status)}`}>
            {localPlan.status === 'not_started' ? 'Not Started' : 
              localPlan.status === 'in_progress' ? 'In Progress' : 'Completed'}
          </span>
          
          {/* Expand/Collapse Icon */}
          <svg 
            className={`w-5 h-5 text-gray-500 transform transition-transform ${expandedPlan ? 'rotate-180' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      
      {/* Plan Details */}
      {expandedPlan && (
        <div className="p-4 border-t border-gray-200">
          {/* Description */}
          <p className="text-gray-600 mb-4">{localPlan.description}</p>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
            <div 
              className="bg-blue-600 h-2.5 rounded-full" 
              style={{width: `${localPlan.progress_percentage}%`}}
            ></div>
          </div>
          
          {/* Activities */}
          <h4 className="text-md font-medium text-gray-900 mb-2">Activities</h4>
          <div className="space-y-3">
            {localPlan.activities.map((activity, index) => (
              <div key={activity.id} className="border border-gray-200 rounded p-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded mr-2">
                        {index + 1}
                      </span>
                      <h5 className="text-gray-900 font-medium">{activity.title}</h5>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{activity.description}</p>
                    
                    {/* Activity Metadata */}
                    <div className="flex flex-wrap items-center mt-2 text-xs text-gray-500 gap-3">
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {activity.duration_minutes} minutes
                      </span>
                      
                      {activity.status === 'completed' && (
                        <span className="flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          Completed on {formatDate(activity.completed_at)}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Status Controls */}
                  <div className="mt-3 sm:mt-0">
                    <select
                      className="w-full sm:w-auto text-sm border border-gray-300 rounded px-2 py-1"
                      value={activity.status}
                      onChange={(e) => handleStatusChange(activity.id, e.target.value)}
                      disabled={updating}
                      aria-label={`Set status for ${activity.title}`}
                    >
                      <option value="not_started">Not Started</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                    </select>
                  </div>
                </div>
                
                {/* Content Link (if available) */}
                {activity.content_id && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <a 
                      href={`/content/${activity.content_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-sm flex items-center"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Open learning resource
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LearningPlan;