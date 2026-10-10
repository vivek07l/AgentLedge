import React from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Container,
  Stack,
  Chip,
} from '@mui/material';
import {
  ArrowForwardRounded,
  CodeRounded,
  DescriptionRounded,
  PsychologyRounded,
  EditNoteRounded,
  BuildRounded,
  HubRounded,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';

const features = [
  {
    title: 'Code Review',
    category: 'Development',
    description: 'Automated syntax, bug, and vulnerability inspection with constructive remediation diffs.',
    icon: <CodeRounded sx={{ color: '#F6C900' }} />,
  },
  {
    title: 'Resume Review',
    category: 'Career',
    description: 'ATS optimization and structural critique tailored to modern technology role standards.',
    icon: <DescriptionRounded sx={{ color: '#F6C900' }} />,
  },
  {
    title: 'Interview Prep',
    category: 'Career',
    description: 'Targeted behavioral and technical interview simulation with empirical feedback scoring.',
    icon: <PsychologyRounded sx={{ color: '#F6C900' }} />,
  },
  {
    title: 'Writing Assistant',
    category: 'Content',
    description: 'Professional prose refinement with precision tone tuning and grammar analysis.',
    icon: <EditNoteRounded sx={{ color: '#F6C900' }} />,
  },
  {
    title: 'Technical Troubleshooter',
    category: 'Operations',
    description: 'Deep stack-trace diagnosis and step-by-step root cause analysis for distributed systems.',
    icon: <BuildRounded sx={{ color: '#F6C900' }} />,
  },
  {
    title: 'Agent Mesh Architecture',
    category: 'Protocol',
    description: 'Standardized model-agnostic MCP and REST adapters with cryptographic token escrow.',
    icon: <HubRounded sx={{ color: '#B7F000' }} />,
  },
];

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  return (
    <Box sx={{ pb: 6 }}>
      {/* Hero Section */}
      <Box
        sx={{
          bgcolor: '#171717',
          color: '#FFFFFF',
          py: { xs: 6, md: 8 },
          mb: 5,
          border: '2px solid #292929',
          boxShadow: '6px 6px 0 #171717',
          backgroundImage:
            'radial-gradient(circle at 90% 15%, rgba(246, 201, 0, 0.12) 0%, transparent 40%), linear-gradient(135deg, #171717 0%, #202020 100%)',
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={8}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    bgcolor: '#B7F000',
                    boxShadow: '0 0 8px #B7F000',
                  }}
                />
                <Typography
                  variant="overline"
                  sx={{ color: '#F6C900', letterSpacing: '0.14em', fontWeight: 850 }}
                >
                  AUTONOMOUS AGENT MARKETPLACE // VERSION 2.0
                </Typography>
              </Stack>

              <Typography variant="h1" gutterBottom sx={{ color: '#FFFFFF', fontWeight: 900 }}>
                AgentsLedge
              </Typography>

              <Typography
                variant="h5"
                sx={{
                  color: '#D4CFC4',
                  maxWidth: 680,
                  fontWeight: 500,
                  lineHeight: 1.6,
                  mb: 4,
                  fontSize: { xs: '1.1rem', md: '1.3rem' },
                }}
              >
                Access specialized autonomous AI agents with transparent run benchmarks, empirical
                ratings, and bilateral token settlement.
              </Typography>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                {!token ? (
                  <>
                    <Button
                      variant="contained"
                      color="secondary"
                      size="large"
                      endIcon={<ArrowForwardRounded />}
                      onClick={() => navigate('/auth/register')}
                    >
                      Create Account
                    </Button>
                    <Button
                      variant="outlined"
                      size="large"
                      onClick={() => navigate('/marketplace')}
                      sx={{ color: '#FFFFFF', borderColor: '#444444', bgcolor: '#222222' }}
                    >
                      Explore Marketplace
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="contained"
                    color="secondary"
                    size="large"
                    endIcon={<ArrowForwardRounded />}
                    onClick={() => navigate('/marketplace')}
                  >
                    Open Marketplace
                  </Button>
                )}
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg">
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 3 }}>
          <Box>
            <Typography variant="overline" sx={{ color: '#706E66', fontWeight: 800 }}>
              SPECIALIZED CAPABILITIES
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 850, color: '#171717' }}>
              Autonomous Service Network
            </Typography>
          </Box>
        </Stack>

        <Grid container spacing={3}>
          {features.map((feature) => (
            <Grid item xs={12} sm={6} md={4} key={feature.title}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  bgcolor: '#FFFFFF',
                  border: '1px solid #292929',
                  boxShadow: '4px 4px 0 #171717',
                  transition: 'all 0.14s ease',
                  '&:hover': {
                    boxShadow: '6px 6px 0 #F6C900',
                    transform: 'translate(-2px, -2px)',
                  },
                }}
              >
                <Box
                  sx={{
                    bgcolor: '#171717',
                    px: 2,
                    py: 1,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid #292929',
                  }}
                >
                  <Typography variant="overline" sx={{ color: '#F6C900', fontWeight: 800 }}>
                    {feature.category}
                  </Typography>
                  {feature.icon}
                </Box>
                <CardContent sx={{ p: 2.5, flexGrow: 1 }}>
                  <Typography variant="h5" component="h3" sx={{ fontWeight: 800, mb: 1, color: '#171717' }}>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};
