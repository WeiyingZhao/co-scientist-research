// Research Session Types
export interface ResearchSession {
  session_id: string;
  research_goal: ResearchGoal;
  status: SessionStatus;
  current_agent: string | null;
  current_iteration: number;
  max_iterations: number;
  hypotheses: Hypothesis[];
  experiments: ExperimentDesign[];
  literature: LiteratureReference[];
  messages: AgentMessage[];
  created_at: string;
  updated_at: string;
}

export interface ResearchGoal {
  description: string;
  domain: string;
  constraints: string[];
  priority_areas: string[];
}

export type SessionStatus =
  | 'initializing'
  | 'generating'
  | 'reflecting'
  | 'ranking'
  | 'evolving'
  | 'waiting_feedback'
  | 'completed'
  | 'error';

// Hypothesis Types
export interface Hypothesis {
  id: string;
  statement: string;
  rationale: string;
  supporting_evidence: string[];
  methodology_outline: string;
  expected_outcomes: string[];
  data_requirements: string[];
  novelty_score: number;
  feasibility_score: number;
  impact_score: number;
  elo_rating: number;
  status: HypothesisStatus;
  reviews: HypothesisReview[];
  iteration: number;
  parent_id: string | null;
  created_at: string;
}

export type HypothesisStatus =
  | 'generated'
  | 'under_review'
  | 'ranked'
  | 'evolved'
  | 'selected'
  | 'discarded';

export interface HypothesisReview {
  id: string;
  hypothesis_id: string;
  reviewer_agent: string;
  novelty_assessment: string;
  feasibility_assessment: string;
  impact_assessment: string;
  methodology_critique: string;
  improvement_suggestions: string[];
  overall_recommendation: 'accept' | 'revise' | 'reject';
  confidence_score: number;
  created_at: string;
}

// Experiment Design Types
export interface ExperimentDesign {
  id: string;
  hypothesis_id: string;
  title: string;
  objective: string;
  methodology: string;
  data_sources: DataSource[];
  analysis_steps: AnalysisStep[];
  expected_results: string;
  validation_approach: string;
  code_template: string | null;
  estimated_complexity: 'low' | 'medium' | 'high';
  created_at: string;
}

export interface DataSource {
  name: string;
  type: string;
  description: string;
  access_method: string;
}

export interface AnalysisStep {
  step_number: number;
  description: string;
  tools_required: string[];
  expected_output: string;
}

// Literature Types
export interface LiteratureReference {
  id: string;
  title: string;
  authors: string[];
  publication_year: number;
  journal: string | null;
  doi: string | null;
  abstract: string;
  relevance_score: number;
  key_findings: string[];
  url: string | null;
}

// Agent Types
export interface AgentMessage {
  id: string;
  agent_type: AgentType;
  content: string;
  message_type: 'thought' | 'action' | 'result' | 'decision';
  timestamp: string;
  metadata: Record<string, unknown>;
}

export type AgentType =
  | 'supervisor'
  | 'generation'
  | 'reflection'
  | 'ranking'
  | 'proximity'
  | 'evolution'
  | 'meta-review'
  | 'experiment'
  | 'literature';

export interface AgentNode {
  id: string;
  type: AgentType;
  label: string;
  status: 'idle' | 'active' | 'completed' | 'error';
  description: string;
}

// API Request/Response Types
export interface StartResearchRequest {
  research_goal: string;
  domain?: string;
  max_iterations?: number;
  model?: string;
}

export interface StartResearchResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface FeedbackRequest {
  feedback_type: 'approve' | 'revise' | 'reject' | 'custom';
  content: string;
  target_hypothesis_id?: string;
}

// WebSocket Message Types
export interface WSMessage {
  type: 'status' | 'agent_update' | 'hypothesis_update' | 'error' | 'complete';
  data: unknown;
  timestamp: string;
}

export interface StatusUpdate {
  session_id: string;
  status: SessionStatus;
  current_agent: AgentType | null;
  message: string;
  progress: number;
}

// UI State Types
export interface UIState {
  sidebarCollapsed: boolean;
  activeTab: 'hypotheses' | 'experiments' | 'literature';
  selectedHypothesisId: string | null;
  graphZoom: number;
  graphCenter: { x: number; y: number };
}
