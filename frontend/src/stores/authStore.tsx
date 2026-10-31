import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../contracts/models';
import { UserRole } from '../contracts/enums';
import { mockService } from '../services/mock/mockService';

interface AuthContextType {
  user: User;
  role: UserRole;
  isAuthenticated: boolean;
  login: (email: string, role?: UserRole) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User>(() => mockService.getActiveUser());
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);

  const switchRole = (newRole: UserRole) => {
    const updatedUser = mockService.setActiveRole(newRole);
    setUser(updatedUser);
  };

  const login = async (email: string, role?: UserRole) => {
    if (role) {
      mockService.setActiveRole(role);
    }
    const res = await mockService.login(email);
    setUser(res.user);
    setIsAuthenticated(true);
  };

  const logout = () => {
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user.role,
        isAuthenticated,
        login,
        logout,
        switchRole,
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
