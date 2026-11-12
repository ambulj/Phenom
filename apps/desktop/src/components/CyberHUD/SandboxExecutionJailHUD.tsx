import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  PlayRegular,
  CheckmarkCircleRegular,
  WarningRegular,
  ErrorCircleRegular,
} from '@fluentui/react-icons';

export interface SandboxVerdictState {
  is_safe: boolean;
  risk_level: 'SAFE' | 'LOW' | 'HIGH' | 'CRITICAL';
  disallowed_imports: string[];
  dangerous_calls: string[];
  jail_escape_vectors: string[];
  details: string;
}

interface SandboxExecutionJailHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SandboxExecutionJailHUD: React.FC<SandboxExecutionJailHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [sourceCode, setSourceCode] = useState<string>(
    "numbers = [10, 20, 30, 40, 50]\ntotal = sum(numbers)\nprint('Total array sum:', total)\nresult = total * 2"
  );

  const [verdict, setVerdict] = useState<SandboxVerdictState>({
    is_safe: true,
    risk_level: 'SAFE',
    disallowed_imports: [],
    dangerous_calls: [],
    jail_escape_vectors: [],
    details: 'Code tree passed AST security inspection with zero violations.',
  });

  const [executionOutput, setExecutionOutput] = useState<{
    status: string;
    stdout: string;
    stderr: string;
    returnValue: string | null;
    durationMs: number;
  }>({
    status: 'SUCCESS',
    stdout: 'Total array sum: 150\n',
    stderr: '',
    returnValue: '300',
    durationMs: 1.42,
  });

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'sandbox.execution_update' && externalEvent.payload) {
      if (externalEvent.payload.verdict) setVerdict(externalEvent.payload.verdict);
      if (externalEvent.payload.output) setExecutionOutput(externalEvent.payload.output);
    }
  }, [externalEvent]);

  const handleSelectPreset = (presetType: string) => {
    if (presetType === 'os_blocked') {
      const code = "import os\nos.system('echo compromised')";
      setSourceCode(code);
      setVerdict({
        is_safe: false,
        risk_level: 'HIGH',
        disallowed_imports: ['os'],
        dangerous_calls: ['system'],
        jail_escape_vectors: [],
        details: "Security violations detected: imports=['os'], calls=['system']",
      });
      setExecutionOutput({
        status: 'SECURITY_VIOLATION',
        stdout: '',
        stderr: "Security violations detected: imports=['os'], calls=['system']",
        returnValue: null,
        durationMs: 0.85,
      });
      setFeedback('Preset: Blocked unauthorized module import (os.system).');
    } else if (presetType === 'escape_blocked') {
      const code = 'classes = ().__class__.__bases__[0].__subclasses__()\nprint(classes)';
      setSourceCode(code);
      setVerdict({
        is_safe: false,
        risk_level: 'CRITICAL',
        disallowed_imports: [],
        dangerous_calls: [],
        jail_escape_vectors: ['__class__', '__bases__', '__subclasses__'],
        details: 'Critical jail escape vector detected: prototype dunder manipulation.',
      });
      setExecutionOutput({
        status: 'SECURITY_VIOLATION',
        stdout: '',
        stderr: 'Critical jail escape vector blocked by AST security visitor.',
        returnValue: null,
        durationMs: 0.64,
      });
      setFeedback('Preset: Blocked AST jail escape attempt.');
    } else if (presetType === 'loop_timeout') {
      const code = 'while True:\n    pass\n';
      setSourceCode(code);
      setVerdict({
        is_safe: true,
        risk_level: 'SAFE',
        disallowed_imports: [],
        dangerous_calls: [],
        jail_escape_vectors: [],
        details: 'Code tree syntactically valid.',
      });
      setExecutionOutput({
        status: 'TIMEOUT',
        stdout: '',
        stderr: 'Execution timed out after 2.0s (step limit exceeded).',
        returnValue: null,
        durationMs: 2000.1,
      });
      setFeedback('Preset: Enforced AST execution timeout (2.0s limit).');
    } else {
      const code =
        "numbers = [10, 20, 30, 40, 50]\ntotal = sum(numbers)\nprint('Total array sum:', total)\nresult = total * 2";
      setSourceCode(code);
      setVerdict({
        is_safe: true,
        risk_level: 'SAFE',
        disallowed_imports: [],
        dangerous_calls: [],
        jail_escape_vectors: [],
        details: 'Code tree passed AST security inspection with zero violations.',
      });
      setExecutionOutput({
        status: 'SUCCESS',
        stdout: 'Total array sum: 150\n',
        stderr: '',
        returnValue: '300',
        durationMs: 1.42,
      });
      setFeedback('Preset: Loaded safe numerical array processing.');
    }

    if (sendMessage) {
      sendMessage({
        type: 'sandbox.select_preset',
        payload: { preset: presetType },
      });
    }
  };

  const handleExecute = () => {
    if (!verdict.is_safe) {
      setFeedback('Execution blocked by AST security visitor gates.');
      return;
    }
    setFeedback('Code executed successfully inside isolated micro-sandbox jail.');
    if (sendMessage) {
      sendMessage({
        type: 'sandbox.execute_code',
        payload: { source_code: sourceCode },
      });
    }
  };

  return (
    <div
      style={{
        width: '840px',
        maxHeight: '85vh',
        background: 'rgba(12, 16, 28, 0.94)',
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
          background: 'linear-gradient(90deg, rgba(0, 240, 255, 0.08), rgba(0, 255, 136, 0.04))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheckmarkRegular style={{ fontSize: '24px', color: '#00F0FF' }} />
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
              DYNAMIC MICRO-SANDBOX & AST JAIL
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.55)' }}>
              Capability-Gated Ephemeral Code Execution Environment (SEC-04, ENV-02)
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
        {/* Preset Selector */}
        <div
          style={{
            background: 'rgba(18, 24, 38, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '12px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '11px', color: '#8A99AD', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            TEST SCENARIOS:
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {[
              { id: 'safe_math', label: 'Numerical (Safe)' },
              { id: 'os_blocked', label: 'Syscall (Blocked)' },
              { id: 'escape_blocked', label: 'Dunder Escape (Blocked)' },
              { id: 'loop_timeout', label: 'Infinite Loop (Timeout)' },
            ].map((p) => (
              <button
                key={p.id}
                onClick={() => handleSelectPreset(p.id)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#E0E6ED',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.2s',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Source Code Area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6' }}>UNTRUSTED PYTHON CODE SNIPPET</div>
          <textarea
            value={sourceCode}
            onChange={(e) => setSourceCode(e.target.value)}
            rows={5}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: 'rgba(8, 12, 20, 0.85)',
              border: `1px solid ${verdict.is_safe ? 'rgba(0, 240, 255, 0.3)' : 'rgba(255, 60, 100, 0.5)'}`,
              borderRadius: '8px',
              padding: '12px',
              color: '#FFFFFF',
              fontFamily: 'monospace',
              fontSize: '12px',
              lineHeight: '1.4',
              outline: 'none',
              resize: 'vertical',
            }}
          />
        </div>

        {/* AST Security Verdict Card */}
        <div
          style={{
            background:
              verdict.risk_level === 'SAFE'
                ? 'rgba(0, 255, 136, 0.08)'
                : verdict.risk_level === 'CRITICAL'
                ? 'rgba(255, 60, 100, 0.12)'
                : 'rgba(255, 200, 0, 0.1)',
            border: `1px solid ${
              verdict.risk_level === 'SAFE'
                ? 'rgba(0, 255, 136, 0.3)'
                : verdict.risk_level === 'CRITICAL'
                ? 'rgba(255, 60, 100, 0.4)'
                : 'rgba(255, 200, 0, 0.4)'
            }`,
            borderRadius: '10px',
            padding: '14px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {verdict.risk_level === 'SAFE' ? (
              <CheckmarkCircleRegular style={{ color: '#00FF88', fontSize: '20px' }} />
            ) : verdict.risk_level === 'CRITICAL' ? (
              <ErrorCircleRegular style={{ color: '#FF3C64', fontSize: '20px' }} />
            ) : (
              <WarningRegular style={{ color: '#FFC800', fontSize: '20px' }} />
            )}
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF' }}>
                AST SECURITY STATUS: {verdict.risk_level}
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)' }}>{verdict.details}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            {verdict.disallowed_imports.map((mod, i) => (
              <span
                key={i}
                style={{
                  background: 'rgba(255, 60, 100, 0.2)',
                  color: '#FF6488',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  fontFamily: 'monospace',
                }}
              >
                disallowed: {mod}
              </span>
            ))}
          </div>
        </div>

        {/* Execution Output Console */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6' }}>SANDBOX CONSOLE OUTPUT</span>
            <div style={{ fontSize: '11px', color: '#8A99AD' }}>
              Status: <span style={{ color: executionOutput.status === 'SUCCESS' ? '#00FF88' : '#FF3C64' }}>{executionOutput.status}</span> |
              Duration: <span style={{ color: '#00F0FF' }}>{executionOutput.durationMs}ms</span>
            </div>
          </div>

          <div
            style={{
              background: 'rgba(6, 10, 16, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '12px',
              minHeight: '80px',
              fontFamily: 'monospace',
              fontSize: '11px',
              color: '#00FF88',
              lineHeight: '1.4',
              whiteSpace: 'pre-wrap',
            }}
          >
            {executionOutput.stdout && <div>{executionOutput.stdout}</div>}
            {executionOutput.returnValue && (
              <div style={{ color: '#00F0FF', marginTop: '4px' }}>
                ➜ Return Value: {executionOutput.returnValue}
              </div>
            )}
            {executionOutput.stderr && (
              <div style={{ color: '#FF4A6E', marginTop: '4px' }}>{executionOutput.stderr}</div>
            )}
            {!executionOutput.stdout && !executionOutput.stderr && (
              <span style={{ color: 'rgba(255, 255, 255, 0.3)' }}>[Terminal empty]</span>
            )}
          </div>
        </div>

        {/* Capability Gates Telemetry */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '8px',
            fontSize: '10px',
            fontFamily: 'monospace',
          }}
        >
          <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(0, 240, 255, 0.15)', textAlign: 'center' }}>
            <span style={{ color: '#00FF88' }}>● </span>NO FILESYSTEM
          </div>
          <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(0, 240, 255, 0.15)', textAlign: 'center' }}>
            <span style={{ color: '#00FF88' }}>● </span>NO SOCKETS
          </div>
          <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(0, 240, 255, 0.15)', textAlign: 'center' }}>
            <span style={{ color: '#00FF88' }}>● </span>NO SUBPROCESS
          </div>
          <div style={{ background: 'rgba(0, 240, 255, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(0, 240, 255, 0.15)', textAlign: 'center' }}>
            <span style={{ color: '#00FF88' }}>● </span>RULE 8 SHIELD
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleExecute}
            style={{
              background: 'rgba(0, 240, 255, 0.2)',
              border: '1px solid #00F0FF',
              color: '#00F0FF',
              borderRadius: '8px',
              padding: '10px 20px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <PlayRegular /> Execute In Micro-Sandbox Jail (Tier 1)
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
        <span>Restricted Builtins Whitelist | 2.0s Execution Timeout Enforcement</span>
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
