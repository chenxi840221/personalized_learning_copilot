import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getContent, getRecommendations } from '../services/content';
import ContentRecommendation from '../components/ContentRecommendation';

const ContentPage = () => {
  const { subject } = useParams();
  const [contentItems, setContentItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSubject, setActiveSubject] = useState(subject || 'All');
  const [activeType, setActiveType] = useState('All');
  
  // Available subjects and content types
  const subjects = ['All', 'Mathematics', 'Science', 'English'];
  const contentTypes = ['All', 'Video', 'Article', 'Interactive', 'Quiz', 'Lesson', 'Worksheet', 'Activity'];
  
  // Fetch content on component mount and when filters change
  useEffect(() => {
    const fetchContent = async () => {
      setIsLoading(true);
      setError('');
      
      try {
        let data;
        
        // If "All" is selected, get recommendations
        if (activeSubject === 'All' && activeType === 'All') {
          data = await getRecommendations();
        } else {
          // Otherwise, get filtered content
          const subjectParam = activeSubject !== 'All' ? activeSubject : null;
          const typeParam = activeType !== 'All' ? activeType.toLowerCase() : null;
          data = await getContent(subjectParam, typeParam);
        }
        
        setContentItems(data);
      } catch (err) {
        console.error('Error fetching content:', err);
        setError('Failed to load content');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchContent();
  }, [activeSubject, activeType]);
  
  // Set active subject from URL param on mount
  useEffect(() => {
    if (subject) {
      setActiveSubject(subject);
    }
  }, [subject]);
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">
          {activeSubject === 'All' ? 'Browse All Content' : `${activeSubject} Resources`}
        </h1>
        
        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div>
            <label htmlFor="subject-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Subject
            </label>
            <select
              id="subject-filter"
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={activeSubject}
              onChange={(e) => setActiveSubject(e.target.value)}
            >
              {subjects.map(subj => (
                <option key={subj} value={subj}>
                  {subj}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label htmlFor="type-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Content Type
            </label>
            <select
              id="type-filter"
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={activeType}
              onChange={(e) => setActiveType(e.target.value)}
            >
              {contentTypes.map(type => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Error Message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {/* Content Items */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-600">Loading content...</p>
          </div>
        ) : contentItems.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {contentItems.map(content => (
              <ContentRecommendation key={content.id} content={content} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No content found for the selected filters.</p>
            <p className="mt-2">Try changing your filter options.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentPage;