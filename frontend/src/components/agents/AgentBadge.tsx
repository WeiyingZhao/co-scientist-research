'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import type { AgentType } from '@/types';
import {
  Brain,
  Sparkles,
  Search,
  Scale,
  GitBranch,
  Zap,
  FileSearch,
  Beaker,
  BookOpen,
} from 'lucide-react';

interface AgentBadgeProps {
  agentType: AgentType;
  status?: 'idle' | 'active' | 'completed' | 'error';
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const agentConfig: Record<
  AgentType,
  { icon: React.ComponentType<{ className?: string }>; label: string; color: string }
> = {
  supervisor: {
    icon: Brain,
    label: 'Supervisor',
    color: 'agent-supervisor',
  },
  generation: {
    icon: Sparkles,
    label: 'Generation',
    color: 'agent-generation',
  },
  reflection: {
    icon: Search,
    label: 'Reflection',
    color: 'agent-reflection',
  },
  ranking: {
    icon: Scale,
    label: 'Ranking',
    color: 'agent-ranking',
  },
  proximity: {
    icon: GitBranch,
    label: 'Proximity',
    color: 'agent-proximity',
  },
  evolution: {
    icon: Zap,
    label: 'Evolution',
    color: 'agent-evolution',
  },
  'meta-review': {
    icon: FileSearch,
    label: 'Meta Review',
    color: 'agent-meta-review',
  },
  experiment: {
    icon: Beaker,
    label: 'Experiment',
    color: 'agent-experiment',
  },
  literature: {
    icon: BookOpen,
    label: 'Literature',
    color: 'agent-literature',
  },
};

const sizeClasses = {
  sm: 'h-6 text-xs gap-1 px-2',
  md: 'h-8 text-sm gap-1.5 px-3',
  lg: 'h-10 text-base gap-2 px-4',
};

const iconSizes = {
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

export function AgentBadge({
  agentType,
  status = 'idle',
  showLabel = true,
  size = 'md',
  className,
}: AgentBadgeProps) {
  const config = agentConfig[agentType];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full font-medium transition-all duration-300',
        `border border-${config.color}/50 bg-${config.color}/10 text-${config.color}`,
        status === 'active' && 'animate-pulse shadow-lg',
        status === 'completed' && 'opacity-70',
        status === 'error' && 'border-status-error/50 bg-status-error/10 text-status-error',
        sizeClasses[size],
        className
      )}
      style={{
        borderColor: `var(--tw-${config.color}, currentColor)`,
      }}
    >
      <Icon className={cn(iconSizes[size], status === 'active' && 'animate-spin')} />
      {showLabel && <span>{config.label}</span>}
      {status === 'active' && (
        <span className="relative flex h-2 w-2">
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              `bg-${config.color}`
            )}
          />
          <span
            className={cn(
              'relative inline-flex rounded-full h-2 w-2',
              `bg-${config.color}`
            )}
          />
        </span>
      )}
    </div>
  );
}

export function StatusDot({
  status,
  className,
}: {
  status: 'idle' | 'active' | 'completed' | 'error' | 'pending';
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-block w-2 h-2 rounded-full',
        status === 'idle' && 'bg-slate-500',
        status === 'active' && 'bg-agent-generation animate-pulse shadow-neon-cyan',
        status === 'completed' && 'bg-status-success shadow-neon-emerald',
        status === 'error' && 'bg-status-error',
        status === 'pending' && 'bg-slate-600',
        className
      )}
    />
  );
}
