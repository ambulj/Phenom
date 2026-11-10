import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  WrenchRegular,
  ArrowResetRegular,
  CheckmarkCircleRegular,
  FlashRegular,
  WarningRegular,
} from '@fluentui/react-icons';

export interface HealingReportState {
  error_type: string;
  error_message: string;
  file_path: string;
  line_number: number;
  culprit_line: string;
  fault_category: string;
  confidence_score: number;
  recommended_strategy: string;
}

interface SelfHealingKernelHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SelfHealingKernelHUD: React.FC<SelfHealingKernelHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [report, setReport] = useState<HealingReportState>({
    error_type: 'KeyError',
    error_message: "'api_timeout'",
    file_path: 'services/backend/cache.py',
    line_number: 18,
    culprit_line: "val = config['api_timeout']",
    fault_category: 'MISSING_DICTIONARY_KEY',
    confidence_score: 0.95,
    recommended_strategy: 'Convert direct dict index access to dict.get(key, default).',
  });

  const [activeDiff, setActiveDiff] = useState<string>(
    `--- a/services/backend/cache.py\n+++ b/services/backend/cache.py\n@@ -16,4 +16,4 @@\n def lookup_cache(config):\n-    val = config['api_timeout']\n+    val = config.get('api_timeout', None)\n     return val`
  );

  const [patchApplied, setPatchApplied] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'healing.diagnostic_update' && externalEvent.payload) {
      if (externalEvent.payload.report) setReport(externalEvent.payload.report);
      if (externalEvent.payload.unified_diff) setActiveDiff(externalEvent.payload.unified_diff);
      setPatchApplied(false);
    }
  }, [externalEvent]);

  const handleSimulateError = (errorType: string) => {
    setPatchApplied(false);
    if (errorType === 'AttributeError') {
      setReport({
        error_type: 'AttributeError',
        error_message: "'NoneType' object has no attribute 'profile'",
        file_path: 'services/backend/api.py',
        line_number: 42,
        culprit_line: 'return user.profile',
        fault_category: 'NULL_OR_NONE_DEREFERENCE',
        confidence_score: 0.96,
        recommended_strategy: 'Insert None guard or fallback default before member access.',
      });
      setActiveDiff(
        `--- a/services/backend/api.py\n+++ b/services/backend/api.py\n@@ -40,4 +40,4 @@\n def get_user_data(user):\n-    return user.profile\n+    return (user.profile if user is not None else None)`
      );
      setFeedback('Simulated AttributeError: NoneType dereference localized.');
    } else if (errorType === 'ZeroDivisionError') {
      setReport({
        error_type: 'ZeroDivisionError',
        error_message: 'division by zero',
        file_path: 'services/backend/metrics.py',
        line_number: 29,
        culprit_line: 'return total_score / count',
        fault_category: 'DIVISION_BY_ZERO',
        confidence_score: 0.98,
        recommended_strategy: 'Insert divisor non-zero guard or ternary check before division.',
      });
      setActiveDiff(
        `--- a/services/backend/metrics.py\n+++ b/services/backend/metrics.py\n@@ -27,4 +27,4 @@\n def calculate_average(total_score, count):\n-    return total_score / count\n+    return (total_score / count if count != 0 else 0)`
      );
      setFeedback('Simulated ZeroDivisionError: Divisor non-zero guard synthesized.');
    } else {
      setReport({
        error_type: 'KeyError',
        error_message: "'api_timeout'",
        file_path: 'services/backend/cache.py',
        line_number: 18,
        culprit_line: "val = config['api_timeout']",
        fault_category: 'MISSING_DICTIONARY_KEY',
        confidence_score: 0.95,
        recommended_strategy: 'Convert direct dict index access to dict.get(key, default).',
      });
      setActiveDiff(
        `--- a/services/backend/cache.py\n+++ b/services/backend/cache.py\n@@ -16,4 +16,4 @@\n def lookup_cache(config):\n-    val = config['api_timeout']\n+    val = config.get('api_timeout', None)\n     return val`
      );
      setFeedback('Simulated KeyError: Dict fallback get() synthesized.');
    }

    if (sendMessage) {
      sendMessage({
        type: 'healing.simulate_error',
        payload: { error_type: errorType },
      });
    }
  };

  const handleApplyPatch = () => {
    setPatchApplied(true);
    setFeedback(`Applied AST healing patch to ${report.file_path}. Snapshot recorded.`);
    if (sendMessage) {
      sendMessage({
        type: 'healing.apply_patch',
        payload: { file_path: report.file_path, fault_category: report.fault_category },
      });
    }
  };

  const handleRollback = () => {
    setPatchApplied(false);
    setFeedback(`Rolled back patch on ${report.file_path} to pre-mutation snapshot (Rule 7).`);
    if (sendMessage) {
      sendMessage({
        type: 'healing.rollback_patch',
        payload: { file_path: report.file_path },
      });
    }
  };

  return (
    <div
      style={{
        width: '820px',
        maxHeight: '85vh',
        background: 'rgba(14, 18, 30, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: '14px',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 240, 255, 0.2)',
        color: '#E0E6ED',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 1000,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          background: 'linear-gradient(90deg, rgba(0, 240, 255, 0.08), rgba(255, 60, 100, 0.04))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <WrenchRegular style={{ fontSize: '24px', color: '#00F0FF' }} />
          <div>
            <div
              style={{
                fontSize: '15px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: '#FFFFFF',
                textTransform: 'uppercase',
              }}
            >
              AUTONOMOUS SELF-HEALING KERNEL
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.55)' }}>
              Neuro-Symbolic Traceback Diagnostic & AST Patch Synthesizer (HEAL-01)
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8A99AD',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Main Body */}
      <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* Simulation Controls */}
        <div
          style={{
            background: 'rgba(18, 24, 38, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '14px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: '#8A99AD', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            SIMULATE FAULT SCENARIO:
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['KeyError', 'AttributeError', 'ZeroDivisionError'].map((err) => (
              <button
                key={err}
                onClick={() => handleSimulateError(err)}
                style={{
                  background: report.error_type === err ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${report.error_type === err ? '#00F0FF' : 'rgba(255, 255, 255, 0.15)'}`,
                  color: report.error_type === err ? '#00F0FF' : '#E0E6ED',
                  borderRadius: '6px',
                  padding: '5px 12px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.2s',
                }}
              >
                {err}
              </button>
            ))}
          </div>
        </div>

        {/* Diagnostic Report Card */}
        <div
          style={{
            background: 'rgba(20, 26, 42, 0.8)',
            border: '1px solid rgba(255, 60, 100, 0.3)',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <WarningRegular style={{ color: '#FF3C64', fontSize: '18px' }} />
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF' }}>
                {report.error_type}: {report.error_message}
              </span>
            </div>
            <span
              style={{
                background: 'rgba(0, 240, 255, 0.15)',
                color: '#00F0FF',
                fontSize: '10px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                border: '1px solid rgba(0, 240, 255, 0.3)',
              }}
            >
              {report.fault_category} ({(report.confidence_score * 100).toFixed(0)}% MATCH)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '11px' }}>
            <div>
              <span style={{ color: '#8A99AD' }}>Target File: </span>
              <span style={{ color: '#FFFFFF', fontFamily: 'monospace' }}>
                {report.file_path}:{report.line_number}
              </span>
            </div>
            <div>
              <span style={{ color: '#8A99AD' }}>Culprit Expression: </span>
              <span style={{ color: '#FF7B90', fontFamily: 'monospace' }}>{report.culprit_line}</span>
            </div>
          </div>

          <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)' }}>
            <span style={{ color: '#00F0FF', fontWeight: 600 }}>Recommended Strategy: </span>
            {report.recommended_strategy}
          </div>
        </div>

        {/* Unified Diff Preview */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6', marginBottom: '8px' }}>
            SYNTHESIZED AST REPAIR PATCH (UNIFIED DIFF)
          </div>
          <pre
            style={{
              background: 'rgba(8, 12, 20, 0.85)',
              border: '1px solid rgba(0, 240, 255, 0.2)',
              borderRadius: '8px',
              padding: '14px',
              fontSize: '11px',
              fontFamily: 'monospace',
              lineHeight: '1.5',
              overflowX: 'auto',
              color: '#C0D0E0',
            }}
          >
            {activeDiff.split('\n').map((line, idx) => {
              const isDel = line.startsWith('-');
              const isAdd = line.startsWith('+');
              const isHeader = line.startsWith('@@');
              return (
                <div
                  key={idx}
                  style={{
                    color: isDel ? '#FF4A6E' : isAdd ? '#00FF88' : isHeader ? '#00F0FF' : '#A0B2C6',
                    background: isDel ? 'rgba(255, 74, 110, 0.1)' : isAdd ? 'rgba(0, 255, 136, 0.1)' : 'transparent',
                    padding: '1px 4px',
                    borderRadius: '2px',
                  }}
                >
                  {line}
                </div>
              );
            })}
          </pre>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleApplyPatch}
            disabled={patchApplied}
            style={{
              background: patchApplied ? 'rgba(0, 255, 136, 0.2)' : 'rgba(0, 240, 255, 0.2)',
              border: `1px solid ${patchApplied ? '#00FF88' : '#00F0FF'}`,
              color: patchApplied ? '#00FF88' : '#00F0FF',
              borderRadius: '8px',
              padding: '10px 20px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: patchApplied ? 'default' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <FlashRegular /> {patchApplied ? 'Patch Applied' : 'Apply Healing Patch (Tier 1)'}
          </button>

          <button
            onClick={handleRollback}
            disabled={!patchApplied}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: patchApplied ? '#FFFFFF' : '#6A788A',
              borderRadius: '8px',
              padding: '10px 18px',
              fontSize: '12px',
              cursor: patchApplied ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowResetRegular /> Rollback Snapshot (Rule 7)
          </button>
        </div>

        {/* Feedback alert */}
        {feedback && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(0, 240, 255, 0.1)',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              fontSize: '11px',
              color: '#00F0FF',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <CheckmarkCircleRegular /> {feedback}
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 20px',
          borderTop: '1px solid rgba(0, 240, 255, 0.15)',
          background: 'rgba(8, 12, 20, 0.6)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: '#8A99AD',
        }}
      >
        <span>Rule 7 Non-Destructive Snapshot History | Rule 8 Payment Shield Active</span>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#FFFFFF',
            borderRadius: '6px',
            padding: '6px 14px',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Close HUD
        </button>
      </div>
    </div>
  );
};
