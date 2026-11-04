import React, { useState } from 'react';
import {
  DismissRegular,
  EyeRegular,
  EyeOffRegular,
  CursorClickRegular,
  AppsRegular,
  DesktopRegular,
} from '@fluentui/react-icons';
import {
  SpatialOverlayStatePayload,
  GhostAnnotationPayload,
} from '../../types/protocol';

interface HolographicSpatialCanvasProps {
  state: SpatialOverlayStatePayload | null;
  onToggleOverlay?: (isActive: boolean, clickThrough?: boolean) => void;
  onDismissAnnotation?: (annotationId: string) => void;
  onToggleClickThrough?: (enabled: boolean) => void;
}

export const HolographicSpatialCanvas: React.FC<HolographicSpatialCanvasProps> = ({
  state,
  onToggleOverlay,
  onDismissAnnotation,
  onToggleClickThrough,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!state) {
    return null;
  }

  const { is_active, click_through, direct_composition_enabled, active_window, annotations } = state;

  const getStyleColor = (preset: GhostAnnotationPayload['style_preset']) => {
    switch (preset) {
      case 'neon_amber':
        return '#ffb800';
      case 'matrix_green':
        return '#00ff88';
      case 'crimson_alert':
        return '#ff3366';
      case 'cyber_cyan':
      default:
        return '#00f0ff';
    }
  };

  return (
    <div
      style={{
        background: 'rgba(8, 12, 24, 0.88)',
        border: '1px solid #00f0ff44',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(12px)',
        boxShadow: is_active ? '0 0 20px rgba(0, 240, 255, 0.25)' : '0 2px 10px rgba(0,0,0,0.5)',
        transition: 'all 0.3s ease',
        maxWidth: 480,
      }}
    >
      {/* Top Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <DesktopRegular style={{ color: '#00f0ff', fontSize: 16 }} />
          <span style={{ fontWeight: 600, letterSpacing: 0.5, color: '#00f0ff' }}>
            HOLOGRAPHIC SPATIAL CANVAS
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: is_active ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              color: is_active ? '#00f0ff' : '#94a3b8',
              fontWeight: 'bold',
            }}
          >
            {is_active ? 'OVERLAY ACTIVE' : 'STANDBY'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {onToggleClickThrough && (
            <button
              onClick={() => onToggleClickThrough(!click_through)}
              title={click_through ? 'Click-Through Enabled (Passthrough)' : 'Click-Through Disabled (Interactive)'}
              style={{
                background: click_through ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 184, 0, 0.2)',
                border: `1px solid ${click_through ? '#00f0ff55' : '#ffb80055'}`,
                color: click_through ? '#00f0ff' : '#ffb800',
                borderRadius: 4,
                padding: '3px 8px',
                cursor: 'pointer',
                fontSize: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <CursorClickRegular style={{ fontSize: 12 }} />
              {click_through ? 'PASSTHROUGH' : 'CAPTURE'}
            </button>
          )}

          {onToggleOverlay && (
            <button
              onClick={() => onToggleOverlay(!is_active, click_through)}
              style={{
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.15)',
                color: is_active ? '#00f0ff' : '#94a3b8',
                borderRadius: 4,
                padding: '3px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {is_active ? <EyeRegular style={{ fontSize: 13 }} /> : <EyeOffRegular style={{ fontSize: 13 }} />}
            </button>
          )}

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
            {isMinimized ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Active Target Window Tracking */}
          {active_window && (
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.35)',
                borderRadius: 6,
                padding: '8px 10px',
                marginBottom: 10,
                border: '1px solid rgba(255,255,255,0.06)',
                fontSize: 11,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <AppsRegular style={{ fontSize: 12 }} /> TARGET WINDOW
                </span>
                <span style={{ color: '#38bdf8' }}>PID: {active_window.pid}</span>
              </div>
              <div style={{ fontWeight: 600, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {active_window.title || 'Desktop Surface'}
              </div>
              <div style={{ color: '#64748b', fontSize: 10, marginTop: 2 }}>
                App: {active_window.process_name} | Bounds: {active_window.bounds.left},{active_window.bounds.top} ({active_window.bounds.width}x{active_window.bounds.height})
              </div>
            </div>
          )}

          {/* DirectComposition Status Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 10,
              color: '#64748b',
              marginBottom: 8,
              padding: '0 2px',
            }}
          >
            <span>DirectComposition: {direct_composition_enabled ? 'ENABLED' : 'FALLBACK'}</span>
            <span>Ghost Annotations: {annotations.length}</span>
          </div>

          {/* Annotations List */}
          {annotations.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '16px 0',
                color: '#64748b',
                fontStyle: 'italic',
                fontSize: 11,
              }}
            >
              No ghost annotations anchored.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto' }}>
              {annotations.map((ann) => {
                const color = getStyleColor(ann.style_preset);
                return (
                  <div
                    key={ann.id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.65)',
                      border: `1px solid ${color}44`,
                      borderLeft: `3px solid ${color}`,
                      borderRadius: 6,
                      padding: '8px 10px',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color }}>{ann.title}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span
                          style={{
                            fontSize: 9,
                            padding: '1px 4px',
                            borderRadius: 3,
                            background: `${color}22`,
                            color,
                          }}
                        >
                          {ann.anchor_point}
                        </span>
                        {onDismissAnnotation && (
                          <button
                            onClick={() => onDismissAnnotation(ann.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#94a3b8',
                              cursor: 'pointer',
                              padding: 0,
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            <DismissRegular style={{ fontSize: 13 }} />
                          </button>
                        )}
                      </div>
                    </div>

                    <div style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.4 }}>
                      {ann.content}
                    </div>

                    <div style={{ fontSize: 9, color: '#64748b', marginTop: 4 }}>
                      Screen: ({ann.screen_x}, {ann.screen_y}) | Target: {ann.target_window_title || 'Active Window'}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};
