import React, { useState } from 'react';
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  FilterRegular,
  EyeOffRegular,
  ChatRegular,
  SparkleRegular,
  FlashRegular,
  ArrowCounterclockwiseRegular,
} from '@fluentui/react-icons';

interface ToolMetadataUI {
  tool_name: string;
  arguments: Record<string, any>;
  result?: Record<string, any>;
  timestamp: string;
}

interface ExecutionStreamShieldHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const ExecutionStreamShieldHUD: React.FC<ExecutionStreamShieldHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [personaMode, setPersonaMode] = useState<string>('ADAPTIVE_AUTO');
  const [leaksBlocked, setLeaksBlocked] = useState<number>(42);
  const [charsSanitized, setCharsSanitized] = useState<number>(3180);
  const [toolsIntercepted, setToolsIntercepted] = useState<number>(18);

  const sampleRawLeak = `Haan Bro! Let's open CompactGUI.

** Tool :** \`open_app(app_name)\`

** JSON Execution Block :**
\`\`\`json
{"tool": "open_app", "args": {"app_name": "CompactGUI"}}
\`\`\`

This command will launch the CompactGUI application.
[Action Executed: Opened CompactGUI]

All set.
[Tool open_app Result: {"app_name": "CompactGUI", "launched": true, "launcher_pid": 7176}]
All set.`;

  const [rawInput, setRawInput] = useState<string>(sampleRawLeak);
  const [cleanOutput, setCleanOutput] = useState<string>('Haan Bro! Let\'s open CompactGUI.\n\nAll set.');
  const [interceptedTools, setInterceptedTools] = useState<ToolMetadataUI[]>([
    {
      tool_name: 'open_app',
      arguments: { app_name: 'CompactGUI' },
      result: { launched: true, launcher_pid: 7176 },
      timestamp: '13:00:15',
    },
  ]);

  const handleSimulateSanitize = () => {
    // Client-side mirror of sanitizer
    let cleaned = rawInput;
    cleaned = cleaned.replace(/\*{1,2}\s*Tool\s*:\s*\*{1,2}\s*[`'"]?([a-zA-Z0-9_\-\.]+)(?:\([^\)]*\))?[`'"]?/gi, '');
    cleaned = cleaned.replace(/\*{1,2}\s*JSON\s+Execution\s+Block\s*:\s*\*{1,2}/gi, '');
    cleaned = cleaned.replace(/```(?:json)?\s*(\{\s*["']tool["']\s*:\s*[\s\S]*?\})\s*```/gi, '');
    cleaned = cleaned.replace(/\{\s*["']tool["']\s*:\s*["'][^"']+["']\s*,\s*["']args["']\s*:\s*\{[^\}]*\}\s*\}/gi, '');
    cleaned = cleaned.replace(/This command will launch the [^\n\.]+\./gi, '');
    cleaned = cleaned.replace(/\[Action\s+Executed\s*:\s*[^\]]+\]/gi, '');
    cleaned = cleaned.replace(/\[Tool\s+([a-zA-Z0-9_\-\.]+)\s+Result\s*:\s*([^\n\]]+|[\s\S]*?)\]/gi, '');
    cleaned = cleaned.replace(/^\s*```(?:json)?\s*$/gm, '');
    cleaned = cleaned.replace(/^\s*json\s*$/gm, '');
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

    // Dedup repeated trailing lines
    const lines = cleaned.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
    const deduped: string[] = [];
    for (const l of lines) {
      if (!deduped.length || deduped[deduped.length - 1] !== l) {
        deduped.push(l);
      }
    }
    const finalClean = deduped.join('\n\n');

    setCleanOutput(finalClean);
    setLeaksBlocked((prev) => prev + 1);
    setCharsSanitized((prev) => prev + (rawInput.length - finalClean.length));
    setToolsIntercepted((prev) => prev + 1);
    setInterceptedTools([
      {
        tool_name: 'open_app',
        arguments: { app_name: 'CompactGUI' },
        result: { launched: true, launcher_pid: 7176 },
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const handleResetMetrics = () => {
    setLeaksBlocked(0);
    setCharsSanitized(0);
    setToolsIntercepted(0);
    setRawInput(sampleRawLeak);
    setCleanOutput('Haan Bro! Let\'s open CompactGUI.\n\nAll set.');
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 15, 0.88)',
        backdropFilter: 'blur(16px)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        color: '#f0f6fc',
        fontFamily: "'Segoe UI Variable Text', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(14, 165, 233, 0.08) 0%, rgba(2, 6, 23, 0.6) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ShieldCheckmarkRegular style={{ fontSize: '24px', color: '#38bdf8' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, letterSpacing: '0.5px' }}>
              Execution Stream Shield & Adaptive Persona
            </h2>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Milestone 29 Phase 1 • Zero-Noise Chat Filter & Contextual Response Shaper
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleResetMetrics}
            title="Reset Shield Metrics"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '6px 12px',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
            }}
          >
            <ArrowCounterclockwiseRegular /> Reset Metrics
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: 'none',
                borderRadius: '8px',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f0f6fc',
                cursor: 'pointer',
              }}
            >
              <DismissRegular style={{ fontSize: '18px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Metric Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', marginBottom: '8px' }}>
              <FilterRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Blocked Leaks</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{leaksBlocked}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Raw tool syntax blocks intercepted</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(34, 197, 94, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#4ade80', marginBottom: '8px' }}>
              <EyeOffRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Characters Purged</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{charsSanitized}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Noise chars removed from stream</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(168, 85, 247, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', marginBottom: '8px' }}>
              <FlashRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Tools Intercepted</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{toolsIntercepted}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Extracted to background telemetry</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', marginBottom: '8px' }}>
              <SparkleRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Active Persona</span>
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', whiteSpace: 'nowrap' }}>{personaMode}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Adaptive verbal response tuning</div>
          </div>
        </div>

        {/* Persona Mode Switcher */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            padding: '16px',
          }}
        >
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#94a3b8', marginBottom: '12px', textTransform: 'uppercase' }}>
            Configure Adaptive Persona Mode
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
            {[
              { id: 'ADAPTIVE_AUTO', title: 'Adaptive Auto', desc: 'Silent/minimal for apps, witty for queries' },
              { id: 'SILENT_EXECUTION', title: 'Silent Mode', desc: 'Zero output on tool execution' },
              { id: 'MINIMAL_CONFIRMATION', title: 'Minimal Fast-Path', desc: 'Ultra-short "Done." or "Opening App..."' },
              { id: 'CONVERSATIONAL_WITTY', title: 'Jarvis / Bro', desc: 'Playful, punchy conversational tone' },
            ].map((m) => {
              const active = personaMode === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => setPersonaMode(m.id)}
                  style={{
                    background: active ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${active ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                    borderRadius: '8px',
                    padding: '12px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    color: '#f8fafc',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontSize: '14px', fontWeight: 600, color: active ? '#38bdf8' : '#f1f5f9' }}>{m.title}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>{m.desc}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Live Sanitizer Simulator Comparison */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Raw Stream Output Input */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '12px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#f87171' }}>
                Raw LLM Stream Input (With Leaked Syntax)
              </span>
              <button
                onClick={handleSimulateSanitize}
                style={{
                  background: '#ef4444',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  color: '#fff',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Run Sanitizer
              </button>
            </div>
            <textarea
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              style={{
                flex: 1,
                minHeight: '180px',
                background: 'rgba(2, 6, 23, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '10px',
                color: '#fca5a5',
                fontSize: '12px',
                fontFamily: 'monospace',
                resize: 'none',
              }}
            />
          </div>

          {/* Clean User-Visible Chat Prose */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              borderRadius: '12px',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ChatRegular style={{ fontSize: '16px', color: '#4ade80' }} />
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#4ade80' }}>
                Clean User-Visible Chat Prose
              </span>
            </div>
            <div
              style={{
                flex: 1,
                minHeight: '180px',
                background: 'rgba(2, 6, 23, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '12px',
                color: '#86efac',
                fontSize: '13px',
                whiteSpace: 'pre-wrap',
                fontFamily: "'Segoe UI', sans-serif",
                lineHeight: '1.5',
              }}
            >
              {cleanOutput || <span style={{ color: '#64748b', fontStyle: 'italic' }}>[Silent Execution - No Output]</span>}
            </div>
          </div>
        </div>

        {/* Extracted Tool Telemetry Feed */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            borderRadius: '12px',
            padding: '16px',
          }}
        >
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#38bdf8', marginBottom: '8px', textTransform: 'uppercase' }}>
            Extracted Background Tool Telemetry (Routed to Side HUD, Hidden from Chat)
          </div>
          {interceptedTools.map((t, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(2, 6, 23, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '8px',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '12px',
              }}
            >
              <div>
                <span style={{ fontWeight: 600, color: '#38bdf8' }}>{t.tool_name}</span>
                <span style={{ color: '#94a3b8', marginLeft: '12px' }}>
                  Args: {JSON.stringify(t.arguments)}
                </span>
                {t.result && (
                  <span style={{ color: '#4ade80', marginLeft: '12px' }}>
                    Result: {JSON.stringify(t.result)}
                  </span>
                )}
              </div>
              <span style={{ color: '#64748b', fontSize: '11px' }}>{t.timestamp}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
export default ExecutionStreamShieldHUD;
