import React, { useState } from 'react';
import {
  ServerMultipleRegular,
  BatteryChargeRegular,
  BatteryWarningRegular,
  WarningRegular,
  ArrowSyncRegular,
  DismissCircleRegular,
} from '@fluentui/react-icons';
import {
  SwarmClusterStatePayload,
  SwarmNodeTelemetryPayload,
  DistributedWorkloadPayload,
} from '../../types/protocol';

interface SwarmComputeHUDProps {
  clusterState: SwarmClusterStatePayload | null;
  recentTasks?: DistributedWorkloadPayload[];
  onOffloadWorkload?: (workloadType: 'SPECULATIVE_DECODING' | 'EMBEDDING_BATCH' | 'DOCUMENT_INDEXING', itemsCount: number) => void;
  onAbortWorkload?: (taskId: string) => void;
}

export const SwarmComputeHUD: React.FC<SwarmComputeHUDProps> = ({
  clusterState,
  recentTasks = [],
  onOffloadWorkload,
  onAbortWorkload,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [itemsCount, setItemsCount] = useState(10);

  if (!clusterState) {
    return null;
  }

  const {
    active_node_count,
    total_vram_mb,
    total_ram_mb,
    nodes,
    active_workload_count,
    is_healthy,
  } = clusterState;

  return (
    <div
      style={{
        background: 'rgba(7, 12, 26, 0.92)',
        border: '1px solid #00f0ff55',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(14px)',
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.12)',
        maxWidth: 440,
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
          <ServerMultipleRegular style={{ color: '#00f0ff', fontSize: 16 }} />
          <span style={{ fontWeight: 600, color: '#f8fafc', letterSpacing: 0.5 }}>
            DISTRIBUTED SWARM COMPUTE
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: is_healthy ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 51, 102, 0.2)',
              color: is_healthy ? '#00ff88' : '#ff3366',
              border: `1px solid ${is_healthy ? '#00ff8855' : '#ff336655'}`,
            }}
          >
            {is_healthy ? `${active_node_count} NODES ONLINE` : 'MESH OFFLINE'}
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
          {/* Capacity Aggregates */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 6,
              background: 'rgba(15, 23, 42, 0.7)',
              padding: '6px 8px',
              borderRadius: 6,
              border: '1px solid #1e293b',
              textAlign: 'center',
            }}
          >
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>TOTAL VRAM</div>
              <div style={{ color: '#00f0ff', fontWeight: 600, fontSize: 13 }}>
                {(total_vram_mb / 1024).toFixed(1)} GB
              </div>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>TOTAL RAM</div>
              <div style={{ color: '#38bdf8', fontWeight: 600, fontSize: 13 }}>
                {(total_ram_mb / 1024).toFixed(1)} GB
              </div>
            </div>
            <div>
              <div style={{ color: '#94a3b8', fontSize: 9 }}>ACTIVE JOBS</div>
              <div style={{ color: '#ffb800', fontWeight: 600, fontSize: 13 }}>
                {active_workload_count}
              </div>
            </div>
          </div>

          {/* Node Topology List */}
          <div>
            <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>
              CLUSTER PEER TOPOLOGY ({nodes.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 150, overflowY: 'auto' }}>
              {nodes.map((node: SwarmNodeTelemetryPayload) => (
                <div
                  key={node.node_id}
                  style={{
                    background: node.is_online ? 'rgba(15, 23, 42, 0.6)' : 'rgba(30, 41, 59, 0.3)',
                    border: `1px solid ${node.is_online ? '#334155' : '#1e293b'}`,
                    borderRadius: 6,
                    padding: '6px 8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ color: node.is_online ? '#f1f5f9' : '#64748b', fontWeight: 500 }}>
                        {node.device_name}
                      </span>
                      <span
                        style={{
                          fontSize: 9,
                          padding: '1px 4px',
                          borderRadius: 3,
                          background: 'rgba(0, 240, 255, 0.15)',
                          color: '#00f0ff',
                        }}
                      >
                        {node.node_type}
                      </span>
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: 10 }}>
                      VRAM: {node.available_vram_mb}MB | RAM: {node.available_ram_mb}MB | {node.compute_flops_rating.toFixed(1)}x
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {node.thermal_throttled && (
                      <WarningRegular style={{ color: '#ff3366', fontSize: 14 }} title="Thermal Throttled" />
                    )}
                    {node.is_plugged_in ? (
                      <BatteryChargeRegular style={{ color: '#00ff88', fontSize: 14 }} title="AC Connected" />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <BatteryWarningRegular
                          style={{
                            color: node.battery_percent < 20 ? '#ff3366' : '#ffb800',
                            fontSize: 14,
                          }}
                        />
                        <span style={{ fontSize: 9, color: node.battery_percent < 20 ? '#ff3366' : '#ffb800' }}>
                          {node.battery_percent}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* In-Flight & Recent Workloads */}
          {recentTasks.length > 0 && (
            <div>
              <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>
                ACTIVE & RECENT WORKLOADS
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 110, overflowY: 'auto' }}>
                {recentTasks.slice(-3).map((task: DistributedWorkloadPayload) => (
                  <div
                    key={task.task_id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.5)',
                      border: '1px solid #1e293b',
                      borderRadius: 4,
                      padding: '4px 6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: 10,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <ArrowSyncRegular style={{ color: '#38bdf8', fontSize: 12 }} />
                      <span style={{ color: '#cbd5e1' }}>{task.workload_type}</span>
                      <span style={{ color: '#64748b' }}>-&gt; {task.assigned_node_id}</span>
                      {task.failover_count > 0 && (
                        <span style={{ color: '#ffb800', fontSize: 9 }}>[FAILOVER x{task.failover_count}]</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          color: task.status === 'COMPLETED' ? '#00ff88' : task.status === 'RUNNING' ? '#ffb800' : '#ff3366',
                        }}
                      >
                        {task.status}
                      </span>
                      {task.status === 'RUNNING' && onAbortWorkload && (
                        <button
                          onClick={() => onAbortWorkload(task.task_id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#ff3366',
                            cursor: 'pointer',
                          }}
                        >
                          <DismissCircleRegular style={{ fontSize: 12 }} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Offload Actions */}
          <div style={{ borderTop: '1px solid #1e293b', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#94a3b8', fontSize: 10 }}>ITEMS / SLICES:</span>
              <input
                type="number"
                min={1}
                max={500}
                value={itemsCount}
                onChange={(e) => setItemsCount(Math.max(1, parseInt(e.target.value) || 10))}
                style={{
                  width: 50,
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid #334155',
                  borderRadius: 4,
                  padding: '2px 4px',
                  color: '#e2e8f0',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4 }}>
              <button
                onClick={() => onOffloadWorkload && onOffloadWorkload('SPECULATIVE_DECODING', itemsCount)}
                style={{
                  background: 'rgba(0, 240, 255, 0.15)',
                  border: '1px solid #00f0ff55',
                  color: '#00f0ff',
                  borderRadius: 4,
                  padding: '4px 6px',
                  fontSize: 10,
                  cursor: 'pointer',
                }}
              >
                SPECULATIVE
              </button>
              <button
                onClick={() => onOffloadWorkload && onOffloadWorkload('EMBEDDING_BATCH', itemsCount)}
                style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  border: '1px solid #38bdf855',
                  color: '#38bdf8',
                  borderRadius: 4,
                  padding: '4px 6px',
                  fontSize: 10,
                  cursor: 'pointer',
                }}
              >
                EMBEDDINGS
              </button>
              <button
                onClick={() => onOffloadWorkload && onOffloadWorkload('DOCUMENT_INDEXING', itemsCount)}
                style={{
                  background: 'rgba(255, 184, 0, 0.15)',
                  border: '1px solid #ffb80055',
                  color: '#ffb800',
                  borderRadius: 4,
                  padding: '4px 6px',
                  fontSize: 10,
                  cursor: 'pointer',
                }}
              >
                INDEXING
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
