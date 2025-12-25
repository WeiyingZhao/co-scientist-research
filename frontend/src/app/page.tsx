'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, GlassCard } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { useResearchStore } from '@/store';
import { startResearch } from '@/lib/api';
import { Rocket, Settings2, ChevronDown, ChevronUp, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import type { ResearchSession } from '@/types';

const domains = [
  'Urban Heat Islands',
  'Land Cover Classification',
  'Agricultural Monitoring',
  'Water Quality',
  'Air Quality',
  'Climate Change',
  'Disaster Response',
  'Biodiversity',
  'Custom',
];

const models = [
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'claude-3-opus', label: 'Claude 3 Opus' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
];

// Mock recent sessions for demonstration
const mockRecentSessions: Partial<ResearchSession>[] = [
  {
    session_id: '1',
    research_goal: {
      description: 'Detecting urban heat islands in Mumbai using Sentinel-2 imagery',
      domain: 'Urban Heat Islands',
      constraints: [],
      priority_areas: [],
    },
    status: 'completed',
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    session_id: '2',
    research_goal: {
      description: 'Agricultural yield prediction using multi-temporal NDVI analysis',
      domain: 'Agricultural Monitoring',
      constraints: [],
      priority_areas: [],
    },
    status: 'completed',
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
  {
    session_id: '3',
    research_goal: {
      description: 'Mapping coral reef health using hyperspectral satellite data',
      domain: 'Biodiversity',
      constraints: [],
      priority_areas: [],
    },
    status: 'error',
    created_at: new Date(Date.now() - 259200000).toISOString(),
  },
];

export default function LaunchpadPage() {
  const router = useRouter();
  const { setCurrentSession, setLoading, isLoading, setError } = useResearchStore();

  const [researchGoal, setResearchGoal] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [domain, setDomain] = useState('Custom');
  const [maxIterations, setMaxIterations] = useState([3]);
  const [model, setModel] = useState('gpt-4');

  const handleLaunch = async () => {
    if (!researchGoal.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await startResearch({
        research_goal: researchGoal,
        domain: domain !== 'Custom' ? domain : undefined,
        max_iterations: maxIterations[0],
        model,
      });

      // Navigate to mission control with the session ID
      router.push(`/mission?session=${response.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start research');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-status-success" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-status-error" />;
      default:
        return <Clock className="w-4 h-4 text-status-warning" />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl mx-auto text-center mb-12"
        >
          <h1 className="font-display text-4xl md:text-5xl font-bold mb-4 text-gradient">
            Geospatial AI Co-Scientist
          </h1>
          <p className="text-lg text-muted-foreground mb-8">
            Accelerate your research with AI-powered hypothesis generation,
            literature analysis, and experiment design for geospatial analysis.
          </p>
        </motion.div>

        {/* Research Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="max-w-3xl mx-auto mb-8"
        >
          <GlassCard className="p-6">
            <div className="space-y-4">
              <Textarea
                placeholder="Enter your research goal... (e.g., 'Detecting urban heat islands in Mumbai using Sentinel-2')"
                value={researchGoal}
                onChange={(e) => setResearchGoal(e.target.value)}
                className="min-h-[120px] text-lg"
              />

              {/* Configuration Toggle */}
              <button
                onClick={() => setShowConfig(!showConfig)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Settings2 className="w-4 h-4" />
                <span>Advanced Configuration</span>
                {showConfig ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {/* Configuration Panel */}
              {showConfig && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="grid gap-4 md:grid-cols-3 pt-4 border-t border-white/10"
                >
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Domain</label>
                    <Select value={domain} onValueChange={setDomain}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {domains.map((d) => (
                          <SelectItem key={d} value={d}>
                            {d}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Max Iterations: {maxIterations[0]}
                    </label>
                    <Slider
                      value={maxIterations}
                      onValueChange={setMaxIterations}
                      min={1}
                      max={10}
                      step={1}
                      className="mt-4"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Model</label>
                    <Select value={model} onValueChange={setModel}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {models.map((m) => (
                          <SelectItem key={m.value} value={m.value}>
                            {m.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </motion.div>
              )}

              {/* Launch Button */}
              <Button
                variant="neon"
                size="lg"
                className="w-full gap-2"
                onClick={handleLaunch}
                disabled={!researchGoal.trim() || isLoading}
              >
                <Rocket className="w-5 h-5" />
                {isLoading ? 'Launching Mission...' : 'Launch Research Mission'}
              </Button>
            </div>
          </GlassCard>
        </motion.div>

        {/* Recent Missions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="max-w-5xl mx-auto"
        >
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-muted-foreground" />
            Recent Missions
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {mockRecentSessions.map((session) => (
              <Card
                key={session.session_id}
                className="cursor-pointer hover:border-cyan-500/50 transition-all"
                onClick={() => router.push(`/discovery?session=${session.session_id}`)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <Badge variant={session.status === 'completed' ? 'success' : session.status === 'error' ? 'error' : 'warning'}>
                      {session.status}
                    </Badge>
                    {getStatusIcon(session.status as string)}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm font-medium line-clamp-2 mb-2">
                    {session.research_goal?.description}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="default" className="text-xs">
                      {session.research_goal?.domain}
                    </Badge>
                    <span>
                      {new Date(session.created_at!).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
