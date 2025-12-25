import { create } from 'zustand';
import type {
  ResearchSession,
  Hypothesis,
  ExperimentDesign,
  AgentMessage,
  SessionStatus,
  AgentType,
  LiteratureReference,
} from '@/types';

interface ResearchStore {
  // Session state
  currentSession: ResearchSession | null;
  sessions: ResearchSession[];
  isLoading: boolean;
  error: string | null;

  // Real-time state
  activeAgent: AgentType | null;
  agentStatuses: Record<AgentType, 'idle' | 'active' | 'completed' | 'error'>;
  progress: number;

  // UI state
  selectedHypothesisId: string | null;
  activeTab: 'hypotheses' | 'experiments' | 'literature';
  isSidebarCollapsed: boolean;

  // WebSocket
  ws: WebSocket | null;
  wsConnected: boolean;

  // Actions
  setCurrentSession: (session: ResearchSession | null) => void;
  addSession: (session: ResearchSession) => void;
  updateSession: (sessionId: string, updates: Partial<ResearchSession>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Real-time actions
  setActiveAgent: (agent: AgentType | null) => void;
  updateAgentStatus: (agent: AgentType, status: 'idle' | 'active' | 'completed' | 'error') => void;
  setProgress: (progress: number) => void;
  addMessage: (message: AgentMessage) => void;
  updateHypothesis: (hypothesis: Hypothesis) => void;
  addHypothesis: (hypothesis: Hypothesis) => void;
  updateExperiment: (experiment: ExperimentDesign) => void;
  addLiterature: (reference: LiteratureReference) => void;

  // UI actions
  setSelectedHypothesis: (id: string | null) => void;
  setActiveTab: (tab: 'hypotheses' | 'experiments' | 'literature') => void;
  toggleSidebar: () => void;

  // WebSocket actions
  setWebSocket: (ws: WebSocket | null) => void;
  setWsConnected: (connected: boolean) => void;

  // Reset
  reset: () => void;
}

const initialAgentStatuses: Record<AgentType, 'idle' | 'active' | 'completed' | 'error'> = {
  supervisor: 'idle',
  generation: 'idle',
  reflection: 'idle',
  ranking: 'idle',
  proximity: 'idle',
  evolution: 'idle',
  'meta-review': 'idle',
  experiment: 'idle',
  literature: 'idle',
};

export const useResearchStore = create<ResearchStore>((set, get) => ({
  // Initial state
  currentSession: null,
  sessions: [],
  isLoading: false,
  error: null,
  activeAgent: null,
  agentStatuses: { ...initialAgentStatuses },
  progress: 0,
  selectedHypothesisId: null,
  activeTab: 'hypotheses',
  isSidebarCollapsed: false,
  ws: null,
  wsConnected: false,

  // Session actions
  setCurrentSession: (session) => set({ currentSession: session }),

  addSession: (session) => set((state) => ({
    sessions: [...state.sessions, session],
  })),

  updateSession: (sessionId, updates) => set((state) => {
    const updatedSessions = state.sessions.map((s) =>
      s.session_id === sessionId ? { ...s, ...updates } : s
    );
    const updatedCurrent =
      state.currentSession?.session_id === sessionId
        ? { ...state.currentSession, ...updates }
        : state.currentSession;
    return {
      sessions: updatedSessions,
      currentSession: updatedCurrent as ResearchSession | null,
    };
  }),

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Real-time actions
  setActiveAgent: (agent) => set({ activeAgent: agent }),

  updateAgentStatus: (agent, status) => set((state) => ({
    agentStatuses: { ...state.agentStatuses, [agent]: status },
  })),

  setProgress: (progress) => set({ progress }),

  addMessage: (message) => set((state) => {
    if (!state.currentSession) return state;
    return {
      currentSession: {
        ...state.currentSession,
        messages: [...state.currentSession.messages, message],
      },
    };
  }),

  updateHypothesis: (hypothesis) => set((state) => {
    if (!state.currentSession) return state;
    const hypotheses = state.currentSession.hypotheses.map((h) =>
      h.id === hypothesis.id ? hypothesis : h
    );
    return {
      currentSession: { ...state.currentSession, hypotheses },
    };
  }),

  addHypothesis: (hypothesis) => set((state) => {
    if (!state.currentSession) return state;
    return {
      currentSession: {
        ...state.currentSession,
        hypotheses: [...state.currentSession.hypotheses, hypothesis],
      },
    };
  }),

  updateExperiment: (experiment) => set((state) => {
    if (!state.currentSession) return state;
    const existingIndex = state.currentSession.experiments.findIndex(
      (e) => e.id === experiment.id
    );
    const experiments = existingIndex >= 0
      ? state.currentSession.experiments.map((e) =>
          e.id === experiment.id ? experiment : e
        )
      : [...state.currentSession.experiments, experiment];
    return {
      currentSession: { ...state.currentSession, experiments },
    };
  }),

  addLiterature: (reference) => set((state) => {
    if (!state.currentSession) return state;
    return {
      currentSession: {
        ...state.currentSession,
        literature: [...state.currentSession.literature, reference],
      },
    };
  }),

  // UI actions
  setSelectedHypothesis: (id) => set({ selectedHypothesisId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  // WebSocket actions
  setWebSocket: (ws) => set({ ws }),
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // Reset
  reset: () => set({
    currentSession: null,
    isLoading: false,
    error: null,
    activeAgent: null,
    agentStatuses: { ...initialAgentStatuses },
    progress: 0,
    selectedHypothesisId: null,
    ws: null,
    wsConnected: false,
  }),
}));
