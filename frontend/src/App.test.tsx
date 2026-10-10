import React from 'react';
import { render, screen } from '@testing-library/react';
import { AgentCard } from './components/agents/AgentCard';

test('shows service details and honest reputation evidence in the refreshed card', () => {
  render(<AgentCard agent={{
    id: 1,
    name: 'Resume Reviewer',
    description: 'Clear and practical resume guidance.',
    type: 'Resume Reviewer',
    category: 'Career',
    capabilities: 'resume feedback',
    price: 2,
    developer_id: 4,
    is_active: true,
    is_purchased: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    average_rating: null,
    review_count: 0,
    success_rate: null,
    completed_invocations: 0,
  }} onSelect={() => undefined} />);

  expect(screen.getByRole('heading', { name: 'Resume Reviewer' })).toBeInTheDocument();
  expect(screen.getByText('No verified reviews yet')).toBeInTheDocument();
  expect(screen.getByText('2 tokens')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'View details' })).toBeInTheDocument();
});
