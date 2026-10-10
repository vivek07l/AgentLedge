import React from 'react';
import { Box, Button, Container, Paper, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';

type LegalInfoProps = { kind: 'terms' | 'privacy' };

export const LegalInfo: React.FC<LegalInfoProps> = ({ kind }) => {
  const navigate = useNavigate();
  const isTerms = kind === 'terms';

  return (
    <Container maxWidth="md" sx={{ py: 5 }}>
      <Paper variant="outlined" sx={{ p: { xs: 2.5, sm: 4 } }}>
        <Typography variant="overline" color="primary.main">AGENTLEDGE · PROTOTYPE</Typography>
        <Typography variant="h3" sx={{ mt: 1, mb: 2 }}>{isTerms ? 'Terms and Conditions' : 'Privacy Summary'}</Typography>
        <Typography color="text.secondary" paragraph>
          This page describes the current demonstration project. It is a plain-language product summary, not a reviewed legal agreement or privacy notice. Do not use this prototype for sensitive information or production transactions.
        </Typography>
        {isTerms ? <>
          <Typography variant="h6" sx={{ mt: 3 }}>Demo services and credits</Typography>
          <Typography color="text.secondary" paragraph>Token balances and token top-ups in this prototype are simulated credits. No card payment is taken. Local demo agent responses are examples, not model-generated professional advice.</Typography>
          <Typography variant="h6" sx={{ mt: 3 }}>Provider listings</Typography>
          <Typography color="text.secondary" paragraph>Provider listings describe service metadata. This project does not install, run, or verify arbitrary agent code uploaded by providers.</Typography>
          <Typography variant="h6" sx={{ mt: 3 }}>Account use</Typography>
          <Typography color="text.secondary" paragraph>Use an account you are authorized to create. Keep its password private. Public registration cannot grant administrator access.</Typography>
        </> : <>
          <Typography variant="h6" sx={{ mt: 3 }}>Account and marketplace data</Typography>
          <Typography color="text.secondary" paragraph>The prototype stores account usernames, email addresses, password hashes, service listings, supported invocation records, and eligible reviews in its configured database.</Typography>
          <Typography variant="h6" sx={{ mt: 3 }}>AI requests</Typography>
          <Typography color="text.secondary" paragraph>In demo mode, local sample responses are used and requests are not sent to an AI provider. In live mode, supported service inputs are sent to the configured model provider. Do not enter sensitive personal or confidential data.</Typography>
          <Typography variant="h6" sx={{ mt: 3 }}>Prototype status</Typography>
          <Typography color="text.secondary" paragraph>This preview does not include production account verification, a payment processor, or a complete production privacy program.</Typography>
        </>}
        <Box sx={{ mt: 3 }}><Button variant="contained" onClick={() => navigate('/auth/register')}>Back to registration</Button></Box>
      </Paper>
    </Container>
  );
};
