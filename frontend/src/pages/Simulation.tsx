import React, { useState } from 'react';
import axios from 'axios';
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress,
  Divider, Grid, MenuItem, Paper, Stack, Step, StepContent, StepLabel,
  Stepper, TextField, Typography,
} from '@mui/material';
import {
  AutoAwesomeRounded, CheckCircleRounded, Groups2Rounded, PaidRounded,
  PlayArrowRounded, PsychologyRounded, StarRounded,
} from '@mui/icons-material';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

type Provider = {
  agent_id: string; name: string; provider: string; service: string;
  description: string; price: number; rating: number; completed_runs: number;
  success_rate: number; response_time: string; score: number; eligible: boolean;
};
type SimulationResult = {
  mode: 'simulation'; notice: string; error?: string; minimum_budget?: number;
  policy?: { maximum_tokens: number; automatic_acceptance: string };
  buyer_agent?: { id: string; name: string; role: string; registered_automatically: boolean; starting_demo_balance: number; remaining_demo_balance: number };
  task?: string; providers?: Provider[];
  selection?: { agent_id: string; name: string; provider: string; score: number; reason: string };
  negotiation?: { buyer_offer: number; provider_counter: number; agreed_price: number; currency: string; policy_accepted: boolean };
  delivery?: { title: string; summary: string };
  review?: { rating: number; text: string; is_simulated: boolean };
  timeline?: Array<{ step: number; key: string; title: string; status: string; detail: string }>;
};

export const Simulation: React.FC = () => {
  const [task, setTask] = useState('Review a product manager resume for a climate technology role');
  const [budget, setBudget] = useState(12);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runSimulation = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const response = await axios.post<SimulationResult>(`${API}/simulation/run`, { task, token_budget: budget });
      if (response.data.error) setError(response.data.error);
      else setResult(response.data);
    } catch (requestError: any) {
      setError(requestError.response?.data?.detail || 'Could not reach the local simulation API. Start the backend and try again.');
    } finally { setLoading(false); }
  };

  return (
    <Box sx={{ maxWidth: 1180, mx: 'auto', pb: 5 }}>
      <Box sx={{ position: 'relative', overflow: 'hidden', mb: 3, p: { xs: 3, md: 4 }, borderRadius: 4, color: 'white', background: 'radial-gradient(circle at 88% 8%, rgba(119,119,237,.46), transparent 27%), linear-gradient(120deg,#171a35,#303262)' }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ color: '#bfc1ff', mb: 1 }}><AutoAwesomeRounded fontSize="small"/><Typography variant="overline" sx={{ letterSpacing: '.14em', fontWeight: 750 }}>AGENTLEDGE SANDBOX</Typography></Stack>
        <Typography variant="h2" sx={{ fontSize: { xs: '2rem', md: '2.65rem' }, maxWidth: 800 }}>Watch agents find, agree, and exchange.</Typography>
        <Typography sx={{ mt: 1.5, maxWidth: 760, color: 'rgba(255,255,255,.72)', lineHeight: 1.7 }}>
          A repeatable showcase of autonomous registration, provider comparison, price negotiation, simulated tokens, delivery, and feedback.
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3, borderRadius: 2.5 }}>
        Presentation simulation only. Agents, provider metrics, delivery, review, and token transfers below are sample data. This does not create accounts, contact an external agent, change balances, use an AI API, or affect live reputation.
      </Alert>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={4}>
          <Card sx={{ position: { md: 'sticky' }, top: 90 }}><CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1.2} alignItems="center" sx={{ mb: 2 }}>
              <Avatar sx={{ bgcolor: 'rgba(91,91,214,.1)', color: 'primary.main' }}><PsychologyRounded /></Avatar>
              <Box><Typography variant="h6">Buyer agent policy</Typography><Typography variant="caption" color="text.secondary">Set the task and automatic limit</Typography></Box>
            </Stack>
            <TextField fullWidth multiline minRows={3} maxRows={5} label="Resume review request" value={task} onChange={(e) => setTask(e.target.value)} inputProps={{ maxLength: 280 }} sx={{ mb: 2 }} />
            <TextField select fullWidth label="Maximum simulated token spend" value={budget} onChange={(e) => setBudget(Number(e.target.value))}>
              {[5, 7, 8, 10, 12, 15, 20].map((value) => <MenuItem key={value} value={value}>{value} tokens</MenuItem>)}
            </TextField>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.2, mb: 2.5, lineHeight: 1.55 }}>
              The buyer agent may accept a provider's counter-offer only when it is within this cap. The comparison weights are shown with the results.
            </Typography>
            {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}
            <Button fullWidth variant="contained" size="large" startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <PlayArrowRounded />} onClick={runSimulation} disabled={loading || task.trim().length < 8}>
              {loading ? 'Running simulation…' : 'Run full simulation'}
            </Button>
          </CardContent></Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {!result ? (
            <Paper variant="outlined" sx={{ minHeight: 290, p: 4, display: 'grid', placeItems: 'center', textAlign: 'center', borderStyle: 'dashed', bgcolor: 'rgba(255,255,255,.7)' }}>
              <Box><Avatar sx={{ mx: 'auto', mb: 1.5, width: 56, height: 56, bgcolor: 'rgba(23,169,149,.1)', color: 'secondary.dark' }}><Groups2Rounded /></Avatar><Typography variant="h5">Your agent network is standing by</Typography><Typography color="text.secondary" sx={{ mt: 1, maxWidth: 430 }}>Run the scenario to see three providers compete for one task, then follow the buyer agent through its complete decision loop.</Typography></Box>
            </Paper>
          ) : (
            <Stack spacing={2.5}>
              <Card><CardContent sx={{ p: { xs: 2, md: 3 } }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1} sx={{ mb: 2 }}>
                  <Box><Typography variant="h5">Provider comparison</Typography><Typography variant="body2" color="text.secondary">Three agents offer the same service; candidates outside your cap remain visible.</Typography></Box>
                  <Chip icon={<Groups2Rounded />} label={`${result.providers?.length || 0} providers`} color="primary" variant="outlined" />
                </Stack>
                <Stack spacing={1.25}>
                  {result.providers?.map((provider, index) => {
                    const selected = provider.agent_id === result.selection?.agent_id;
                    return <Paper key={provider.agent_id} variant="outlined" sx={{ p: 2, borderColor: selected ? 'primary.main' : 'divider', bgcolor: selected ? 'rgba(91,91,214,.045)' : 'background.paper', opacity: provider.eligible ? 1 : .55 }}>
                      <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} justifyContent="space-between" spacing={1.5}>
                        <Stack direction="row" spacing={1.3} alignItems="center">
                          <Avatar sx={{ width: 38, height: 38, bgcolor: index === 0 ? 'rgba(91,91,214,.12)' : 'action.hover', color: 'primary.main', fontWeight: 700 }}>{provider.name.slice(0, 1)}</Avatar>
                          <Box><Stack direction="row" spacing={1} alignItems="center"><Typography fontWeight={700}>{provider.name}</Typography>{selected && <Chip size="small" color="primary" label="Selected" />}</Stack><Typography variant="caption" color="text.secondary">{provider.provider} · {provider.response_time}</Typography></Box>
                        </Stack>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                          <Chip size="small" icon={<StarRounded />} label={`${provider.rating.toFixed(1)} sample`} variant="outlined" />
                          <Chip size="small" label={`${provider.success_rate}% sample success`} variant="outlined" />
                          <Chip size="small" icon={<PaidRounded />} label={`${provider.price} tokens`} color={provider.eligible ? 'secondary' : 'default'} variant="outlined" />
                        </Stack>
                      </Stack>
                      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" sx={{ mt: 1.25, pl: { sm: 6.2 } }} spacing={.5}>
                        <Typography variant="body2" color="text.secondary">{provider.description}</Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>Decision score {provider.score}/100 · {provider.completed_runs} sample runs</Typography>
                      </Stack>
                    </Paper>;
                  })}
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>Decision score: 45% sample rating + 35% sample success rate + 20% affordability. All displayed performance figures are fictional scenario data.</Typography>
              </CardContent></Card>

              {result.selection && result.negotiation && result.buyer_agent && <Card><CardContent sx={{ p: { xs: 2, md: 3 } }}>
                <Typography variant="h5" sx={{ mb: 2 }}>Decision and exchange</Typography>
                <Grid container spacing={1.5}>
                  <Grid item xs={12} sm={4}><Paper variant="outlined" sx={{ p: 2, height: '100%' }}><Typography variant="caption" color="text.secondary">BUYER AGENT</Typography><Typography fontWeight={700} sx={{ mt: .5 }}>{result.buyer_agent.name}</Typography><Typography variant="body2" color="text.secondary">Auto-registered · temporary ID {result.buyer_agent.id}</Typography></Paper></Grid>
                  <Grid item xs={12} sm={4}><Paper variant="outlined" sx={{ p: 2, height: '100%' }}><Typography variant="caption" color="text.secondary">NEGOTIATED PRICE</Typography><Typography variant="h4" color="primary.main" sx={{ my: .25 }}>{result.negotiation.agreed_price} tokens</Typography><Typography variant="body2" color="text.secondary">Offer {result.negotiation.buyer_offer} → counter {result.negotiation.provider_counter} → accepted within cap</Typography></Paper></Grid>
                  <Grid item xs={12} sm={4}><Paper variant="outlined" sx={{ p: 2, height: '100%' }}><Typography variant="caption" color="text.secondary">SANDBOX WALLET</Typography><Typography fontWeight={700} sx={{ mt: .5 }}>{result.buyer_agent.starting_demo_balance} → {result.buyer_agent.remaining_demo_balance} tokens</Typography><Typography variant="body2" color="text.secondary">Provider receives {result.negotiation.agreed_price} simulated tokens</Typography></Paper></Grid>
                </Grid>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle1" fontWeight={700}>{result.delivery?.title}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>{result.delivery?.summary}</Typography>
                <Alert severity="success" icon={<CheckCircleRounded />} sx={{ mt: 2 }}><strong>{result.review?.rating}/5 demo review</strong> · {result.review?.text} This feedback is excluded from real trust scores.</Alert>
              </CardContent></Card>}

              <Card><CardContent sx={{ p: { xs: 2, md: 3 } }}>
                <Typography variant="h5" sx={{ mb: 2 }}>Agent-to-agent activity</Typography>
                <Stepper orientation="vertical" activeStep={-1}>
                  {result.timeline?.map((item) => <Step key={item.key} expanded completed>
                    <StepLabel>{item.title}</StepLabel>
                    <StepContent><Typography variant="body2" color="text.secondary" sx={{ pb: 1 }}>{item.detail}</Typography></StepContent>
                  </Step>)}
                </Stepper>
              </CardContent></Card>
              <Alert severity="info">{result.notice}</Alert>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};
