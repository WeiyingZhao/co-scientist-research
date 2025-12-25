'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { Header } from '@/components/layout/Header';
import { GlassCard, Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useResearchStore } from '@/store';
import { getResearchOverview, getHypotheses, getExperiments } from '@/lib/api';
import { truncateText, formatEloScore, getAgentColor } from '@/lib/utils';
import type { Hypothesis, ExperimentDesign } from '@/types';
import {
  Trophy,
  Download,
  FileText,
  Code,
  Copy,
  Check,
  ChevronRight,
  Lightbulb,
  Target,
  TrendingUp,
  Beaker,
} from 'lucide-react';

export default function DiscoveryDeckPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');

  const { currentSession, setCurrentSession, isLoading, setLoading, error, setError } =
    useResearchStore();

  const [selectedHypothesis, setSelectedHypothesis] = useState<Hypothesis | null>(null);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [experiments, setExperiments] = useState<ExperimentDesign[]>([]);
  const [copiedCode, setCopiedCode] = useState(false);

  const fetchData = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const [overview, hyps, exps] = await Promise.all([
        getResearchOverview(sessionId),
        getHypotheses(sessionId),
        getExperiments(sessionId),
      ]);

      setCurrentSession(overview);
      setHypotheses(hyps);
      setExperiments(exps);

      if (hyps.length > 0) {
        setSelectedHypothesis(hyps[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, [sessionId, setCurrentSession, setLoading, setError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const sortedHypotheses = [...hypotheses].sort((a, b) => b.elo_rating - a.elo_rating);

  const radarData = selectedHypothesis
    ? [
        { subject: 'Novelty', value: selectedHypothesis.novelty_score * 100 },
        { subject: 'Feasibility', value: selectedHypothesis.feasibility_score * 100 },
        { subject: 'Impact', value: selectedHypothesis.impact_score * 100 },
        { subject: 'Evidence', value: (selectedHypothesis.supporting_evidence.length / 5) * 100 },
        { subject: 'Data Ready', value: (selectedHypothesis.data_requirements.length > 0 ? 80 : 20) },
      ]
    : [];

  const eloChartData = sortedHypotheses.slice(0, 10).map((h, i) => ({
    name: `H${i + 1}`,
    elo: h.elo_rating,
    hypothesis: h,
  }));

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleExportMarkdown = () => {
    if (!currentSession) return;

    const markdown = generateMarkdownReport(currentSession, hypotheses, experiments);
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research-report-${sessionId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selectedExperiment = selectedHypothesis
    ? experiments.find((e) => e.hypothesis_id === selectedHypothesis.id)
    : null;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-display font-bold mb-2">Discovery Deck</h1>
            <p className="text-muted-foreground">
              {currentSession?.research_goal?.description || 'Research Results'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleExportMarkdown}>
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: Hypothesis Rankings */}
          <div className="lg:col-span-1">
            <GlassCard className="h-full">
              <div className="p-4 border-b border-white/10">
                <h2 className="font-semibold flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-agent-generation" />
                  Hypothesis Rankings
                </h2>
              </div>
              <ScrollArea className="h-[500px]">
                <div className="p-4 space-y-2">
                  {sortedHypotheses.map((hypothesis, index) => (
                    <motion.button
                      key={hypothesis.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => setSelectedHypothesis(hypothesis)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        selectedHypothesis?.id === hypothesis.id
                          ? 'border-cyan-500 bg-cyan-500/10'
                          : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-purple-500 text-white font-bold text-sm shrink-0">
                          {index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium line-clamp-2">
                            {truncateText(hypothesis.statement, 60)}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="generation" className="text-xs">
                              Elo: {formatEloScore(hypothesis.elo_rating)}
                            </Badge>
                            <Badge variant={hypothesis.status === 'selected' ? 'success' : 'default'} className="text-xs">
                              {hypothesis.status}
                            </Badge>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                      </div>
                    </motion.button>
                  ))}
                </div>
              </ScrollArea>
            </GlassCard>
          </div>

          {/* Center & Right: Details */}
          <div className="lg:col-span-2 space-y-6">
            {selectedHypothesis ? (
              <>
                {/* Hypothesis Detail Card */}
                <GlassCard className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <Badge variant="generation" className="mb-2">
                        <Trophy className="w-3 h-3 mr-1" />
                        Rank #{sortedHypotheses.findIndex((h) => h.id === selectedHypothesis.id) + 1}
                      </Badge>
                      <h2 className="text-xl font-semibold">{selectedHypothesis.statement}</h2>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold text-gradient">
                        {formatEloScore(selectedHypothesis.elo_rating)}
                      </div>
                      <p className="text-sm text-muted-foreground">Elo Rating</p>
                    </div>
                  </div>

                  <p className="text-muted-foreground mb-6">{selectedHypothesis.rationale}</p>

                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Radar Chart */}
                    <div>
                      <h3 className="text-sm font-medium mb-2">Score Distribution</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <RadarChart data={radarData}>
                          <PolarGrid stroke="rgba(255,255,255,0.1)" />
                          <PolarAngleAxis
                            dataKey="subject"
                            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                          />
                          <PolarRadiusAxis
                            angle={30}
                            domain={[0, 100]}
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                          />
                          <Radar
                            dataKey="value"
                            stroke="#06B6D4"
                            fill="#06B6D4"
                            fillOpacity={0.3}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Details */}
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-sm font-medium flex items-center gap-2 mb-2">
                          <Target className="w-4 h-4 text-agent-reflection" />
                          Expected Outcomes
                        </h3>
                        <ul className="text-sm text-muted-foreground space-y-1">
                          {selectedHypothesis.expected_outcomes.map((outcome, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-agent-generation">•</span>
                              {outcome}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <h3 className="text-sm font-medium flex items-center gap-2 mb-2">
                          <TrendingUp className="w-4 h-4 text-agent-ranking" />
                          Data Requirements
                        </h3>
                        <div className="flex flex-wrap gap-1">
                          {selectedHypothesis.data_requirements.map((req, i) => (
                            <Badge key={i} variant="default" className="text-xs">
                              {req}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </GlassCard>

                {/* Elo Distribution Chart */}
                <GlassCard className="p-6">
                  <h3 className="font-semibold mb-4">Elo Score Distribution</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={eloChartData}>
                      <XAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.6)' }} />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.6)' }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(11, 14, 20, 0.9)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '8px',
                        }}
                        labelFormatter={(_, payload) => {
                          if (payload && payload[0]) {
                            return truncateText((payload[0].payload as typeof eloChartData[0]).hypothesis.statement, 50);
                          }
                          return '';
                        }}
                      />
                      <Bar dataKey="elo" radius={[4, 4, 0, 0]}>
                        {eloChartData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={
                              entry.hypothesis.id === selectedHypothesis.id
                                ? '#06B6D4'
                                : 'rgba(6, 182, 212, 0.3)'
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </GlassCard>

                {/* Experiment Design */}
                {selectedExperiment && (
                  <GlassCard className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold flex items-center gap-2">
                        <Beaker className="w-5 h-5 text-agent-experiment" />
                        Experiment Design
                      </h3>
                      <Badge variant={
                        selectedExperiment.estimated_complexity === 'low' ? 'success' :
                        selectedExperiment.estimated_complexity === 'medium' ? 'warning' : 'error'
                      }>
                        {selectedExperiment.estimated_complexity} complexity
                      </Badge>
                    </div>

                    <Tabs defaultValue="methodology">
                      <TabsList>
                        <TabsTrigger value="methodology">Methodology</TabsTrigger>
                        <TabsTrigger value="data">Data Sources</TabsTrigger>
                        {selectedExperiment.code_template && (
                          <TabsTrigger value="code">Code Template</TabsTrigger>
                        )}
                      </TabsList>

                      <TabsContent value="methodology" className="mt-4">
                        <div className="prose prose-invert prose-sm max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {selectedExperiment.methodology}
                          </ReactMarkdown>
                        </div>
                      </TabsContent>

                      <TabsContent value="data" className="mt-4">
                        <div className="space-y-3">
                          {selectedExperiment.data_sources.map((source, i) => (
                            <div key={i} className="p-3 rounded-lg bg-slate-800/50 border border-white/10">
                              <h4 className="font-medium text-sm">{source.name}</h4>
                              <p className="text-xs text-muted-foreground mt-1">{source.description}</p>
                              <div className="flex gap-2 mt-2">
                                <Badge variant="default" className="text-xs">{source.type}</Badge>
                                <Badge variant="generation" className="text-xs">{source.access_method}</Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </TabsContent>

                      {selectedExperiment.code_template && (
                        <TabsContent value="code" className="mt-4">
                          <div className="relative">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="absolute top-2 right-2"
                              onClick={() => handleCopyCode(selectedExperiment.code_template!)}
                            >
                              {copiedCode ? (
                                <Check className="w-4 h-4 text-status-success" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </Button>
                            <pre className="p-4 rounded-lg bg-slate-900 border border-white/10 overflow-x-auto">
                              <code className="text-sm font-mono text-foreground">
                                {selectedExperiment.code_template}
                              </code>
                            </pre>
                          </div>
                        </TabsContent>
                      )}
                    </Tabs>
                  </GlassCard>
                )}
              </>
            ) : (
              <GlassCard className="p-12 text-center">
                <Lightbulb className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h2 className="text-lg font-medium mb-2">No Hypothesis Selected</h2>
                <p className="text-muted-foreground">
                  Select a hypothesis from the rankings to view its details.
                </p>
              </GlassCard>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function generateMarkdownReport(
  session: any,
  hypotheses: Hypothesis[],
  experiments: ExperimentDesign[]
): string {
  const sortedHypotheses = [...hypotheses].sort((a, b) => b.elo_rating - a.elo_rating);

  let markdown = `# Research Report: ${session.research_goal?.description || 'Geospatial Analysis'}\n\n`;
  markdown += `**Generated:** ${new Date().toISOString()}\n\n`;
  markdown += `---\n\n`;

  markdown += `## Executive Summary\n\n`;
  markdown += `This report presents the findings from an AI-assisted research session on geospatial analysis. `;
  markdown += `The system generated and evaluated ${hypotheses.length} hypotheses through multiple iterations of generation, reflection, and ranking.\n\n`;

  markdown += `## Top Hypotheses\n\n`;
  sortedHypotheses.slice(0, 5).forEach((h, i) => {
    markdown += `### ${i + 1}. ${h.statement}\n\n`;
    markdown += `**Elo Rating:** ${Math.round(h.elo_rating)} | `;
    markdown += `**Novelty:** ${Math.round(h.novelty_score * 100)}% | `;
    markdown += `**Feasibility:** ${Math.round(h.feasibility_score * 100)}% | `;
    markdown += `**Impact:** ${Math.round(h.impact_score * 100)}%\n\n`;
    markdown += `${h.rationale}\n\n`;
    markdown += `**Expected Outcomes:**\n`;
    h.expected_outcomes.forEach((o) => {
      markdown += `- ${o}\n`;
    });
    markdown += `\n`;
  });

  if (experiments.length > 0) {
    markdown += `## Experiment Designs\n\n`;
    experiments.forEach((e) => {
      markdown += `### ${e.title}\n\n`;
      markdown += `**Objective:** ${e.objective}\n\n`;
      markdown += `**Complexity:** ${e.estimated_complexity}\n\n`;
      markdown += `**Methodology:**\n${e.methodology}\n\n`;
      if (e.code_template) {
        markdown += `**Code Template:**\n\`\`\`python\n${e.code_template}\n\`\`\`\n\n`;
      }
    });
  }

  return markdown;
}
