import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Button,
  TextField,
  Paper,
  Alert,
  CircularProgress,
  Rating,
  Stack,
  Chip,
  Grid,
} from '@mui/material';
import {
  SendRounded,
  ArrowBackRounded,
  HandshakeRounded,
  TerminalRounded,
} from '@mui/icons-material';
import { useAuth } from '../store/AuthContext';
import { agentService } from '../services/agent';
import type { Agent, Negotiation } from '../types/agent';
import MarkdownOutput from '../components/MarkdownOutput';
import { parseContent } from '../utils/parseContent';

interface LocationState {
  previousChat?: {
    query: string;
    response: string;
    showAsPreviousContext?: boolean;
  };
}

export const AgentDetails: React.FC = () => {
  const params = useParams<{ id: string }>();
  const location = useLocation();
  const { previousChat } = (location.state as LocationState) || {};
  const { token, user, refreshUser } = useAuth();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [input, setInput] = useState('');
  const [output, setOutput] = useState('');
  const [demoMode, setDemoMode] = useState(false);
  const [invocationId, setInvocationId] = useState<number | null>(null);
  const [reviewRating, setReviewRating] = useState<number | null>(5);
  const [reviewText, setReviewText] = useState('');
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);
  const [previousContext, setPreviousContext] = useState<{ query: string; response: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [budget, setBudget] = useState('');
  const [offer, setOffer] = useState('');
  const [negotiationLoading, setNegotiationLoading] = useState(false);
  const [invocationLoading, setInvocationLoading] = useState(false);
  const invocationKey = useRef<string | null>(null);

  useEffect(() => {
    const fetchAgent = async () => {
      if (!params.id) {
        setLoading(false);
        return;
      }

      try {
        const response = await agentService.getAgent(token, parseInt(params.id, 10));
        if (response.status === 'success' && response.data) {
          setAgent(response.data);
          setBudget(String(Math.max(response.data.price, user?.token_balance || response.data.price)));
          setOffer(String(response.data.price));
          if (previousChat) {
            if (previousChat.showAsPreviousContext) {
              setPreviousContext({
                query: previousChat.query,
                response: previousChat.response,
              });
            } else {
              setInput(previousChat.query);
              setOutput(previousChat.response);
            }
          }
        } else {
          setError(response.error || 'Failed to fetch agent details');
        }
      } catch (err) {
        setError('Failed to fetch agent details');
      } finally {
        setLoading(false);
      }
    };

    fetchAgent();
  }, [token, params.id, previousChat, user?.token_balance]);

  const handleInvoke = async () => {
    if (!agent || !token || !input.trim() || invocationLoading) return;
    setInvocationLoading(true);
    if (!invocationKey.current) {
      invocationKey.current =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `invoke-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    try {
      const request = {
        agent_type: agent.name.toLowerCase().replace(/ /g, '_'),
        input_text: input,
      };

      const response = await agentService.invokeAgent(
        token,
        agent.id,
        request,
        negotiation?.id,
        invocationKey.current
      );

      if (response.status === 'success' && response.data) {
        invocationKey.current = null;
        setOutput(parseContent(response.data.output_text || response.data.output_data || ''));
        setDemoMode(Boolean(response.data.demo_mode));
        setInvocationId(response.data.invocation_id ?? response.data.id ?? null);
        setPurchaseMessage(
          response.data.demo_mode
            ? 'Demo only: this run did not use a live model and no tokens were charged.'
            : `Execution completed. ${response.data.charged_tokens || 0} tokens settled; balance ${response.data.remaining_balance}.`
        );
        if (response.data.remaining_balance != null) await refreshUser();
      } else {
        const errorMessage = response.error;
        if (response.httpStatus != null) invocationKey.current = null;
        setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to invoke agent');
      }
    } catch (err) {
      setError('Failed to invoke agent');
    } finally {
      setInvocationLoading(false);
    }
  };

  const handleStartNegotiation = async () => {
    if (!agent || !token) return;
    setNegotiationLoading(true);
    setError(null);
    const response = await agentService.startNegotiation(token, agent.id, Number(budget), Number(offer));
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not start negotiation');
    setNegotiationLoading(false);
  };

  const handleBuyerOffer = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true);
    setError(null);
    const response = await agentService.submitOffer(token, negotiation.id, Number(offer));
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not submit offer');
    setNegotiationLoading(false);
  };

  const handleAcceptCounter = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true);
    setError(null);
    const response = await agentService.acceptCounter(token, negotiation.id);
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not accept offer');
    setNegotiationLoading(false);
  };

  const handleRejectNegotiation = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true);
    setError(null);
    const response = await agentService.rejectNegotiation(token, negotiation.id);
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not reject negotiation');
    setNegotiationLoading(false);
  };

  const handleReview = async () => {
    if (!agent || !token || !invocationId || !reviewRating) return;
    const response = await agentService.createReview(token, agent.id, invocationId, reviewRating, reviewText);
    if (response.status === 'success') {
      setReviewMessage('Thanks. Your verified review has been recorded.');
      setInvocationId(null);
    } else {
      setReviewMessage(response.error || 'Could not submit your review.');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress sx={{ color: '#F6C900' }} />
      </Box>
    );
  }

  if (!agent) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">Agent not found</Alert>
      </Container>
    );
  }

  const isOwner = user?.id === agent.developer_id;
  const canInvoke = agent.execution_available !== false
    && (agent.price <= 0 || isOwner || user?.is_admin || negotiation?.status === 'accepted');

  return (
    <Container maxWidth="lg" sx={{ mt: 3, mb: 6 }}>
      {/* Return to Marketplace link */}
      <Box sx={{ mb: 2 }}>
        <Button
          component={RouterLink}
          to="/marketplace"
          startIcon={<ArrowBackRounded />}
          variant="outlined"
          size="small"
        >
          Back to marketplace
        </Button>
      </Box>

      {/* Service Header Card */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 4 },
          mb: 3,
          bgcolor: '#171717',
          color: '#FFFFFF',
          border: '2px solid #292929',
          boxShadow: '6px 6px 0 #171717',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Chip
            size="small"
            label={agent.category || 'General'}
            sx={{ bgcolor: '#F6C900', color: '#171717', fontWeight: 800 }}
          />
          <Typography variant="overline" sx={{ color: '#A09E96', letterSpacing: '0.12em', fontWeight: 800 }}>
            AGENT ID // #{agent.id}
          </Typography>
        </Stack>

        <Typography variant="h2" sx={{ fontWeight: 900, mb: 1.5, color: '#FFFFFF' }}>
          {agent.name}
        </Typography>

        <Typography variant="body1" sx={{ color: '#D4CFC4', maxWidth: 840, lineHeight: 1.65, mb: 3 }}>
          {agent.description}
        </Typography>

        {/* Telemetry Metrics Bar */}
        <Grid container spacing={2} sx={{ pt: 2, borderTop: '1px solid #333333' }}>
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" sx={{ color: '#A09E96', fontWeight: 800 }}>
              LISTED PRICE
            </Typography>
            <Typography variant="h5" sx={{ color: '#FFFFFF', fontWeight: 850, fontFamily: 'monospace' }}>
              {agent.price} tokens
            </Typography>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Typography variant="caption" sx={{ color: '#A09E96', fontWeight: 800 }}>
              VERIFIED RATING
            </Typography>
            <Typography variant="h5" sx={{ color: '#F6C900', fontWeight: 850 }}>
              {agent.average_rating != null ? `${agent.average_rating.toFixed(1)} / 5.0` : 'Unrated'}
            </Typography>
            <Typography variant="caption" sx={{ color: '#706E66' }}>
              {agent.review_count} verified reviews
            </Typography>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Typography variant="caption" sx={{ color: '#A09E96', fontWeight: 800 }}>
              COMPLETED SUCCESS
            </Typography>
            <Typography variant="h5" sx={{ color: '#B7F000', fontWeight: 850 }}>
              {agent.success_rate != null ? `${agent.success_rate}%` : 'Unreported'}
            </Typography>
            <Typography variant="caption" sx={{ color: '#706E66' }}>
              {agent.completed_invocations} verified runs
            </Typography>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Typography variant="caption" sx={{ color: '#A09E96', fontWeight: 800 }}>
              CAPABILITIES
            </Typography>
            <Typography variant="body2" sx={{ color: '#FFFFFF', fontWeight: 600 }}>
              {agent.capabilities || 'Autonomous task handling'}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Autonomous Negotiation Panel */}
      {token && agent.price > 0 && !isOwner && !user?.is_admin && (
        <Paper
          elevation={0}
          sx={{
            p: 3,
            mb: 3,
            bgcolor: '#FFFFFF',
            border: '2px solid #292929',
            boxShadow: '4px 4px 0 #171717',
          }}
        >
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
            <HandshakeRounded sx={{ color: '#171717' }} />
            <Typography variant="h5" sx={{ fontWeight: 850 }}>
              Autonomous Price Negotiation
            </Typography>
          </Stack>
          <Typography color="text.secondary" variant="body2" sx={{ mb: 2 }}>
            No tokens are deducted for negotiating. The agreed price is charged only upon successful live
            execution.
            {agent.minimum_price != null ? ` Provider floor budget: ${agent.minimum_price} tokens.` : ''}
          </Typography>

          {!negotiation && (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="flex-start">
              <TextField
                label="Authorized spend budget"
                type="number"
                size="small"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                inputProps={{ min: 0, step: 0.01 }}
                sx={{ minWidth: 200 }}
              />
              <TextField
                label="Opening token offer"
                type="number"
                size="small"
                value={offer}
                onChange={(e) => setOffer(e.target.value)}
                inputProps={{ min: 0, step: 0.01 }}
                sx={{ minWidth: 180 }}
              />
              <Button
                variant="contained"
                color="secondary"
                onClick={handleStartNegotiation}
                disabled={negotiationLoading}
                sx={{ minHeight: 40 }}
              >
                {negotiationLoading ? 'Initiating…' : 'Start negotiation'}
              </Button>
            </Stack>
          )}

          {negotiation && (
            <>
              <Stack spacing={0.75} sx={{ my: 2 }}>
                {negotiation.offers.map((item) => (
                  <Paper
                    key={item.id}
                    variant="outlined"
                    sx={{ p: 1.5, border: '1px solid #292929', bgcolor: item.actor_role === 'buyer' ? '#FAF8F0' : '#FFFFFF' }}
                  >
                    <Typography variant="body2" fontWeight={700}>
                      {item.actor_role === 'system' ? 'System daemon' : item.actor_role === 'buyer' ? 'You (Buyer)' : 'Provider daemon'} ·{' '}
                      {item.action.replace('_', ' ')}
                      {item.amount != null ? ` · ${item.amount} tokens` : ''}
                    </Typography>
                  </Paper>
                ))}
              </Stack>

              {negotiation.status === 'awaiting_buyer' && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="center">
                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={handleAcceptCounter}
                    disabled={negotiationLoading}
                  >
                    Accept provider counter
                  </Button>
                  <TextField
                    label="Your next counter offer"
                    type="number"
                    size="small"
                    value={offer}
                    onChange={(e) => setOffer(e.target.value)}
                    inputProps={{ min: 0, max: negotiation.buyer_budget, step: 0.01 }}
                    sx={{ minWidth: 180 }}
                  />
                  <Button
                    variant="outlined"
                    onClick={handleBuyerOffer}
                    disabled={negotiationLoading || negotiation.round_count >= negotiation.max_rounds}
                  >
                    Send counter
                  </Button>
                  <Button
                    color="inherit"
                    onClick={handleRejectNegotiation}
                    disabled={negotiationLoading}
                  >
                    Reject
                  </Button>
                </Stack>
              )}

              {negotiation.status === 'accepted' && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <strong>Agreement settled at {negotiation.agreed_price} tokens.</strong> You may now invoke this
                  agent at the agreed rate.
                </Alert>
              )}

              {(negotiation.status === 'failed' || negotiation.status === 'rejected') && (
                <Box sx={{ mt: 2 }}>
                  <Alert severity="info" sx={{ mb: 1.5 }}>
                    Negotiation {negotiation.status}. You may begin a fresh round with adjusted parameters.
                  </Alert>
                  <Button variant="outlined" onClick={() => setNegotiation(null)}>
                    Start fresh negotiation
                  </Button>
                </Box>
              )}
            </>
          )}
        </Paper>
      )}

      {/* Execution Workspace Card */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2.5, md: 3.5 },
          mb: 3,
          bgcolor: '#FFFFFF',
          border: '2px solid #292929',
          boxShadow: '4px 4px 0 #171717',
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
          <TerminalRounded sx={{ color: '#171717' }} />
          <Typography variant="h5" sx={{ fontWeight: 850 }}>
            Execution Sandbox
          </Typography>
        </Stack>

        {agent.execution_available === false ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            This listing is available for discovery, but it does not have a connected executable implementation yet. Running it is disabled and no tokens will be charged.
          </Alert>
        ) : !token ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Sign in to negotiate token rates and send task queries to this agent.
          </Alert>
        ) : !canInvoke ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Complete an agreed price above before running this paid autonomous service.
          </Alert>
        ) : (
          <>
            {previousContext && (
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  mb: 2,
                  bgcolor: '#FAF8F0',
                  border: '1px solid #292929',
                  boxShadow: '2px 2px 0 #171717',
                }}
              >
                <Typography variant="caption" sx={{ color: '#A09E96', fontWeight: 800, display: 'block', mb: 0.5 }}>
                  PRIOR CONTEXT (read-only)
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  Q: {previousContext.query}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  A: {previousContext.response}
                </Typography>
              </Paper>
            )}
            <TextField
              fullWidth
              multiline
              rows={4}
              variant="outlined"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                invocationKey.current = null;
              }}
              placeholder={`Provide instructions or payload for ${agent.name}...`}
              sx={{ mb: 2 }}
            />

            <Button
              variant="contained"
              color="primary"
              onClick={handleInvoke}
              disabled={!input.trim() || invocationLoading}
              startIcon={invocationLoading ? <CircularProgress size={18} color="inherit" /> : <SendRounded sx={{ color: '#F6C900' }} />}
              sx={{ minWidth: 150 }}
            >
              {invocationLoading ? 'Executing…' : 'Invoke agent'}
            </Button>
          </>
        )}

        {!token && (
          <Button component={RouterLink} to="/auth/login" variant="contained" color="secondary" sx={{ mt: 1 }}>
            Sign in to use this agent
          </Button>
        )}

        {purchaseMessage && (
          <Alert
            severity={purchaseMessage.startsWith('Execution completed') ? 'success' : 'info'}
            sx={{ mt: 2 }}
          >
            {purchaseMessage}
          </Alert>
        )}

        {output && (
          <Box sx={{ mt: 3 }}>
            {demoMode && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Local demo output: This response was generated from local templates without consuming live LLM
                tokens.
              </Alert>
            )}
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Output Result
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2.5,
                bgcolor: '#FAF8F0',
                border: '1px solid #292929',
                boxShadow: '2px 2px 0 #171717',
              }}
            >
              <MarkdownOutput content={output} />
            </Paper>
          </Box>
        )}

        {/* Verified Review Submission on Completed Run */}
        {invocationId && output && !demoMode && (
          <Paper
            variant="outlined"
            sx={{
              mt: 3,
              p: 2.5,
              border: '2px solid #292929',
              boxShadow: '3px 3px 0 #171717',
              bgcolor: '#FFFFFF',
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 850, mb: 1 }}>
              Rate this completed run
            </Typography>
            <Rating
              value={reviewRating}
              onChange={(_, value) => setReviewRating(value)}
              sx={{ color: '#F6C900' }}
            />
            <TextField
              fullWidth
              multiline
              minRows={2}
              label="Share verified feedback about the result quality"
              value={reviewText}
              onChange={(event) => setReviewText(event.target.value)}
              sx={{ my: 2 }}
            />
            <Button variant="contained" color="secondary" onClick={handleReview}>
              Submit verified review
            </Button>
          </Paper>
        )}

        {reviewMessage && (
          <Alert
            severity={reviewMessage.startsWith('Thanks') ? 'success' : 'info'}
            sx={{ mt: 2 }}
          >
            {reviewMessage}
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
    </Container>
  );
};
