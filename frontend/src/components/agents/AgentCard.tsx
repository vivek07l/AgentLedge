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
import { Token as TokenIcon } from '@mui/icons-material';
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
        '&:hover .agent-card-arrow': { opacity: 1, transform: 'translateX(3px)' },
      }}
      onClick={() => onSelect?.(agent)}
    >
      <CardContent sx={{ flexGrow: 1, p: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
        <Typography gutterBottom variant="h5" component="div">
          {agent.name}
        </Typography>
        <Box className="agent-card-arrow" sx={{ color: 'primary.main', opacity: .55, transition: 'all .18s ease', fontSize: 19 }}>↗</Box>
        </Box>
        <Typography variant="body2" color="text.secondary">
          {agent.description}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 2 }}>
          <Chip size="small" color="primary" variant="outlined" label={agent.category || 'General'} />
          {agent.average_rating != null ? (
            <Chip size="small" color="primary" variant="outlined" label={`${agent.average_rating.toFixed(1)}/5 · ${agent.review_count} reviews`} />
          ) : <Chip size="small" variant="outlined" label="No verified reviews yet" />}
          {agent.success_rate != null && (
            <Chip size="small" color="success" variant="outlined" label={`${agent.success_rate}% success · ${agent.completed_invocations} runs`} />
          )}
        </Box>
        {agent.capabilities && <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>Capabilities: {agent.capabilities}</Typography>}
      </CardContent>
      <CardActions sx={{ justifyContent: 'space-between', p: 2.5, pt: 0 }}>
        <Chip
          icon={<TokenIcon />}
          label={`${agent.price} tokens`}
          color="primary"
          variant="outlined"
        />
        {agent.is_purchased ? (
          <Chip 
            label="Purchased" 
            color="success"
            sx={{ minWidth: 85 }}
          />
        ) : (
          <Button 
            size="small" 
            color="primary" 
            variant="contained"
            sx={{ minWidth: 85 }}
          >
            View details
          </Button>
        )}
      </CardActions>
    </Card>
  );
};
