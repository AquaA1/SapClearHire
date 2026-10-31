import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User } from '../contracts/models';
import { UserRole } from '../contracts/enums';
import { authService } from '../services/api/authService';
import { getStoredToken, setStoredToken, removeStoredToken } from '../services/api/client';

export interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitializing: boolean;
  login: (email: string, password?: string) => Promise<User>;
  register: (fullName: string, email: string, password?: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);

  const logout = useCallback(() => {
    removeStoredToken();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // Hydrate session from localStorage on application start
  useEffect(() => {
    const hydrateSession = async () => {
      const token = getStoredToken();
      if (!token) {
        setIsInitializing(false);
        return;
      }

      try {
        const currentUser = await authService.getMe();
        setUser(currentUser);
        setIsAuthenticated(true);
      } catch (err) {
        console.warn('Session hydration failed (expired or invalid token):', err);
        logout();
      } finally {
        setIsInitializing(false);
      }
    };

    hydrateSession();

    // Listen for unauthorized events emitted by apiClient
    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener('clearhire:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('clearhire:unauthorized', handleUnauthorized);
    };
  }, [logout]);

  const login = async (email: string, password = ''): Promise<User> => {
    setIsLoading(true);
    try {
      const tokenRes = await authService.login({ email, password });
      setStoredToken(tokenRes.access_token);
      const currentUser = await authService.getMe();
      setUser(currentUser);
      setIsAuthenticated(true);
      return currentUser;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (fullName: string, email: string, password = ''): Promise<User> => {
    setIsLoading(true);
    try {
      // 1. Create candidate user in backend
      await authService.register({ full_name: fullName, email, password });
      // 2. Authenticate to obtain Bearer JWT
      const tokenRes = await authService.login({ email, password });
      setStoredToken(tokenRes.access_token);
      // 3. Hydrate user identity
      const currentUser = await authService.getMe();
      setUser(currentUser);
      setIsAuthenticated(true);
      return currentUser;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        isAuthenticated,
        isLoading,
        isInitializing,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const useAuthStore = useAuth;
