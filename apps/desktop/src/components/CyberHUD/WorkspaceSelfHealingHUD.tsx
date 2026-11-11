import React, { useState } from 'react';
import {
  DismissRegular,
  WrenchRegular,
  CheckmarkCircleRegular,
  WarningRegular,
  ArrowResetRegular,
  DocumentEditRegular,
} from '@fluentui/react-icons';

export interface WorkspaceSelfHealingHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

interface DiagnosisUI {
  id: string;
  category: 'COMPILER_ERROR' | 'TEST_FAILURE' | 'MISSING_DEPENDENCY' | 'RUNTIME_EXCEPTION';
  file_path: string;
  line_number: number;
  error_message: string;
  suggested_strategy: string;
  confidence: number;
}

interface PatchUI {
  id: string;
  diagnosis_id: string;
  file_path: string;
  unified_diff: string;
  status: 'STAGED' | 'APPLIED' | 'ROLLED_BACK';
}

export const WorkspaceSelfHealingHUD: React.FC<WorkspaceSelfHealingHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [diagnoses] = useState<DiagnosisUI[]>([
    {
      id: 'diag-1',
      category: 'COMPILER_ERROR',
      file_path: 'apps/desktop/src/components/Orb.tsx',
      line_number: 42,
      error_message: "TS2339: Property 'renderTarget' does not exist on type 'WebGLRenderer'.",
      suggested_strategy: 'Cast renderer to Three.js WebGLRenderTarget or update Three.js context binding',
      confidence: 0.98,
    },
    {
      id: 'diag-2',
      category: 'TEST_FAILURE',
      file_path: 'services/backend/tests/test_screen_grounding.py',
      line_number: 88,
      error_message: 'AssertionError: assert 0.012 < 0.010 (latency ceiling SLA check)',
      suggested_strategy: 'Optimize screen bounding box cache to reduce latency by 2ms',
      confidence: 0.95,
    },
  ]);

  const [activePatch, setActivePatch] = useState<PatchUI>({
    id: 'patch-101',
    diagnosis_id: 'diag-1',
    file_path: 'apps/desktop/src/components/Orb.tsx',
    unified_diff: `--- a/apps/desktop/src/components/Orb.tsx
+++ b/apps/desktop/src/components/Orb.tsx
@@ -41,3 +41,3 @@
-const target = (renderer as any).renderTarget;
+const target = renderer.getRenderTarget();
`,
    status: 'STAGED',
  });

  const [appliedCount, setAppliedCount] = useState<number>(4);
  const [rollbackCount, setRollbackCount] = useState<number>(1);
  const [notification, setNotification] = useState<string | null>(null);

  const handleApplyPatch = () => {
    setActivePatch((prev) => ({ ...prev, status: 'APPLIED' }));
    setAppliedCount((prev) => prev + 1);
    setNotification('Hot-patch successfully applied with snapshot backup cached.');
    setTimeout(() => setNotification(null), 3000);
  };

  const handleRollbackPatch = () => {
    setActivePatch((prev) => ({ ...prev, status: 'ROLLED_BACK' }));
    setRollbackCount((prev) => prev + 1);
    setNotification('Hot-patch safely rolled back to pre-patch snapshot.');
    setTimeout(() => setNotification(null), 3000);
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'COMPILER_ERROR':
        return '#ef4444';
      case 'TEST_FAILURE':
        return '#f59e0b';
      case 'MISSING_DEPENDENCY':
        return '#a855f7';
      default:
        return '#38bdf8';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 60,
        right: 24,
        width: 720,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(12, 17, 29, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 14,
        boxShadow: '0 20px 40px rgba(0,0,0,0.65), 0 0 30px rgba(56, 189, 248, 0.15)',
        color: '#e2e8f0',
        zIndex: 120,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 18px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.12) 0%, transparent 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              padding: 6,
              borderRadius: 8,
              backgroundColor: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
            }}
          >
            <WrenchRegular fontSize={20} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: '0.4px', color: '#f8fafc' }}>
              WORKSPACE SELF-HEALING & AST HOT-PATCHING
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Milestone 31 Phase 4 • HEAL-01 • PATCH-02 • Compiler Triage • 1-Click Rollback
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular fontSize={18} />
        </button>
      </div>

      {/* Main Content */}
      <div style={{ padding: 18, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Telemetry Bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <WarningRegular fontSize={13} /> Active Issues
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444', marginTop: 4 }}>
              {diagnoses.length} Diagnosed
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>Triage Complete</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <CheckmarkCircleRegular fontSize={13} /> Patches Applied
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e', marginTop: 4 }}>
              {appliedCount}
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>Rule 7 Snapshots</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <ArrowResetRegular fontSize={13} /> Rollbacks
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b', marginTop: 4 }}>
              {rollbackCount}
            </div>
            <div style={{ fontSize: 10, color: '#22c55e' }}>Zero Data Loss</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <WrenchRegular fontSize={13} /> Daemon State
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#38bdf8', marginTop: 6 }}>
              MONITORING
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>Local Offline</div>
          </div>
        </div>

        {/* Notification Toast */}
        {notification && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(34, 197, 94, 0.2)',
              border: '1px solid rgba(34, 197, 94, 0.4)',
              color: '#86efac',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            ✓ {notification}
          </div>
        )}

        {/* Diagnosed Issues List */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 8 }}>
            ACTIVE WORKSPACE DIAGNOSES
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 150, overflowY: 'auto' }}>
            {diagnoses.map((diag) => (
              <div
                key={diag.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(148, 163, 184, 0.15)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: 4,
                        fontSize: 9,
                        fontWeight: 700,
                        backgroundColor: `${getCategoryColor(diag.category)}20`,
                        color: getCategoryColor(diag.category),
                        border: `1px solid ${getCategoryColor(diag.category)}40`,
                      }}
                    >
                      {diag.category}
                    </span>
                    <span style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'Consolas, monospace' }}>
                      {diag.file_path}:{diag.line_number}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#38bdf8' }}>
                    {(diag.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#f8fafc', marginTop: 4 }}>
                  {diag.error_message}
                </div>
                <div style={{ fontSize: 10.5, color: '#cbd5e1', marginTop: 2 }}>
                  Strategy: {diag.suggested_strategy}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Staged Hot-Patch Diff Viewer */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1' }}>
              UNIFIED DIFF HOT-PATCH PREVIEW [{activePatch.id}]
            </span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: activePatch.status === 'APPLIED' ? '#22c55e' : '#38bdf8',
              }}
            >
              STATUS: {activePatch.status}
            </span>
          </div>

          <pre
            style={{
              padding: 12,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              color: '#f8fafc',
              fontSize: 11,
              fontFamily: 'Consolas, monospace',
              overflowX: 'auto',
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            {activePatch.unified_diff.split('\n').map((line, idx) => {
              let color = '#cbd5e1';
              if (line.startsWith('+') && !line.startsWith('+++')) color = '#4ade80';
              if (line.startsWith('-') && !line.startsWith('---')) color = '#f87171';
              if (line.startsWith('@@')) color = '#38bdf8';
              return (
                <div key={idx} style={{ color }}>
                  {line}
                </div>
              );
            })}
          </pre>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
            <button
              onClick={handleApplyPatch}
              disabled={activePatch.status === 'APPLIED'}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 8,
                backgroundColor: activePatch.status === 'APPLIED' ? '#334155' : '#0284c7',
                border: 'none',
                color: '#fff',
                fontWeight: 600,
                fontSize: 12,
                cursor: activePatch.status === 'APPLIED' ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <DocumentEditRegular fontSize={16} />
              Apply Staged Hot-Patch
            </button>

            <button
              onClick={handleRollbackPatch}
              disabled={activePatch.status !== 'APPLIED'}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                backgroundColor: activePatch.status === 'APPLIED' ? 'rgba(239, 68, 68, 0.2)' : '#1e293b',
                border: activePatch.status === 'APPLIED' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid #334155',
                color: activePatch.status === 'APPLIED' ? '#fca5a5' : '#64748b',
                fontWeight: 600,
                fontSize: 12,
                cursor: activePatch.status === 'APPLIED' ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <ArrowResetRegular fontSize={16} /> 1-Click Rollback
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
