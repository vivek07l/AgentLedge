export interface Agent {
  id: number;
  name: string;
  description: string;
  type: string;
  price: number;
  minimum_price?: number | null;
  developer_id: number;
  is_active: boolean;
  is_purchased: boolean;
  created_at: string;
  updated_at: string;
  category: string;
  capabilities: string;
  average_rating?: number | null;
  review_count: number;
  success_rate?: number | null;
  completed_invocations: number;
  execution_available?: boolean;
}

export interface CreateAgentData {
  name: string;
  description: string;
  type: string;
  price: number;
}

export interface UpdateAgentData {
  name?: string;
  description?: string;
  type?: string;
  price?: number;
  is_active?: boolean;
}

export interface InterviewPrepRequest {
  topic: string;
  experience_level?: string;
  context?: string;
}

export interface CodeReviewRequest {
  code: string;
  language?: string;
  context?: string;
}

export interface ResumeReviewRequest {
  resume_text: string;
  context?: string;
}

export interface WritingAssistantRequest {
  text: string;
  style?: string;
  context?: string;
}

export interface TechnicalTroubleshootingRequest {
  problem: string;
  system_info?: string;
  context?: string;
}

export interface AgentInvocationRequest {
  agent_type: string;
  code_review?: CodeReviewRequest;
  resume_review?: ResumeReviewRequest;
  interview_prep?: InterviewPrepRequest;
  writing_assistant?: WritingAssistantRequest;
  technical_troubleshooting?: TechnicalTroubleshootingRequest;
}

export interface AgentInvocationResponse {
  id: number;
  purchase_id?: number | null;
  agent_id: number;
  input_data: string;
  output_data?: string;
  output_text?: string;
  tokens_used: number;
  created_at: string;
  agent_name: string;
  invocation_id?: number;
  demo_mode?: boolean;
  demo_notice?: string | null;
  agreed_price?: number;
  charged_tokens?: number;
  settlement_status?: string;
  remaining_balance?: number;
  negotiation_id?: number | null;
  execution_status?: string;
  amount_charged?: number;
  transaction_id?: number | null;
  negotiation?: Negotiation | null;
  status?: string;
}

export interface NegotiationOffer {
  id: number;
  actor_role: string;
  action: string;
  amount: number | null;
  created_at: string;
}

export interface Negotiation {
  id: number;
  agent_id: number;
  agent_name: string;
  buyer_budget: number;
  status: 'open' | 'awaiting_buyer' | 'accepted' | 'rejected' | 'failed';
  agreed_price: number | null;
  round_count: number;
  max_rounds: number;
  offers: NegotiationOffer[];
}

export interface AgentPurchaseResponse {
  agent_id: number;
  purchase_id: number;
  purchase_price: number;
  remaining_balance: number;
}

export interface TimeSeriesData {
  timestamp: string;
  invocations: number;
  success_rate: number;
  succeeded?: number;
  failed?: number;
  demo_invocations?: number;
  average_response_time?: number;
}

export interface AgentAnalytics {
  id: number;
  name: string;
  time_series: TimeSeriesData[];
}

export interface AgentMetrics {
  agent_id: number;
  agent_name: string;
  timeSeries: TimeSeriesData[];
}
