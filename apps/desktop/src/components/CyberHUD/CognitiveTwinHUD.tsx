import React, { useState } from 'react';
import {
  SparkleRegular,
  DeleteRegular,
  LockClosedRegular,
} from '@fluentui/react-icons';
import { CognitiveTwinStatePayload } from '../../types/protocol';

interface CognitiveTwinHUDProps {
  twinState: CognitiveTwinStatePayload | null;
  onIngestEpisode?: (label: string) => void;
  onPruneGraph?: (minAffinity: number) => void;
}

export const CognitiveTwinHUD: React.FC<CognitiveTwinHUDProps> = ({
  twinState,
  onIngestEpisode,
  onPruneGraph,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [activityInput, setActivityInput] = useState('');

  if (!twinState) {
    return null;
  }

  const {
    total_nodes,
    total_edges,
    active_context_nodes,
    anticipations,
    is_locked,
  } = twinState;

  const stateColor = is_locked ? '#ef4444' : '#a855f7';

  return (
    <div
      style={{
        background: 'rgba(12, 10, 24, 0.94)',
        border: `1px solid ${stateColor}55`,
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: `0 4px 20px ${stateColor}22`,
        maxWidth: 450,
        margin: '8px 0',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #2e1065',
          paddingBottom: 6,
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {is_locked ? (
            <LockClosedRegular style={{ color: '#ef4444', fontSize: 16 }} />
          ) : (
            <SparkleRegular style={{ color: stateColor, fontSize: 16 }} />
          )}
          <span style={{ fontWeight: 700, letterSpacing: 0.5, color: '#f8fafc' }}>
            COGNITIVE TWIN & LIFE-GRAPH
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
            {is_locked ? 'LOCKED' : 'SYNCHRONIZED'}
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
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 8,
              marginBottom: 8,
              fontSize: 11,
              background: '#1e114066',
              padding: 8,
              borderRadius: 6,
            }}
          >
            <div>
              <span style={{ color: '#94a3b8' }}>Nodes: </span>
              <span style={{ color: '#c084fc', fontWeight: 600 }}>{total_nodes}</span>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Edges: </span>
              <span style={{ color: '#c084fc', fontWeight: 600 }}>{total_edges}</span>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Active: </span>
              <span style={{ color: '#38bdf8' }}>{active_context_nodes.length}</span>
            </div>
          </div>

          {/* Ingest Episode Input */}
          <div style={{ marginBottom: 10, display: 'flex', gap: 6 }}>
            <input
              type="text"
              placeholder="Ingest activity (e.g. reviewing code)"
              value={activityInput}
              onChange={(e) => setActivityInput(e.target.value)}
              disabled={is_locked}
              style={{
                flex: 1,
                background: '#090514',
                border: '1px solid #4c1d95',
                borderRadius: 4,
                padding: '4px 8px',
                color: '#f8fafc',
                fontSize: 11,
              }}
            />
            <button
              onClick={() => {
                if (activityInput.trim()) {
                  onIngestEpisode?.(activityInput.trim());
                  setActivityInput('');
                }
              }}
              disabled={is_locked || !activityInput.trim()}
              style={{
                background: is_locked ? '#334155' : '#7c3aed',
                border: 'none',
                borderRadius: 4,
                color: '#ffffff',
                padding: '4px 10px',
                fontSize: 11,
                cursor: is_locked ? 'not-allowed' : 'pointer',
              }}
            >
              Ingest
            </button>
            <button
              onClick={() => onPruneGraph?.(0.15)}
              disabled={is_locked}
              title="Prune low-affinity nodes"
              style={{
                background: '#33415544',
                border: '1px solid #475569',
                borderRadius: 4,
                color: '#cbd5e1',
                padding: '4px 8px',
                display: 'flex',
                alignItems: 'center',
                cursor: is_locked ? 'not-allowed' : 'pointer',
              }}
            >
              <DeleteRegular style={{ fontSize: 12 }} />
            </button>
          </div>

          {/* Anticipated Next Steps */}
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
              <span>Projected Next Actions</span>
              <span>{anticipations.length} available</span>
            </div>
            <div
              style={{
                maxHeight: 140,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              {anticipations.length === 0 ? (
                <div style={{ color: '#475569', fontSize: 10, fontStyle: 'italic', padding: '4px 0' }}>
                  No high-confidence anticipations projected.
                </div>
              ) : (
                anticipations.map((ant) => (
                  <div
                    key={ant.anticipation_id}
                    style={{
                      background: '#1a0b2e88',
                      border: '1px solid #581c87',
                      borderRadius: 4,
                      padding: '5px 8px',
                      fontSize: 10,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#f3e8ff', fontWeight: 600 }}>{ant.suggested_action}</span>
                      <span
                        style={{
                          background: '#10b98122',
                          color: '#34d399',
                          border: '1px solid #10b98144',
                          borderRadius: 3,
                          padding: '1px 4px',
                          fontSize: 9,
                        }}
                      >
                        {(ant.confidence * 100).toFixed(0)}% conf
                      </span>
                    </div>
                    <div style={{ color: '#a78bfa', fontSize: 9, marginTop: 2 }}>
                      {ant.reasoning_path} {ant.target_tool && `• tool: ${ant.target_tool}`}
                    </div>
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
