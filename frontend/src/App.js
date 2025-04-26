import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { useAuth } from './hooks/useAuth';

// Layout Components
import Navigation from './components/Navigation';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ContentPage from './pages/ContentPage';
import ProfilePage from './pages/ProfilePage';

// Enhanced Protected Route Component
import ProtectedRoute from './components/ProtectedRoute';

// Debug Components (Only in development)
import AuthDebugger from './components/AuthDebugger';

function App() {
  const { authInitialized } = useAuth();
  
  // Show loading spinner until authentication is initialized
  if (!authInitialized) {
    return (
      <div className="App min-h-screen bg-gray-50 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        <p className="ml-3 text-gray-600">Loading application...</p>
      </div>
    );
  }
  
  return (
    <div className="App min-h-screen bg-gray-50">
      <Navigation />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Protected Routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } />
          
          <Route path="/content/:subject?" element={
            <ProtectedRoute>
              <ContentPage />
            </ProtectedRoute>
          } />
          
          <Route path="/profile" element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          } />
          
          {/* Debug Routes - Only visible in development */}
          {process.env.NODE_ENV === 'development' && (
            <Route path="/debug/auth" element={<AuthDebugger />} />
          )}
          
          {/* Fallback Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;