import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Fade,
  Grid,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
} from '@mui/material';
import {
  AutoAwesomeRounded,
  CheckCircleRounded,
  ChevronLeftRounded,
  ChevronRightRounded,
  Groups2Rounded,
  PauseRounded,
  PaidRounded,
  PlayArrowRounded,
  PsychologyRounded,
  ReplayRounded,
  StarRounded,
  SpeedRounded,
} from '@mui/icons-material';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const PLAYBACK_MS = 1900;
const stages = [
  'Compare providers',
  'Buyer offer',
  'Provider counter',
  'Agreement',
  'Token exchange',
  'Service delivery',
  'Review',
  'Summary',
];

type Provider = {
  agent_id: string;
  name: string;
  provider: string;
  service: string;
  description: string;
  price: number;
  rating: number;
  completed_runs: number;
  success_rate: number;
  response_time: string;
  score: number;
  eligible: boolean;
};

type SimulationResult = {
  mode: 'simulation';
  notice: string;
  error?: string;
  minimum_budget?: number;
  policy?: { maximum_tokens: number; automatic_acceptance: string };
  buyer_agent?: {
    id: string;
    name: string;
    role: string;
    registered_automatically: boolean;
    starting_demo_balance: number;
    remaining_demo_balance: number;
  };
  task?: string;
  providers?: Provider[];
  selection?: { agent_id: string; name: string; provider: string; score: number; reason: string };
  negotiation?: {
    buyer_offer: number;
    provider_counter: number;
    agreed_price: number;
    currency: string;
    policy_accepted: boolean;
  };
  delivery?: { title: string; summary: string };
  review?: { rating: number; text: string; is_simulated: boolean };
  timeline?: Array<{ step: number; key: string; title: string; status: string; detail: string }>;
};

const StageFrame: React.FC<{ index: number; children: React.ReactNode }> = ({ index, children }) => (
  <Fade key={index} in timeout={320}>
    <Box>{children}</Box>
  </Fade>
);

export const Simulation: React.FC = () => {
  const [task, setTask] = useState('Review a product manager resume for a climate technology role');
  const [budget, setBudget] = useState(12);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeStage, setActiveStage] = useState(0);
  const [playing, setPlaying] = useState(false);
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)');

  useEffect(() => {
    if (!playing || !result) return undefined;
    const timer = window.setTimeout(
      () => {
        if (activeStage >= stages.length - 1) {
          setPlaying(false);
          return;
        }
        setActiveStage((current) => current + 1);
      },
      reduceMotion ? 350 : PLAYBACK_MS
    );
    return () => window.clearTimeout(timer);
  }, [playing, activeStage, result, reduceMotion]);

  const runSimulation = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    setPlaying(false);
    setActiveStage(0);
    try {
      const response = await axios.post<SimulationResult>(`${API}/simulation/run`, {
        task,
        token_budget: budget,
      });
      if (response.data.error) setError(response.data.error);
      else {
        setResult(response.data);
        setPlaying(true);
      }
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail ||
          'Could not reach the local simulation API. Start the backend and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const moveTo = (next: number) => {
    const bounded = Math.max(0, Math.min(stages.length - 1, next));
    setActiveStage(bounded);
    setPlaying(bounded < stages.length - 1);
  };

  const selected = result?.providers?.find(
    (provider) => provider.agent_id === result.selection?.agent_id
  );
  const negotiation = result?.negotiation;
  const buyer = result?.buyer_agent;
  const timeline = result?.timeline;
  const currentTimelineEvent =
    activeStage === 0
      ? timeline?.find((item) => item.key === 'compare')
      : activeStage >= 1 && activeStage <= 3
      ? timeline?.find((item) => item.key === 'negotiate')
      : activeStage === 4
      ? timeline?.find((item) => item.key === 'exchange')
      : activeStage === 5
      ? timeline?.find((item) => item.key === 'deliver')
      : activeStage === 6
      ? timeline?.find((item) => item.key === 'review')
      : undefined;

  return (
    <Box sx={{ maxWidth: 1180, mx: 'auto', pb: 5 }}>
      {/* Lamborghini-inspired Simulation Header */}
      <Box
        sx={{
          position: 'relative',
          overflow: 'hidden',
          mb: 3,
          p: { xs: 3, md: 4.5 },
          border: '2px solid #292929',
          boxShadow: '6px 6px 0 #171717',
          color: '#FFFFFF',
          bgcolor: '#171717',
          backgroundImage:
            'radial-gradient(circle at 90% 12%, rgba(183, 240, 0, 0.15) 0%, transparent 35%), linear-gradient(135deg, #171717 0%, #202020 100%)',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
          <Box
            sx={{
              display: 'inline-block',
              width: 10,
              height: 10,
              bgcolor: '#B7F000',
              boxShadow: '0 0 8px #B7F000',
            }}
          />
          <Typography
            variant="overline"
            sx={{
              letterSpacing: '0.14em',
              fontWeight: 800,
              color: '#F6C900',
              fontSize: '0.75rem',
            }}
          >
            AGENTSLEDGE SANDBOX // MULTI-AGENT PROTOCOL
          </Typography>
        </Stack>
        <Typography
          variant="h2"
          sx={{
            fontSize: { xs: '2rem', md: '2.7rem' },
            fontWeight: 900,
            maxWidth: 820,
            lineHeight: 1.1,
          }}
        >
          Watch agents find, agree, and exchange.
        </Typography>
        <Typography
          sx={{
            mt: 1.5,
            maxWidth: 760,
            color: '#D4CFC4',
            lineHeight: 1.65,
            fontSize: { xs: 15, md: 16 },
          }}
        >
          Follow the buyer agent from multi-provider benchmarking through dynamic price negotiation,
          cryptographic demo-token escrow, simulated service delivery, and verified reputation feedback.
        </Typography>
      </Box>

      <Alert
        severity="info"
        sx={{
          mb: 3,
          bgcolor: '#FFFFFF',
          border: '1px solid #292929',
          boxShadow: '3px 3px 0 #171717',
        }}
      >
        <strong>Presentation Simulation Sandbox:</strong> Agents, provider metrics, token settlements,
        and review scores below are generated from deterministic simulation algorithms. This isolated
        mode does not touch database ledgers, incur live token balances, or contact remote LLM APIs.
      </Alert>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              position: { md: 'sticky' },
              top: 90,
              bgcolor: '#FFFFFF',
              border: '2px solid #292929',
              boxShadow: '4px 4px 0 #171717',
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                <Avatar
                  sx={{
                    bgcolor: '#171717',
                    color: '#F6C900',
                    border: '1px solid #F6C900',
                    borderRadius: 0,
                    width: 38,
                    height: 38,
                  }}
                >
                  <PsychologyRounded />
                </Avatar>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 850, fontSize: '1.1rem' }}>
                    Buyer agent policy
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Configure prompt & spend threshold
                  </Typography>
                </Box>
              </Stack>
              <TextField
                fullWidth
                multiline
                minRows={3}
                maxRows={5}
                label="Task instruction for buyer"
                value={task}
                onChange={(e) => setTask(e.target.value)}
                inputProps={{ maxLength: 280 }}
                sx={{ mb: 2 }}
              />
              <TextField
                select
                fullWidth
                label="Maximum authorized token spend"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
              >
                {[5, 7, 8, 10, 12, 15, 20].map((value) => (
                  <MenuItem key={value} value={value}>
                    {value} tokens cap
                  </MenuItem>
                ))}
              </TextField>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                sx={{ mt: 1.2, mb: 2.5, lineHeight: 1.55 }}
              >
                The buyer agent automatically rejects counter-offers exceeding this ceiling.
                Empirical scoring determines which matching provider is engaged.
              </Typography>
              {error && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}
              <Button
                fullWidth
                variant="contained"
                color="secondary"
                size="large"
                startIcon={
                  loading ? (
                    <CircularProgress size={18} color="inherit" />
                  ) : (
                    <PlayArrowRounded sx={{ color: '#171717' }} />
                  )
                }
                onClick={runSimulation}
                disabled={loading || task.trim().length < 8}
                sx={{
                  py: 1.25,
                  fontWeight: 900,
                  fontSize: '0.88rem',
                }}
              >
                {loading ? 'Running simulation…' : result ? 'Rerun simulation' : 'Start agent simulation'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {!result ? (
            <Paper
              variant="outlined"
              sx={{
                minHeight: 320,
                p: 4,
                display: 'grid',
                placeItems: 'center',
                textAlign: 'center',
                bgcolor: '#FFFFFF',
                border: '2px dashed #292929',
                boxShadow: '4px 4px 0 #171717',
              }}
            >
              <Box>
                <Avatar
                  sx={{
                    mx: 'auto',
                    mb: 2,
                    width: 56,
                    height: 56,
                    bgcolor: '#171717',
                    color: '#F6C900',
                    border: '2px solid #F6C900',
                    borderRadius: 0,
                  }}
                >
                  <Groups2Rounded sx={{ fontSize: 32 }} />
                </Avatar>
                <Typography variant="h5" sx={{ fontWeight: 850, mb: 1 }}>
                  Autonomous Agent Mesh Standing By
                </Typography>
                <Typography color="text.secondary" sx={{ maxWidth: 460, mx: 'auto', lineHeight: 1.6 }}>
                  Launch the scenario on the left to benchmark three autonomous providers, execute
                  multi-round counter negotiations, and observe the completed service handoff.
                </Typography>
              </Box>
            </Paper>
          ) : (
            <Stack spacing={2.5}>
              {/* Simulation Stage Controller */}
              <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                  <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    justifyContent="space-between"
                    spacing={1}
                    alignItems={{ sm: 'center' }}
                  >
                    <Box>
                      <Typography
                        variant="overline"
                        sx={{ color: '#F6C900', bgcolor: '#171717', px: 1, py: 0.2, fontWeight: 900 }}
                      >
                        PROTOCOL STAGE // {activeStage + 1} OF {stages.length}
                      </Typography>
                      <Typography variant="h5" sx={{ fontWeight: 850, mt: 0.5 }}>
                        {stages[activeStage]}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Button
                        size="small"
                        variant="contained"
                        color="primary"
                        startIcon={playing ? <PauseRounded /> : <PlayArrowRounded />}
                        onClick={() =>
                          activeStage === stages.length - 1
                            ? setPlaying(false)
                            : setPlaying((value) => !value)
                        }
                      >
                        {playing ? 'Pause' : activeStage === stages.length - 1 ? 'Complete' : 'Resume'}
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<ReplayRounded />}
                        onClick={() => {
                          setActiveStage(0);
                          setPlaying(true);
                        }}
                      >
                        Replay
                      </Button>
                    </Stack>
                  </Stack>

                  <LinearProgress
                    variant="determinate"
                    value={((activeStage + 1) / stages.length) * 100}
                    sx={{
                      mt: 2.5,
                      height: 8,
                      borderRadius: 0,
                      bgcolor: '#EAE5D9',
                      '& .MuiLinearProgress-bar': { bgcolor: '#F6C900' },
                    }}
                  />

                  <Box sx={{ display: 'flex', gap: 0.7, mt: 1.5, overflowX: 'auto', pb: 0.5 }}>
                    {stages.map((stage, index) => (
                      <Chip
                        key={stage}
                        size="small"
                        label={`${index + 1}. ${stage}`}
                        onClick={() => moveTo(index)}
                        sx={{
                          flexShrink: 0,
                          cursor: 'pointer',
                          borderRadius: 0,
                          fontWeight: 750,
                          bgcolor:
                            index === activeStage
                              ? '#F6C900'
                              : index < activeStage
                              ? '#B7F000'
                              : '#FFFFFF',
                          color: '#171717',
                          border: '1px solid #171717',
                        }}
                      />
                    ))}
                  </Box>
                </CardContent>
              </Card>

              {/* Stage Specific Visualization Frame */}
              <StageFrame index={activeStage}>
                {/* STAGE 0: COMPARE PROVIDERS */}
                {activeStage === 0 && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        justifyContent="space-between"
                        spacing={1}
                        sx={{ mb: 2 }}
                      >
                        <Box>
                          <Typography variant="h5" sx={{ fontWeight: 850 }}>
                            Provider Comparison Matrix
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Buyer spending cap: <strong>{result.policy?.maximum_tokens ?? budget} tokens</strong>. Ranked
                            by multi-variable performance algorithm.
                          </Typography>
                        </Box>
                        <Chip
                          icon={<Groups2Rounded sx={{ color: '#171717 !important' }} />}
                          label={`${result.providers?.length || 0} evaluated`}
                          sx={{ bgcolor: '#F6C900', color: '#171717', fontWeight: 800, border: '1px solid #171717' }}
                        />
                      </Stack>

                      <Stack spacing={1.5}>
                        {result.providers?.map((provider, index) => {
                          const isSelected = provider.agent_id === result.selection?.agent_id;
                          return (
                            <Paper
                              key={provider.agent_id}
                              variant="outlined"
                              sx={{
                                p: 2,
                                borderColor: isSelected ? '#171717' : '#292929',
                                borderWidth: isSelected ? 2 : 1,
                                bgcolor: isSelected ? '#FAF8F0' : '#FFFFFF',
                                boxShadow: isSelected ? '3px 3px 0 #F6C900' : 'none',
                                opacity: provider.eligible ? 1 : 0.6,
                                animation: reduceMotion ? 'none' : `simCardIn .38s ease-out ${index * 100}ms both`,
                                '@keyframes simCardIn': {
                                  from: { opacity: 0, transform: 'translateY(12px)' },
                                  to: { opacity: provider.eligible ? 1 : 0.6, transform: 'translateY(0)' },
                                },
                              }}
                            >
                              <Stack
                                direction={{ xs: 'column', sm: 'row' }}
                                alignItems={{ sm: 'center' }}
                                justifyContent="space-between"
                                spacing={1.5}
                              >
                                <Stack direction="row" spacing={1.5} alignItems="center">
                                  <Avatar
                                    sx={{
                                      width: 40,
                                      height: 40,
                                      bgcolor: isSelected ? '#171717' : '#EAE5D9',
                                      color: isSelected ? '#F6C900' : '#171717',
                                      fontWeight: 800,
                                      borderRadius: 0,
                                      border: '1px solid #171717',
                                    }}
                                  >
                                    {provider.name.slice(0, 1)}
                                  </Avatar>
                                  <Box>
                                    <Stack direction="row" spacing={1} alignItems="center">
                                      <Typography fontWeight={800}>{provider.name}</Typography>
                                      {isSelected && (
                                        <Chip
                                          size="small"
                                          label="Buyer Selection"
                                          sx={{ bgcolor: '#B7F000', color: '#171717', fontWeight: 800, border: '1px solid #171717' }}
                                        />
                                      )}
                                    </Stack>
                                    <Typography variant="caption" color="text.secondary">
                                      {provider.provider} · {provider.response_time} latency
                                    </Typography>
                                  </Box>
                                </Stack>
                                <Stack direction="row" spacing={1} flexWrap="wrap">
                                  <Chip
                                    size="small"
                                    icon={<StarRounded sx={{ color: '#171717 !important' }} />}
                                    label={`${provider.rating.toFixed(1)} sample`}
                                    sx={{ bgcolor: '#FFFFFF', border: '1px solid #292929', fontWeight: 700 }}
                                  />
                                  <Chip
                                    size="small"
                                    icon={<SpeedRounded sx={{ color: '#171717 !important' }} />}
                                    label={`${provider.success_rate}% success`}
                                    sx={{ bgcolor: '#B7F000', color: '#171717', border: '1px solid #171717', fontWeight: 800 }}
                                  />
                                  <Chip
                                    size="small"
                                    icon={<PaidRounded sx={{ color: '#171717 !important' }} />}
                                    label={`${provider.price} tokens`}
                                    sx={{ bgcolor: '#F6C900', color: '#171717', border: '1px solid #171717', fontWeight: 800 }}
                                  />
                                </Stack>
                              </Stack>
                              <Stack
                                direction={{ xs: 'column', sm: 'row' }}
                                justifyContent="space-between"
                                sx={{ mt: 1.5, pl: { sm: 6.5 } }}
                                spacing={0.5}
                              >
                                <Typography variant="body2" color="text.secondary">
                                  {provider.description}
                                </Typography>
                                <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 700, whiteSpace: 'nowrap' }}>
                                  Score: {provider.score}/100 ({provider.completed_runs} runs)
                                </Typography>
                              </Stack>
                            </Paper>
                          );
                        })}
                      </Stack>
                      <Alert severity="success" sx={{ mt: 2.5 }}>
                        <strong>{result.selection?.name} selected by buyer:</strong> {result.selection?.reason}
                      </Alert>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
                        Evaluation weighting: 45% empirical rating + 35% completed success rate + 20% cost efficiency.
                      </Typography>
                    </CardContent>
                  </Card>
                )}

                {/* STAGES 1-3: AGENT NEGOTIATION */}
                {activeStage >= 1 && activeStage <= 3 && negotiation && buyer && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2.5 }}>
                        <Avatar sx={{ bgcolor: '#171717', color: '#F6C900', borderRadius: 0 }}>
                          <PsychologyRounded />
                        </Avatar>
                        <Box>
                          <Typography variant="h5" sx={{ fontWeight: 850 }}>
                            Autonomous Protocol Negotiation
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Live offer and counter exchange between buyer policy and provider daemon.
                          </Typography>
                        </Box>
                      </Stack>

                      <Stack spacing={1.5}>
                        {activeStage >= 1 && (
                          <Stack direction="row" spacing={1.5} alignItems="flex-start">
                            <Avatar sx={{ width: 34, height: 34, bgcolor: '#171717', color: '#FFFFFF', borderRadius: 0, fontWeight: 800 }}>
                              B
                            </Avatar>
                            <Paper variant="outlined" sx={{ p: 2, maxWidth: '88%', bgcolor: '#FAF8F0', border: '1px solid #292929' }}>
                              <Typography variant="caption" sx={{ color: '#F6C900', bgcolor: '#171717', px: 0.8, py: 0.2, fontWeight: 800 }}>
                                BUYER · {buyer.name}
                              </Typography>
                              <Typography fontWeight={750} sx={{ mt: 0.75 }}>
                                Opens offer at {negotiation.buyer_offer} sandbox tokens for "{result.task}".
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Policy spend cap: {result.policy?.maximum_tokens ?? budget} tokens.
                              </Typography>
                            </Paper>
                          </Stack>
                        )}

                        {activeStage >= 2 && (
                          <Stack direction="row" spacing={1.5} alignItems="flex-start">
                            <Avatar sx={{ width: 34, height: 34, bgcolor: '#F6C900', color: '#171717', borderRadius: 0, fontWeight: 800 }}>
                              P
                            </Avatar>
                            <Paper variant="outlined" sx={{ p: 2, maxWidth: '88%', bgcolor: '#FFFFFF', border: '1px solid #292929' }}>
                              <Typography variant="caption" sx={{ color: '#171717', bgcolor: '#B7F000', px: 0.8, py: 0.2, fontWeight: 800 }}>
                                PROVIDER · {selected?.name}
                              </Typography>
                              <Typography fontWeight={750} sx={{ mt: 0.75 }}>
                                Counters at {negotiation.provider_counter} sandbox tokens.
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Based on listed execution complexity from catalog.
                              </Typography>
                            </Paper>
                          </Stack>
                        )}

                        {activeStage >= 3 && (
                          <Alert
                            severity={negotiation.policy_accepted ? 'success' : 'error'}
                            icon={<CheckCircleRounded />}
                            sx={{ mt: 1 }}
                          >
                            <strong>
                              {negotiation.policy_accepted
                                ? `Settlement agreement reached at ${negotiation.agreed_price} tokens.`
                                : 'No agreement reached.'}
                            </strong>{' '}
                            {negotiation.policy_accepted
                              ? `Counter-offer falls safely within buyer's ${result.policy?.maximum_tokens ?? budget}-token authorization limit.`
                              : 'Offer exceeds buyer authorization budget.'}
                          </Alert>
                        )}
                      </Stack>

                      <Divider sx={{ my: 2.5 }} />
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" color="text.secondary">
                          Negotiation state:
                        </Typography>
                        <Chip
                          size="small"
                          sx={{
                            borderRadius: 0,
                            fontWeight: 800,
                            bgcolor:
                              activeStage >= 3
                                ? negotiation.policy_accepted
                                  ? '#B7F000'
                                  : '#FF8888'
                                : '#F6C900',
                            color: '#171717',
                            border: '1px solid #171717',
                          }}
                          label={
                            activeStage >= 3
                              ? negotiation.policy_accepted
                                ? 'Agreed & Finalized'
                                : 'Rejected'
                              : 'In Progress'
                          }
                        />
                      </Stack>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE 4: TOKEN EXCHANGE */}
                {activeStage === 4 && negotiation && buyer && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                        <PaidRounded sx={{ color: '#171717', fontSize: 28 }} />
                        <Typography variant="h5" sx={{ fontWeight: 850 }}>
                          Simulated Wallet Settlement
                        </Typography>
                      </Stack>
                      {negotiation.policy_accepted ? (
                        <>
                          <Alert severity="success" icon={<CheckCircleRounded />} sx={{ mb: 2.5 }}>
                            Demo token transfer confirmed · Receipt ID: SIM-{buyer.id.slice(-6).toUpperCase()}
                          </Alert>
                          <Grid container spacing={2}>
                            <Grid item xs={12} sm={4}>
                              <Paper variant="outlined" sx={{ p: 2, height: '100%', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                                <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
                                  BUYER BALANCE
                                </Typography>
                                <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 800, fontFamily: 'monospace' }}>
                                  {buyer.starting_demo_balance} → {buyer.remaining_demo_balance}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Balance after escrow reservation
                                </Typography>
                              </Paper>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <Paper variant="outlined" sx={{ p: 2, height: '100%', bgcolor: '#FAF8F0', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                                <Typography variant="overline" sx={{ color: '#171717', fontWeight: 800 }}>
                                  ESCROW TRANSFERRED
                                </Typography>
                                <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 850, color: '#171717', fontFamily: 'monospace' }}>
                                  {negotiation.agreed_price} tokens
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Locked pending verification
                                </Typography>
                              </Paper>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <Paper variant="outlined" sx={{ p: 2, height: '100%', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                                <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
                                  PROVIDER BENEFICIARY
                                </Typography>
                                <Typography fontWeight={800} sx={{ mt: 0.5 }}>
                                  {selected?.name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Simulated payout recipient
                                </Typography>
                              </Paper>
                            </Grid>
                          </Grid>
                        </>
                      ) : (
                        <Alert severity="warning">
                          No agreement was reached, so no tokens were transferred.
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* STAGE 5: SERVICE DELIVERY */}
                {activeStage === 5 && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                        <Avatar sx={{ bgcolor: '#B7F000', color: '#171717', borderRadius: 0 }}>
                          <AutoAwesomeRounded />
                        </Avatar>
                        <Box>
                          <Typography variant="h5" sx={{ fontWeight: 850 }}>
                            {selected?.name || 'Provider'} Delivering Result
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Autonomous payload execution completed according to task contract.
                          </Typography>
                        </Box>
                      </Stack>
                      <Paper
                        variant="outlined"
                        sx={{
                          p: 3,
                          border: '2px solid #171717',
                          boxShadow: '3px 3px 0 #F6C900',
                          bgcolor: '#FAF8F0',
                          animation: reduceMotion ? 'none' : 'simOutput .45s ease-out',
                          '@keyframes simOutput': {
                            from: { opacity: 0.2, transform: 'translateY(10px)' },
                            to: { opacity: 1, transform: 'translateY(0)' },
                          },
                        }}
                      >
                        <Chip
                          size="small"
                          label="SIMULATED SERVICE PAYLOAD // NOT LIVE AI"
                          sx={{ mb: 2, bgcolor: '#171717', color: '#F6C900', fontWeight: 800 }}
                        />
                        <Typography variant="h6" sx={{ fontWeight: 850, mb: 1 }}>
                          {result.delivery?.title || 'Sample output'}
                        </Typography>
                        <Typography sx={{ lineHeight: 1.8, color: '#171717' }}>
                          {result.delivery?.summary}
                        </Typography>
                      </Paper>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE 6: DEMO REVIEW */}
                {activeStage === 6 && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                        <StarRounded sx={{ color: '#F6C900', fontSize: 28 }} />
                        <Typography variant="h5" sx={{ fontWeight: 850 }}>
                          Verified Execution Feedback
                        </Typography>
                      </Stack>
                      <Paper variant="outlined" sx={{ p: 3, border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Typography fontWeight={800}>{buyer?.name || 'Buyer agent'}</Typography>
                          <Chip
                            icon={<StarRounded sx={{ color: '#171717 !important' }} />}
                            label={`${result.review?.rating ?? '—'}/5 Stars`}
                            sx={{ bgcolor: '#F6C900', color: '#171717', fontWeight: 800 }}
                          />
                        </Stack>
                        <Typography sx={{ mt: 1.5, color: '#333333', lineHeight: 1.6 }}>
                          "{result.review?.text}"
                        </Typography>
                      </Paper>
                      <Alert severity="info" sx={{ mt: 2.5 }}>
                        Sandbox review only. Verified reviews on live runs require real account invocation.
                      </Alert>
                    </CardContent>
                  </Card>
                )}

                {/* STAGE 7: SIMULATION SUMMARY */}
                {activeStage === 7 && (
                  <Card sx={{ bgcolor: '#FFFFFF', border: '2px solid #292929', boxShadow: '4px 4px 0 #171717' }}>
                    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
                      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
                        <CheckCircleRounded sx={{ color: '#B7F000', fontSize: 28 }} />
                        <Typography variant="h5" sx={{ fontWeight: 850 }}>
                          Protocol Lifecycle Complete
                        </Typography>
                      </Stack>
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <Paper variant="outlined" sx={{ p: 2, height: '100%', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                            <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
                              PROVIDER ENGAGED
                            </Typography>
                            <Typography fontWeight={850} sx={{ mt: 0.5 }}>
                              {result.selection?.name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              {result.selection?.reason}
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Paper variant="outlined" sx={{ p: 2, height: '100%', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                            <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
                              SETTLEMENT PATH
                            </Typography>
                            <Typography fontWeight={850} sx={{ mt: 0.5 }}>
                              {negotiation?.buyer_offer} offer → {negotiation?.provider_counter} counter → {negotiation?.agreed_price} agreed
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              {negotiation?.policy_accepted
                                ? `${negotiation.agreed_price} demo tokens successfully transferred`
                                : 'No tokens transferred'}
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={12}>
                          <Paper variant="outlined" sx={{ p: 2.5, bgcolor: '#FAF8F0', border: '1px solid #292929', boxShadow: '2px 2px 0 #171717' }}>
                            <Typography variant="overline" sx={{ color: '#171717', fontWeight: 800 }}>
                              DELIVERY & RATING SUMMARY
                            </Typography>
                            <Typography fontWeight={850} sx={{ mt: 0.5 }}>
                              {result.delivery?.title} · {result.review?.rating}/5 rating
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 0.75, color: '#333333' }}>
                              {result.delivery?.summary}
                            </Typography>
                          </Paper>
                        </Grid>
                      </Grid>
                      <Alert severity="info" sx={{ mt: 2.5 }}>
                        {result.notice}
                      </Alert>
                    </CardContent>
                  </Card>
                )}
              </StageFrame>

              {/* Event Timeline Log */}
              {currentTimelineEvent && (
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    border: '1px solid #292929',
                    bgcolor: '#FFFFFF',
                    boxShadow: '2px 2px 0 #171717',
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{ color: '#171717', bgcolor: '#F6C900', px: 0.8, py: 0.2, fontWeight: 900 }}
                  >
                    TIMELINE TELEMETRY // {currentTimelineEvent.title.toUpperCase()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                    {currentTimelineEvent.detail}
                  </Typography>
                </Paper>
              )}

              {/* Step Navigation Controls */}
              <Stack direction="row" justifyContent="space-between">
                <Button
                  startIcon={<ChevronLeftRounded />}
                  onClick={() => moveTo(activeStage - 1)}
                  disabled={activeStage === 0}
                  variant="outlined"
                >
                  Previous step
                </Button>
                <Button
                  endIcon={
                    activeStage === stages.length - 1 ? <ReplayRounded /> : <ChevronRightRounded />
                  }
                  variant="contained"
                  color="secondary"
                  onClick={() =>
                    activeStage === stages.length - 1
                      ? (setActiveStage(0), setPlaying(true))
                      : moveTo(activeStage + 1)
                  }
                >
                  {activeStage === stages.length - 1 ? 'Replay simulation' : 'Next step'}
                </Button>
              </Stack>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};
