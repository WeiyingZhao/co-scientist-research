import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string): string {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

export function getAgentColor(agentType: string): string {
  const colors: Record<string, string> = {
    generation: '#06B6D4',
    reflection: '#F59E0B',
    ranking: '#8B5CF6',
    proximity: '#EC4899',
    evolution: '#14B8A6',
    supervisor: '#3B82F6',
    'meta-review': '#A855F7',
    experiment: '#22C55E',
    literature: '#EAB308',
  };
  return colors[agentType.toLowerCase()] || '#6B7280';
}

export function getAgentColorClass(agentType: string): string {
  const classes: Record<string, string> = {
    generation: 'text-agent-generation border-agent-generation',
    reflection: 'text-agent-reflection border-agent-reflection',
    ranking: 'text-agent-ranking border-agent-ranking',
    proximity: 'text-agent-proximity border-agent-proximity',
    evolution: 'text-agent-evolution border-agent-evolution',
    supervisor: 'text-agent-supervisor border-agent-supervisor',
    'meta-review': 'text-agent-meta-review border-agent-meta-review',
    experiment: 'text-agent-experiment border-agent-experiment',
    literature: 'text-agent-literature border-agent-literature',
  };
  return classes[agentType.toLowerCase()] || 'text-gray-400 border-gray-400';
}

export function formatEloScore(score: number): string {
  return Math.round(score).toString();
}

export function getEloScoreColor(score: number): string {
  if (score >= 1600) return 'text-status-success';
  if (score >= 1400) return 'text-agent-generation';
  if (score >= 1200) return 'text-agent-reflection';
  return 'text-muted-foreground';
}
