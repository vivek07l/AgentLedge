import React, { useEffect, useState } from 'react';
import {
  Container,
  Grid,
  Typography,
  Alert,
  TextField,
  MenuItem,
  Button,
  Stack,
  Box,
  InputAdornment,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import {
  SearchRounded,
  ArrowForwardRounded,
  PlayCircleOutlineRounded,
  RestartAltRounded,
  VerifiedRounded,
  SpeedRounded,
  GridViewRounded,
  TableRowsRounded,
} from '@mui/icons-material';
import { AgentCard } from '../components/agents/AgentCard';
import { agentService } from '../services/agent';
import { useAuth } from '../store/AuthContext';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Agent } from '../types/agent';
import axios from 'axios';

export const Marketplace: React.FC = () => {
  const { token, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [sort, setSort] = useState('relevance');
  const [categories, setCategories] = useState<string[]>([]);
  const [maxPrice, setMaxPrice] = useState('');
  const [minimumRating, setMinimumRating] = useState('');
  const [minimumSuccess, setMinimumSuccess] = useState('');
  const [offset, setOffset] = useState(0);
  const [aiMode, setAiMode] = useState<'demo' | 'live' | 'error' | null>(null);
  const [aiModeMessage, setAiModeMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'compare'>('grid');
  const publishedNotice = (location.state as { publishedService?: string } | null)?.publishedService;

  useEffect(() => {
    axios
      .get(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/system/status`)
      .then((response) => {
        setAiMode(response.data.ai_mode);
        setAiModeMessage(response.data.message || null);
      })
      .catch(() => setAiMode(null));
  }, []);

  useEffect(() => {
    agentService.listCategories().then((response) => {
      if (response.status === 'success' && response.data) {
        setCategories(response.data);
      }
    });
  }, []);

  useEffect(() => {
    const fetchAgents = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await agentService.listAgents(token, {
          query,
          category,
          sort,
          ...(maxPrice ? { max_price: Number(maxPrice) } : {}),
          ...(minimumRating ? { minimum_rating: Number(minimumRating) } : {}),
          ...(minimumSuccess ? { minimum_success_rate: Number(minimumSuccess) } : {}),
          limit: 50,
          offset,
        });
        if (response.status === 'success' && response.data) {
          setAgents((current) => (offset ? [...current, ...response.data!] : response.data!));
        } else {
          setError(response.error || 'Failed to fetch agents');
        }
      } catch (err) {
        setError('Failed to load agents');
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, [token, query, category, sort, maxPrice, minimumRating, minimumSuccess, offset]);

  const resetFilters = () => {
    setQuery('');
    setCategory('');
    setSort('relevance');
    setMaxPrice('');
    setMinimumRating('');
    setMinimumSuccess('');
    setOffset(0);
  };

  const handleSelectAgent = (agent: Agent) => {
    navigate(`/agents/${agent.id}`);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: { xs: 2, md: 3 }, mb: 6 }}>
      {publishedNotice && <Alert severity="success" sx={{ mb: 2 }}>
        “{publishedNotice}” was published. The marketplace catalog has been refreshed.
      </Alert>}
      {/* Lamborghini-inspired Hero Banner */}
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
            'radial-gradient(circle at 92% 10%, rgba(246, 201, 0, 0.15) 0%, transparent 40%), linear-gradient(135deg, #171717 0%, #1F1F1F 100%)',
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
            AGENTSLEDGE // AUTONOMOUS SERVICE NETWORK
          </Typography>
        </Stack>

        <Typography
          variant="h1"
          sx={{
            maxWidth: 780,
            fontSize: { xs: '2.2rem', md: '3.1rem' },
            fontWeight: 900,
            lineHeight: 1.08,
            color: '#FFFFFF',
          }}
        >
          Discover, compare & deploy autonomous agents.
        </Typography>

        <Typography
          sx={{
            color: '#D4CFC4',
            maxWidth: 680,
            mt: 1.5,
            mb: 3,
            fontSize: { xs: 15, md: 16 },
            lineHeight: 1.6,
          }}
        >
          Explore verified AI providers, compare empirical run success rates, and negotiate
          token settlement with complete cryptographic clarity.
        </Typography>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
          <Button
            variant="contained"
            color="secondary"
            endIcon={<ArrowForwardRounded />}
            onClick={() => document.getElementById('agent-search')?.focus()}
            sx={{ minWidth: 170 }}
          >
            Explore marketplace
          </Button>
          <Button
            variant="outlined"
            startIcon={<PlayCircleOutlineRounded sx={{ color: '#B7F000' }} />}
            onClick={() => navigate('/simulation')}
            sx={{
              color: '#FFFFFF',
              borderColor: '#444444',
              bgcolor: '#222222',
              '&:hover': {
                borderColor: '#F6C900',
                color: '#F6C900',
                bgcolor: '#292929',
              },
            }}
          >
            Watch agent-to-agent simulation
          </Button>
        </Stack>
      </Box>

      {/* System Mode Alerts */}
      {aiMode === 'demo' && (
        <Alert
          severity="info"
          sx={{
            mb: 3,
            bgcolor: '#FFFFFF',
            border: '1px solid #292929',
            boxShadow: '3px 3px 0 #171717',
          }}
        >
          <strong>Local Demo Mode Active:</strong> You can register, explore providers, and run
          labeled sample requests without external API credentials. Demo runs do not alter reputation scores.
        </Alert>
      )}
      {aiMode === 'live' && (
        <Alert
          severity="success"
          sx={{
            mb: 3,
            bgcolor: '#F0FED0',
            border: '1px solid #8EBD00',
            color: '#171717',
            boxShadow: '3px 3px 0 #171717',
          }}
        >
          <strong>Live AI Provider Connected:</strong> Live execution is active. Provider failures are reported as failures; no demo result is substituted.
        </Alert>
      )}
      {aiMode === 'error' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <strong>Live provider configuration error:</strong> {aiModeMessage || 'The configured live provider is missing its API key. No demo response will be substituted.'}
        </Alert>
      )}

      {/* Workflow Navigation & Provider Publishing */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 1.5,
          mb: 2.5,
        }}
      >
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip
            label="01 · DISCOVER"
            sx={{ bgcolor: '#F6C900', color: '#171717', fontWeight: 800, border: '1px solid #171717' }}
          />
          <Chip
            label="02 · BENCHMARK & COMPARE"
            sx={{ bgcolor: '#FFFFFF', color: '#171717', fontWeight: 800, border: '1px solid #292929' }}
          />
          <Chip
            label="03 · NEGOTIATE & RUN"
            sx={{ bgcolor: '#B7F000', color: '#171717', fontWeight: 800, border: '1px solid #171717' }}
          />
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ width: { xs: '100%', sm: 'auto' } }}>
          <Button
            size="small"
            variant={viewMode === 'grid' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('grid')}
            startIcon={<GridViewRounded />}
            sx={{
              width: { xs: 'calc(50% - 4px)', sm: 'auto' },
              minHeight: 34,
              fontSize: '0.75rem',
              bgcolor: viewMode === 'grid' ? '#171717' : '#FFFFFF',
            }}
          >
            Catalog
          </Button>
          <Button
            size="small"
            variant={viewMode === 'compare' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('compare')}
            startIcon={<TableRowsRounded />}
            sx={{
              width: { xs: 'calc(50% - 4px)', sm: 'auto' },
              minHeight: 34,
              fontSize: '0.75rem',
              bgcolor: viewMode === 'compare' ? '#F6C900' : '#FFFFFF',
              color: viewMode === 'compare' ? '#171717' : '#171717',
            }}
          >
            Compare table
          </Button>
          <Button
            size="small"
            variant="outlined"
            disabled={authLoading}
            onClick={() => navigate(token ? '/provider/listings' : '/auth/register',
              token ? undefined : { state: { accountType: 'provider' } })}
            sx={{ minHeight: 34, fontSize: '0.75rem', ml: { sm: 1 }, width: { xs: '100%', sm: 'auto' } }}
          >
            {authLoading ? 'Loading account…' : 'Publish a service →'}
          </Button>
        </Stack>
      </Box>

      {/* Quick Category Bar */}
      <Box
        sx={{
          display: 'flex',
          gap: 1,
          flexWrap: 'wrap',
          mb: 2,
          pb: 0.5,
        }}
      >
        <Chip
          label="All categories"
          clickable
          onClick={() => {
            setOffset(0);
            setCategory('');
          }}
          sx={{
            bgcolor: category === '' ? '#F6C900' : '#FFFFFF',
            color: '#171717',
            fontWeight: 800,
            border: '1px solid #292929',
            boxShadow: category === '' ? '2px 2px 0 #171717' : 'none',
          }}
        />
        {categories.map((cat) => (
          <Chip
            key={cat}
            label={cat}
            clickable
            onClick={() => {
              setOffset(0);
              setCategory(cat);
            }}
            sx={{
              bgcolor: category.toLowerCase() === cat.toLowerCase() ? '#F6C900' : '#FFFFFF',
              color: '#171717',
              fontWeight: 800,
              border: '1px solid #292929',
              boxShadow: category.toLowerCase() === cat.toLowerCase() ? '2px 2px 0 #171717' : 'none',
            }}
          />
        ))}
      </Box>

      {/* Technical Search & Multi-Telemetry Filter Toolbar */}
      <Paper
        elevation={0}
        sx={{
          mb: 3,
          p: 2.5,
          bgcolor: '#FFFFFF',
          border: '2px solid #292929',
          boxShadow: '4px 4px 0 #171717',
        }}
      >
        <Grid container spacing={1.5} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              id="agent-search"
              placeholder="Search services, skills, or tags..."
              value={query}
              onChange={(event) => {
                setOffset(0);
                setQuery(event.target.value);
              }}
              fullWidth
              size="small"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchRounded sx={{ color: '#171717' }} />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              select
              label="Category"
              value={category}
              onChange={(event) => {
                setOffset(0);
                setCategory(event.target.value);
              }}
              fullWidth
              size="small"
            >
              <MenuItem value="">All categories</MenuItem>
              {categories.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={6} sm={4} md={2}>
            <TextField
              select
              label="Sort order"
              value={sort}
              onChange={(event) => {
                setOffset(0);
                setSort(event.target.value);
              }}
              fullWidth
              size="small"
            >
              <MenuItem value="relevance">Relevance</MenuItem>
              <MenuItem value="rating">Rating & reviews</MenuItem>
              <MenuItem value="success_rate">Success rate</MenuItem>
              <MenuItem value="price">Lowest token price</MenuItem>
              <MenuItem value="price_desc">Highest token price</MenuItem>
            </TextField>
          </Grid>

          <Grid item xs={4} sm={2} md={1.25}>
            <TextField
              label="Max price"
              type="number"
              value={maxPrice}
              onChange={(event) => {
                setOffset(0);
                setMaxPrice(event.target.value);
              }}
              inputProps={{ min: 0, step: 1 }}
              fullWidth
              size="small"
            />
          </Grid>

          <Grid item xs={4} sm={2} md={1.25}>
            <TextField
              label="Min rating"
              type="number"
              value={minimumRating}
              onChange={(event) => {
                setOffset(0);
                setMinimumRating(event.target.value);
              }}
              inputProps={{ min: 0, max: 5, step: 0.1 }}
              fullWidth
              size="small"
            />
          </Grid>

          <Grid item xs={4} sm={2} md={1.5}>
            <TextField
              label="Min success %"
              type="number"
              value={minimumSuccess}
              onChange={(event) => {
                setOffset(0);
                setMinimumSuccess(event.target.value);
              }}
              inputProps={{ min: 0, max: 100, step: 1 }}
              fullWidth
              size="small"
            />
          </Grid>

          <Grid item xs={12} sm={12} md="auto">
            <Button
              variant="outlined"
              size="small"
              onClick={resetFilters}
              startIcon={<RestartAltRounded />}
              sx={{ minHeight: 38, width: { xs: '100%', md: 'auto' } }}
            >
              Reset
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Discovery Results Count and Metrics Summary */}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        sx={{ mt: 2, mb: 2 }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h5" sx={{ fontWeight: 850, color: '#171717', fontSize: { xs: '1.15rem', sm: '1.5rem' } }}>
            {viewMode === 'compare' ? 'Provider Comparison Matrix' : 'Active Services Catalog'}
          </Typography>
          <Chip
            size="small"
            label={`${agents.length} ${agents.length === 1 ? 'service' : 'services'}`}
            sx={{ bgcolor: '#171717', color: '#FFFFFF', fontWeight: 800 }}
          />
        </Stack>

        <Typography variant="caption" sx={{ color: '#5A5A52', fontFamily: 'monospace', overflowWrap: 'anywhere' }}>
          RESULTS VERIFIED VIA AGENTSLEDGE API
        </Typography>
      </Stack>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && agents.length === 0 && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: 8,
            bgcolor: '#FFFFFF',
            border: '1px solid #292929',
            boxShadow: '3px 3px 0 #171717',
          }}
        >
          <CircularProgress sx={{ color: '#F6C900', mb: 2 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#171717' }}>
            SCANNING AGENTSLEDGE MARKETPLACE...
          </Typography>
        </Box>
      )}

      {/* View Mode: Comparison Matrix */}
      {viewMode === 'compare' && agents.length > 0 && (
        <TableContainer
          component={Paper}
          sx={{
            border: '2px solid #292929',
            boxShadow: '4px 4px 0 #171717',
            borderRadius: 0,
            mb: 4,
          }}
        >
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: '#171717' }}>
              <TableRow>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>SERVICE</TableCell>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>CATEGORY</TableCell>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>PRICE</TableCell>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>RATING & EVIDENCE</TableCell>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>SUCCESS RATE</TableCell>
                <TableCell sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>CAPABILITIES</TableCell>
                <TableCell align="right" sx={{ color: '#FFFFFF', fontWeight: 800, py: 1.5 }}>ACTION</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {agents.map((agent, index) => (
                <TableRow
                  key={agent.id}
                  sx={{
                    bgcolor: index % 2 === 0 ? '#FFFFFF' : '#FAF8F2',
                    '&:hover': { bgcolor: '#F5F2E9' },
                  }}
                >
                  <TableCell sx={{ fontWeight: 800, color: '#171717' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                      {agent.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#706E66' }}>
                      ID: #{agent.id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={agent.category || 'General'}
                      sx={{ bgcolor: '#171717', color: '#FFFFFF', fontWeight: 700 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography sx={{ fontWeight: 800, fontFamily: 'monospace' }}>
                      {agent.price} tokens
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {agent.average_rating != null ? (
                      <Chip
                        size="small"
                        icon={<VerifiedRounded sx={{ fontSize: '14px !important', color: '#171717 !important' }} />}
                        label={`${agent.average_rating.toFixed(1)}/5 (${agent.review_count})`}
                        sx={{ bgcolor: '#F6C900', color: '#171717', fontWeight: 800 }}
                      />
                    ) : (
                      <Typography variant="caption" sx={{ color: '#706E66' }}>
                        No verified reviews
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {agent.success_rate != null ? (
                      <Chip
                        size="small"
                        icon={<SpeedRounded sx={{ fontSize: '14px !important', color: '#171717 !important' }} />}
                        label={`${agent.success_rate}% (${agent.completed_invocations} runs)`}
                        sx={{ bgcolor: '#B7F000', color: '#171717', fontWeight: 800 }}
                      />
                    ) : (
                      <Typography variant="caption" sx={{ color: '#706E66' }}>
                        Unreported
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ color: '#333333', maxWidth: 220, display: 'block' }}>
                      {agent.capabilities || 'Standard agent service'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="contained"
                      color="primary"
                      onClick={() => handleSelectAgent(agent)}
                      sx={{ fontSize: '0.72rem', py: 0.5 }}
                    >
                      View details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* View Mode: Card Grid */}
      {viewMode === 'grid' && (
        <Grid container spacing={2.5}>
          {agents.map((agent) => (
            <Grid item xs={12} sm={6} md={4} key={agent.id}>
              <AgentCard agent={agent} onSelect={handleSelectAgent} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Empty State */}
      {!loading && agents.length === 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 5,
            textAlign: 'center',
            bgcolor: '#FFFFFF',
            border: '2px solid #292929',
            boxShadow: '4px 4px 0 #171717',
            mt: 2,
          }}
        >
          <Box
            sx={{
              width: 52,
              height: 52,
              bgcolor: '#F6C900',
              border: '2px solid #171717',
              display: 'grid',
              placeItems: 'center',
              mx: 'auto',
              mb: 2,
            }}
          >
            <SearchRounded sx={{ fontSize: 28, color: '#171717' }} />
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 850, mb: 1, color: '#171717' }}>
            No matching agents found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 480, mx: 'auto', mb: 3 }}>
            No active services matched your query and filter thresholds. Try broadening your
            search terms or resetting price and rating criteria.
          </Typography>
          <Button variant="contained" color="secondary" onClick={resetFilters}>
            Reset all filters
          </Button>
        </Paper>
      )}

      {/* Pagination Load More */}
      {agents.length >= 50 && (
        <Box sx={{ textAlign: 'center', mt: 4 }}>
          <Button
            variant="outlined"
            onClick={() => setOffset((current) => current + 50)}
            sx={{ px: 4, py: 1 }}
          >
            Load more real marketplace listings
          </Button>
        </Box>
      )}
    </Container>
  );
};
