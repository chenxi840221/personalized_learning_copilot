import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getContent, getRecommendations, searchContent } from '../services/content';
import ContentRecommendation from '../components/ContentRecommendation';

const ContentPage = () => {
  const { subject } = useParams();
  const [contentItems, setContentItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeSubject, setActiveSubject] = useState(subject || 'All');
  const [activeType, setActiveType] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  
  // Available subjects and content types - extended with more options
  const subjects = ['All', 'Mathematics', 'Science', 'English', 'History', 'Geography', 'Arts'];
  const contentTypes = ['All', 'Video', 'Article', 'Interactive', 'Quiz', 'Lesson', 'Worksheet', 'Activity'];
  
  // Fetch content on component mount and when filters change
  useEffect(() => {
    const fetchContent = async () => {
      setIsLoading(true);
      setError('');
      
      try {
        let data = [];
        
        if (isSearching && searchQuery.trim()) {
          // If there's a search query, use search API
          console.log(`🔍 Searching for: "${searchQuery}"`);
          const subjectParam = activeSubject !== 'All' ? activeSubject : null;
          const typeParam = activeType !== 'All' ? activeType.toLowerCase() : null;
          
          data = await searchContent(searchQuery, subjectParam, typeParam);
        } else if (activeSubject === 'All' && activeType === 'All') {
          // If "All" is selected, get recommendations
          console.log('📚 Getting personalized recommendations');
          data = await getRecommendations();
        } else {
          // Otherwise, get filtered content
          const subjectParam = activeSubject !== 'All' ? activeSubject : null;
          const typeParam = activeType !== 'All' ? activeType.toLowerCase() : null;
          console.log(`📚 Getting filtered content - Subject: ${subjectParam}, Type: ${typeParam}`);
          
          data = await getContent(subjectParam, typeParam);
        }
        
        console.log(`📊 Loaded ${data?.length || 0} content items`);
        setContentItems(data || []);
      } catch (err) {
        console.error('❌ Error fetching content:', err);
        setError(err.message || 'Failed to load content. Please try again.');
      } finally {
        setIsLoading(false);
        setIsRetrying(false);
        setIsSearching(false);
      }
    };
    
    fetchContent();
  }, [activeSubject, activeType, isRetrying, isSearching, searchQuery]);
  
  // Set active subject from URL param on mount
  useEffect(() => {
    if (subject) {
      setActiveSubject(subject);
    }
  }, [subject]);
  
  // Handle retry when fetch fails
  const handleRetry = () => {
    setIsRetrying(true);
  };
  
  // Handle search
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setIsSearching(true);
    }
  };
  
  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
    setIsSearching(false);
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-6">
          {isSearching && searchQuery 
            ? `Search Results: "${searchQuery}"` 
            : activeSubject === 'All' 
              ? 'Browse All Content' 
              : `${activeSubject} Resources`}
        </h1>
        
        {/* Search Bar */}
        <div className="mb-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-grow relative">
              <input
                type="search"
                placeholder="Search for content..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                disabled={isLoading}
              />
              {isSearching && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-3 top-2 text-gray-400 hover:text-gray-600"
                  aria-label="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading || !searchQuery.trim()}
            >
              Search
            </button>
          </form>
        </div>
        
        {/* Filters */}
        <div className="flex flex-col sm:flex-row flex-wrap gap-4 mb-6">
          <div className="w-full sm:w-auto">
            <label htmlFor="subject-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Subject
            </label>
            <select
              id="subject-filter"
              className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={activeSubject}
              onChange={(e) => setActiveSubject(e.target.value)}
              disabled={isLoading}
            >
              {subjects.map(subj => (
                <option key={subj} value={subj}>
                  {subj}
                </option>
              ))}
            </select>
          </div>
          
          <div className="w-full sm:w-auto">
            <label htmlFor="type-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Content Type
            </label>
            <select
              id="type-filter"
              className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={activeType}
              onChange={(e) => setActiveType(e.target.value)}
              disabled={isLoading}
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
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <p className="font-bold">Error loading content</p>
                <p>{error}</p>
              </div>
              <button 
                onClick={handleRetry}
                className="mt-2 sm:mt-0 bg-red-200 hover:bg-red-300 text-red-800 font-bold py-1 px-3 rounded"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        
        {/* Loading State */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-600">Loading content...</p>
          </div>
        ) : contentItems.length > 0 ? (
          /* Content Items */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {contentItems.map(content => (
              <ContentRecommendation key={content.id} content={content} />
            ))}
          </div>
        ) : (
          /* No Content Found */
          <div className="text-center py-12 text-gray-500">
            <svg 
              className="mx-auto h-12 w-12 text-gray-400" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 12H4" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 4v16M17 4v16" />
            </svg>
            <p className="mt-2 text-lg">
              {isSearching 
                ? `No results found for "${searchQuery}"`
                : "No content found for the selected filters."}
            </p>
            <p className="mt-1">
              {isSearching
                ? "Try a different search term or broaden your filters."
                : "Try changing your filter options or select 'All' to see all available content."}
            </p>
            {isSearching && (
              <button
                onClick={handleClearSearch}
                className="mt-4 px-4 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200"
              >
                Clear Search
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentPage;