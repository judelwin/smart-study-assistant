import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

export interface User {
  id: string;
  email: string;
  created_at: string;
}

interface UserUsage {
  documents: {
    current: number;
    limit: number;
    remaining: number;
  };
  classes: {
    current: number;
    limit: number;
    remaining: number;
  };
  limits: {
    max_file_size_mb: number;
    max_files_per_upload: number;
    uploads_per_hour: number;
  };
}

interface UserContextType {
  user: User | null;
  token: string | null;
  usage: UserUsage | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  refreshUsage: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUserContext = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUserContext must be used within a UserProvider');
  }
  return context;
};

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(false);
  const [usage, setUsage] = useState<UserUsage | null>(null);
  const navigate = useNavigate();

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Invalid email or password.');
        }
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }
      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      // Get user info
      const userResponse = await fetch('/auth/me', {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      const userData = await userResponse.json();
      setUser(userData);
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }
      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      // Get user info
      const userResponse = await fetch('/auth/me', {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      const userData = await userResponse.json();
      setUser(userData);
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  };

  const refreshUsage = async () => {
    if (!token) return;
    try {
      const response = await fetch('/api/user/usage', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const usageData = await response.json();
        setUsage(usageData);
      }
    } catch (error) {
      console.error('Failed to fetch usage data:', error);
    }
  };

  useEffect(() => {
    // On mount, try to fetch user info if token exists
    const fetchUser = async () => {
      if (!token) return;
      try {
        const userResponse = await fetch('/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (userResponse.ok) {
          const userData = await userResponse.json();
          setUser(userData);
          // Fetch usage data after user is loaded
          // await refreshUsage();
        } else {
          // Token is invalid or expired
          setUser(null);
          setToken(null);
          localStorage.removeItem('token');
        }
      } catch (error) {
        // Network error or service unavailable - don't clear token immediately
        // This prevents clearing valid tokens when services are just temporarily down
        console.log('Auth service unavailable, keeping token for retry');
        // Don't clear the token on network errors - let the user retry when services are back
      }
    };
    fetchUser();
  }, [token]);

  const value: UserContextType = {
    user,
    token,
    usage,
    login,
    register,
    logout,
    isLoading,
    refreshUsage,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
}; 