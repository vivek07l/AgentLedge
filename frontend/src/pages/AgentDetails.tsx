import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, Link as RouterLink } from 'react-router-dom';
import { Container, Typography, Box, Button, TextField, Paper, Alert, CircularProgress, Rating, Stack } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
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
  const [previousContext, setPreviousContext] = useState<{query: string; response: string} | null>(null);
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
      if (!params.id) { setLoading(false); return; }

      try {
        const response = await agentService.getAgent(token, parseInt(params.id, 10));
        if (response.status === 'success' && response.data) {
          setAgent(response.data);
          setBudget(String(Math.max(response.data.price, user?.token_balance || response.data.price)));
          setOffer(String(response.data.price));
          // If we have previous chat history, set it as context
          if (previousChat) {
            if (previousChat.showAsPreviousContext) {
              setPreviousContext({
                query: previousChat.query,
                response: previousChat.response
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
      invocationKey.current = typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID() : `invoke-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    try {
      const request = {
        agent_type: agent.name.toLowerCase().replace(/ /g, '_'),
        input_text: input
      };
      
      const response = await agentService.invokeAgent(token, agent.id, request, negotiation?.id, invocationKey.current);

      if (response.status === 'success' && response.data) {
        invocationKey.current = null;
        setOutput(parseContent(response.data.output_text || response.data.output_data || ''));
        setDemoMode(Boolean(response.data.demo_mode));
        setInvocationId(response.data.invocation_id ?? response.data.id ?? null);
        setPurchaseMessage(response.data.demo_mode
          ? 'Demo only: this run did not use a model and no tokens were charged.'
          : `Execution completed. ${response.data.charged_tokens || 0} tokens settled; balance ${response.data.remaining_balance}.`);
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
    setNegotiationLoading(true); setError(null);
    const response = await agentService.startNegotiation(token, agent.id, Number(budget), Number(offer));
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not start negotiation');
    setNegotiationLoading(false);
  };

  const handleBuyerOffer = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true); setError(null);
    const response = await agentService.submitOffer(token, negotiation.id, Number(offer));
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not submit offer');
    setNegotiationLoading(false);
  };

  const handleAcceptCounter = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true); setError(null);
    const response = await agentService.acceptCounter(token, negotiation.id);
    if (response.data) setNegotiation(response.data);
    else setError(response.error || 'Could not accept offer');
    setNegotiationLoading(false);
  };

  const handleRejectNegotiation = async () => {
    if (!negotiation || !token) return;
    setNegotiationLoading(true); setError(null);
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
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (!agent) {
    return (
      <Container>
        <Alert severity="error">Agent not found</Alert>
      </Container>
    );
  }

  const isOwner = user?.id === agent.developer_id;
  const canInvoke = agent.price <= 0 || isOwner || user?.is_admin || negotiation?.status === 'accepted';

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {agent && (
        <>
          <Typography variant="h4" gutterBottom>
            {agent.name}
          </Typography>
          <Typography variant="body1" paragraph>
            {agent.description}
          </Typography>
          <Typography variant="subtitle1" gutterBottom>
            Price: {agent.price} tokens
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            <Typography variant="body2" color="text.secondary">{agent.category || 'General'} · {agent.capabilities || 'Specialized agent'}</Typography>
            <Typography variant="body2" color="text.secondary">
              {agent.average_rating != null ? `${agent.average_rating.toFixed(1)}/5 from ${agent.review_count} reviews` : 'No verified reviews yet'}
              {agent.success_rate != null ? ` · ${agent.success_rate}% success across ${agent.completed_invocations} completed runs` : ''}
            </Typography>
          </Box>
          
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            Try it out
          </Typography>

          {token && agent.price > 0 && !isOwner && !user?.is_admin && <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>Agree on a price</Typography>
            <Typography color="text.secondary" variant="body2" sx={{ mb: 2 }}>
              No credits are deducted for negotiating. The agreed price is charged only after a successful live run. Local demo runs are free.
              {agent.minimum_price != null ? ` Provider minimum: ${agent.minimum_price} tokens.` : ''}
            </Typography>
            {!negotiation && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="flex-start">
              <TextField label="Authorized budget" type="number" size="small" value={budget} onChange={e => setBudget(e.target.value)} inputProps={{ min: 0, step: 0.01 }} />
              <TextField label="Opening offer" type="number" size="small" value={offer} onChange={e => setOffer(e.target.value)} inputProps={{ min: 0, step: 0.01 }} />
              <Button variant="contained" onClick={handleStartNegotiation} disabled={negotiationLoading}>Start negotiation</Button>
            </Stack>}
            {negotiation && <>
              <Stack spacing={0.75} sx={{ my: 1.5 }}>
                {negotiation.offers.map(item => <Typography key={item.id} variant="body2">
                  {item.actor_role === 'system' ? 'System' : item.actor_role === 'buyer' ? 'You' : 'Provider'} · {item.action.replace('_', ' ')}{item.amount != null ? ` · ${item.amount} tokens` : ''}
                </Typography>)}
              </Stack>
              {negotiation.status === 'awaiting_buyer' && <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <Button variant="contained" onClick={handleAcceptCounter} disabled={negotiationLoading}>Accept provider counter</Button>
                <TextField label="Your next offer" type="number" size="small" value={offer} onChange={e => setOffer(e.target.value)} inputProps={{ min: 0, max: negotiation.buyer_budget, step: 0.01 }} />
                <Button variant="outlined" onClick={handleBuyerOffer} disabled={negotiationLoading || negotiation.round_count >= negotiation.max_rounds}>Counter</Button>
                <Button color="inherit" onClick={handleRejectNegotiation} disabled={negotiationLoading}>Reject</Button>
              </Stack>}
              {negotiation.status === 'accepted' && <Alert severity="success" sx={{ mt: 1 }}>Agreed at {negotiation.agreed_price} tokens. This agreed price will be used for execution.</Alert>}
              {(negotiation.status === 'failed' || negotiation.status === 'rejected') && <Alert severity="info" sx={{ mt: 1 }}>Negotiation {negotiation.status}. Start a new negotiation to try again.</Alert>}
              {(negotiation.status === 'failed' || negotiation.status === 'rejected') && <Button sx={{ mt: 1 }} onClick={() => setNegotiation(null)}>Start a new negotiation</Button>}
            </>}
          </Paper>}

          {previousContext && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Previous Context:
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'rgba(0, 0, 0, 0.02)' }}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Query:
                  </Typography>
                  <Typography variant="body1">{previousContext.query}</Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Response:
                  </Typography>
                  <MarkdownOutput content={previousContext.response} />
                </Box>
              </Paper>
            </Box>
          )}

          {!token ? <Alert severity="info" sx={{ mb: 2 }}>Sign in to negotiate and send this service a task.</Alert> : !canInvoke ? <Alert severity="info" sx={{ mb: 2 }}>Complete an agreement above before invoking this paid service.</Alert> : <><TextField
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={input}
            onChange={(e) => { setInput(e.target.value); invocationKey.current = null; }}
            placeholder="Enter your query here..."
            sx={{ mb: 2 }}
          />
          
          <Button
            variant="contained"
            onClick={handleInvoke}
            disabled={!input.trim() || invocationLoading}
            startIcon={invocationLoading ? <CircularProgress size={18} /> : <SendIcon />}
          >
            Invoke Agent
          </Button>
          </>}
          {!token && <Button component={RouterLink} to="/auth/login" variant="contained">Sign in to use this agent</Button>}

          {purchaseMessage && <Alert severity={purchaseMessage.startsWith('Execution completed') ? 'success' : 'info'} sx={{ mt: 2 }}>{purchaseMessage}</Alert>}

          {output && (
            <Box sx={{ mt: 4 }}>
              {demoMode && <Alert severity="info" sx={{ mb: 2 }}>Local demo output: no AI model processed this request. Configure a supported provider in the backend `.env` to enable live responses.</Alert>}
              <Typography variant="h6" gutterBottom>
                Output
              </Typography>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <MarkdownOutput content={output} />
              </Paper>
            </Box>
          )}

          {demoMode && output && <Alert severity="info" sx={{ mt: 2 }}>This sample response is not a verified service run, so it cannot create a live reputation review. Use the separate Agent-to-Agent Simulation to see a clearly labeled demo review.</Alert>}

          {invocationId && output && !demoMode && (
            <Paper variant="outlined" sx={{ mt: 3, p: 2 }}>
              <Typography variant="h6" gutterBottom>Rate this completed run</Typography>
              <Rating value={reviewRating} onChange={(_, value) => setReviewRating(value)} />
              <TextField fullWidth multiline minRows={2} label="Optional feedback" value={reviewText} onChange={(event) => setReviewText(event.target.value)} sx={{ my: 2 }} />
              <Button variant="outlined" onClick={handleReview}>Submit verified review</Button>
            </Paper>
          )}
          {reviewMessage && <Alert severity={reviewMessage.startsWith('Thanks') ? 'success' : 'info'} sx={{ mt: 2 }}>{reviewMessage}</Alert>}

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </>
      )}
    </Container>
  );
};
