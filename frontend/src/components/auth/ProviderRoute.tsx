import React from 'react';
import { Link as RouterLink, Navigate } from 'react-router-dom';
import { Alert, Button, Container, Stack, Typography } from '@mui/material';
import { useAuth } from '../../store/AuthContext';

export const ProviderRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token, loading } = useAuth();
  if (loading) return null;
  if (!token || !user) {
    return <Navigate to="/auth/register" state={{ accountType: 'provider' }} replace />;
  }
  if (!user.is_developer) {
    return <Container maxWidth="sm" sx={{ py: 8 }}>
      <Stack spacing={2}>
        <Typography variant="h5">Provider access is required</Typography>
        <Alert severity="info">
          You are signed in, but this account is not authorized to publish services. Sign in with a provider account or ask a marketplace administrator to enable provider access.
        </Alert>
        <Button component={RouterLink} to="/marketplace" variant="outlined" sx={{ alignSelf: 'flex-start' }}>
          Back to marketplace
        </Button>
      </Stack>
    </Container>;
  }
  return <>{children}</>;
};
