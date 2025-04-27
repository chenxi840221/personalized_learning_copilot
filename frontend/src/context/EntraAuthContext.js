// frontend/src/context/EntraAuthContext.js
import React, { createContext, useState, useEffect, useCallback } from 'react';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import axios from 'axios';
import { apiClient } from '../services/api';

// Create the Auth Context
export const EntraAuthContext = createContext();

// MSAL configuration for Entra ID
const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${process.env.REACT_APP_TENANT_ID}`,
    redirectUri: window.location.origin + '/auth/callback',
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'localStorage', // or 'sessionStorage'
    storeAuthStateInCookie: false
  }
};

// Authentication scopes
const loginRequest = {
  scopes: ['User.Read']
};

const apiRequest = {
  scopes: [process.env.REACT_APP_API_SCOPE || `api://${process.env.REACT_APP_CLIENT_ID}/user_impersonation`]
};

export const EntraAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [msalInstance, setMsalInstance] = useState(null);
  
  // Initialize MSAL instance
  useEffect(() => {
    try {
      const msalApp = new PublicClientApplication(msalConfig);
      setMsalInstance(msalApp);
      
      // Handle redirect response
      msalApp.handleRedirectPromise().then(response => {
        if (response) {
          // Handle successful authentication
          handleResponse(response);
        } else {
          // Check if user is already signed in
          const accounts = msalApp.getAllAccounts();
          if (accounts.length > 0) {
            msalApp.setActiveAccount(accounts[0]);
            getUserInfo(msalApp);
          } else {
            setLoading(false);
          }
        }
      }).catch(err => {
        console.error('Error handling redirect:', err);
        setError(err.message || 'Failed to authenticate');
        setLoading(false);
      });
    } catch (err) {
      console.error('Error initializing MSAL:', err);
      setError(err.message || 'Failed to initialize authentication');
      setLoading(false);
    }
  }, []);
  
  // Handle authentication response
  const handleResponse = useCallback(async (response) => {
    if (response.account) {
      // Set active account
      msalInstance.setActiveAccount(response.account);
      
      // Get user info
      await getUserInfo(msalInstance);
    }
  }, [msalInstance]);
  
  // Get user information from token and profile API
  const getUserInfo = useCallback(async (msalApp) => {
    try {
      setLoading(true);
      
      // Get access token for API
      const tokenResponse = await msalApp.acquireTokenSilent(apiRequest);
      
      // Set authorization header for API requests
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokenResponse.accessToken}`;
      
      // Get user profile from API
      const userProfile = await apiClient.get('/auth/profile');
      
      // Set user info
      setUser({
        ...userProfile.data,
        accessToken: tokenResponse.accessToken
      });
      
      setLoading(false);
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        // User needs to login again
        console.log('Interaction required, redirecting to login');
        msalApp.acquireTokenRedirect(apiRequest);
      } else {
        console.error('Error getting user info:', err);
        setError(err.message || 'Failed to get user information');
        setLoading(false);
      }
    }
  }, []);
  
  // Login function
  const login = useCallback(async () => {
    if (!msalInstance) return;
    
    try {
      // Start login flow with redirect
      await msalInstance.loginRedirect(loginRequest);
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to login');
    }
  }, [msalInstance]);
  
  // Logout function
  const logout = useCallback(() => {
    if (!msalInstance) return;
    
    try {
      // Logout user
      const logoutRequest = {
        account: msalInstance.getActiveAccount(),
        postLogoutRedirectUri: window.location.origin
      };
      
      // Clear user state
      setUser(null);
      
      // Clear auth header
      delete apiClient.defaults.headers.common['Authorization'];
      
      // Redirect to logout
      msalInstance.logoutRedirect(logoutRequest);
    } catch (err) {
      console.error('Logout error:', err);
    }
  }, [msalInstance]);
  
  // Get access token for API calls
  const getAccessToken = useCallback(async () => {
    if (!msalInstance) return null;
    
    try {
      // Try silent token acquisition first
      const tokenResponse = await msalInstance.acquireTokenSilent(apiRequest);
      return tokenResponse.accessToken;
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        // User needs to login again
        console.log('Interaction required, redirecting to login');
        await msalInstance.acquireTokenRedirect(apiRequest);
        return null;
      }
      console.error('Error getting access token:', err);
      return null;
    }
  }, [msalInstance]);
  
  // Check if user is authenticated
  const isAuthenticated = !!user;
  
  // Check if token is valid
  const isTokenValid = useCallback(() => {
    if (!user || !user.accessToken) return false;
    
    // Get token parts
    const tokenParts = user.accessToken.split('.');
    if (tokenParts.length !== 3) return false;
    
    try {
      // Decode token payload
      const payload = JSON.parse(atob(tokenParts[1]));
      
      // Check if token is expired
      const now = Math.floor(Date.now() / 1000);
      return payload.exp > now;
    } catch (err) {
      console.error('Error validating token:', err);
      return false;
    }
  }, [user]);
  
  // Context value
  const value = {
    user,
    loading,
    error,
    login,
    logout,
    getAccessToken,
    isAuthenticated,
    isTokenValid,
    msalInstance
  };

  return (
    <EntraAuthContext.Provider value={value}>
      {children}
    </EntraAuthContext.Provider>
  );
};

export default EntraAuthContext;