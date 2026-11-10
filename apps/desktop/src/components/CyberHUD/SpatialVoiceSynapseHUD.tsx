import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  LocationRegular,
  MicRegular,
  CheckmarkCircleRegular,
  SparkleRegular,
} from '@fluentui/react-icons';

export interface CursorContextState {
  x: number;
  y: number;
  window_title: string;
  target_element: string;
  target_symbol: string;
}

export interface ResolvedIntentState {
  spoken_command: string;
  action_verb: string;
  resolved_target: string;
  target_type: string;
  resolution_latency_ms: number;
  confidence: number;
  is_deictic: boolean;
  bounding_box: { left: number; top: number; width: number; height: number };
}

interface SpatialVoiceSynapseHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SpatialVoiceSynapseHUD: React.FC<SpatialVoiceSynapseHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [cursor, setCursor] = useState<CursorContextState>({
    x: 820,
    y: 440,
    window_title: 'Phenom IDE - services/backend/api.py',
    target_element: 'EditorPane.CodeEditor',
    target_symbol: 'fetch_user_records',
  });

  const [spokenDirective, setSpokenDirective] = useState<string>('refactor this function please');

  const [resolvedIntent, setResolvedIntent] = useState<ResolvedIntentState>({
    spoken_command: 'refactor this function please',
    action_verb: 'refactor',
    resolved_target: 'fetch_user_records',
    target_type: 'AST_FUNCTION',
    resolution_latency_ms: 12.4,
    confidence: 0.96,
    is_deictic: true,
    bounding_box: { left: 610, top: 360, width: 420, height: 160 },
  });

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'spatial.telemetry_update' && externalEvent.payload) {
      if (externalEvent.payload.cursor) setCursor(externalEvent.payload.cursor);
      if (externalEvent.payload.intent) setResolvedIntent(externalEvent.payload.intent);
    }
  }, [externalEvent]);

  const handleSimulateDirective = (directive: string, symbol: string, verb: string) => {
    setSpokenDirective(directive);
    setCursor((prev) => ({ ...prev, target_symbol: symbol }));
    setResolvedIntent({
      spoken_command: directive,
      action_verb: verb,
      resolved_target: symbol,
      target_type: 'AST_FUNCTION',
      resolution_latency_ms: +(Math.random() * 8 + 8).toFixed(1),
      confidence: 0.96,
      is_deictic: true,
      bounding_box: { left: cursor.x - 210, top: cursor.y - 80, width: 420, height: 160 },
    });
    setFeedback(`Resolved deictic directive '${directive}' ➜ target symbol: ${symbol}`);

    if (sendMessage) {
      sendMessage({
        type: 'spatial.resolve_intent',
        payload: { spoken_command: directive, cursor_coords: { x: cursor.x, y: cursor.y } },
      });
    }
  };

  const handleHighlight = () => {
    setFeedback(`Emitted screen beacon overlay for '${resolvedIntent.resolved_target}'.`);
    if (sendMessage) {
      sendMessage({
        type: 'spatial.highlight_target',
        payload: { target_name: resolvedIntent.resolved_target },
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
          background: 'linear-gradient(90deg, rgba(0, 240, 255, 0.08), rgba(255, 180, 0, 0.04))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <LocationRegular style={{ fontSize: '24px', color: '#00F0FF' }} />
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
              SPATIAL CURSOR-VOICE INTENT SYNAPSE
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.55)' }}>
              Cross-Modal Deictic Speech & Screen Coordinate Resolver (VOX-07, GES-01)
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
        {/* Cursor Beacon Telemetry */}
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
          <div>
            <div style={{ fontSize: '10px', color: '#00F0FF', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              ACTIVE SCREEN CURSOR BEACON
            </div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span>X: <span style={{ color: '#00F0FF' }}>{cursor.x}</span>px</span>
              <span>Y: <span style={{ color: '#00F0FF' }}>{cursor.y}</span>px</span>
              <span style={{ fontSize: '12px', color: '#8A99AD', fontWeight: 400 }}>● {cursor.window_title}</span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '10px', color: '#8A99AD' }}>TARGET SYMBOL UNDER FOCUS</div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#00FF88', fontFamily: 'monospace', marginTop: '2px' }}>
              {cursor.target_symbol}
            </div>
          </div>
        </div>

        {/* Spoken Directive Simulator */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#A0B2C6', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MicRegular style={{ color: '#00F0FF' }} /> SPOKEN DEICTIC DIRECTIVE
            </span>
            <span style={{ fontSize: '11px', color: '#00F0FF' }}>&lt; 35ms Resolution SLA</span>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { label: 'Refactor This', cmd: 'refactor this function please', sym: 'fetch_user_records', verb: 'refactor' },
              { label: 'Explain Here', cmd: 'explain this code block', sym: 'validate_payload_signature', verb: 'explain' },
              { label: 'Benchmark Here', cmd: 'benchmark this loop here', sym: 'compute_hash_matrix', verb: 'benchmark' },
              { label: 'Inspect Focus', cmd: 'inspect active target', sym: 'render_timeline_chart', verb: 'inspect' },
            ].map((btn, idx) => (
              <button
                key={idx}
                onClick={() => handleSimulateDirective(btn.cmd, btn.sym, btn.verb)}
                style={{
                  background: spokenDirective === btn.cmd ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${spokenDirective === btn.cmd ? '#00F0FF' : 'rgba(255, 255, 255, 0.15)'}`,
                  color: spokenDirective === btn.cmd ? '#00F0FF' : '#E0E6ED',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  transition: 'all 0.2s',
                }}
              >
                "{btn.label}"
              </button>
            ))}
          </div>
        </div>

        {/* Resolved Intent Card */}
        <div
          style={{
            background: 'rgba(20, 28, 46, 0.8)',
            border: '1px solid rgba(0, 240, 255, 0.3)',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  background: 'rgba(0, 255, 136, 0.15)',
                  color: '#00FF88',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}
              >
                {resolvedIntent.action_verb}
              </span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF', fontFamily: 'monospace' }}>
                {resolvedIntent.resolved_target}
              </span>
              <span style={{ fontSize: '11px', color: '#8A99AD' }}>({resolvedIntent.target_type})</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '11px', color: '#00F0FF', fontWeight: 600 }}>
                ⚡ {resolvedIntent.resolution_latency_ms} ms
              </span>
              <span
                style={{
                  background: 'rgba(0, 240, 255, 0.15)',
                  color: '#00F0FF',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  fontWeight: 700,
                }}
              >
                {(resolvedIntent.confidence * 100).toFixed(0)}% CONFIDENCE
              </span>
            </div>
          </div>

          {/* Bounding Box Visualizer */}
          <div
            style={{
              background: 'rgba(8, 12, 20, 0.9)',
              border: '1px dashed rgba(0, 240, 255, 0.4)',
              borderRadius: '8px',
              padding: '12px',
              fontSize: '11px',
              color: '#A0B2C6',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <span>BOUNDING BOX: </span>
              <span style={{ color: '#00FF88', fontFamily: 'monospace' }}>
                [{resolvedIntent.bounding_box.left}, {resolvedIntent.bounding_box.top}, {resolvedIntent.bounding_box.width}x{resolvedIntent.bounding_box.height}]
              </span>
            </div>
            <button
              onClick={handleHighlight}
              style={{
                background: 'rgba(0, 240, 255, 0.15)',
                border: '1px solid rgba(0, 240, 255, 0.3)',
                color: '#00F0FF',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <SparkleRegular /> Broadcast Highlight Beacon
            </button>
          </div>
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
        <span>Zero-Latency Spatial Coordinate Fusion | Rule 8 Shield Active</span>
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
