import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

const ProfilePage = () => {
  const { user } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    grade_level: user?.grade_level || '',
    subjects_of_interest: user?.subjects_of_interest || [],
    learning_style: user?.learning_style || ''
  });
  
  // Available subjects
  const availableSubjects = ['Mathematics', 'Science', 'English', 'History', 'Geography', 'Art'];
  
  // Available learning styles
  const learningStyles = [
    { value: 'visual', label: 'Visual' },
    { value: 'auditory', label: 'Auditory' },
    { value: 'reading_writing', label: 'Reading/Writing' },
    { value: 'kinesthetic', label: 'Kinesthetic' },
    { value: 'mixed', label: 'Mixed/Multiple' }
  ];
  
  // Toggle edit mode
  const toggleEdit = () => {
    setIsEditing(!isEditing);
    
    // Reset form data if canceling edit
    if (isEditing) {
      setFormData({
        full_name: user?.full_name || '',
        email: user?.email || '',
        grade_level: user?.grade_level || '',
        subjects_of_interest: user?.subjects_of_interest || [],
        learning_style: user?.learning_style || ''
      });
    }
  };
  
  // Handle input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };
  
  // Handle checkbox changes for subjects
  const handleSubjectChange = (e) => {
    const { value, checked } = e.target;
    if (checked) {
      setFormData({
        ...formData,
        subjects_of_interest: [...formData.subjects_of_interest, value]
      });
    } else {
      setFormData({
        ...formData,
        subjects_of_interest: formData.subjects_of_interest.filter(subject => subject !== value)
      });
    }
  };
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Here you would call an API to update the user profile
    // For this POC, we'll just simulate success and exit edit mode
    
    // TODO: Implement actual profile update API call
    console.log('Updated profile data:', formData);
    
    // Exit edit mode
    setIsEditing(false);
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Your Profile</h1>
          <button
            onClick={toggleEdit}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              isEditing 
                ? 'bg-gray-200 text-gray-700 hover:bg-gray-300' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
        </div>
        
        {isEditing ? (
          // Edit Mode
          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Full Name */}
              <div>
                <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name
                </label>
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.full_name}
                  onChange={handleChange}
                />
              </div>
              
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-100"
                  value={formData.email}
                  readOnly
                  disabled
                />
                <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
              </div>
              
              {/* Grade Level */}
              <div>
                <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700 mb-1">
                  Grade Level (1-12)
                </label>
                <input
                  id="grade_level"
                  name="grade_level"
                  type="number"
                  min="1"
                  max="12"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.grade_level}
                  onChange={handleChange}
                />
              </div>
              
              {/* Subjects of Interest */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Subjects of Interest
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {availableSubjects.map(subject => (
                    <div key={subject} className="flex items-center">
                      <input
                        id={`subject-${subject}`}
                        type="checkbox"
                        name="subjects_of_interest"
                        value={subject}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        checked={formData.subjects_of_interest.includes(subject)}
                        onChange={handleSubjectChange}
                      />
                      <label htmlFor={`subject-${subject}`} className="ml-2 block text-sm text-gray-700">
                        {subject}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Learning Style */}
              <div>
                <label htmlFor="learning_style" className="block text-sm font-medium text-gray-700 mb-1">
                  Learning Style
                </label>
                <select
                  id="learning_style"
                  name="learning_style"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.learning_style}
                  onChange={handleChange}
                >
                  <option value="">Select your learning style</option>
                  {learningStyles.map(style => (
                    <option key={style.value} value={style.value}>
                      {style.label}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Submit Button */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </form>
        ) : (
          // View Mode
          <div className="space-y-6">
            {/* Basic Information */}
            <div className="border-b border-gray-200 pb-4">
              <h2 className="text-lg font-medium text-gray-800 mb-4">Basic Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Username</p>
                  <p className="mt-1">{user?.username}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Full Name</p>
                  <p className="mt-1">{user?.full_name || 'Not specified'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Email</p>
                  <p className="mt-1">{user?.email}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Grade Level</p>
                  <p className="mt-1">{user?.grade_level || 'Not specified'}</p>
                </div>
              </div>
            </div>
            
            {/* Learning Preferences */}
            <div>
              <h2 className="text-lg font-medium text-gray-800 mb-4">Learning Preferences</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Learning Style</p>
                  <p className="mt-1 capitalize">
                    {user?.learning_style 
                      ? user.learning_style.replace('_', '/') 
                      : 'Not specified'}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Subjects of Interest</p>
                  {user?.subjects_of_interest && user.subjects_of_interest.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {user.subjects_of_interest.map(subject => (
                        <span 
                          key={subject}
                          className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded"
                        >
                          {subject}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-1">No subjects specified</p>
                  )}
                </div>
              </div>
            </div>
            
            {/* Account Information */}
            <div className="border-t border-gray-200 pt-4">
              <h2 className="text-lg font-medium text-gray-800 mb-4">Account Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Account Status</p>
                  <p className="mt-1 flex items-center">
                    <span className="h-2.5 w-2.5 rounded-full bg-green-500 mr-2"></span>
                    Active
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Member Since</p>
                  <p className="mt-1">
                    {user?.created_at 
                      ? new Date(user.created_at).toLocaleDateString() 
                      : 'Unknown'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;