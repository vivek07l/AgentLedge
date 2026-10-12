import React from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Alert,
  TextField,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Switch,
  Stack,
} from '@mui/material';
import { Delete, Key } from '@mui/icons-material';
import { useAuth } from '../store/AuthContext';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { authService } from '../services/auth';
import { autonomousPolicyService, AutonomousPolicy } from '../services/autonomousPolicy';

const validationSchema = Yup.object({
  username: Yup.string().required('Username is required'),
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
  current_password: Yup.string().min(8, 'Password must be at least 8 characters'),
  new_password: Yup.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: Yup.string().oneOf(
    [Yup.ref('new_password')],
    'Passwords must match'
  ),
});

const passwordValidationSchema = Yup.object({
  current_password: Yup.string().required('Current password is required'),
  new_password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .required('New password is required'),
  confirm_password: Yup.string()
    .oneOf([Yup.ref('new_password')], 'Passwords must match')
    .required('Please confirm your password'),
});

export const Profile: React.FC = () => {
  const { user, updateUser, token } = useAuth();
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [passwordDialogOpen, setPasswordDialogOpen] = React.useState(false);
  const [apiKeys, setApiKeys] = React.useState<
    { id: string; name: string; created_at: string }[]
  >([]);
  const [autonomousPolicy, setAutonomousPolicy] = React.useState<AutonomousPolicy | null>(null);
  const [autonomousCategories, setAutonomousCategories] = React.useState('');
  const [autonomousListingIds, setAutonomousListingIds] = React.useState('');
  const [savingAutonomousPolicy, setSavingAutonomousPolicy] = React.useState(false);

  React.useEffect(() => {
    if (!token) return;
    autonomousPolicyService.get(token).then((policy) => {
      setAutonomousPolicy(policy);
      setAutonomousCategories(policy.allowed_categories.join(', '));
      setAutonomousListingIds(policy.allowed_listing_ids.join(', '));
    }).catch(() => {
      setError('Autonomous settings are unavailable. Update the backend before configuring this feature.');
    });
  }, [token]);

  const saveAutonomousPolicy = async () => {
    if (!token || !autonomousPolicy) return;
    const categories = autonomousCategories.split(',').map((item) => item.trim()).filter(Boolean);
    const listingIds = autonomousListingIds.split(',').map((item) => Number(item.trim())).filter((item) => Number.isInteger(item) && item > 0);
    if (autonomousPolicy.enabled && categories.length === 0 && listingIds.length === 0) {
      setError('Add at least one allowed category or listing ID before enabling autonomous mode.');
      return;
    }
    setSavingAutonomousPolicy(true);
    setError(null);
    try {
      const saved = await autonomousPolicyService.update(token, {
        enabled: autonomousPolicy.enabled,
        max_task_budget: Number(autonomousPolicy.max_task_budget),
        max_offer_price: Number(autonomousPolicy.max_offer_price),
        max_daily_spend: Number(autonomousPolicy.max_daily_spend),
        allowed_categories: categories,
        allowed_listing_ids: listingIds,
        max_negotiation_attempts: Number(autonomousPolicy.max_negotiation_attempts),
        max_execution_retries: Number(autonomousPolicy.max_execution_retries),
        auto_review: autonomousPolicy.auto_review,
      });
      setAutonomousPolicy(saved);
      setSuccess('Autonomous execution policy saved.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not save autonomous execution settings.');
    } finally {
      setSavingAutonomousPolicy(false);
    }
  };

  const formik = useFormik({
    initialValues: {
      username: user?.username || '',
      email: user?.email || '',
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
    validationSchema,
    onSubmit: async (values) => {
      try {
        await updateUser({
          username: values.username,
          email: values.email,
        });
        setSuccess('Profile updated successfully');
      } catch (err) {
        setError('Failed to update profile');
      }
    },
  });

  const passwordFormik = useFormik({
    initialValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
    validationSchema: passwordValidationSchema,
    onSubmit: async (values) => {
      try {
        await authService.updatePassword(token || '', {
          current_password: values.current_password,
          new_password: values.new_password,
        });
        setSuccess('Password updated successfully');
        setPasswordDialogOpen(false);
        passwordFormik.resetForm();
      } catch (err) {
        setError('Failed to update password');
      }
    },
  });

  const handleCreateApiKey = async () => {
    try {
      // Call API to create new API key
      const response = await fetch('/api/developer/api-keys', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      setApiKeys([...apiKeys, data]);
      setSuccess('API key created successfully');
    } catch (err) {
      setError('Failed to create API key');
    }
  };

  const handleDeleteApiKey = async (keyId: string) => {
    try {
      // Call API to delete API key
      await fetch(`/api/developer/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setApiKeys(apiKeys.filter((key) => key.id !== keyId));
      setSuccess('API key deleted successfully');
    } catch (err) {
      setError('Failed to delete API key');
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Profile Settings
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <Paper id="autonomous-execution" sx={{ p: 3, mb: 3, scrollMarginTop: 96 }}>
          <Typography variant="h5" component="h2" gutterBottom>
            Autonomous Execution
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Set one account policy for connected agents. When enabled, eligible marketplace actions can proceed without per-action website approvals, within the limits below. Existing pending approvals are cancelled when you save this enabled policy.
          </Typography>
          {autonomousPolicy ? (
            <Stack spacing={2}>
              <FormControlLabel
                control={<Switch checked={autonomousPolicy.enabled} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, enabled: event.target.checked })} />}
                label={autonomousPolicy.enabled ? 'Autonomous mode enabled' : 'Autonomous mode disabled'}
              />
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}><TextField fullWidth type="number" label="Maximum budget per task" value={autonomousPolicy.max_task_budget} inputProps={{ min: 0.01, max: 1000, step: 0.5 }} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, max_task_budget: Number(event.target.value) })} /></Grid>
                <Grid item xs={12} sm={4}><TextField fullWidth type="number" label="Maximum accepted offer" value={autonomousPolicy.max_offer_price} inputProps={{ min: 0.01, max: 1000, step: 0.5 }} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, max_offer_price: Number(event.target.value) })} /></Grid>
                <Grid item xs={12} sm={4}><TextField fullWidth type="number" label="Daily token spending limit" value={autonomousPolicy.max_daily_spend} inputProps={{ min: 0.01, max: 10000, step: 1 }} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, max_daily_spend: Number(event.target.value) })} /></Grid>
                <Grid item xs={12} sm={6}><TextField fullWidth label="Allowed categories (comma separated)" value={autonomousCategories} onChange={(event) => setAutonomousCategories(event.target.value)} helperText="Match marketplace category names exactly; a category or listing allowlist is required." /></Grid>
                <Grid item xs={12} sm={6}><TextField fullWidth label="Allowed listing IDs (comma separated)" value={autonomousListingIds} onChange={(event) => setAutonomousListingIds(event.target.value)} helperText="Optional IDs; use this to allow specific listings." /></Grid>
                <Grid item xs={12} sm={4}><TextField fullWidth type="number" label="New negotiations per day" value={autonomousPolicy.max_negotiation_attempts} inputProps={{ min: 1, max: 100 }} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, max_negotiation_attempts: Number(event.target.value) })} /></Grid>
                <Grid item xs={12} sm={4}><TextField fullWidth type="number" label="Provider retry limit" value={autonomousPolicy.max_execution_retries} inputProps={{ min: 0, max: 3 }} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, max_execution_retries: Number(event.target.value) })} /></Grid>
                <Grid item xs={12} sm={4}><FormControlLabel control={<Switch checked={autonomousPolicy.auto_review} onChange={(event) => setAutonomousPolicy({ ...autonomousPolicy, auto_review: event.target.checked })} />} label="Post factual completion reviews automatically" /></Grid>
              </Grid>
              <Typography variant="body2" color="text.secondary">
                Balance: {autonomousPolicy.token_balance} tokens · Spent today: {autonomousPolicy.spent_today} · Daily budget remaining: {autonomousPolicy.remaining_daily_budget}
              </Typography>
              <Box><Button variant="contained" onClick={saveAutonomousPolicy} disabled={savingAutonomousPolicy}>{savingAutonomousPolicy ? 'Saving…' : 'Save autonomous policy'}</Button></Box>
            </Stack>
          ) : <Typography color="text.secondary">Loading account policy…</Typography>}
        </Paper>

        <Grid container spacing={3}>
          {/* Profile Information */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  mb: 3,
                }}
              >
                <Avatar
                  sx={{ width: 64, height: 64, mr: 2 }}
                  src={user?.avatar_url}
                >
                  {user?.username?.[0]?.toUpperCase()}
                </Avatar>
                <Box>
                  <Typography variant="h6">{user?.username}</Typography>
                  <Typography color="text.secondary">{user?.email}</Typography>
                </Box>
              </Box>

              <form onSubmit={formik.handleSubmit}>
                <TextField
                  fullWidth
                  name="username"
                  label="Username"
                  value={formik.values.username}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.username && Boolean(formik.errors.username)
                  }
                  helperText={formik.touched.username && formik.errors.username}
                  sx={{ mb: 2 }}
                />
                <TextField
                  fullWidth
                  name="email"
                  label="Email"
                  value={formik.values.email}
                  onChange={formik.handleChange}
                  error={formik.touched.email && Boolean(formik.errors.email)}
                  helperText={formik.touched.email && formik.errors.email}
                  sx={{ mb: 2 }}
                />
                <Button variant="contained" type="submit">
                  Save Changes
                </Button>
                <Button
                  variant="outlined"
                  sx={{ ml: 2 }}
                  onClick={() => setPasswordDialogOpen(true)}
                >
                  Change Password
                </Button>
              </form>
            </Paper>
          </Grid>

          {/* API Keys */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  mb: 2,
                }}
              >
                <Typography variant="h6">API Keys</Typography>
                <Button
                  variant="contained"
                  startIcon={<Key />}
                  onClick={handleCreateApiKey}
                >
                  Create New Key
                </Button>
              </Box>
              <List>
                {apiKeys.map((key) => (
                  <React.Fragment key={key.id}>
                    <ListItem>
                      <ListItemText
                        primary={key.name}
                        secondary={`Created: ${new Date(
                          key.created_at
                        ).toLocaleDateString()}`}
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => handleDeleteApiKey(key.id)}
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>

      </Box>

      {/* Change Password Dialog */}
      <Dialog
        open={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <form onSubmit={passwordFormik.handleSubmit}>
          <DialogTitle>Change Password</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              <TextField
                fullWidth
                type="password"
                name="current_password"
                label="Current Password"
                value={passwordFormik.values.current_password}
                onChange={passwordFormik.handleChange}
                error={
                  passwordFormik.touched.current_password &&
                  Boolean(passwordFormik.errors.current_password)
                }
                helperText={
                  passwordFormik.touched.current_password &&
                  passwordFormik.errors.current_password
                }
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                type="password"
                name="new_password"
                label="New Password"
                value={passwordFormik.values.new_password}
                onChange={passwordFormik.handleChange}
                error={
                  passwordFormik.touched.new_password &&
                  Boolean(passwordFormik.errors.new_password)
                }
                helperText={
                  passwordFormik.touched.new_password &&
                  passwordFormik.errors.new_password
                }
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                type="password"
                name="confirm_password"
                label="Confirm New Password"
                value={passwordFormik.values.confirm_password}
                onChange={passwordFormik.handleChange}
                error={
                  passwordFormik.touched.confirm_password &&
                  Boolean(passwordFormik.errors.confirm_password)
                }
                helperText={
                  passwordFormik.touched.confirm_password &&
                  passwordFormik.errors.confirm_password
                }
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPasswordDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Update Password
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Container>
  );
};
