import React, { useState } from 'react';
import {
  HandDrawRegular,
  CubeRegular,
  PinRegular,
} from '@fluentui/react-icons';
import {
  VolumetricWorkspaceStatePayload,
  VolumetricNodePayload,
} from '../../types/protocol';

interface VolumetricWorkspaceHUDProps {
  state: VolumetricWorkspaceStatePayload | null;
  onSetProjection?: (mode: 'cylindrical' | 'spherical' | 'planar') => void;
  onSpawnNode?: (label: string, x: number, y: number, z: number, colorHex: string) => void;
  onClearCanvas?: () => void;
  onInjectGesture?: (gestureType: string, confidence: number, x: number, y: number, z: number) => void;
}

export const VolumetricWorkspaceHUD: React.FC<VolumetricWorkspaceHUDProps> = ({
  state,
  onSetProjection,
  onSpawnNode,
  onClearCanvas,
  onInjectGesture,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [newNodeLabel, setNewNodeLabel] = useState('HUD Card');

  if (!state) {
    return null;
  }

  const {
    is_active,
    projection_mode,
    total_nodes,
    nodes,
    active_gesture,
    selected_node_id,
  } = state;

  const handleQuickSpawn = () => {
    if (onSpawnNode && newNodeLabel.trim()) {
      const randomX = (Math.random() * 2 - 1).toFixed(2);
      const randomY = (Math.random() * 1.5 - 0.75).toFixed(2);
      const randomZ = (1.0 + Math.random() * 1.5).toFixed(2);
      onSpawnNode(newNodeLabel.trim(), parseFloat(randomX), parseFloat(randomY), parseFloat(randomZ), '#00f0ff');
    }
  };

  return (
    <div
      style={{
        background: 'rgba(6, 10, 22, 0.92)',
        border: '1px solid #00f0ff55',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(14px)',
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.12)',
        maxWidth: 420,
        width: '100%',
        marginBottom: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #1e293b',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CubeRegular style={{ color: '#00f0ff', fontSize: 16 }} />
          <span style={{ fontWeight: 600, color: '#f8fafc', letterSpacing: 0.5 }}>
            VOLUMETRIC SPATIAL 3D CANVAS
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: is_active ? 'rgba(0, 240, 255, 0.2)' : 'rgba(100, 116, 139, 0.2)',
              color: is_active ? '#00f0ff' : '#94a3b8',
              border: `1px solid ${is_active ? '#00f0ff55' : '#64748b55'}`,
            }}
          >
            {is_active ? '3D ACTIVE' : 'STANDBY'}
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[EXPAND]' : '[MINIMIZE]'}
        </button>
      </div>

      {!isMinimized && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* Projection Geometry Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8', fontSize: 11 }}>PROJECTION GEOMETRY:</span>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['cylindrical', 'spherical', 'planar'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => onSetProjection && onSetProjection(mode)}
                  style={{
                    background: projection_mode === mode ? 'rgba(0, 240, 255, 0.25)' : 'rgba(15, 23, 42, 0.6)',
                    border: `1px solid ${projection_mode === mode ? '#00f0ff' : '#334155'}`,
                    color: projection_mode === mode ? '#00f0ff' : '#94a3b8',
                    borderRadius: 4,
                    padding: '3px 8px',
                    fontSize: 10,
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                  }}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Vision Gesture Telemetry */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid #1e293b',
              borderRadius: 6,
              padding: '8px 10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <HandDrawRegular style={{ color: '#ffb800', fontSize: 14 }} />
                <span style={{ color: '#cbd5e1', fontSize: 11, fontWeight: 500 }}>TOUCHLESS GESTURE TRACKER</span>
              </div>
              <span
                style={{
                  fontSize: 10,
                  color: active_gesture ? '#ffb800' : '#64748b',
                  fontWeight: 600,
                }}
              >
                {active_gesture ? active_gesture.gesture_type : 'NO GESTURE'}
              </span>
            </div>

            {active_gesture ? (
              <div style={{ fontSize: 10, color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  HAND: ({active_gesture.hand_position.x.toFixed(2)}, {active_gesture.hand_position.y.toFixed(2)}, {active_gesture.hand_position.z.toFixed(2)})m
                </span>
                <span>CONF: {(active_gesture.confidence * 100).toFixed(0)}%</span>
              </div>
            ) : (
              <div style={{ fontSize: 10, color: '#475569' }}>
                Rule 4 Enforced: Only landmark 3D vector coordinates processed. Zero pixel frames stored.
              </div>
            )}

            {/* Quick Gesture Simulators */}
            <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
              <button
                onClick={() => onInjectGesture && onInjectGesture('PINCH', 0.95, 0.0, 0.0, 1.2)}
                style={{
                  background: 'rgba(255, 184, 0, 0.15)',
                  border: '1px solid #ffb80055',
                  color: '#ffb800',
                  borderRadius: 4,
                  padding: '2px 6px',
                  fontSize: 9,
                  cursor: 'pointer',
                }}
              >
                Sim PINCH
              </button>
              <button
                onClick={() => onInjectGesture && onInjectGesture('POINT', 0.92, 0.2, 0.1, 1.5)}
                style={{
                  background: 'rgba(0, 240, 255, 0.15)',
                  border: '1px solid #00f0ff55',
                  color: '#00f0ff',
                  borderRadius: 4,
                  padding: '2px 6px',
                  fontSize: 9,
                  cursor: 'pointer',
                }}
              >
                Sim POINT
              </button>
              <button
                onClick={() => onInjectGesture && onInjectGesture('PALM_DISMISS', 0.98, 0.0, 0.0, 1.0)}
                style={{
                  background: 'rgba(255, 51, 102, 0.15)',
                  border: '1px solid #ff336655',
                  color: '#ff3366',
                  borderRadius: 4,
                  padding: '2px 6px',
                  fontSize: 9,
                  cursor: 'pointer',
                }}
              >
                Sim PALM DISMISS
              </button>
            </div>
          </div>

          {/* Active 3D Spatial Nodes */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ color: '#94a3b8', fontSize: 11 }}>
                SPATIAL SCENE NODES ({total_nodes})
              </span>
              {selected_node_id && (
                <span style={{ color: '#00f0ff', fontSize: 10 }}>
                  TARGETED: {selected_node_id}
                </span>
              )}
            </div>

            {nodes.length === 0 ? (
              <div
                style={{
                  padding: '12px',
                  textAlign: 'center',
                  color: '#64748b',
                  fontSize: 11,
                  border: '1px dashed #334155',
                  borderRadius: 6,
                }}
              >
                No active 3D volumetric nodes.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto' }}>
                {nodes.map((node: VolumetricNodePayload) => {
                  const isSelected = selected_node_id === node.node_id;
                  return (
                    <div
                      key={node.node_id}
                      style={{
                        background: isSelected ? 'rgba(0, 240, 255, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                        border: `1px solid ${isSelected ? node.color_hex : '#1e293b'}`,
                        borderRadius: 6,
                        padding: '6px 8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            background: node.color_hex,
                            boxShadow: `0 0 6px ${node.color_hex}`,
                          }}
                        />
                        <span style={{ color: '#f1f5f9', fontWeight: 500 }}>{node.label}</span>
                        {node.is_pinned && <PinRegular style={{ color: '#ffb800', fontSize: 12 }} />}
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: 10 }}>
                        pos: ({node.position.x.toFixed(1)}, {node.position.y.toFixed(1)}, {node.position.z.toFixed(1)})m
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Quick Controls */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="text"
              value={newNodeLabel}
              onChange={(e) => setNewNodeLabel(e.target.value)}
              placeholder="Node label..."
              style={{
                flex: 1,
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid #334155',
                borderRadius: 4,
                padding: '4px 8px',
                color: '#e2e8f0',
                fontSize: 11,
                fontFamily: 'monospace',
              }}
            />
            <button
              onClick={handleQuickSpawn}
              style={{
                background: 'rgba(0, 240, 255, 0.15)',
                border: '1px solid #00f0ff55',
                color: '#00f0ff',
                borderRadius: 4,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              SPAWN 3D
            </button>
            <button
              onClick={() => onClearCanvas && onClearCanvas()}
              style={{
                background: 'rgba(255, 51, 102, 0.15)',
                border: '1px solid #ff336655',
                color: '#ff3366',
                borderRadius: 4,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              CLEAR
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
