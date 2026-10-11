import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, CircularProgress, Container, Stack, Typography } from '@mui/material';
import { actionApprovalService, ActionApproval } from '../services/actionApprovals';
import { useAuth } from '../store/AuthContext';

const labels: Record<string, string> = {
  start_negotiation: 'Create negotiation and submit initial offer',
  submit_offer: 'Submit negotiation offer',
  accept_negotiation: 'Accept provider price',
  reject_negotiation: 'Reject negotiation',
  invoke_service: 'Run service',
  submit_review: 'Submit review',
};

export const ActionApprovals: React.FC = () => {
  const { token } = useAuth();
  const [items, setItems] = useState<ActionApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      setError(null);
      setItems(await actionApprovalService.list(token));
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not load pending approvals. Refresh and try again.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void refresh(); }, [refresh]);

  const decide = async (item: ActionApproval, decision: 'approve' | 'reject') => {
    if (!token || busyId) return;
    setBusyId(item.approval_id);
    setError(null);
    try {
      await actionApprovalService.decide(token, item.approval_id, decision);
      setNotice(decision === 'approve'
        ? 'Approved. The connected agent can now perform this exact action once.'
        : 'Rejected. The connected agent cannot perform this action.');
      await refresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Could not save your decision. Refresh and try again.');
    } finally {
      setBusyId(null);
    }
  };

  return <Container maxWidth="md" sx={{ py: 4 }}>
    <Typography variant="h4" sx={{ mb: 1 }}>AgentMesh action approvals</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>
      Review each exact action before the connected agent can submit an offer, accept a price, spend tokens, or post a review. Approvals expire after ten minutes and can be used once.
    </Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}
    {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
      : items.length === 0 ? <Alert severity="info">There are no pending AgentMesh actions to approve.</Alert>
      : <Stack spacing={2}>{items.map((item) => <Card key={item.approval_id} variant="outlined">
        <CardContent>
          <Typography variant="h6">{labels[item.action] || item.action}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1 }}>
            Expires {new Date(item.expires_at).toLocaleString()}
          </Typography>
          <Box component="pre" sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 1, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 13 }}>
            {JSON.stringify(item.payload, null, 2)}
          </Box>
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button color="inherit" disabled={busyId !== null} onClick={() => void decide(item, 'reject')}>Reject</Button>
            <Button variant="contained" disabled={busyId !== null} onClick={() => void decide(item, 'approve')}>
              {busyId === item.approval_id ? <CircularProgress size={20} color="inherit" /> : 'Approve this action'}
            </Button>
          </Stack>
        </CardContent>
      </Card>)}</Stack>}
  </Container>;
};
