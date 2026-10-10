import { createAuthenticatedApi } from './api';
import axios from 'axios';
import type { ApiResponse } from '../types/api';
import type { 
  Agent, 
  AgentInvocationRequest, 
  AgentInvocationResponse, 
  AgentAnalytics, 
  AgentPurchaseResponse,
  Negotiation,
} from '../types/agent';

const API_BASE_URL = 'http://localhost:8000'; // replace with your actual API base URL

const agentService = {
  getProviderStats: async (token: string): Promise<ApiResponse<{ settled_tokens_earned: number; settled_transactions: number; token_balance: number; active_listings: number }>> => {
    try {
      const response = await createAuthenticatedApi(token).get('/users/me/provider-stats');
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      return { error: typeof detail === 'string' ? detail : 'Failed to fetch provider stats', status: 'error' };
    }
  },
  startNegotiation: async (token: string, agentId: number, buyerBudget: number, initialOffer: number): Promise<ApiResponse<Negotiation>> => {
    try {
      const response = await createAuthenticatedApi(token).post<Negotiation>('/negotiations', {
        agent_id: agentId, buyer_budget: buyerBudget, initial_offer: initialOffer,
      });
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      return { error: typeof detail === 'string' ? detail : 'Could not start negotiation', status: 'error' };
    }
  },

  submitOffer: async (token: string, negotiationId: number, amount: number): Promise<ApiResponse<Negotiation>> => {
    try {
      const response = await createAuthenticatedApi(token).post<Negotiation>(`/negotiations/${negotiationId}/offers`, { amount });
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      return { error: typeof detail === 'string' ? detail : 'Could not submit offer', status: 'error' };
    }
  },

  acceptCounter: async (token: string, negotiationId: number): Promise<ApiResponse<Negotiation>> => {
    try {
      const response = await createAuthenticatedApi(token).post<Negotiation>(`/negotiations/${negotiationId}/accept`);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      return { error: typeof detail === 'string' ? detail : 'Could not accept counter-offer', status: 'error' };
    }
  },

  rejectNegotiation: async (token: string, negotiationId: number): Promise<ApiResponse<Negotiation>> => {
    try {
      const response = await createAuthenticatedApi(token).post<Negotiation>(`/negotiations/${negotiationId}/reject`);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      return { error: typeof detail === 'string' ? detail : 'Could not reject negotiation', status: 'error' };
    }
  },
  getAgent: async (token: string | null, id: number): Promise<ApiResponse<Agent>> => {
    try {
      const api = token ? createAuthenticatedApi(token) : axios.create({ baseURL: process.env.REACT_APP_API_URL || API_BASE_URL });
      const response = await api.get<Agent>(`/agents/${id}`);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to fetch agent',
        status: 'error'
      };
    }
  },

  listAgents: async (token: string | null, filters: { query?: string; category?: string; sort?: string } = {}): Promise<ApiResponse<Agent[]>> => {
    try {
      const api = token ? createAuthenticatedApi(token) : axios.create({ baseURL: process.env.REACT_APP_API_URL || API_BASE_URL });
      const response = await api.get<Agent[]>('/agents', { params: filters });
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to fetch agents',
        status: 'error'
      };
    }
  },

  listMyAgents: async (token: string): Promise<ApiResponse<Agent[]>> => {
    try {
      const response = await createAuthenticatedApi(token).get<Agent[]>('/users/me/agents');
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      return { error: error.response?.data?.detail || 'Failed to fetch your listings', status: 'error' };
    }
  },

  createReview: async (token: string, agentId: number, invocationId: number, rating: number, reviewText: string) => {
    try {
      const api = createAuthenticatedApi(token);
      const response = await api.post(`/agents/${agentId}/reviews`, {
        invocation_id: invocationId, rating, review_text: reviewText,
      });
      return { data: response.data, status: 'success' as const };
    } catch (error: any) {
      const message = error.response?.data?.detail;
      return { error: typeof message === 'string' ? message : 'Failed to submit review', status: 'error' as const };
    }
  },

  createAgent: async (token: string, agentData: Partial<Agent>): Promise<ApiResponse<Agent>> => {
    try {
      const api = createAuthenticatedApi(token);
      const response = await api.post<Agent>('/agents/create', agentData);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to create agent',
        status: 'error'
      };
    }
  },

  updateAgent: async (token: string, id: number, agentData: Partial<Agent>): Promise<ApiResponse<Agent>> => {
    try {
      const api = createAuthenticatedApi(token);
      const response = await api.put<Agent>(`/agents/${id}`, agentData);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to update agent',
        status: 'error'
      };
    }
  },

  deleteAgent: async (token: string, id: number): Promise<ApiResponse<void>> => {
    try {
      const api = createAuthenticatedApi(token);
      await api.delete(`/agents/${id}`);
      return { status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to delete agent',
        status: 'error'
      };
    }
  },

  purchaseAgent: async (token: string, agentId: number): Promise<ApiResponse<AgentPurchaseResponse>> => {
    try {
      const api = createAuthenticatedApi(token);
      // The server reads price from the listing; never trust a browser-supplied price.
      const response = await api.post<AgentPurchaseResponse>('/agents/purchase', { agent_id: agentId });
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to purchase agent',
        status: 'error'
      };
    }
  },

  invokeAgent: async (
    token: string,
    agentId: number,
    request: AgentInvocationRequest,
    negotiationId?: number,
    idempotencyKey?: string,
  ): Promise<ApiResponse<AgentInvocationResponse>> => {
    try {
      const api = createAuthenticatedApi(token);
      const createKey = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto)
        ? crypto.randomUUID() : `invoke-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const requestKey = idempotencyKey || createKey();
      const response = await api.post<AgentInvocationResponse>(`/agents/invoke/${agentId}`, {
        ...request, ...(negotiationId ? { negotiation_id: negotiationId } : {}),
      }, { headers: { 'Idempotency-Key': requestKey } });
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      console.error('Detailed error information:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        responseData: error.response?.data,
        requestConfig: {
          url: error.config?.url,
          method: error.config?.method,
          headers: error.config?.headers,
          data: error.config?.data
        }
      });
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to invoke agent',
        status: 'error',
        httpStatus: error.response?.status,
      };
    }
  },

  listInvocations: async (token: string): Promise<ApiResponse<AgentInvocationResponse[]>> => {
    try {
      const api = createAuthenticatedApi(token);
      const response = await api.get<AgentInvocationResponse[]>('/users/me/invocations');
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to fetch invocations',
        status: 'error'
      };
    }
  },

  getAgentAnalytics: async (token: string, agentId: number): Promise<ApiResponse<AgentAnalytics>> => {
    try {
      const api = createAuthenticatedApi(token);
      const response = await api.get<AgentAnalytics>(`/agents/${agentId}/analytics`);
      return { data: response.data, status: 'success' };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail;
      return {
        error: typeof errorMessage === 'string' ? errorMessage : 'Failed to fetch agent analytics',
        status: 'error'
      };
    }
  },

  async summarizeConversation(token: string, input: string, output: string) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/agents/summarize`,
        {
          input_text: input,
          output_text: output
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error summarizing conversation:', error);
      return {
        status: 'error',
        error: 'Failed to summarize conversation',
      };
    }
  },
};

export { agentService };
