import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PlayRegular,
  ClockRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface DAGNodeHUD {
  id: string;
  name: string;
  role: string;
  wave: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  x: number;
  y: number;
  duration_ms?: number;
}

export interface SwarmOrchestratorHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SwarmOrchestratorHUD: React.FC<SwarmOrchestratorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [goal, setGoal] = useState<string>('Refactor billing engine with atomic worktrees & offline RAG');
  const [currentWave, setCurrentWave] = useState<number>(1);
  const [totalWaves] = useState<number>(3);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  const [nodes, setNodes] = useState<DAGNodeHUD[]>([
    { id: 'node_research', name: 'Research Patterns', role: 'researcher', wave: 0, status: 'completed', x: 80, y: 120, duration_ms: 24.5 },
    { id: 'node_ast_map', name: 'Map AST Symbols', role: 'synthesizer', wave: 0, status: 'completed', x: 80, y: 260, duration_ms: 18.2 },
    { id: 'node_implement', name: 'Synthesize Patch', role: 'coder', wave: 1, status: 'running', x: 300, y: 190, duration_ms: 45.0 },
    { id: 'node_test', name: 'Diagnostic Tests', role: 'tester', wave: 2, status: 'pending', x: 520, y: 120 },
    { id: 'node_review', name: 'Rule 8 Safety Review', role: 'reviewer', wave: 2, status: 'pending', x: 520, y: 260 }
  ]);

  const [workers] = useState<Array<{ id: string; role: string; status: string }>>([
    { id: 'worker_1', role: 'coder', status: 'running' },
    { id: 'worker_2', role: 'tester', status: 'idle' },
    { id: 'worker_3', role: 'reviewer', status: 'idle' },
    { id: 'worker_4', role: 'synthesizer', status: 'idle' }
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'swarm.dag_update' && externalEvent.payload) {
      if (externalEvent.payload.goal) setGoal(externalEvent.payload.goal);
      if (externalEvent.payload.current_wave !== undefined) setCurrentWave(externalEvent.payload.current_wave);
      if (externalEvent.payload.nodes) setNodes(externalEvent.payload.nodes);
    }
  }, [externalEvent]);

  const handleExecuteWave = () => {
    setIsExecuting(true);
    if (sendMessage) {
      sendMessage({
        type: 'swarm.execute_wave',
        payload: { wave_index: currentWave }
      });
    }

    setTimeout(() => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.wave === currentWave) return { ...n, status: 'completed', duration_ms: 32.4 };
          if (n.wave === currentWave + 1) return { ...n, status: 'running' };
          return n;
        })
      );
      setCurrentWave((prev) => Math.min(totalWaves, prev + 1));
      setIsExecuting(false);
    }, 1200);
  };

  const getNodeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'running':
        return '#00f3ff';
      case 'failed':
        return '#ef4444';
      default:
        return '#64748b';
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(8, 12, 22, 0.95)',
        border: '1px solid rgba(0, 243, 255, 0.4)',
        borderRadius: 14,
        boxShadow: '0 8px 36px rgba(0, 0, 0, 0.75), 0 0 20px rgba(0, 243, 255, 0.2)',
        backdropFilter: 'blur(28px)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        overflow: 'hidden'
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(0, 0, 0, 0.3)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SparkleRegular style={{ fontSize: 20, color: '#00f3ff' }} />
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '0.04em', color: '#f8fafc' }}>
            SWARM TASK GRAPH (DAG) ORCHESTRATOR
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(0, 243, 255, 0.15)',
              color: '#00f3ff',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              fontWeight: 600
            }}
          >
            SWM-01
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              padding: '2px 8px',
              borderRadius: 4,
              border: '1px solid rgba(56, 189, 248, 0.25)'
            }}
          >
            <ClockRegular style={{ fontSize: 13 }} />
            <span>Wave {currentWave} of {totalWaves}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleExecuteWave}
            disabled={isExecuting || currentWave > totalWaves}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: '#0284c7',
              border: 'none',
              color: '#ffffff',
              borderRadius: 6,
              padding: '5px 12px',
              fontSize: 12,
              cursor: isExecuting ? 'not-allowed' : 'pointer',
              fontWeight: 600
            }}
          >
            <PlayRegular style={{ fontSize: 14 }} />
            <span>{isExecuting ? 'Dispatching...' : 'Execute Wave'}</span>
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 4,
              borderRadius: 6
            }}
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        </div>
      </div>

      {/* Goal Banner */}
      <div style={{ padding: '8px 18px', backgroundColor: 'rgba(0, 0, 0, 0.4)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: '#64748b' }}>Active Objective:</span>
        <span style={{ fontSize: 12, color: '#38bdf8', fontFamily: 'monospace' }}>{goal}</span>
      </div>

      {/* Main Grid: SVG Canvas + Workers Inspector */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* SVG DAG Visualizer */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
          <svg style={{ width: '100%', height: '100%' }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(0, 243, 255, 0.5)" />
              </marker>
            </defs>

            {/* Directed Edges */}
            <line x1="80" y1="120" x2="300" y2="190" stroke="rgba(0, 243, 255, 0.4)" strokeWidth="2" markerEnd="url(#arrow)" />
            <line x1="80" y1="260" x2="300" y2="190" stroke="rgba(0, 243, 255, 0.4)" strokeWidth="2" markerEnd="url(#arrow)" />
            <line x1="300" y1="190" x2="520" y2="120" stroke="rgba(0, 243, 255, 0.4)" strokeWidth="2" markerEnd="url(#arrow)" />
            <line x1="300" y1="190" x2="520" y2="260" stroke="rgba(0, 243, 255, 0.4)" strokeWidth="2" markerEnd="url(#arrow)" />

            {/* Nodes */}
            {nodes.map((n) => {
              const color = getNodeColor(n.status);
              return (
                <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
                  <circle
                    r="22"
                    fill="rgba(8, 12, 22, 0.9)"
                    stroke={color}
                    strokeWidth="3"
                    style={{ filter: n.status === 'running' ? 'drop-shadow(0 0 8px #00f3ff)' : 'none' }}
                  />
                  <text textAnchor="middle" dy="4" fill="#f8fafc" fontSize="10" fontWeight="bold">
                    W{n.wave}
                  </text>
                  <text textAnchor="middle" dy="36" fill="#e2e8f0" fontSize="11" fontWeight="500">
                    {n.name}
                  </text>
                  <text textAnchor="middle" dy="48" fill="#64748b" fontSize="9" fontFamily="monospace">
                    [{n.role.toUpperCase()}]
                  </text>
                  {n.duration_ms && (
                    <text textAnchor="middle" dy="60" fill="#10b981" fontSize="9">
                      {n.duration_ms}ms
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Right Column: Ephemeral Subagent Pool */}
        <div style={{ width: 280, borderLeft: '1px solid rgba(255, 255, 255, 0.08)', backgroundColor: 'rgba(0, 0, 0, 0.3)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>
            EPHEMERAL WORKER POOL ({workers.length})
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {workers.map((w) => (
              <div
                key={w.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  marginBottom: 8,
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${w.status === 'running' ? '#00f3ff' : 'rgba(255, 255, 255, 0.06)'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9' }}>{w.id}</span>
                  <span
                    style={{
                      fontSize: 10,
                      color: w.status === 'running' ? '#00f3ff' : '#64748b',
                      fontWeight: 600
                    }}
                  >
                    {w.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 4 }}>
                  Role: {w.role}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
