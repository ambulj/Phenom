import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  CloudSyncRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  TimerRegular,
  SendRegular,
  TableRegular,
} from '@fluentui/react-icons';

export interface StateRegisterEntryUI {
  key: string;
  value: any;
  author: string;
  timestamp: number;
  vector_clock: Record<string, number>;
}

interface SwarmConsensusCRDTHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SwarmConsensusCRDTHUD: React.FC<SwarmConsensusCRDTHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [vectorClocks, setVectorClocks] = useState<Record<string, Record<string, number>>>({
    agent_codearchitect: { agent_codearchitect: 4, agent_securityauditor: 2 },
    agent_securityauditor: { agent_securityauditor: 3, agent_codearchitect: 4 },
    agent_testorchestrator: { agent_testorchestrator: 2 },
    agent_knowledgeresearcher: { agent_knowledgeresearcher: 1 },
  });

  const [stateEntries, setStateEntries] = useState<StateRegisterEntryUI[]>([
    {
      key: 'mesh_consensus_protocol',
      value: 'CRDT_LWW_VECTOR_CLOCKS',
      author: 'system',
      timestamp: Date.now() - 3600000,
      vector_clock: { system: 1 },
    },
    {
      key: 'active_compiler',
      value: 'Vite + TSC Strict',
      author: 'agent_codearchitect',
      timestamp: Date.now() - 1200000,
      vector_clock: { agent_codearchitect: 4 },
    },
    {
      key: 'test_coverage_threshold',
      value: '100% Pass Invariant',
      author: 'agent_testorchestrator',
      timestamp: Date.now() - 600000,
      vector_clock: { agent_testorchestrator: 2 },
    },
  ]);

  const [propAgent, setPropAgent] = useState<string>('agent_codearchitect');
  const [propKey, setPropKey] = useState<string>('target_runtime');
  const [propValue, setPropValue] = useState<string>('Python 3.11.9 CUDA 12.8');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'crdt.update' && externalEvent.payload) {
      if (externalEvent.payload.clocks) setVectorClocks(externalEvent.payload.clocks);
      if (externalEvent.payload.entries) setStateEntries(externalEvent.payload.entries);
    }
  }, [externalEvent]);

  const handleProposeDelta = () => {
    const updatedClocks = { ...vectorClocks };
    const currAgentClock = { ...(updatedClocks[propAgent] || {}) };
    currAgentClock[propAgent] = (currAgentClock[propAgent] || 0) + 1;
    updatedClocks[propAgent] = currAgentClock;
    setVectorClocks(updatedClocks);

    const now = Date.now();
    const existingIdx = stateEntries.findIndex((e) => e.key === propKey);
    const newEntry: StateRegisterEntryUI = {
      key: propKey,
      value: propValue,
      author: propAgent,
      timestamp: now,
      vector_clock: currAgentClock,
    };

    if (existingIdx >= 0) {
      const updatedEntries = [...stateEntries];
      updatedEntries[existingIdx] = newEntry;
      setStateEntries(updatedEntries);
    } else {
      setStateEntries([...stateEntries, newEntry]);
    }

    if (sendMessage) {
      sendMessage({
        type: 'crdt.propose_delta',
        payload: {
          agent_id: propAgent,
          key: propKey,
          value: propValue,
        },
      });
    }

    setFeedback(`Applied LWW CRDT delta: [${propKey}] -> '${propValue}' (Author: ${propAgent})`);
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 40,
        right: 40,
        width: 680,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(10, 18, 28, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'Segoe UI, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 240, 255, 0.05)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CloudSyncRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              DISTRIBUTED STATE CONSENSUS & CRDT REGISTER
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 27-03 • Lamport Vector Clocks • Last-Write-Wins Reconciliation
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: 18 }} />
        </button>
      </div>

      {feedback && (
        <div
          style={{
            padding: '8px 18px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderBottom: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckmarkCircleRegular style={{ fontSize: 16 }} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Content scroll area */}
      <div style={{ padding: 18, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Lamport Vector Clocks Grid */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <TimerRegular style={{ fontSize: 14 }} />
            LAMPORT VECTOR CLOCKS (CAUSALITY ORDERING)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            {Object.entries(vectorClocks).map(([aid, clock]) => (
              <div
                key={aid}
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(0, 240, 255, 0.15)',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>{aid}</div>
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                    Clocks: {Object.entries(clock).map(([k, v]) => `${k.replace('agent_', '')}:${v}`).join(', ')}
                  </div>
                </div>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#00f0ff',
                    backgroundColor: 'rgba(0, 240, 255, 0.1)',
                    padding: '2px 8px',
                    borderRadius: 4,
                  }}
                >
                  Tick {clock[aid] || 1}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Converged State Matrix */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <TableRegular style={{ fontSize: 14 }} />
            CONVERGED STATE REGISTERS ({stateEntries.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {stateEntries.map((entry) => (
              <div
                key={entry.key}
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>
                    <span style={{ color: '#00f0ff' }}>[{entry.key}]</span> ={' '}
                    <span style={{ color: '#a78bfa' }}>"{String(entry.value)}"</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                    Author: {entry.author} • Updated: {new Date(entry.timestamp).toLocaleTimeString()}
                  </div>
                </div>

                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 10,
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                  }}
                >
                  CONVERGED
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Propose Delta Form */}
        <div
          style={{
            padding: 12,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(0, 240, 255, 0.15)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', display: 'flex', alignItems: 'center', gap: 6 }}>
            <SendRegular style={{ fontSize: 14 }} />
            PROPOSE CRDT STATE DELTA (LAST-WRITE-WINS)
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1.5fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Author Agent</label>
              <select
                value={propAgent}
                onChange={(e) => setPropAgent(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              >
                {Object.keys(vectorClocks).map((aid) => (
                  <option key={aid} value={aid} style={{ background: '#0f172a' }}>
                    {aid}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Register Key</label>
              <input
                type="text"
                value={propKey}
                onChange={(e) => setPropKey(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Proposed Value</label>
              <input
                type="text"
                value={propValue}
                onChange={(e) => setPropValue(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              />
            </div>
          </div>

          <button
            onClick={handleProposeDelta}
            style={{
              padding: '8px 14px',
              backgroundColor: '#00f0ff',
              border: 'none',
              borderRadius: 4,
              color: '#000',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <SendRegular style={{ fontSize: 14 }} />
            Propose & Merge CRDT Delta
          </button>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 18px',
          borderTop: '1px solid rgba(0, 240, 255, 0.2)',
          fontSize: 11,
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 240, 255, 0.02)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldCheckmarkRegular style={{ color: '#00f0ff' }} />
          Conflict-Free Deterministic Convergence (Rule 7 Reversible)
        </span>
        <span>Lamport Clocks Active</span>
      </div>
    </div>
  );
};
