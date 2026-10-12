import { createAuthenticatedApi } from './api';

export interface AutonomousPolicy {
  enabled: boolean;
  max_task_budget: number;
  max_offer_price: number;
  max_daily_spend: number;
  allowed_categories: string[];
  allowed_listing_ids: number[];
  max_negotiation_attempts: number;
  max_execution_retries: number;
  auto_review: boolean;
  token_balance: number;
  spent_today: number;
  remaining_daily_budget: number;
}

export const autonomousPolicyService = {
  async get(token: string): Promise<AutonomousPolicy> {
    const response = await createAuthenticatedApi(token).get<AutonomousPolicy>('/users/me/autonomous-policy');
    return response.data;
  },
  async update(token: string, policy: Partial<AutonomousPolicy>): Promise<AutonomousPolicy> {
    const response = await createAuthenticatedApi(token).patch<AutonomousPolicy>('/users/me/autonomous-policy', policy);
    return response.data;
  },
};
