import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: UserRole[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRoles }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();
  
  // Check if token exists in localStorage
  const hasToken = localStorage.getItem('access_token');

  if (isLoading) {
    return (
      <div className="loading-container">
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  if (!isAuthenticated || !hasToken) {
    // Redirect to login page but save the location they were trying to go to
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRoles && user && !requiredRoles.includes(user.role)) {
    // User doesn't have required role, redirect to their default page
    switch (user.role) {
      case 'driver':
        return <Navigate to="/driver" replace />;
      case 'customer':
        return <Navigate to="/customer" replace />;
      default:
        return <Navigate to="/dashboard" replace />;
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;