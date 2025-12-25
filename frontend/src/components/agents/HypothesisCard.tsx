'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { cn, formatEloScore, getEloScoreColor, truncateText } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Hypothesis } from '@/types';
import { Trophy, TrendingUp, Target, Lightbulb } from 'lucide-react';

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  rank?: number;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

export function HypothesisCard({
  hypothesis,
  rank,
  isSelected,
  onClick,
  className,
}: HypothesisCardProps) {
  const statusVariant = {
    generated: 'default',
    under_review: 'reflection',
    ranked: 'ranking',
    evolved: 'evolution',
    selected: 'success',
    discarded: 'error',
  } as const;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <Card
        className={cn(
          'cursor-pointer transition-all duration-300 hover:border-cyan-500/50',
          isSelected && 'border-cyan-500 shadow-neon-cyan',
          className
        )}
        onClick={onClick}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              {rank && (
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 font-bold text-sm">
                  #{rank}
                </div>
              )}
              <CardTitle className="text-base line-clamp-2">
                {truncateText(hypothesis.statement, 80)}
              </CardTitle>
            </div>
            <Badge variant={statusVariant[hypothesis.status]}>
              {hypothesis.status.replace('_', ' ')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground line-clamp-2">
            {hypothesis.rationale}
          </p>

          <div className="grid grid-cols-2 gap-2">
            <ScoreIndicator
              icon={Trophy}
              label="Elo Rating"
              value={formatEloScore(hypothesis.elo_rating)}
              color={getEloScoreColor(hypothesis.elo_rating)}
            />
            <ScoreIndicator
              icon={Lightbulb}
              label="Novelty"
              value={`${Math.round(hypothesis.novelty_score * 100)}%`}
              color="text-agent-generation"
            />
            <ScoreIndicator
              icon={Target}
              label="Feasibility"
              value={`${Math.round(hypothesis.feasibility_score * 100)}%`}
              color="text-agent-reflection"
            />
            <ScoreIndicator
              icon={TrendingUp}
              label="Impact"
              value={`${Math.round(hypothesis.impact_score * 100)}%`}
              color="text-agent-ranking"
            />
          </div>

          {hypothesis.data_requirements.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {hypothesis.data_requirements.slice(0, 3).map((req, i) => (
                <span
                  key={i}
                  className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400"
                >
                  {truncateText(req, 20)}
                </span>
              ))}
              {hypothesis.data_requirements.length > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{hypothesis.data_requirements.length - 3} more
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ScoreIndicator({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className={cn('h-4 w-4', color)} />
      <span className="text-muted-foreground">{label}:</span>
      <span className={cn('font-medium', color)}>{value}</span>
    </div>
  );
}

export function HypothesisCardSkeleton() {
  return (
    <Card className="animate-pulse">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-700" />
            <div className="h-4 w-48 bg-slate-700 rounded" />
          </div>
          <div className="h-5 w-16 bg-slate-700 rounded-full" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-8 bg-slate-700 rounded" />
        <div className="grid grid-cols-2 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-6 bg-slate-700 rounded" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
