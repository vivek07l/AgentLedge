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
  Stack,
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
      <Box sx={{ mt: { xs: 4, sm: 6 }, mb: 6 }}>
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
              AGENTSLEDGE // NEW MEMBER REGISTRATION
            </Typography>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 850, color: '#171717' }}>
              Create Account
            </Typography>
          </Stack>

          <Typography fontWeight={750} sx={{ mb: 1, color: '#171717' }}>
            Account role selection:
          </Typography>
          <RadioGroup
            row
            name="accountType"
            value={formik.values.accountType}
            onChange={formik.handleChange}
            sx={{ mb: 2 }}
          >
            <FormControlLabel
              value="user"
              control={<Radio sx={{ color: '#171717', '&.Mui-checked': { color: '#F6C900' } }} />}
              label={<Typography variant="body2" fontWeight={650}>Discover & invoke agents</Typography>}
            />
            <FormControlLabel
              value="provider"
              control={<Radio sx={{ color: '#171717', '&.Mui-checked': { color: '#F6C900' } }} />}
              label={<Typography variant="body2" fontWeight={650}>Register agent services</Typography>}
            />
          </RadioGroup>

          {formik.values.accountType === 'provider' && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Provider accounts can publish and manage services in the marketplace immediately upon registration.
            </Alert>
          )}

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
              error={formik.touched.confirmPassword && Boolean(formik.errors.confirmPassword)}
              helperText={formik.touched.confirmPassword && formik.errors.confirmPassword}
              sx={{ mb: 2.5 }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  name="acceptTerms"
                  checked={formik.values.acceptTerms}
                  onChange={formik.handleChange}
                  sx={{ color: '#171717', '&.Mui-checked': { color: '#171717' } }}
                />
              }
              label={
                <Typography variant="body2">
                  I have read the{' '}
                  <Link component={RouterLink} to="/terms" sx={{ color: '#171717', fontWeight: 700 }}>
                    Prototype Terms
                  </Link>{' '}
                  and{' '}
                  <Link component={RouterLink} to="/privacy" sx={{ color: '#171717', fontWeight: 700 }}>
                    Privacy Summary
                  </Link>
                </Typography>
              }
            />
            {formik.touched.acceptTerms && formik.errors.acceptTerms && (
              <Typography color="error" variant="caption" display="block" sx={{ mb: 1 }}>
                {formik.errors.acceptTerms}
              </Typography>
            )}

            <Button
              fullWidth
              variant="contained"
              color="secondary"
              size="large"
              type="submit"
              disabled={formik.isSubmitting}
              sx={{ mt: 2, mb: 2, py: 1.25, fontWeight: 900 }}
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
              <Link component={RouterLink} to="/auth/login" sx={{ color: '#171717', fontWeight: 800 }}>
                Sign in
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};
