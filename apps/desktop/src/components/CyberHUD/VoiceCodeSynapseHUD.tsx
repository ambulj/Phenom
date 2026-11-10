import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  CodeRegular,
  Speaker2Regular,
  PlayRegular,
  ArrowResetRegular,
  CheckmarkCircleRegular,
} from '@fluentui/react-icons';

export interface SynapseMutationHUD {
  transaction_id: string;
  file_path: string;
  target_symbol: string;
  mutation_type: string;
  unified_diff: string;
  acoustic_cue: string;
  duration_ms: number;
}

interface VoiceCodeSynapseHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const VoiceCodeSynapseHUD: React.FC<VoiceCodeSynapseHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [spokenUtterance, setSpokenUtterance] = useState<string>(
    'Add type hint float to parameter timeout_seconds in function fetch_data'
  );
  const [targetSymbol, setTargetSymbol] = useState<string>('fetch_data');
  const [filePath] = useState<string>('services/backend/api.py');
  const [activeEarcon, setActiveEarcon] = useState<string>('ast_success');

  const [activeDiff, setActiveDiff] = useState<string>(
    `--- a/services/backend/api.py\n+++ b/services/backend/api.py\n@@ -12,4 +12,4 @@\n-def fetch_data(url: str, timeout_seconds=10.0):\n+def fetch_data(url: str, timeout_seconds: float = 10.0):`
  );

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'synapse.mutation_update' && externalEvent.payload) {
      if (externalEvent.payload.spoken_utterance) setSpokenUtterance(externalEvent.payload.spoken_utterance);
      if (externalEvent.payload.target_symbol) setTargetSymbol(externalEvent.payload.target_symbol);
      if (externalEvent.payload.unified_diff) setActiveDiff(externalEvent.payload.unified_diff);
      if (externalEvent.payload.acoustic_cue) setActiveEarcon(externalEvent.payload.acoustic_cue);
    }
  }, [externalEvent]);

  const handleApplySpoken = (mutationType: string, params: any) => {
    setFeedback(`Applied spoken mutation: ${mutationType}`);
    setActiveEarcon('ast_success');

    if (mutationType === 'rename_param') {
      setActiveDiff(
        `--- a/services/backend/api.py\n+++ b/services/backend/api.py\n@@ -12,4 +12,4 @@\n-def fetch_data(url: str, timeout_ms=1000):\n+def fetch_data(url: str, timeout_seconds=1.0):`
      );
    } else if (mutationType === 'wrap_try_except') {
      setActiveDiff(
        `--- a/services/backend/api.py\n+++ b/services/backend/api.py\n@@ -12,5 +12,9 @@\n def fetch_data(url: str):\n+    try:\n         return requests.get(url)\n+    except Exception as e:\n+        return False`
      );
    }

    if (sendMessage) {
      sendMessage({
        type: 'synapse.apply_mutation',
        payload: { file_path: filePath, target_symbol: targetSymbol, mutation_type: mutationType, parameters: params },
      });
    }

    setTimeout(() => setFeedback(null), 3000);
  };

  const handlePlayEarcon = (cue: string) => {
    setActiveEarcon(cue);
    setFeedback(`Played procedural acoustic earcon: ${cue}`);
    if (sendMessage) {
      sendMessage({
        type: 'synapse.play_earcon',
        payload: { cue_type: cue },
      });
    }
    setTimeout(() => setFeedback(null), 2500);
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(236, 72, 153, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(236, 72, 153, 0.18)',
        display: 'flex',
        flexDirection: 'column',
        color: '#e2e8f0',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid rgba(236, 72, 153, 0.2)',
          background: 'rgba(190, 24, 93, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CodeRegular style={{ fontSize: 22, color: '#f472b6' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#fbcfe8' }}>
              VOICE-CODE SYNAPSE &amp; REAL-TIME AST CO-EDITOR
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 23-03 • Conversational AST Mutations &amp; Procedural Acoustic Earcons (SYN-01 / VOX-06)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => handlePlayEarcon('ast_success')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(236, 72, 153, 0.2)',
              color: '#fbcfe8',
              border: '1px solid rgba(236, 72, 153, 0.4)',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <Speaker2Regular style={{ fontSize: 14 }} />
            <span>Test Chime</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
              }}
            >
              <DismissRegular style={{ fontSize: 18 }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Spoken Utterance Banner */}
        <div
          style={{
            padding: 14,
            borderRadius: 8,
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
              Live Spoken Code Directive
            </span>
            <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#f472b6' }}>
              Target: {targetSymbol} ({filePath})
            </span>
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#fbcfe8' }}>
            &ldquo;{spokenUtterance}&rdquo;
          </div>
        </div>

        {/* Quick Action Mutation Triggers */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => handleApplySpoken('rename_param', { old_param: 'timeout_ms', new_param: 'timeout_seconds' })}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#e2e8f0',
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <PlayRegular style={{ fontSize: 12 }} />
            <span>Rename Param</span>
          </button>

          <button
            onClick={() => handleApplySpoken('wrap_try_except', {})}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#e2e8f0',
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <PlayRegular style={{ fontSize: 12 }} />
            <span>Wrap Try / Except</span>
          </button>

          <button
            onClick={() => handlePlayEarcon('syntax_error')}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(248, 113, 113, 0.15)',
              border: '1px solid rgba(248, 113, 113, 0.3)',
              color: '#f87171',
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <ArrowResetRegular style={{ fontSize: 12 }} />
            <span>Syntax Error Cue</span>
          </button>
        </div>

        {/* Unified Diff View */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
              AST Buffer Unified Diff Preview
            </span>
            <span
              style={{
                fontSize: 11,
                fontFamily: 'monospace',
                background: 'rgba(236, 72, 153, 0.15)',
                color: '#f472b6',
                padding: '2px 8px',
                borderRadius: 4,
              }}
            >
              Earcon: {activeEarcon}
            </span>
          </div>

          <div
            style={{
              padding: 14,
              borderRadius: 8,
              background: '#090d16',
              border: '1px solid rgba(236, 72, 153, 0.25)',
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: 12,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}
          >
            {activeDiff.split('\n').map((line, idx) => {
              let color = '#cbd5e1';
              let bg = 'transparent';
              if (line.startsWith('+')) {
                color = '#4ade80';
                bg = 'rgba(74, 222, 128, 0.1)';
              } else if (line.startsWith('-')) {
                color = '#f87171';
                bg = 'rgba(248, 113, 113, 0.1)';
              } else if (line.startsWith('@@')) {
                color = '#38bdf8';
              }
              return (
                <div key={idx} style={{ color, backgroundColor: bg, padding: '1px 4px', borderRadius: 2 }}>
                  {line}
                </div>
              );
            })}
          </div>
        </div>

        {/* Status Toast */}
        {feedback && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(236, 72, 153, 0.15)',
              border: '1px solid rgba(236, 72, 153, 0.3)',
              color: '#f472b6',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 14 }} />
            <span>{feedback}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '8px 20px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#64748b',
        }}
      >
        <div>In-Memory Procedural Earcons • Rule 4 Zero Audio Disk Persistence</div>
        <div>AST Syntax Verified • Guardian SLA &lt; 25.0ms</div>
      </div>
    </div>
  );
};
