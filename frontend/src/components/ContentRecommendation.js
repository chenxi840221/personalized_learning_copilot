import React from 'react';

const ContentRecommendation = ({ content }) => {
  // Get content type icon
  const getContentTypeIcon = () => {
    switch (content.content_type) {
      case 'video':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'interactive':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        );
      case 'quiz':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'worksheet':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case 'lesson':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        );
      case 'activity':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
        );
      case 'article':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
        );
    }
  };

  // Get difficulty color
  const getDifficultyColor = () => {
    const difficulty = content.difficulty_level || 'intermediate';
    switch (difficulty) {
      case 'beginner':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'intermediate':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'advanced':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Get grade level display
  const getGradeLevel = () => {
    if (!content.grade_level || content.grade_level.length === 0) {
      return "All grades";
    }
    
    // Sort the grade levels
    const grades = [...content.grade_level].sort((a, b) => a - b);
    
    // Format as range or list
    if (grades.length === 1) {
      return `Grade ${grades[0]}`;
    } else if (grades.length === 2) {
      return `Grades ${grades[0]} & ${grades[1]}`;
    } else {
      // Check if it's a continuous range
      let isRange = true;
      for (let i = 1; i < grades.length; i++) {
        if (grades[i] !== grades[i-1] + 1) {
          isRange = false;
          break;
        }
      }
      
      if (isRange) {
        return `Grades ${grades[0]}-${grades[grades.length - 1]}`;
      } else {
        return `Grades ${grades.join(', ')}`;
      }
    }
  };

  // Format duration
  const formatDuration = (minutes) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins > 0 ? `${mins}m` : ''}`;
  };

  // Check if the content has required properties before rendering
  if (!content || !content.title) {
    return (
      <div className="block bg-white border border-gray-200 rounded-lg p-4 h-full">
        <p className="text-gray-500">Content not available</p>
      </div>
    );
  }

  // Handle URL appropriately
  const contentUrl = content.url || '#';
  const openContent = (e) => {
    if (contentUrl === '#') {
      e.preventDefault();
      alert('Content URL not available');
    }
  };

  return (
    <a 
      href={contentUrl} 
      target="_blank" 
      rel="noopener noreferrer"
      onClick={openContent}
      className="block bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow duration-200 h-full"
    >
      <div className="p-4 flex flex-col h-full">
        {/* Content Type and Subject */}
        <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
          <div className="flex items-center text-sm text-gray-600">
            {getContentTypeIcon()}
            <span className="ml-1 capitalize">{content.content_type}</span>
          </div>
          
          <span className="text-sm font-medium text-blue-600">
            {content.subject}
          </span>
        </div>
        
        {/* Title */}
        <h3 className="text-lg font-medium text-gray-900 mb-2 line-clamp-2">
          {content.title}
        </h3>
        
        {/* Description */}
        <p className="text-gray-600 text-sm mb-3 line-clamp-3 flex-grow">
          {content.description}
        </p>
        
        {/* Topics */}
        {content.topics && content.topics.length > 0 && (
          <div className="mb-3">
            <div className="flex flex-wrap gap-1">
              {content.topics.slice(0, 3).map((topic, index) => (
                <span 
                  key={index} 
                  className="inline-block bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full"
                >
                  {topic}
                </span>
              ))}
              {content.topics.length > 3 && (
                <span className="text-xs text-gray-500">+{content.topics.length - 3} more</span>
              )}
            </div>
          </div>
        )}
        
        {/* Metadata */}
        <div className="flex items-center justify-between mt-auto flex-wrap gap-2 pt-2">
          {/* Difficulty */}
          <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getDifficultyColor()}`}>
            {content.difficulty_level || 'intermediate'}
          </span>
          
          <div className="flex gap-3">
            {/* Grade Level */}
            <span className="text-xs text-gray-500 flex items-center">
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              {getGradeLevel()}
            </span>
            
            {/* Duration */}
            {content.duration_minutes && (
              <span className="text-xs text-gray-500 flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {formatDuration(content.duration_minutes)}
              </span>
            )}
          </div>
        </div>
      </div>
    </a>
  );
};

export default ContentRecommendation;