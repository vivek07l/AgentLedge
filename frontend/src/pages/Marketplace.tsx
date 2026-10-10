import React, { useEffect, useState } from 'react';
import { Container, Grid, Typography, Alert, TextField, MenuItem, Button, Stack, Card, CardContent, Box, InputAdornment, Chip } from '@mui/material';
import { SearchRounded, AutoAwesomeRounded, ArrowForwardRounded, PlayCircleOutlineRounded, StarRounded } from '@mui/icons-material';
import { AgentCard } from '../components/agents/AgentCard';
import { agentService } from '../services/agent';
import { useAuth } from '../store/AuthContext';
import { useNavigate } from 'react-router-dom';
import type { Agent } from '../types/agent';
import axios from 'axios';

const simulationProviders = [
  { name: 'ResumePilot', company: 'Northstar Agents', price: 8, rating: '4.9', success: '98%', tagline: 'ATS fit, impact bullets, and an edit plan.' },
  { name: 'CV Compass', company: 'Paperplane AI', price: 7, rating: '4.7', success: '96%', tagline: 'Recruiter-style feedback tailored to a role.' },
  { name: 'CareerLens', company: 'BrightPath Labs', price: 5, rating: '4.4', success: '93%', tagline: 'Clear, concise edits for early-career resumes.' },
];

export const Marketplace: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [sort, setSort] = useState('relevance');
  const [aiMode, setAiMode] = useState<'demo' | 'live' | null>(null);

  useEffect(() => {
    axios.get(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/system/status`)
      .then((response) => setAiMode(response.data.ai_mode))
      .catch(() => setAiMode(null));
  }, []);

  useEffect(() => {
    const fetchAgents = async () => {
      setError(null);
      try {
        const response = await agentService.listAgents(token, { query, category, sort });
        if (response.status === 'success' && response.data) {
          setAgents(response.data);
        } else {
          setError(response.error || 'Failed to fetch agents');
        }
      } catch (err) {
        setError('Failed to load agents');
      }
    };

    fetchAgents();
  }, [token, query, category, sort]);

  const handleSelectAgent = (agent: Agent) => {
    navigate(`/agents/${agent.id}`);
  };

  if (error) {
    return (
      <Container>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: { xs: 2, md: 4 }, mb: 6 }}>
      <Box sx={{ position: 'relative', overflow: 'hidden', mb: 3, p: { xs: 3, md: 5 }, borderRadius: 5, color: '#fff', background: 'radial-gradient(circle at 82% 10%, rgba(119,119,237,.54), transparent 28%), linear-gradient(120deg,#171a35 0%,#27294e 58%,#34356b 100%)' }}>
        <Box sx={{ position: 'absolute', right: { xs: -45, md: 70 }, top: -88, width: 300, height: 300, border: '1px solid rgba(255,255,255,.1)', borderRadius: '50%', '&:after': { content: '""', position: 'absolute', inset: 30, border: '1px solid rgba(255,255,255,.08)', borderRadius: '50%' } }} />
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, color: '#aeb2ff' }}><AutoAwesomeRounded fontSize="small" /><Typography variant="overline" sx={{ letterSpacing: '.15em', fontWeight: 700 }}>AGENT SERVICE NETWORK</Typography></Stack>
        <Typography variant="h1" sx={{ maxWidth: 710, fontSize: { xs: '2.5rem', md: '3.45rem' } }}>Find the right agent for the work.</Typography>
        <Typography sx={{ color: 'rgba(255,255,255,.7)', maxWidth: 620, mt: 2, mb: 3, fontSize: { xs: 15, md: 17 }, lineHeight: 1.7 }}>
          Explore specialist services, compare verified reputation, and choose with confidence.
        </Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
          <Button variant="contained" color="secondary" endIcon={<ArrowForwardRounded />} onClick={() => document.getElementById('agent-search')?.focus()}>Explore marketplace</Button>
          <Button variant="outlined" startIcon={<PlayCircleOutlineRounded />} onClick={() => navigate('/simulation')} sx={{ color: 'white', borderColor: 'rgba(255,255,255,.35)', '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,.08)' } }}>Watch agent-to-agent simulation</Button>
        </Stack>
      </Box>
      {aiMode === 'demo' && <Alert severity="info" sx={{ mb: 3 }}>Local demo mode is active. You can register, browse, and try sample agent workflows without an API key; responses are clearly marked and do not affect reputation.</Alert>}
      {aiMode === 'live' && <Alert severity="success" sx={{ mb: 3 }}>An AI API key is configured. If the live provider is unavailable, the app falls back to labeled demo responses.</Alert>}

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}><Card sx={{ height: '100%' }}><CardContent sx={{ p: 3 }}>
          <Typography variant="overline" color="primary.main" sx={{ letterSpacing: '.13em', fontWeight: 750 }}>DISCOVER</Typography>
          <Typography variant="h5" sx={{ mt: .5 }}>I need a service</Typography>
          <Typography color="text.secondary" sx={{ my: 1.5 }}>Browse listings, compare ratings and completed-run evidence, then try a service.</Typography>
          <Button variant="contained" onClick={() => document.getElementById('agent-search')?.focus()}>Find an agent</Button>
        </CardContent></Card></Grid>
        <Grid item xs={12} md={6}><Card sx={{ height: '100%', background: 'linear-gradient(135deg,#f1f1ff,#fff 80%)' }}><CardContent sx={{ p: 3 }}>
          <Typography variant="overline" color="secondary.dark" sx={{ letterSpacing: '.13em', fontWeight: 750 }}>PUBLISH</Typography>
          <Typography variant="h5" sx={{ mt: .5 }}>I provide an agent service</Typography>
          <Typography color="text.secondary" sx={{ my: 1.5 }}>Create a provider account to publish and manage listings beside other specialists.</Typography>
          <Button variant="outlined" onClick={() => navigate('/auth/register', { state: { accountType: 'provider' } })}>Become a provider</Button>
        </CardContent></Card></Grid>
      </Grid>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2, p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper' }}>
        <TextField id="agent-search" label="Search services or capabilities" value={query} onChange={(event) => setQuery(event.target.value)} fullWidth InputProps={{ startAdornment: <InputAdornment position="start"><SearchRounded color="action" /></InputAdornment> }} />
        <TextField select label="Category" value={category} onChange={(event) => setCategory(event.target.value)} sx={{ minWidth: 180 }}>
          <MenuItem value="">All categories</MenuItem>
          {Array.from(new Set(agents.map((agent) => agent.category).filter(Boolean))).sort().map((value) => (
            <MenuItem key={value} value={value}>{value}</MenuItem>
          ))}
        </TextField>
        <TextField select label="Sort by" value={sort} onChange={(event) => setSort(event.target.value)} sx={{ minWidth: 180 }}>
          <MenuItem value="relevance">Relevance</MenuItem>
          <MenuItem value="rating">Rating and evidence</MenuItem>
          <MenuItem value="success_rate">Success rate</MenuItem>
          <MenuItem value="price">Lowest price</MenuItem>
        </TextField>
        <Button variant="outlined" onClick={() => { setQuery(''); setCategory(''); setSort('relevance'); }}>Reset</Button>
      </Stack>

      <Stack direction="row" alignItems="baseline" justifyContent="space-between" sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h5">Explore services</Typography>
        <Typography variant="body2" color="text.secondary">{agents.length} {agents.length === 1 ? 'service' : 'services'}</Typography>
      </Stack>
      <Grid container spacing={2.5}>
        {agents.map((agent) => (
          <Grid item xs={12} sm={6} md={4} key={agent.id}>
            <AgentCard
              agent={agent}
              onSelect={handleSelectAgent}
            />
          </Grid>
        ))}
      </Grid>
      {agents.length === 0 && <Typography color="text.secondary" sx={{ mt: 3 }}>No matching agents found.</Typography>}

      <Box sx={{ mt: 6 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'end' }} justifyContent="space-between" spacing={1} sx={{ mb: 2 }}>
          <Box><Typography variant="overline" color="secondary.dark" sx={{ letterSpacing: '.13em', fontWeight: 750 }}>SANDBOX EXAMPLES</Typography><Typography variant="h5">Three providers. One service.</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>Compare example resume reviewers, then watch a buyer agent negotiate.</Typography></Box>
          <Chip size="small" label="Fictional sample metrics" variant="outlined" />
        </Stack>
        <Grid container spacing={2}>
          {simulationProviders.map((provider) => <Grid item xs={12} sm={6} md={4} key={provider.name}>
            <Card sx={{ height: '100%' }}><CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center"><Typography variant="h6">{provider.name}</Typography><Chip size="small" icon={<StarRounded />} label={`${provider.rating} sample`} color="primary" variant="outlined" /></Stack>
              <Typography variant="caption" color="text.secondary">{provider.company}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ my: 1.5, minHeight: 40 }}>{provider.tagline}</Typography>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}><Chip size="small" label={`Resume review · ${provider.price} tokens`} /><Typography variant="caption" color="text.secondary">{provider.success} sample success</Typography></Stack>
              <Button fullWidth variant="outlined" onClick={() => navigate('/simulation')}>Compare in simulation</Button>
            </CardContent></Card>
          </Grid>)}
        </Grid>
      </Box>
    </Container>
  );
};
