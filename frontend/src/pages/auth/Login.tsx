import React from 'react';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Link,
  Alert,
  CircularProgress,
  Stack,
} from '@mui/material';
import { useAuth } from '../../store/AuthContext';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import type { LoginCredentials } from '../../types/user';

export const Login: React.FC = () => {
  const { login, error: authError, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginCredentials>();

  const onSubmit = async (data: LoginCredentials) => {
    try {
      await login(data);
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      // Error handled by AuthContext
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: { xs: 4, sm: 8 }, mb: 4 }}>
        <Paper
          elevation={0}
          sx={{
            p: { xs: 3, sm: 4.5 },
            bgcolor: '#FFFFFF',
            border: '2px solid #292929',
            boxShadow: '6px 6px 0 #171717',
          }}
        >
          <Stack alignItems="center" sx={{ mb: 3 }}>
            <Box
              sx={{
                width: 38,
                height: 38,
                bgcolor: '#F6C900',
                border: '2px solid #171717',
                boxShadow: '2px 2px 0 #171717',
                display: 'grid',
                placeItems: 'center',
                color: '#171717',
                fontWeight: 900,
                fontSize: 20,
                clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
                mb: 1.5,
              }}
            >
              A
            </Box>
            <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
              AGENTSLEDGE // AUTHENTICATION
            </Typography>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 850, color: '#171717' }}>
              Sign In
            </Typography>
          </Stack>

          <form onSubmit={handleSubmit(onSubmit)}>
            <TextField
              margin="normal"
              required
              fullWidth
              label="Username"
              autoComplete="username"
              autoFocus
              {...register('username', { required: 'Username is required' })}
              error={!!errors.username}
              helperText={errors.username?.message}
            />

            <TextField
              margin="normal"
              required
              fullWidth
              label="Password"
              type="password"
              autoComplete="current-password"
              {...register('password', { required: 'Password is required' })}
              error={!!errors.password}
              helperText={errors.password?.message}
            />

            {authError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {authError}
              </Alert>
            )}

            <Button
              type="submit"
              fullWidth
              variant="contained"
              color="secondary"
              size="large"
              sx={{ mt: 3, mb: 2, py: 1.25, fontWeight: 900 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In'}
            </Button>

            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Link component={RouterLink} to="/auth/forgot-password" variant="body2" sx={{ color: '#171717', fontWeight: 650 }}>
                Forgot password?
              </Link>
            </Box>
            <Box sx={{ mt: 1, textAlign: 'center' }}>
              <Link component={RouterLink} to="/admin/login" variant="body2" sx={{ color: '#706E66' }}>
                Administrator portal →
              </Link>
            </Box>

            <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid #EAE5D9', textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Don't have an account?{' '}
                <Link component={RouterLink} to="/auth/register" sx={{ color: '#171717', fontWeight: 800 }}>
                  Create an account
                </Link>
              </Typography>
            </Box>
          </form>
        </Paper>
      </Box>
    </Container>
  );
};
