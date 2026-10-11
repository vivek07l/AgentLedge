import React, { useCallback, useEffect, useState } from 'react';
import {
  Container,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useAuth } from '../../store/AuthContext';
import { agentService } from '../../services/agent';
import { Agent } from '../../types/agent';
import { useNavigate } from 'react-router-dom';

interface AgentFormData {
  name: string;
  description: string;
  category: string;
  capabilities: string;
  price: number;
  minimum_price: number | null;
}

export const AgentManagement: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [formData, setFormData] = useState<AgentFormData>({
    name: '',
    description: '',
    category: 'General',
    capabilities: '',
    price: 0,
    minimum_price: null,
  });

  const fetchAgents = useCallback(async () => {
    if (!token) return;

    try {
      const response = await agentService.listMyAgents(token);
      if (response.status === 'success' && response.data) {
        setAgents(response.data);
      } else {
        setError(response.error || 'Failed to fetch agents');
      }
    } catch (err) {
      setError('Failed to fetch agents');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || saving) return;
    setError(null);
    setSuccess(null);
    const cleaned = {
      ...formData,
      name: formData.name.trim(),
      description: formData.description.trim(),
      category: formData.category.trim(),
      capabilities: formData.capabilities.trim(),
    };
    if (!cleaned.name || !cleaned.description || !cleaned.category) {
      setError('Enter a service name, description, and category before publishing.');
      return;
    }
    if (!Number.isFinite(cleaned.price) || cleaned.price < 0
      || (cleaned.minimum_price !== null && (!Number.isFinite(cleaned.minimum_price)
        || cleaned.minimum_price < 0 || cleaned.minimum_price > cleaned.price))) {
      setError('Check the listed price and minimum price. The minimum must be between zero and the listed price.');
      return;
    }

    try {
      setSaving(true);
      const response = selectedAgent
        ? await agentService.updateAgent(token, selectedAgent.id, cleaned)
        : await agentService.createAgent(token, cleaned);

      if (response.status === 'success') {
        const createdName = cleaned.name;
        if (!selectedAgent) {
          handleCloseDialog();
          navigate('/marketplace', { state: { publishedService: createdName } });
          return;
        }
        await fetchAgents();
        handleCloseDialog();
        setSuccess(`“${createdName}” was updated.`);
      } else {
        setError(response.error || 'Failed to save agent');
      }
    } catch (err) {
      setError(err instanceof Error ? `Could not save this service: ${err.message}` : 'Could not save this service. Check your connection and try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (agent: Agent) => {
    setSelectedAgent(agent);
    setFormData({
      name: agent.name,
      description: agent.description,
      category: agent.category || 'General',
      capabilities: agent.capabilities || '',
      price: agent.price,
      minimum_price: agent.minimum_price ?? Number((agent.price * 0.8).toFixed(2)),
    });
    setDialogOpen(true);
  };

  const handleDelete = async (agent: Agent) => {
    if (!token) return;

    try {
      const response = await agentService.deleteAgent(token, agent.id);
      if (response.status === 'success') {
        await fetchAgents();
        setDeleteDialogOpen(false);
      } else {
        setError(response.error || 'Failed to delete agent');
      }
    } catch (err) {
      setError('Failed to delete agent');
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedAgent(null);
    setFormData({
      name: '',
      description: '',
      category: 'General',
      capabilities: '',
      price: 0,
      minimum_price: null,
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Agent Management</Typography>
        <Button variant="contained" color="primary" onClick={() => setDialogOpen(true)}>
          Create Agent
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Price</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {agents.map((agent) => (
              <TableRow key={agent.id}>
                <TableCell>{agent.name}</TableCell>
                <TableCell>{agent.description}</TableCell>
                <TableCell>{agent.category || 'General'}</TableCell>
                <TableCell>{agent.price} demo tokens</TableCell>
                <TableCell align="right">
                  <IconButton onClick={() => handleEdit(agent)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    color="error"
                    onClick={() => {
                      setSelectedAgent(agent);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>{selectedAgent ? 'Edit Agent' : 'Create Agent'}</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
              {!selectedAgent && <Alert severity="info">
                Publishing creates a searchable marketplace listing. New listings are discovery-only until an executable implementation is connected and approved by the platform.
              </Alert>}
              <TextField
                label="Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                inputProps={{ maxLength: 120 }}
                fullWidth
              />
              <TextField
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                required
                inputProps={{ maxLength: 5000 }}
                multiline
                rows={4}
                fullWidth
              />
              <TextField
                label="Category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                required
                inputProps={{ maxLength: 80 }}
                fullWidth
              />
              <TextField
                label="Capabilities (comma separated)"
                value={formData.capabilities}
                onChange={(e) => setFormData({ ...formData, capabilities: e.target.value })}
                helperText="Describe what this agent can do so others can find it."
                inputProps={{ maxLength: 1000 }}
                fullWidth
              />
              <TextField
                label="Price"
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: Number(e.target.value) })}
                required
                fullWidth
              />
              <TextField
                label="Minimum acceptable price"
                type="number"
                value={formData.minimum_price ?? ''}
                onChange={(e) => setFormData({ ...formData, minimum_price: e.target.value === '' ? null : Number(e.target.value) })}
                helperText="Negotiation will never accept below this amount. Leave blank to use 80% of the listed price."
                inputProps={{ min: 0, max: formData.price, step: 0.01 }}
                fullWidth
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog} disabled={saving}>Cancel</Button>
            <Button type="submit" variant="contained" color="primary" disabled={saving}>
              {saving ? <CircularProgress size={20} color="inherit" /> : selectedAgent ? 'Save' : 'Publish service'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Agent</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {selectedAgent?.name}? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => selectedAgent && handleDelete(selectedAgent)}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
