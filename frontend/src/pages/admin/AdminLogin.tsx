import React from 'react';
import { Alert, Box, Button, Container, Paper, TextField, Typography } from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../../store/AuthContext';
import type { LoginCredentials } from '../../types/user';

export const AdminLogin: React.FC = () => {
  const { loginAdmin, error, loading } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit } = useForm<LoginCredentials>();
  const submit = async (credentials: LoginCredentials) => {
    if (await loginAdmin(credentials)) navigate('/admin', { replace: true });
  };
  return <Container maxWidth="sm"><Box sx={{ mt: 10 }}><Paper sx={{ p: { xs: 3, sm: 5 }, borderRadius: 0, border: '2px solid #292929', boxShadow: '6px 6px 0 #171717' }}>
    <Typography color="primary" variant="overline" sx={{ fontWeight: 800, color: '#F6C900', bgcolor: '#171717', px: 1, py: 0.2 }}>AGENTSLEDGE CONTROL</Typography>
    <Typography variant="h4" fontWeight={850} gutterBottom sx={{ mt: 1 }}>Administrator sign in</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>Manage marketplace listings and member accounts.</Typography>
    <form onSubmit={handleSubmit(submit)}>
      <TextField fullWidth label="Username" autoComplete="username" margin="normal" {...register('username', { required: true })} />
      <TextField fullWidth label="Password" type="password" autoComplete="current-password" margin="normal" {...register('password', { required: true })} />
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      <Button fullWidth size="large" variant="contained" type="submit" disabled={loading} sx={{ mt: 3 }}>Sign in securely</Button>
    </form>
    <Button component={RouterLink} to="/auth/login" sx={{ mt: 2 }}>Back to member login</Button>
  </Paper></Box></Container>;
};
