import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default:
          'border border-white/20 bg-white/5 text-foreground',
        generation:
          'border border-agent-generation/50 bg-agent-generation/10 text-agent-generation',
        reflection:
          'border border-agent-reflection/50 bg-agent-reflection/10 text-agent-reflection',
        ranking:
          'border border-agent-ranking/50 bg-agent-ranking/10 text-agent-ranking',
        proximity:
          'border border-agent-proximity/50 bg-agent-proximity/10 text-agent-proximity',
        evolution:
          'border border-agent-evolution/50 bg-agent-evolution/10 text-agent-evolution',
        supervisor:
          'border border-agent-supervisor/50 bg-agent-supervisor/10 text-agent-supervisor',
        'meta-review':
          'border border-agent-meta-review/50 bg-agent-meta-review/10 text-agent-meta-review',
        experiment:
          'border border-agent-experiment/50 bg-agent-experiment/10 text-agent-experiment',
        literature:
          'border border-agent-literature/50 bg-agent-literature/10 text-agent-literature',
        success:
          'border border-status-success/50 bg-status-success/10 text-status-success',
        warning:
          'border border-status-warning/50 bg-status-warning/10 text-status-warning',
        error:
          'border border-status-error/50 bg-status-error/10 text-status-error',
        info:
          'border border-status-info/50 bg-status-info/10 text-status-info',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
