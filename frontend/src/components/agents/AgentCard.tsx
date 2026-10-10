import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Box,
  Chip,
} from '@mui/material';
import {
  Token as TokenIcon,
  ArrowForwardRounded,
  VerifiedRounded,
  SpeedRounded,
} from '@mui/icons-material';
import type { Agent } from '../../types/agent';

interface AgentCardProps {
  agent: Agent;
  onSelect?: (agent: Agent) => void;
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  onSelect,
}) => {
  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        cursor: onSelect ? 'pointer' : 'default',
        overflow: 'hidden',
        bgcolor: '#FFFFFF',
        border: '1px solid #292929',
        boxShadow: '4px 4px 0 #171717',
        transition: 'transform 0.14s ease, box-shadow 0.14s ease, border-color 0.14s ease',
        '&:hover': {
          boxShadow: '6px 6px 0 #F6C900',
          borderColor: '#171717',
          transform: 'translate(-2px, -2px)',
          '& .agent-card-arrow': {
            transform: 'translate(2px, -2px)',
            color: '#F6C900',
          },
        },
      }}
      onClick={() => onSelect?.(agent)}
    >
      {/* Category Accent Bar */}
      <Box
        sx={{
          bgcolor: '#171717',
          color: '#FFFFFF',
          px: 2,
          py: 0.6,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #292929',
        }}
      >
        <Typography
          variant="overline"
          sx={{
            fontWeight: 800,
            letterSpacing: '0.12em',
            fontSize: '0.68rem',
            color: '#F6C900',
          }}
        >
          {agent.category || 'General'}
        </Typography>
        <Box
          className="agent-card-arrow"
          sx={{
            color: '#FFFFFF',
            transition: 'all 0.15s ease',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <ArrowForwardRounded sx={{ fontSize: 16 }} />
        </Box>
      </Box>

      <CardContent sx={{ flexGrow: 1, p: 2.5 }}>
        <Typography
          gutterBottom
          variant="h5"
          component="h2"
          sx={{
            fontWeight: 850,
            fontSize: '1.25rem',
            letterSpacing: '-0.02em',
            color: '#171717',
            mb: 1,
          }}
        >
          {agent.name}
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            minHeight: '2.8em',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            lineHeight: 1.5,
            mb: 2,
          }}
        >
          {agent.description}
        </Typography>

        {/* Telemetry badges */}
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 1.5 }}>
          {agent.average_rating != null ? (
            <Chip
              size="small"
              icon={<VerifiedRounded sx={{ fontSize: '14px !important', color: '#171717 !important' }} />}
              label={`${agent.average_rating.toFixed(1)}/5 · ${agent.review_count} reviews`}
              sx={{
                bgcolor: '#F6C900',
                color: '#171717',
                fontWeight: 800,
                border: '1px solid #171717',
              }}
            />
          ) : (
            <Chip
              size="small"
              variant="outlined"
              label="No verified reviews yet"
              sx={{
                bgcolor: '#F5F2E9',
                color: '#5A5A52',
                borderColor: '#D4CFC4',
                fontWeight: 650,
              }}
            />
          )}

          {agent.success_rate != null && (
            <Chip
              size="small"
              icon={<SpeedRounded sx={{ fontSize: '14px !important', color: '#171717 !important' }} />}
              label={`${agent.success_rate}% success · ${agent.completed_invocations} runs`}
              sx={{
                bgcolor: '#B7F000',
                color: '#171717',
                fontWeight: 800,
                border: '1px solid #171717',
              }}
            />
          )}
        </Box>

        {agent.capabilities && (
          <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px dashed #E5E0D5' }}>
            <Typography
              variant="caption"
              sx={{
                color: '#706E66',
                fontFamily: 'monospace',
                fontSize: '0.72rem',
                display: 'block',
                lineHeight: 1.4,
              }}
            >
              <strong style={{ color: '#171717' }}>CAPABILITIES:</strong> {agent.capabilities}
            </Typography>
          </Box>
        )}
      </CardContent>

      <CardActions
        sx={{
          justifyContent: 'space-between',
          p: 2.5,
          pt: 0,
          borderTop: '1px solid #F0ECE1',
        }}
      >
        <Chip
          icon={<TokenIcon sx={{ fontSize: '16px !important', color: '#171717 !important' }} />}
          label={`${agent.price} tokens`}
          variant="outlined"
          sx={{
            fontWeight: 800,
            borderColor: '#292929',
            bgcolor: '#FFFFFF',
            boxShadow: '1px 1px 0 #292929',
          }}
        />

        {agent.is_purchased ? (
          <Chip
            label="Purchased"
            sx={{
              bgcolor: '#B7F000',
              color: '#171717',
              fontWeight: 800,
              border: '1px solid #171717',
              minWidth: 85,
            }}
          />
        ) : (
          <Button
            size="small"
            color="primary"
            variant="contained"
            sx={{
              minWidth: 95,
              fontSize: '0.75rem',
              py: 0.5,
            }}
          >
            View details
          </Button>
        )}
      </CardActions>
    </Card>
  );
};
