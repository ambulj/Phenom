import React, { useState } from 'react';
import {
  DismissRegular,
  WrenchRegular,
  ShieldCheckmarkRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ArrowUploadRegular,
  DeleteRegular,
  CodeRegular,
} from '@fluentui/react-icons';

export interface ToolFoundryHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

interface SyntheticToolUI {
  id: string;
  name: string;
  description: string;
  tier: number;
  status: 'SYNTHESIZED' | 'AST_PASSED' | 'TESTS_PASSED' | 'REGISTERED' | 'REJECTED' | 'UNLOADED';
  security_findings: string[];
  test_elapsed_ms?: number;
  scanned_nodes?: number;
}

export const ToolFoundryHUD: React.FC<ToolFoundryHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [tools, setTools] = useState<SyntheticToolUI[]>([
    {
      id: 'tool-001',
      name: 'synth_compute_word_stats',
      description: 'Calculates word count, sentence count, and character density for text.',
      tier: 0,
      status: 'REGISTERED',
      security_findings: [],
      test_elapsed_ms: 1.2,
      scanned_nodes: 42,
    },
    {
      id: 'tool-002',
      name: 'synth_reverse_text_tokens',
      description: 'Reverses string tokens while preserving punctuation boundaries.',
      tier: 0,
      status: 'REGISTERED',
      security_findings: [],
      test_elapsed_ms: 0.8,
      scanned_nodes: 35,
    },
    {
      id: 'tool-003',
      name: 'synth_csv_column_aggregator',
      description: 'Aggregates numerical columns from local CSV tables without disk mutation.',
      tier: 0,
      status: 'TESTS_PASSED',
      security_findings: [],
      test_elapsed_ms: 2.1,
      scanned_nodes: 58,
    },
    {
      id: 'tool-004',
      name: 'synth_untrusted_network_probe',
      description: 'Rejected: Attempted to import forbidden socket module.',
      tier: 1,
      status: 'REJECTED',
      security_findings: ["Forbidden import 'socket' detected", "Rule 4 local offline violation"],
      scanned_nodes: 18,
    },
  ]);

  const [selectedToolId, setSelectedToolId] = useState<string>('tool-003');

  const selectedTool = tools.find((t) => t.id === selectedToolId) || tools[0];

  const handleHotLoad = (id: string) => {
    setTools((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: 'REGISTERED' as const } : t))
    );
  };

  const handleUnload = (id: string) => {
    setTools((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: 'UNLOADED' as const } : t))
    );
  };

  const registeredCount = tools.filter((t) => t.status === 'REGISTERED').length;
  const verifiedCount = tools.filter((t) => t.status === 'TESTS_PASSED' || t.status === 'REGISTERED').length;
  const rejectedCount = tools.filter((t) => t.status === 'REJECTED').length;

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        left: '20px',
        width: '560px',
        maxHeight: '85vh',
        background: 'rgba(10, 15, 29, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(168, 85, 247, 0.25)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 24px rgba(168, 85, 247, 0.15)',
        color: '#e2e8f0',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(168, 85, 247, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <WrenchRegular style={{ fontSize: '20px', color: '#c084fc' }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px', letterSpacing: '0.5px' }}>
              Dynamic Tool Foundry HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              TOOL-01 / SAND-02 Autonomous Capability Engine
            </div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
            }}
          >
            <DismissRegular style={{ fontSize: '18px' }} />
          </button>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Metric Cards Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          <div
            style={{
              background: 'rgba(168, 85, 247, 0.08)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: '8px',
              padding: '10px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#c084fc' }}>{tools.length}</div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Synthesized</div>
          </div>
          <div
            style={{
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: '8px',
              padding: '10px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981' }}>{verifiedCount}</div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Verified</div>
          </div>
          <div
            style={{
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: '8px',
              padding: '10px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#38bdf8' }}>{registeredCount}</div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Registered</div>
          </div>
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '8px',
              padding: '10px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#ef4444' }}>{rejectedCount}</div>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Rejected</div>
          </div>
        </div>

        {/* Tools Inventory List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Synthesized Micro-Tools
          </div>

          {tools.map((t) => (
            <div
              key={t.id}
              onClick={() => setSelectedToolId(t.id)}
              style={{
                background:
                  selectedToolId === t.id
                    ? 'rgba(168, 85, 247, 0.12)'
                    : 'rgba(255, 255, 255, 0.02)',
                border:
                  selectedToolId === t.id
                    ? '1px solid #c084fc'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '10px 12px',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CodeRegular style={{ color: t.status === 'REJECTED' ? '#ef4444' : '#c084fc' }} />
                  <span style={{ fontWeight: 600, fontSize: '13px' }}>{t.name}</span>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '1px 5px',
                      borderRadius: '4px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      color: '#94a3b8',
                    }}
                  >
                    Tier {t.tier}
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                  {t.description}
                </div>
              </div>

              <div>
                {t.status === 'REGISTERED' && (
                  <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                    <CheckmarkCircleRegular /> Active
                  </span>
                )}
                {t.status === 'TESTS_PASSED' && (
                  <span style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                    <ShieldCheckmarkRegular /> Verified
                  </span>
                )}
                {t.status === 'REJECTED' && (
                  <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
                    <DismissCircleRegular /> Rejected
                  </span>
                )}
                {t.status === 'UNLOADED' && (
                  <span style={{ color: '#f59e0b', fontSize: '11px' }}>Unloaded</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Selected Tool Details & AST Security Card */}
        {selectedTool && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, fontSize: '13px', color: '#c084fc' }}>
                AST Security & Sandbox Verification
              </span>
              {selectedTool.scanned_nodes && (
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                  {selectedTool.scanned_nodes} AST nodes analyzed
                </span>
              )}
            </div>

            {selectedTool.security_findings.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
                {selectedTool.security_findings.map((f, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: '11px',
                      color: '#ef4444',
                      background: 'rgba(239, 68, 68, 0.1)',
                      padding: '4px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    ⚠ {f}
                  </div>
                ))}
              </div>
            ) : (
              <div
                style={{
                  fontSize: '11px',
                  color: '#10b981',
                  background: 'rgba(16, 185, 129, 0.1)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  marginBottom: '8px',
                }}
              >
                ✓ Zero forbidden imports, zero eval/exec, Rule 8 & 11 clean
              </div>
            )}

            {/* Test Execution info */}
            {selectedTool.test_elapsed_ms && (
              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px' }}>
                Sandbox execution completed in <strong style={{ color: '#38bdf8' }}>{selectedTool.test_elapsed_ms}ms</strong>
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              {selectedTool.status !== 'REGISTERED' && selectedTool.status !== 'REJECTED' && (
                <button
                  onClick={() => handleHotLoad(selectedTool.id)}
                  style={{
                    background: '#a855f7',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                  }}
                >
                  <ArrowUploadRegular /> Hot-Load into Registry
                </button>
              )}
              {selectedTool.status === 'REGISTERED' && (
                <button
                  onClick={() => handleUnload(selectedTool.id)}
                  style={{
                    background: 'rgba(239, 68, 68, 0.15)',
                    color: '#ef4444',
                    border: '1px solid #ef4444',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                  }}
                >
                  <DeleteRegular /> Unload Tool
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
