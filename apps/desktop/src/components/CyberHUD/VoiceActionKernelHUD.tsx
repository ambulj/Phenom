import React, { useState } from 'react';
import {
  DismissRegular,
  SoundWaveCircleRegular,
} from '@fluentui/react-icons';
import { VoiceActionKernelStatePayload } from '../../types/protocol';

interface VoiceActionKernelHUDProps {
  kernelState: VoiceActionKernelStatePayload | null;
  onConfigure?: (config: {
    vad_threshold?: number;
    noise_floor_rms?: number;
    barge_in_sensitivity?: number;
  }) => void;
  onAbortAction?: (actionId: string) => void;
}

export const VoiceActionKernelHUD: React.FC<VoiceActionKernelHUDProps> = ({
  kernelState,
  onConfigure,
  onAbortAction,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [localVad, setLocalVad] = useState(0.50);

  if (!kernelState) {
    return null;
  }

  const {
    state,
    is_listening,
    noise_floor_rms,
    vad_threshold,
    active_session_id,
    total_dispatched,
    recent_actions,
  } = kernelState;

  const isBargedIn = state === 'barged_in';
  const isHalted = state === 'halted';

  const stateColor = isHalted
    ? '#ef4444'
    : isBargedIn
    ? '#f59e0b'
    : state === 'dispatching'
    ? '#10b981'
    : is_listening
    ? '#06b6d4'
    : '#64748b';

  return (
    <div
      style={{
        background: 'rgba(9, 14, 26, 0.94)',
        border: `1px solid ${stateColor}55`,
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: `0 4px 20px ${stateColor}22`,
        maxWidth: 440,
        margin: '8px 0',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #1e293b',
          paddingBottom: 6,
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <SoundWaveCircleRegular style={{ color: stateColor, fontSize: 16 }} />
          <span style={{ fontWeight: 700, letterSpacing: 0.5, color: '#f8fafc' }}>
            VOICE-TO-ACTION KERNEL
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '1px 6px',
              borderRadius: 4,
              background: `${stateColor}22`,
              color: stateColor,
              border: `1px solid ${stateColor}44`,
              fontWeight: 600,
            }}
          >
            {state.toUpperCase()}
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[+]' : '[-]'}
        </button>
      </div>

      {!isMinimized && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              marginBottom: 8,
              fontSize: 11,
              background: '#0f172a88',
              padding: 8,
              borderRadius: 6,
            }}
          >
            <div>
              <span style={{ color: '#64748b' }}>Session: </span>
              <span style={{ color: '#38bdf8' }}>{active_session_id || 'NONE'}</span>
            </div>
            <div>
              <span style={{ color: '#64748b' }}>Dispatched: </span>
              <span style={{ color: '#10b981', fontWeight: 600 }}>{total_dispatched}</span>
            </div>
            <div>
              <span style={{ color: '#64748b' }}>Noise Floor: </span>
              <span>{(noise_floor_rms * 100).toFixed(1)}% RMS</span>
            </div>
            <div>
              <span style={{ color: '#64748b' }}>VAD Threshold: </span>
              <span>{(vad_threshold * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* VAD Sensitivity Slider */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>Acoustic VAD Sensitivity:</span>
              <span style={{ color: '#38bdf8' }}>{(localVad * 100).toFixed(0)}%</span>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={localVad}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setLocalVad(val);
                  onConfigure?.({ vad_threshold: val });
                }}
                style={{ flex: 1, cursor: 'pointer' }}
              />
            </div>
          </div>

          {/* Recent Action Dispatch Stream */}
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
              <span>Recent Intent Dispatches</span>
              <span>{recent_actions.length} recorded</span>
            </div>
            <div
              style={{
                maxHeight: 120,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              {recent_actions.length === 0 ? (
                <div style={{ color: '#475569', fontSize: 10, fontStyle: 'italic', padding: '4px 0' }}>
                  No voice actions dispatched yet.
                </div>
              ) : (
                recent_actions.slice(0, 5).map((action) => (
                  <div
                    key={action.action_id}
                    style={{
                      background: '#1e293b55',
                      border: '1px solid #334155',
                      borderRadius: 4,
                      padding: '4px 8px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: 10,
                    }}
                  >
                    <div>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>"{action.raw_transcript}"</span>
                      <div style={{ display: 'flex', gap: 6, color: '#94a3b8', fontSize: 9 }}>
                        <span style={{ color: '#38bdf8' }}>{action.matched_intent}</span>
                        <span>• {action.latency_ms.toFixed(1)}ms</span>
                        <span>• {(action.confidence * 100).toFixed(0)}% conf</span>
                      </div>
                    </div>
                    {action.status === 'dispatched' && (
                      <button
                        onClick={() => onAbortAction?.(action.action_id)}
                        style={{
                          background: '#ef444422',
                          border: '1px solid #ef444455',
                          borderRadius: 3,
                          color: '#f87171',
                          cursor: 'pointer',
                          padding: '2px 4px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 2,
                        }}
                      >
                        <DismissRegular style={{ fontSize: 10 }} />
                        Abort
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
