import { createAuthenticatedApi } from './api';

export interface ActionApproval {
  approval_id: string;
  action: string;
  expires_at: string;
  payload: Record<string, unknown>;
}

export const actionApprovalService = {
  async list(token: string): Promise<ActionApproval[]> {
    const response = await createAuthenticatedApi(token).get<ActionApproval[]>('/users/me/action-approvals');
    return response.data;
  },
  async decide(token: string, approvalId: string, decision: 'approve' | 'reject'): Promise<void> {
    await createAuthenticatedApi(token).post(`/users/me/action-approvals/${encodeURIComponent(approvalId)}`, { decision });
  },
};
