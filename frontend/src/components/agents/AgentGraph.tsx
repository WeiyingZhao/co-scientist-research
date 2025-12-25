'use client';

import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Position,
  Handle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { cn, getAgentColor } from '@/lib/utils';
import { AgentBadge } from './AgentBadge';
import type { AgentType } from '@/types';
import { useResearchStore } from '@/store';

interface AgentNodeData extends Record<string, unknown> {
  agentType: AgentType;
  label: string;
  description: string;
}

const AgentNodeComponent = ({ data }: { data: AgentNodeData }) => {
  const agentStatuses = useResearchStore((state) => state.agentStatuses);
  const status = agentStatuses[data.agentType] || 'idle';
  const color = getAgentColor(data.agentType);

  return (
    <div
      className={cn(
        'glass-card p-4 min-w-[160px] transition-all duration-300',
        status === 'active' && 'border-2 animate-pulse',
        status === 'completed' && 'opacity-80'
      )}
      style={{
        borderColor: status === 'active' ? color : undefined,
        boxShadow: status === 'active' ? `0 0 20px ${color}40` : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-white/20 !w-3 !h-3 !border-2 !border-white/40"
      />
      <div className="flex flex-col items-center gap-2">
        <AgentBadge agentType={data.agentType} status={status} size="sm" />
        <p className="text-xs text-center text-muted-foreground max-w-[140px]">
          {data.description}
        </p>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-white/20 !w-3 !h-3 !border-2 !border-white/40"
      />
    </div>
  );
};

const nodeTypes = {
  agentNode: AgentNodeComponent,
};

const initialNodes: Node<AgentNodeData>[] = [
  {
    id: 'supervisor',
    type: 'agentNode',
    position: { x: 250, y: 0 },
    data: { agentType: 'supervisor', label: 'Supervisor', description: 'Orchestrates workflow' },
  },
  {
    id: 'generation',
    type: 'agentNode',
    position: { x: 50, y: 120 },
    data: { agentType: 'generation', label: 'Generation', description: 'Creates hypotheses' },
  },
  {
    id: 'literature',
    type: 'agentNode',
    position: { x: 450, y: 120 },
    data: { agentType: 'literature', label: 'Literature', description: 'Searches papers' },
  },
  {
    id: 'reflection',
    type: 'agentNode',
    position: { x: 50, y: 240 },
    data: { agentType: 'reflection', label: 'Reflection', description: 'Reviews quality' },
  },
  {
    id: 'ranking',
    type: 'agentNode',
    position: { x: 250, y: 240 },
    data: { agentType: 'ranking', label: 'Ranking', description: 'Compares & ranks' },
  },
  {
    id: 'proximity',
    type: 'agentNode',
    position: { x: 450, y: 240 },
    data: { agentType: 'proximity', label: 'Proximity', description: 'Clusters similar' },
  },
  {
    id: 'evolution',
    type: 'agentNode',
    position: { x: 150, y: 360 },
    data: { agentType: 'evolution', label: 'Evolution', description: 'Refines top ideas' },
  },
  {
    id: 'experiment',
    type: 'agentNode',
    position: { x: 350, y: 360 },
    data: { agentType: 'experiment', label: 'Experiment', description: 'Designs tests' },
  },
  {
    id: 'meta-review',
    type: 'agentNode',
    position: { x: 250, y: 480 },
    data: { agentType: 'meta-review', label: 'Meta Review', description: 'Final synthesis' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e-sup-gen', source: 'supervisor', target: 'generation', animated: true },
  { id: 'e-sup-lit', source: 'supervisor', target: 'literature', animated: true },
  { id: 'e-gen-ref', source: 'generation', target: 'reflection' },
  { id: 'e-ref-rank', source: 'reflection', target: 'ranking' },
  { id: 'e-lit-prox', source: 'literature', target: 'proximity' },
  { id: 'e-rank-evo', source: 'ranking', target: 'evolution' },
  { id: 'e-prox-evo', source: 'proximity', target: 'evolution' },
  { id: 'e-evo-exp', source: 'evolution', target: 'experiment' },
  { id: 'e-exp-meta', source: 'experiment', target: 'meta-review' },
  { id: 'e-evo-meta', source: 'evolution', target: 'meta-review' },
];

export function AgentGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const activeAgent = useResearchStore((state) => state.activeAgent);

  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      const isActive = activeAgent && (edge.source === activeAgent || edge.target === activeAgent);
      return {
        ...edge,
        style: {
          stroke: isActive ? '#06B6D4' : 'rgba(255, 255, 255, 0.2)',
          strokeWidth: isActive ? 2 : 1,
        },
        animated: isActive ? true : undefined,
      };
    });
  }, [edges, activeAgent]);

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-white/10">
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(255, 255, 255, 0.05)"
        />
        <Controls className="!bg-slate-900/80 !border-white/10 !rounded-lg [&>button]:!bg-slate-800 [&>button]:!border-white/10 [&>button:hover]:!bg-slate-700" />
        <MiniMap
          className="!bg-slate-900/80 !border-white/10 !rounded-lg"
          nodeColor={(node) => getAgentColor((node.data as AgentNodeData).agentType)}
          maskColor="rgba(11, 14, 20, 0.8)"
        />
      </ReactFlow>
    </div>
  );
}
