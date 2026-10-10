import React from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  TextField,
  Button,
  Alert,
  Link,
  Divider,
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
} from '@mui/material';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';
import { useFormik } from 'formik';
import * as Yup from 'yup';

const validationSchema = Yup.object({
  username: Yup.string()
    .min(3, 'Username must be at least 3 characters')
    .required('Username is required'),
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
  password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
  confirmPassword: Yup.string()
    .oneOf([Yup.ref('password')], 'Passwords must match')
    .required('Confirm password is required'),
  acceptTerms: Yup.boolean()
    .oneOf([true], 'You must accept the terms and conditions')
    .required('You must accept the terms and conditions'),
});

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, error: authError } = useAuth();
  const [error, setError] = React.useState<string | null>(null);

  const formik = useFormik({
    initialValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptTerms: false,
      accountType: (location.state as { accountType?: string } | null)?.accountType || 'user',
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        const created = await register({
          username: values.username,
          email: values.email,
          password: values.password,
          is_developer: values.accountType === 'provider',
        });
        if (created) navigate(values.accountType === 'provider' ? '/provider/listings' : '/dashboard');
        else setError('Could not create your account. Check your details and try again.');
      } catch (err) {
        setError('Registration failed. Please try again.');
      }
    },
  });

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
          }}
        >
          <Typography variant="h4" component="h1" align="center" gutterBottom>
            Create Account
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            align="center"
            sx={{ mb: 4 }}
          >
            Join AgentLedge
          </Typography>
          <Typography fontWeight={600} sx={{ mb: 1 }}>How will you use AgentLedge?</Typography>
          <RadioGroup row name="accountType" value={formik.values.accountType} onChange={formik.handleChange} sx={{ mb: 2 }}>
            <FormControlLabel value="user" control={<Radio />} label="Discover and use agents" />
            <FormControlLabel value="provider" control={<Radio />} label="Register agent services" />
          </RadioGroup>
          {formik.values.accountType === 'provider' && <Alert severity="info" sx={{ mb: 2 }}>Provider accounts can publish agent service listings after sign-up. You can still use other services too.</Alert>}

          {(authError || error) && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {authError || error}
            </Alert>
          )}

          <form onSubmit={formik.handleSubmit}>
            <TextField
              fullWidth
              name="username"
              label="Username"
              value={formik.values.username}
              onChange={formik.handleChange}
              error={formik.touched.username && Boolean(formik.errors.username)}
              helperText={formik.touched.username && formik.errors.username}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              name="email"
              label="Email"
              type="email"
              value={formik.values.email}
              onChange={formik.handleChange}
              error={formik.touched.email && Boolean(formik.errors.email)}
              helperText={formik.touched.email && formik.errors.email}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              name="password"
              label="Password"
              type="password"
              value={formik.values.password}
              onChange={formik.handleChange}
              error={formik.touched.password && Boolean(formik.errors.password)}
              helperText={formik.touched.password && formik.errors.password}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              name="confirmPassword"
              label="Confirm Password"
              type="password"
              value={formik.values.confirmPassword}
              onChange={formik.handleChange}
              error={
                formik.touched.confirmPassword &&
                Boolean(formik.errors.confirmPassword)
              }
              helperText={
                formik.touched.confirmPassword && formik.errors.confirmPassword
              }
              sx={{ mb: 3 }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  name="acceptTerms"
                  checked={formik.values.acceptTerms}
                  onChange={formik.handleChange}
                />
              }
              label={
                <Typography variant="body2">
                  I have read the{' '}
                  <Link component={RouterLink} to="/terms" color="primary">
                    Prototype Terms
                  </Link>{' '}
                  and{' '}
                  <Link component={RouterLink} to="/privacy" color="primary">
                    Privacy Summary
                  </Link>
                </Typography>
              }
            />
            {formik.touched.acceptTerms && formik.errors.acceptTerms && (
              <Typography color="error" variant="caption" display="block">
                {formik.errors.acceptTerms}
              </Typography>
            )}

            <Button
              fullWidth
              variant="contained"
              size="large"
              type="submit"
              disabled={formik.isSubmitting}
              sx={{ mt: 2, mb: 2 }}
            >
              {formik.isSubmitting ? 'Creating account…' : 'Create Account'}
            </Button>
          </form>

          <Divider sx={{ my: 3 }}>
            <Typography variant="body2" color="text.secondary">
              OR
            </Typography>
          </Divider>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Already have an account?{' '}
              <Link component={RouterLink} to="/auth/login" color="primary">
                Sign in
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};
