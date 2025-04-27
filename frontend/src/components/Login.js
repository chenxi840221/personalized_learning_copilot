// frontend/src/components/Login.js
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useEntraAuth } from '../hooks/useEntraAuth';

const Login = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { user, loading, login, isAuthenticated } = useEntraAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get redirect URL from location state
  const from = location.state?.from?.pathname || '/dashboard';
  
  // Store the redirect path for after authentication
  useEffect(() => {
    if (from && from !== '/login') {
      sessionStorage.setItem('redirectTo', from);
    }
  }, [from]);
  
  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);
  
  // Handle login click
  const handleLogin = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      // Start Entra ID login flow
      await login();
      
      // Login is handled by MSAL redirect flow
      // The page will redirect to Microsoft for authentication
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to login. Please try again.');
      setIsLoading(false);
    }
  };
  
  // If still checking authentication status, show loading
  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[80vh]">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        <p className="ml-2 text-gray-600">Checking authentication status...</p>
      </div>
    );
  }
  
  return (
    <div className="flex justify-center items-center min-h-[80vh]">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-blue-600 mb-6">
          Login to Learning Co-pilot
        </h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <div className="space-y-6">
          <div className="flex flex-col space-y-2">
            <button
              onClick={handleLogin}
              className="w-full bg-[#0078d4] text-white font-bold py-3 px-4 rounded-md hover:bg-[#106ebe] focus:outline-none focus:ring-2 focus:ring-[#0078d4] focus:ring-opacity-50 disabled:opacity-50 flex items-center justify-center"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></span>
                  Signing in...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 15a7 7 0 110-14 7 7 0 010 14z" />
                  </svg>
                  Sign in with Microsoft
                </>
              )}
            </button>
          </div>
          
          <div className="text-center text-sm text-gray-600">
            <p>
              This application uses Entra ID (formerly Azure AD) for authentication.
            </p>
            <p className="mt-2">
              You will be redirected to the Microsoft login page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;