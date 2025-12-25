'use client';

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn, formatDate } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AgentBadge } from '@/components/agents/AgentBadge';
import type { AgentMessage } from '@/types';
import { ChevronDown, ChevronRight, MessageSquare, Zap, CheckCircle, AlertTriangle } from 'lucide-react';

interface MessageStreamProps {
  messages: AgentMessage[];
  className?: string;
}

export function MessageStream({ messages, className }: MessageStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <ScrollArea className={cn('h-full', className)} ref={scrollRef}>
      <div className="space-y-3 p-4">
        <AnimatePresence mode="popLayout">
          {messages.map((message) => (
            <MessageItem key={message.id} message={message} />
          ))}
        </AnimatePresence>
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <MessageSquare className="w-8 h-8 mb-2 opacity-50" />
            <p>Agent activity will appear here</p>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}

function MessageItem({ message }: { message: AgentMessage }) {
  const [isExpanded, setIsExpanded] = React.useState(message.message_type !== 'thought');

  const typeConfig = {
    thought: {
      icon: MessageSquare,
      color: 'text-slate-400',
      bgColor: 'bg-slate-800/30',
    },
    action: {
      icon: Zap,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    result: {
      icon: CheckCircle,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
    },
    decision: {
      icon: AlertTriangle,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
    },
  };

  const config = typeConfig[message.message_type];
  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={cn(
        'rounded-lg border border-white/5 overflow-hidden',
        config.bgColor
      )}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-white/5 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
        )}
        <AgentBadge agentType={message.agent_type} size="sm" showLabel={false} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Icon className={cn('w-4 h-4', config.color)} />
            <span className="text-sm font-medium truncate">
              {message.message_type.charAt(0).toUpperCase() + message.message_type.slice(1)}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatDate(message.timestamp)}
            </span>
          </div>
        </div>
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-0">
              <p className="text-sm text-foreground/80 whitespace-pre-wrap">
                {message.content}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
