import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  // Toggle mobile menu
  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };
  
  // Close mobile menu
  const closeMenu = () => {
    setIsMenuOpen(false);
  };
  
  // Handle logout
  const handleLogout = () => {
    logout();
    navigate('/login');
    closeMenu();
  };
  
  // Check if a link is active
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };
  
  return (
    <nav className="bg-white shadow-md">
      <div className="container mx-auto px-4">
        <div className="flex justify-between h-16">
          {/* Logo and main nav links */}
          <div className="flex">
            {/* Logo */}
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="font-bold text-xl text-blue-600">
                Learning Co-pilot
              </Link>
            </div>
            
            {/* Desktop Navigation Links */}
            <div className="hidden sm:ml-6 sm:flex sm:space-x-4 sm:items-center">
              <Link
                to="/"
                className={`px-3 py-2 text-sm font-medium rounded-md ${
                  isActive('/') 
                    ? 'bg-blue-50 text-blue-700' 
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                Home
              </Link>
              
              {user && (
                <>
                  <Link
                    to="/dashboard"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/dashboard') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    Dashboard
                  </Link>
                  
                  <Link
                    to="/content"
                    className={`px-3 py-2 text-sm font-medium rounded-md ${
                      isActive('/content') 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    Content
                  </Link>
                </>
              )}
            </div>
          </div>
          
          {/* User menu and mobile menu button */}
          <div className="flex items-center">
            {/* Authentication Links (Desktop) */}
            <div className="hidden sm:flex sm:items-center">
              {user ? (
                <div className="ml-3 relative">
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-700 mr-2">
                      {user.full_name || user.username}
                    </span>
                    
                    <Link to="/profile" className="mr-2">
                      <button className="bg-white p-1 rounded-full text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </button>
                    </Link>
                    
                    <button
                      onClick={handleLogout}
                      className="bg-blue-600 text-white px-3 py-1 rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex space-x-2">
                  <Link
                    to="/login"
                    className="px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                  >
                    Login
                  </Link>
                  
                  <Link
                    to="/register"
                    className="px-3 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
            
            {/* Mobile menu button */}
            <div className="flex items-center sm:hidden">
              <button
                onClick={toggleMenu}
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              >
                <span className="sr-only">{isMenuOpen ? 'Close menu' : 'Open menu'}</span>
                {/* Icon when menu is closed */}
                {!isMenuOpen ? (
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                ) : (
                  <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile menu */}
      {isMenuOpen && (
        <div className="sm:hidden">
          <div className="pt-2 pb-3 space-y-1">
            <Link
              to="/"
              className={`block px-3 py-2 text-base font-medium ${
                isActive('/') 
                  ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
              }`}
              onClick={closeMenu}
            >
              Home
            </Link>
            
            {user && (
              <>
                <Link
                  to="/dashboard"
                  className={`block px-3 py-2 text-base font-medium ${
                    isActive('/dashboard') 
                      ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                  }`}
                  onClick={closeMenu}
                >
                  Dashboard
                </Link>
                
                <Link
                  to="/content"
                  className={`block px-3 py-2 text-base font-medium ${
                    isActive('/content') 
                      ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' 
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 border-l-4 border-transparent'
                  }`}
                  onClick={closeMenu}
                >
                  Content
                </Link>
              </>
            )}
          </div>
          
          {/* Mobile Authentication Links */}
          <div className="pt-4 pb-3 border-t border-gray-200">
            {user ? (
              <div>
                <div className="flex items-center px-4">
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <span className="text-gray-600 font-semibold">
                        {user.full_name ? user.full_name.charAt(0) : user.username.charAt(0)}
                      </span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <div className="text-base font-medium text-gray-800">{user.full_name || user.username}</div>
                    <div className="text-sm font-medium text-gray-500">{user.email}</div>
                  </div>
                </div>
                <div className="mt-3 space-y-1">
                  <Link
                    to="/profile"
                    className="block px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-100"
                    onClick={closeMenu}
                  >
                    Your Profile
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-100"
                  >
                    Logout
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-1 px-4">
                <Link
                  to="/login"
                  className="block py-2 text-base font-medium text-gray-700 hover:bg-gray-100"
                  onClick={closeMenu}
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="block py-2 text-base font-medium text-gray-700 hover:bg-gray-100"
                  onClick={closeMenu}
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navigation;