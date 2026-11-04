import React, { useState } from 'react';
import {
  DesktopRegular,
  ArrowSyncRegular,
  DismissRegular,
  CodeRegular,
} from '@fluentui/react-icons';
import { MultiAgentMeshStatePayload } from '../../types/protocol';

interface MultiAgentMeshHUDProps {
  meshState: MultiAgentMeshStatePayload | null;
  onDiscover?: () => void;
  onDelegate?: (targetNodeId: string, capability: string) => void;
  onDisconnect?: (nodeId: string) => void;
}

export const MultiAgentMeshHUD: React.FC<MultiAgentMeshHUDProps> = ({
  meshState,
  onDiscover,
  onDelegate,
  onDisconnect,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!meshState) {
    return null;
  }

  const {
    local_node_id,
    is_advertising,
    peers,
    total_delegated_tasks,
    recent_delegations,
  } = meshState;

  const peerList = Object.values(peers);
  const stateColor = !is_advertising ? '#ef4444' : peerList.length > 0 ? '#06b6d4' : '#64748b';

  return (
    <div
      style={{
        background: 'rgba(7, 16, 26, 0.94)',
        border: `1px solid ${stateColor}55`,
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: `0 4px 20px ${stateColor}22`,
        maxWidth: 460,
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
          <DesktopRegular style={{ color: stateColor, fontSize: 16 }} />
          <span style={{ fontWeight: 700, letterSpacing: 0.5, color: '#f8fafc' }}>
            MULTI-AGENT MESH
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
            {peerList.length} PEERS
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
              <span style={{ color: '#64748b' }}>Local Node: </span>
              <span style={{ color: '#38bdf8' }}>{local_node_id}</span>
            </div>
            <div>
              <span style={{ color: '#64748b' }}>Delegated: </span>
              <span style={{ color: '#10b981', fontWeight: 600 }}>{total_delegated_tasks} tasks</span>
            </div>
          </div>

          {/* Peer Discovery Trigger */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
            <button
              onClick={() => onDiscover?.()}
              style={{
                flex: 1,
                background: '#0284c722',
                border: '1px solid #0284c755',
                borderRadius: 4,
                color: '#38bdf8',
                padding: '4px',
                fontSize: 10,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
              }}
            >
              <ArrowSyncRegular style={{ fontSize: 11 }} /> Scan Subnet for Beacons
            </button>
          </div>

          {/* Connected Peers List */}
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
              Discovered Subnet Nodes ({peerList.length})
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
              {peerList.length === 0 ? (
                <div style={{ color: '#475569', fontSize: 10, fontStyle: 'italic', padding: '4px 0' }}>
                  No peer nodes discovered on local subnet.
                </div>
              ) : (
                peerList.map((peer) => (
                  <div
                    key={peer.node_id}
                    style={{
                      background: '#1e293b55',
                      border: '1px solid #334155',
                      borderRadius: 4,
                      padding: '5px 8px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: 10,
                    }}
                  >
                    <div>
                      <div style={{ color: '#f8fafc', fontWeight: 600 }}>
                        {peer.device_name} ({peer.ip_address}:{peer.port})
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: 9 }}>
                        caps: {peer.capabilities.join(', ')} • status: {peer.status}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => onDelegate?.(peer.node_id, peer.capabilities[0] || 'general_compute')}
                        style={{
                          background: '#10b98122',
                          border: '1px solid #10b98155',
                          borderRadius: 3,
                          color: '#34d399',
                          cursor: 'pointer',
                          padding: '2px 5px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 2,
                        }}
                      >
                        <CodeRegular style={{ fontSize: 9 }} /> Delegate
                      </button>
                      <button
                        onClick={() => onDisconnect?.(peer.node_id)}
                        style={{
                          background: '#ef444422',
                          border: '1px solid #ef444455',
                          borderRadius: 3,
                          color: '#f87171',
                          cursor: 'pointer',
                          padding: '2px 4px',
                        }}
                      >
                        <DismissRegular style={{ fontSize: 9 }} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Delegations */}
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
              Recent Task Delegations
            </div>
            <div
              style={{
                maxHeight: 80,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 3,
              }}
            >
              {recent_delegations.length === 0 ? (
                <div style={{ color: '#475569', fontSize: 10, fontStyle: 'italic' }}>
                  No cross-node tasks delegated yet.
                </div>
              ) : (
                recent_delegations.slice(0, 3).map((task) => (
                  <div
                    key={task.task_id}
                    style={{
                      background: '#0f172a',
                      border: '1px solid #1e293b',
                      borderRadius: 3,
                      padding: '3px 6px',
                      fontSize: 9,
                      display: 'flex',
                      justifyContent: 'space-between',
                      color: '#93c5fd',
                    }}
                  >
                    <span>{task.capability_required} → {task.target_node_id}</span>
                    <span>{task.latency_ms}ms ({task.status})</span>
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
