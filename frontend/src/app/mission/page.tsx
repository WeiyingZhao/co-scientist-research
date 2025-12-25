'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { MessageStream } from '@/components/layout/MessageStream';
import { AgentGraph } from '@/components/agents/AgentGraph';
import { HypothesisCard, HypothesisCardSkeleton } from '@/components/agents/HypothesisCard';
import { GlassCard } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useResearchStore } from '@/store';
import { getSessionStatus, provideFeedback, createWebSocketConnection } from '@/lib/api';
import type { AgentMessage, Hypothesis, ExperimentDesign, LiteratureReference, AgentType } from '@/types';
import {
  Lightbulb,
  Beaker,
  BookOpen,
  Send,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

export default function MissionControlPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');

  const {
    currentSession,
    setCurrentSession,
    activeAgent,
    setActiveAgent,
    updateAgentStatus,
    agentStatuses,
    addMessage,
    updateHypothesis,
    addHypothesis,
    setProgress,
    progress,
    isLoading,
    setLoading,
    error,
    setError,
    selectedHypothesisId,
    setSelectedHypothesis,
    activeTab,
    setActiveTab,
    setWebSocket,
    setWsConnected,
  } = useResearchStore();

  const [feedbackText, setFeedbackText] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  // Fetch session status
  const fetchSession = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const session = await getSessionStatus(sessionId);
      setCurrentSession(session);

      // Check if waiting for feedback
      if (session.status === 'waiting_feedback') {
        setShowFeedback(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch session');
    } finally {
      setLoading(false);
    }
  }, [sessionId, setCurrentSession, setLoading, setError]);

  // Initialize WebSocket connection
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!sessionId) return;

    const ws = createWebSocketConnection(
      sessionId,
      (data: unknown) => {
        const message = data as {
          type: string;
          data: unknown;
        };

        switch (message.type) {
          case 'status':
            const statusData = message.data as {
              current_agent: AgentType | null;
              progress: number;
              status: string;
            };
            if (statusData.current_agent) {
              setActiveAgent(statusData.current_agent);
              updateAgentStatus(statusData.current_agent, 'active');
            }
            setProgress(statusData.progress);
            if (statusData.status === 'waiting_feedback') {
              setShowFeedback(true);
            }
            break;

          case 'agent_update':
            const agentData = message.data as {
              agent: AgentType;
              status: 'idle' | 'active' | 'completed' | 'error';
              message?: AgentMessage;
            };
            updateAgentStatus(agentData.agent, agentData.status);
            if (agentData.message) {
              addMessage(agentData.message);
            }
            break;

          case 'hypothesis_update':
            const hypothesisData = message.data as Hypothesis;
            if (currentSession?.hypotheses.find(h => h.id === hypothesisData.id)) {
              updateHypothesis(hypothesisData);
            } else {
              addHypothesis(hypothesisData);
            }
            break;

          case 'complete':
            setActiveAgent(null);
            Object.keys(agentStatuses).forEach((agent) => {
              updateAgentStatus(agent as AgentType, 'completed');
            });
            break;

          case 'error':
            setError((message.data as { message: string }).message);
            break;
        }
      },
      (err) => {
        console.error('WebSocket error:', err);
        setWsConnected(false);
      },
      () => {
        setWsConnected(false);
      }
    );

    setWebSocket(ws);
    setWsConnected(true);

    return () => {
      ws.close();
      setWebSocket(null);
      setWsConnected(false);
    };
  }, [sessionId]);

  // Initial fetch
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const handleSendFeedback = async () => {
    if (!sessionId || !feedbackText.trim()) return;

    try {
      await provideFeedback(sessionId, {
        feedback_type: 'custom',
        content: feedbackText,
      });
      setFeedbackText('');
      setShowFeedback(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send feedback');
    }
  };

  const hypotheses = currentSession?.hypotheses || [];
  const experiments = currentSession?.experiments || [];
  const literature = currentSession?.literature || [];
  const messages = currentSession?.messages || [];

  // Sort hypotheses by Elo rating
  const sortedHypotheses = [...hypotheses].sort((a, b) => b.elo_rating - a.elo_rating);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 container mx-auto px-4 py-4">
        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Research Progress</span>
            <span className="text-cyan-400 font-medium">{Math.round(progress * 100)}%</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${progress * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-lg bg-status-error/10 border border-status-error/50 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-status-error" />
            <p className="text-status-error">{error}</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="ml-auto"
            >
              Dismiss
            </Button>
          </div>
        )}

        {/* Three-Pane Layout */}
        <div className="grid-mission-control">
          {/* Left Pane: Message Stream */}
          <GlassCard className="flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/10">
              <h2 className="font-semibold">Agent Activity</h2>
            </div>
            <MessageStream messages={messages} className="flex-1" />

            {/* Feedback Input */}
            {showFeedback && (
              <div className="p-4 border-t border-white/10">
                <p className="text-sm text-muted-foreground mb-2">
                  The system is waiting for your feedback:
                </p>
                <div className="flex gap-2">
                  <Textarea
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    placeholder="Provide your feedback..."
                    className="min-h-[60px]"
                  />
                  <Button
                    variant="neon"
                    size="icon"
                    onClick={handleSendFeedback}
                    disabled={!feedbackText.trim()}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </GlassCard>

          {/* Center Pane: Agent Graph */}
          <GlassCard className="flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="font-semibold">Neural Graph</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchSession}
                disabled={isLoading}
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <div className="flex-1 min-h-[400px]">
              <AgentGraph />
            </div>
          </GlassCard>

          {/* Right Pane: Artifacts */}
          <GlassCard className="flex flex-col overflow-hidden">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
              <div className="p-4 border-b border-white/10">
                <TabsList className="w-full">
                  <TabsTrigger value="hypotheses" className="flex-1 gap-1">
                    <Lightbulb className="w-4 h-4" />
                    Hypotheses
                    {hypotheses.length > 0 && (
                      <Badge variant="generation" className="ml-1">
                        {hypotheses.length}
                      </Badge>
                    )}
                  </TabsTrigger>
                  <TabsTrigger value="experiments" className="flex-1 gap-1">
                    <Beaker className="w-4 h-4" />
                    Experiments
                  </TabsTrigger>
                  <TabsTrigger value="literature" className="flex-1 gap-1">
                    <BookOpen className="w-4 h-4" />
                    Literature
                  </TabsTrigger>
                </TabsList>
              </div>

              <ScrollArea className="flex-1">
                <TabsContent value="hypotheses" className="p-4 space-y-3 mt-0">
                  {isLoading && hypotheses.length === 0 ? (
                    <>
                      <HypothesisCardSkeleton />
                      <HypothesisCardSkeleton />
                    </>
                  ) : sortedHypotheses.length > 0 ? (
                    sortedHypotheses.map((hypothesis, index) => (
                      <HypothesisCard
                        key={hypothesis.id}
                        hypothesis={hypothesis}
                        rank={index + 1}
                        isSelected={selectedHypothesisId === hypothesis.id}
                        onClick={() => setSelectedHypothesis(hypothesis.id)}
                      />
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      <Lightbulb className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No hypotheses generated yet</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="experiments" className="p-4 space-y-3 mt-0">
                  {experiments.length > 0 ? (
                    experiments.map((experiment) => (
                      <ExperimentCard key={experiment.id} experiment={experiment} />
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      <Beaker className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No experiments designed yet</p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="literature" className="p-4 space-y-3 mt-0">
                  {literature.length > 0 ? (
                    literature.map((ref) => (
                      <LiteratureCard key={ref.id} reference={ref} />
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground py-8">
                      <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No literature found yet</p>
                    </div>
                  )}
                </TabsContent>
              </ScrollArea>
            </Tabs>
          </GlassCard>
        </div>
      </main>
    </div>
  );
}

function ExperimentCard({ experiment }: { experiment: ExperimentDesign }) {
  return (
    <GlassCard className="p-4">
      <h3 className="font-medium mb-2">{experiment.title}</h3>
      <p className="text-sm text-muted-foreground mb-3">{experiment.objective}</p>
      <div className="flex items-center gap-2">
        <Badge variant={
          experiment.estimated_complexity === 'low' ? 'success' :
          experiment.estimated_complexity === 'medium' ? 'warning' : 'error'
        }>
          {experiment.estimated_complexity} complexity
        </Badge>
        {experiment.code_template && (
          <Badge variant="generation">Has Code</Badge>
        )}
      </div>
    </GlassCard>
  );
}

function LiteratureCard({ reference }: { reference: LiteratureReference }) {
  return (
    <GlassCard className="p-4">
      <h3 className="font-medium text-sm mb-1 line-clamp-2">{reference.title}</h3>
      <p className="text-xs text-muted-foreground mb-2">
        {reference.authors.slice(0, 3).join(', ')}
        {reference.authors.length > 3 && ' et al.'}
        {reference.publication_year && ` (${reference.publication_year})`}
      </p>
      <div className="flex items-center gap-2">
        <Badge variant="default">
          Relevance: {Math.round(reference.relevance_score * 100)}%
        </Badge>
        {reference.doi && (
          <a
            href={`https://doi.org/${reference.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-cyan-400 hover:underline"
          >
            DOI
          </a>
        )}
      </div>
    </GlassCard>
  );
}
