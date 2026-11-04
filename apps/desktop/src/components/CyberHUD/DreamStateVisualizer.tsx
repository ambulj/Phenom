import React, { useState } from 'react';
import {
  WeatherMoonRegular,
  DeleteDismissRegular,
  PlayRegular,
} from '@fluentui/react-icons';
import { DreamEngineStatusPayload } from '../../types/protocol';

interface DreamStateVisualizerProps {
  status: DreamEngineStatusPayload | null;
  onTriggerCycle?: (force: boolean) => void;
  onPruneMemory?: (decayDays: number) => void;
}

export const DreamStateVisualizer: React.FC<DreamStateVisualizerProps> = ({
  status,
  onTriggerCycle,
  onPruneMemory,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const decayDays = 14;

  if (!status) {
    return null;
  }

  const isRunning = status.is_running;
  const isHalted = status.is_halted;
  const phase = status.phase;

  // Status color mapping
  const getPhaseColor = () => {
    if (isHalted) return '#ff3366';
    if (isRunning) return '#9933ff';
    if (phase === 'COMPLETED') return '#00ffcc';
    return '#80b8ff';
  };

  const phaseColor = getPhaseColor();

  return (
    <div
      style={{
        background: 'rgba(12, 16, 28, 0.85)',
        border: `1px solid ${phaseColor}44`,
        borderRadius: 8,
        padding: '10px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(10px)',
        boxShadow: isRunning ? `0 0 15px ${phaseColor}33` : '0 2px 10px rgba(0,0,0,0.5)',
        transition: 'all 0.3s ease',
        maxWidth: 420,
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <WeatherMoonRegular
            style={{
              color: phaseColor,
              fontSize: 16,
              filter: isRunning ? `drop-shadow(0 0 6px ${phaseColor})` : 'none',
            }}
          />
          <span style={{ fontWeight: 600, letterSpacing: '0.5px', color: '#f8fafc' }}>
            NEURAL DREAM CONSOLIDATION
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              background: `${phaseColor}22`,
              border: `1px solid ${phaseColor}66`,
              color: phaseColor,
              padding: '2px 6px',
              borderRadius: 4,
              fontSize: 10,
              textTransform: 'uppercase',
            }}
          >
            {isHalted ? 'HALTED' : phase}
          </span>
          <span style={{ fontSize: 10, color: '#94a3b8' }}>
            {isExpanded ? '▲' : '▼'}
          </span>
        </div>
      </div>

      {/* Expanded Metrics Panel */}
      {isExpanded && (
        <div style={{ marginTop: 12, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }}>
          {/* Quick Metrics */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              marginBottom: 12,
            }}
          >
            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                padding: '6px 8px',
                borderRadius: 6,
                border: '1px solid rgba(255,255,255,0.06)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 9, color: '#94a3b8' }}>CYCLES</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#00ffcc' }}>
                {status.total_cycles_completed}
              </div>
            </div>

            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                padding: '6px 8px',
                borderRadius: 6,
                border: '1px solid rgba(255,255,255,0.06)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 9, color: '#94a3b8' }}>SCHEMAS</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#b366ff' }}>
                {status.total_schemas_formed}
              </div>
            </div>

            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                padding: '6px 8px',
                borderRadius: 6,
                border: '1px solid rgba(255,255,255,0.06)',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 9, color: '#94a3b8' }}>PRUNED</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#ffb300' }}>
                {status.latest_report?.edges_pruned ?? 0}
              </div>
            </div>
          </div>

          {/* Latest Report Details */}
          {status.latest_report && (
            <div
              style={{
                background: 'rgba(0,0,0,0.3)',
                padding: 8,
                borderRadius: 6,
                fontSize: 10,
                color: '#cbd5e1',
                marginBottom: 12,
                lineHeight: 1.5,
              }}
            >
              <div style={{ fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                LAST CYCLE: {status.latest_report.cycle_id}
              </div>
              <div>• Replayed: {status.latest_report.episodes_replayed} episodes</div>
              <div>• Schemas Abstracted: {status.latest_report.schemas_formed}</div>
              <div>• Stale Edges Purged: {status.latest_report.edges_pruned}</div>
              <div>• Nodes Merged: {status.latest_report.duplicate_nodes_merged}</div>
              <div>• Compute Latency: {status.latest_report.duration_ms.toFixed(1)} ms</div>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button
              onClick={() => onTriggerCycle && onTriggerCycle(true)}
              disabled={isRunning || isHalted}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                background: isRunning ? 'rgba(153, 51, 255, 0.2)' : 'rgba(153, 51, 255, 0.3)',
                border: '1px solid #9933ff',
                color: '#f3e8ff',
                borderRadius: 6,
                padding: '6px 10px',
                fontSize: 11,
                cursor: isRunning || isHalted ? 'not-allowed' : 'pointer',
                opacity: isRunning || isHalted ? 0.6 : 1,
              }}
            >
              <PlayRegular style={{ fontSize: 12 }} />
              Trigger Dream
            </button>

            <button
              onClick={() => onPruneMemory && onPruneMemory(decayDays)}
              disabled={isRunning || isHalted}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                background: 'rgba(255, 179, 0, 0.15)',
                border: '1px solid #ffb300',
                color: '#fef3c7',
                borderRadius: 6,
                padding: '6px 10px',
                fontSize: 11,
                cursor: isRunning || isHalted ? 'not-allowed' : 'pointer',
                opacity: isRunning || isHalted ? 0.6 : 1,
              }}
            >
              <DeleteDismissRegular style={{ fontSize: 12 }} />
              Prune Memory
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
