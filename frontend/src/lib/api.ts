import axios from 'axios';
import type {
  ResearchSession,
  StartResearchRequest,
  StartResearchResponse,
  FeedbackRequest,
  Hypothesis,
  ExperimentDesign,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Research Session APIs
export async function startResearch(data: StartResearchRequest): Promise<StartResearchResponse> {
  const response = await api.post('/api/research', data);
  return response.data;
}

export async function getSessionStatus(sessionId: string): Promise<ResearchSession> {
  const response = await api.get(`/api/research/${sessionId}/status`);
  return response.data;
}

export async function getHypotheses(sessionId: string): Promise<Hypothesis[]> {
  const response = await api.get(`/api/research/${sessionId}/hypotheses`);
  return response.data;
}

export async function getExperiments(sessionId: string): Promise<ExperimentDesign[]> {
  const response = await api.get(`/api/research/${sessionId}/experiments`);
  return response.data;
}

export async function getResearchOverview(sessionId: string): Promise<ResearchSession> {
  const response = await api.get(`/api/research/${sessionId}/overview`);
  return response.data;
}

export async function provideFeedback(
  sessionId: string,
  feedback: FeedbackRequest
): Promise<{ status: string; message: string }> {
  const response = await api.post(`/api/research/${sessionId}/feedback`, feedback);
  return response.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/api/research/${sessionId}`);
}

// Available datasets
export async function getDatasets(): Promise<{ datasets: string[] }> {
  const response = await api.get('/api/datasets');
  return response.data;
}

// Methodology recommendations
export async function getMethodologies(analysisType: string): Promise<{ methodologies: string[] }> {
  const response = await api.get(`/api/methodologies/${analysisType}`);
  return response.data;
}

// WebSocket connection
export function createWebSocketConnection(
  sessionId: string,
  onMessage: (data: unknown) => void,
  onError: (error: Event) => void,
  onClose: () => void
): WebSocket {
  const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/api/ws/${sessionId}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      console.error('Failed to parse WebSocket message');
    }
  };

  ws.onerror = onError;
  ws.onclose = onClose;

  return ws;
}

export default api;
