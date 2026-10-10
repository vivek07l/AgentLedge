import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';

export const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user?.is_admin ? <>{children}</> : <Navigate to="/admin/login" replace />;
};
