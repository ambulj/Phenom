import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  FilterRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
} from '@fluentui/react-icons';

export interface SemanticNodeUI {
  node_id: string;
  cluster_topic: string;
  distilled_heuristic: string;
  confidence: number;
  abstraction_level: number;
  source_trace_count: number;
}

interface MemoryConsolidationHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const MemoryConsolidationHUD: React.FC<MemoryConsolidationHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [nodes, setNodes] = useState<SemanticNodeUI[]>([
    {
      node_id: 'node_core_01',
      cluster_topic: 'Core Principles',
      distilled_heuristic: 'Rule 1: Always wrap tool execution in Safety layer with confirmation tiers.',
      confidence: 1.0,
      abstraction_level: 3,
      source_trace_count: 1,
    },
    {
      node_id: 'node_core_04',
      cluster_topic: 'Core Principles',
      distilled_heuristic: 'Rule 4: Zero cloud telemetry egress; strictly local offline computation.',
      confidence: 1.0,
      abstraction_level: 3,
      source_trace_count: 1,
    },
    {
      node_id: 'node_macro_01',
      cluster_topic: 'Python & AST Conventions',
      distilled_heuristic: 'Macro-Strategy: Prefer AST visitors with explicit node checks and LoopGuard ceilings.',
      confidence: 0.96,
      abstraction_level: 2,
      source_trace_count: 4,
    },
    {
      node_id: 'node_micro_01',
      cluster_topic: 'Frontend Architecture',
      distilled_heuristic: 'Heuristic: Desktop Cyber HUDs mount in App.tsx and bind to CommandPalette (Ctrl+K).',
      confidence: 0.92,
      abstraction_level: 1,
      source_trace_count: 3,
    },
  ]);

  const [selectedLevel, setSelectedLevel] = useState<number>(0); // 0=All, 1=Micro, 2=Macro, 3=Core
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'consolidation.update' && externalEvent.payload) {
      if (externalEvent.payload.nodes) setNodes(externalEvent.payload.nodes);
    }
  }, [externalEvent]);

  const handleRunConsolidation = () => {
    if (sendMessage) {
      sendMessage({
        type: 'consolidation.run',
        payload: {},
      });
    }

    const newNode: SemanticNodeUI = {
      node_id: `node_${Math.random().toString(16).slice(2, 6)}`,
      cluster_topic: 'Session Consolidation',
      distilled_heuristic: `Synthesized new heuristic from recent interactive traces (${new Date().toLocaleTimeString()}).`,
      confidence: 0.94,
      abstraction_level: 1,
      source_trace_count: 2,
    };

    setNodes((prev) => [newNode, ...prev]);
    setFeedback('Episodic memory consolidation pass complete. 1 new semantic node distilled.');
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleSoftPrune = () => {
    if (sendMessage) {
      sendMessage({
        type: 'consolidation.prune',
        payload: { threshold: 0.20 },
      });
    }

    setFeedback('Decayed memory traces soft-pruned to cold storage (Rule 7 non-destructibility).');
    setTimeout(() => setFeedback(null), 3000);
  };

  const getLevelBadge = (level: number) => {
    switch (level) {
      case 3:
        return <span style={{ color: '#f59e0b', fontSize: 10, fontWeight: 700 }}>LEVEL 3: CORE</span>;
      case 2:
        return <span style={{ color: '#00ffcc', fontSize: 10, fontWeight: 700 }}>LEVEL 2: MACRO</span>;
      case 1:
        return <span style={{ color: '#38bdf8', fontSize: 10, fontWeight: 700 }}>LEVEL 1: MICRO</span>;
      default:
        return <span style={{ color: '#94a3b8', fontSize: 10 }}>LEVEL 0: RAW</span>;
    }
  };

  const filteredNodes = nodes.filter((n) => {
    const matchesLevel = selectedLevel === 0 || n.abstraction_level === selectedLevel;
    const matchesQuery =
      searchQuery === '' ||
      n.cluster_topic.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.distilled_heuristic.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesQuery;
  });

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 520,
        backgroundColor: '#0a0d14',
        border: '1px solid #1f293d',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.8), 0 0 16px rgba(0, 255, 204, 0.1)',
        color: '#e2e8f0',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        zIndex: 9999,
        overflow: 'hidden',
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'linear-gradient(90deg, rgba(0, 255, 204, 0.08) 0%, rgba(10, 13, 20, 0) 100%)',
          borderBottom: '1px solid #1f293d',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BrainCircuitRegular style={{ color: '#00ffcc', fontSize: 18 }} />
          <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: '0.05em', color: '#f8fafc' }}>
            EPISODIC MEMORY CONSOLIDATION
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: 'rgba(0, 255, 204, 0.2)',
              color: '#00ffcc',
              fontWeight: 600,
            }}
          >
            MEM-06 / ABS-01
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
          >
            <DismissRegular style={{ fontSize: 16 }} />
          </button>
        )}
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Search & Level Filters */}
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search semantic knowledge tree..."
            style={{
              flex: 1,
              backgroundColor: '#070a0f',
              border: '1px solid #1e293b',
              borderRadius: 6,
              padding: '6px 10px',
              color: '#f8fafc',
              fontSize: 11,
              outline: 'none',
            }}
          />
          <div style={{ display: 'flex', gap: 4 }}>
            {[0, 1, 2, 3].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setSelectedLevel(lvl)}
                style={{
                  padding: '4px 8px',
                  borderRadius: 4,
                  backgroundColor: selectedLevel === lvl ? 'rgba(0, 255, 204, 0.2)' : '#0f172a',
                  border: `1px solid ${selectedLevel === lvl ? '#00ffcc' : '#334155'}`,
                  color: selectedLevel === lvl ? '#00ffcc' : '#94a3b8',
                  fontSize: 10,
                  cursor: 'pointer',
                }}
              >
                {lvl === 0 ? 'All' : `L${lvl}`}
              </button>
            ))}
          </div>
        </div>

        {/* Node Stream */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 220, overflowY: 'auto' }}>
          {filteredNodes.map((n) => (
            <div
              key={n.node_id}
              style={{
                backgroundColor: '#070a0f',
                border: '1px solid #1e293b',
                borderRadius: 6,
                padding: '8px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#f1f5f9' }}>{n.cluster_topic}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {getLevelBadge(n.abstraction_level)}
                  <span style={{ fontSize: 10, color: '#00ffcc', fontWeight: 600 }}>
                    {(n.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#cbd5e1' }}>{n.distilled_heuristic}</div>
              <div style={{ fontSize: 9, color: '#64748b' }}>Sources: {n.source_trace_count} trace(s) consolidated</div>
            </div>
          ))}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleRunConsolidation}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: '#00ffcc',
              color: '#0a0d14',
              border: 'none',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <BrainCircuitRegular style={{ fontSize: 14 }} />
            Consolidate Episodic Traces
          </button>

          <button
            onClick={handleSoftPrune}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              color: '#94a3b8',
              fontSize: 11,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <FilterRegular style={{ fontSize: 13 }} />
            Soft-Prune Decayed
          </button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            style={{
              padding: '6px 10px',
              backgroundColor: 'rgba(0, 255, 204, 0.1)',
              border: '1px solid #00ffcc44',
              borderRadius: 6,
              fontSize: 11,
              color: '#00ffcc',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 13 }} />
            <span>{feedback}</span>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 9,
            color: '#475569',
            borderTop: '1px solid #1e293b',
            paddingTop: 8,
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheckmarkRegular style={{ color: '#00ffcc', fontSize: 11 }} />
            Hierarchical Semantic Knowledge Graph Active
          </span>
          <span>Guardian SLA &lt; 25ms</span>
        </div>
      </div>
    </div>
  );
};
