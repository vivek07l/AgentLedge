import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  BarChart,
  People,
  TrendingUp,
  Token,
} from '@mui/icons-material';
import { useAuth } from '../../store/AuthContext';
import { agentService } from '../../services/agent';
import { useNavigate } from 'react-router-dom';
import { Agent } from '../../types/agent';

interface DashboardStats {
  totalInvocations: number;
  activeAgents: number;
  settledTokensEarned: number;
  tokenBalance: number;
}

interface AgentStats {
  id: number;
  invocations: number;
  successRate: number | null;
  reviewCount: number;
}

export const DeveloperDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { token, refreshUser } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    totalInvocations: 0,
    activeAgents: 0,
    settledTokensEarned: 0,
    tokenBalance: 0,
  });
  const [agentStats, setAgentStats] = useState<AgentStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;

      try {
        const [response, providerStats] = await Promise.all([
          agentService.listMyAgents(token), agentService.getProviderStats(token),
        ]);
        if (response.status === 'success' && response.data && providerStats.data) {
          setAgents(response.data);
          const realStats: AgentStats[] = response.data.map(agent => ({
            id: agent.id,
            invocations: agent.completed_invocations || 0,
            successRate: agent.success_rate ?? null,
            reviewCount: agent.review_count || 0,
          }));
          setAgentStats(realStats);

          setStats({
            totalInvocations: realStats.reduce((sum, stat) => sum + stat.invocations, 0),
            activeAgents: providerStats.data.active_listings,
            settledTokensEarned: providerStats.data.settled_tokens_earned,
            tokenBalance: providerStats.data.token_balance,
          });
          await refreshUser();
        } else {
          setError(providerStats.error || response.error || 'Failed to fetch provider data');
        }
      } catch (err) {
        setError('Failed to fetch dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 3,
          }}
        >
          <Typography variant="h4" component="h1">
            Developer Dashboard
          </Typography>
          <Button
            variant="contained"
            onClick={() => navigate('/developer/agents/create')}
          >
            Create New Agent
          </Button>
        </Box>

        <Grid container spacing={3}>
          {/* Summary Cards */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Token color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Tokens earned</Typography>
                </Box>
                <Typography variant="h4">{stats.settledTokensEarned} tokens</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <People color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Active listings</Typography>
                </Box>
                <Typography variant="h4">{stats.activeAgents}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <BarChart color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Invocations</Typography>
                </Box>
                <Typography variant="h4">{stats.totalInvocations}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TrendingUp color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Token balance</Typography>
                </Box>
                <Typography variant="h4">{stats.tokenBalance}</Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Agent Performance List */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Agent Performance
              </Typography>
              <List>
                {agents.map((agent) => (
                  <React.Fragment key={agent.id}>
                    <ListItem
                      sx={{ py: 2 }}
                      secondaryAction={
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() =>
                            navigate(`/developer/agents/${agent.id}`)
                          }
                        >
                          View Details
                        </Button>
                      }
                    >
                      <ListItemText
                        primary={agent.name}
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Grid container spacing={2}>
                              <Grid item xs={12} sm={4}>
                                <Typography variant="body2" color="text.secondary">
                                  Successful runs: {agentStats.find(stat => stat.id === agent.id)?.invocations || 0}
                                </Typography>
                              </Grid>
                              <Grid item xs={12} sm={4}>
                                <Typography variant="body2" color="text.secondary">
                                  Verified reviews: {agentStats.find(stat => stat.id === agent.id)?.reviewCount || 0}
                                </Typography>
                              </Grid>
                              <Grid item xs={12} sm={4}>
                                <Typography variant="body2" color="text.secondary">
                                  Success rate: {agentStats.find(stat => stat.id === agent.id)?.successRate != null ? `${agentStats.find(stat => stat.id === agent.id)?.successRate}%` : 'No live runs'}
                                </Typography>
                              </Grid>
                            </Grid>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
};
