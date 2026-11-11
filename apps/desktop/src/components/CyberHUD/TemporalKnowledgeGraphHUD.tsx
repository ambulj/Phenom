import React, { useState } from 'react';
import {
  DismissRegular,
  SearchRegular,
  BrainCircuitRegular,
  ClockRegular,
  BranchForkRegular,
  NoteRegular,
  CodeRegular,
} from '@fluentui/react-icons';

export interface TemporalKnowledgeGraphHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

interface GraphEntityUI {
  id: string;
  name: string;
  entity_type: string;
  decayed_score: number;
  hop_distance: number;
  properties: Record<string, any>;
}

interface GraphRelationUI {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  weight: number;
}

interface EpisodeUI {
  id: string;
  session_id: string;
  episode_type: 'TERMINAL_RUN' | 'GIT_COMMIT' | 'OBSIDIAN_NOTE' | 'MILESTONE_DECISION';
  summary: string;
  timestamp: string;
}

export const TemporalKnowledgeGraphHUD: React.FC<TemporalKnowledgeGraphHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('Neural Voice Engine');
  const [maxHops, setMaxHops] = useState<number>(2);
  const [activeTab, setActiveTab] = useState<'entities' | 'episodes'>('entities');

  const [entities, setEntities] = useState<GraphEntityUI[]>([
    {
      id: 'ent-vox-engine',
      name: 'ExpressiveVoiceEngine',
      entity_type: 'FILE',
      decayed_score: 0.985,
      hop_distance: 0,
      properties: { language: 'python', milestone: 31, phase: 2 },
    },
    {
      id: 'ent-barge-in',
      name: 'AcousticBargeInSLA',
      entity_type: 'GOAL',
      decayed_score: 0.942,
      hop_distance: 1,
      properties: { target_sla: '< 15ms', status: 'VERIFIED_PASS' },
    },
    {
      id: 'ent-ttfa-sla',
      name: 'StreamingTokenBufferTTFA',
      entity_type: 'CONCEPT',
      decayed_score: 0.891,
      hop_distance: 1,
      properties: { target_sla: '< 250ms', measured: '0.8ms' },
    },
    {
      id: 'ent-guardian-switch',
      name: 'UniversalGuardianKillSwitch',
      entity_type: 'DECISION',
      decayed_score: 0.810,
      hop_distance: 2,
      properties: { rule: 3, latency: '< 0.01ms' },
    },
  ]);

  const relations: GraphRelationUI[] = [
    {
      id: 'rel-1',
      source_id: 'ent-vox-engine',
      target_id: 'ent-barge-in',
      relation_type: 'IMPLEMENTS',
      weight: 1.0,
    },
    {
      id: 'rel-2',
      source_id: 'ent-vox-engine',
      target_id: 'ent-ttfa-sla',
      relation_type: 'DEPENDS_ON',
      weight: 0.9,
    },
    {
      id: 'rel-3',
      source_id: 'ent-barge-in',
      target_id: 'ent-guardian-switch',
      relation_type: 'RESOLVES',
      weight: 0.85,
    },
  ];

  const episodes: EpisodeUI[] = [
    {
      id: 'ep-1',
      session_id: 'sprint-31-02',
      episode_type: 'GIT_COMMIT',
      summary: 'feat(milestone-31): implement Phase 2 local expressive neural voice synthesis',
      timestamp: '22:24:33',
    },
    {
      id: 'ep-2',
      session_id: 'sprint-31-02',
      episode_type: 'TERMINAL_RUN',
      summary: 'pytest services/backend/tests/test_expressive_voice.py (8/8 passed in 2.74s)',
      timestamp: '22:23:03',
    },
    {
      id: 'ep-3',
      session_id: 'sprint-31-02',
      episode_type: 'OBSIDIAN_NOTE',
      summary: 'vault/daily/2026-11-11.md - Voice engine prosody benchmarks and TTFA measurements',
      timestamp: '22:18:40',
    },
  ];

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    // Simulate query execution
    setEntities((prev) =>
      prev.map((e) => ({
        ...e,
        decayed_score: Number((Math.random() * 0.2 + 0.8).toFixed(3)),
      }))
    );
  };

  const getEntityBadgeColor = (type: string) => {
    switch (type) {
      case 'FILE':
        return '#38bdf8';
      case 'GOAL':
        return '#22c55e';
      case 'DECISION':
        return '#f59e0b';
      case 'CONCEPT':
        return '#a855f7';
      default:
        return '#94a3b8';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 60,
        right: 24,
        width: 700,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(12, 17, 29, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 14,
        boxShadow: '0 20px 40px rgba(0,0,0,0.65), 0 0 30px rgba(56, 189, 248, 0.15)',
        color: '#e2e8f0',
        zIndex: 120,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 18px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.12) 0%, transparent 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              padding: 6,
              borderRadius: 8,
              backgroundColor: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
            }}
          >
            <BrainCircuitRegular fontSize={20} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: '0.4px', color: '#f8fafc' }}>
              TEMPORAL KNOWLEDGE GRAPH & EPISODIC MATRIX
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Milestone 31 Phase 3 • MEM-01 • EPISODE-02 • Exponential Decay • k-Hop Associative
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular fontSize={18} />
        </button>
      </div>

      {/* Main Content */}
      <div style={{ padding: 18, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Telemetry Stats Bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <BrainCircuitRegular fontSize={13} /> Entities
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#38bdf8', marginTop: 4 }}>
              {entities.length} Nodes
            </div>
            <div style={{ fontSize: 10, color: '#22c55e' }}>Encrypted SQLite</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <BranchForkRegular fontSize={13} /> Relations
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#a855f7', marginTop: 4 }}>
              {relations.length} Edges
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>Weighted DAG</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <ClockRegular fontSize={13} /> Decay Half-Life
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b', marginTop: 4 }}>
              7.0 Days
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>λ = 0.099/day</div>
          </div>

          <div
            style={{
              padding: 10,
              borderRadius: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <CodeRegular fontSize={13} /> Episodes
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#10b981', marginTop: 4 }}>
              {episodes.length} Indexed
            </div>
            <div style={{ fontSize: 10, color: '#22c55e' }}>Cross-Session</div>
          </div>
        </div>

        {/* Associative Search Bar */}
        <div style={{ display: 'flex', gap: 8 }}>
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: 8,
              padding: '0 10px',
            }}
          >
            <SearchRegular fontSize={16} style={{ color: '#94a3b8', marginRight: 6 }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search concepts, files, goals, or decisions..."
              style={{
                width: '100%',
                background: 'none',
                border: 'none',
                color: '#f8fafc',
                padding: '8px 0',
                fontSize: 12,
                outline: 'none',
              }}
            />
          </div>

          <select
            value={maxHops}
            onChange={(e) => setMaxHops(Number(e.target.value))}
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: 8,
              color: '#f8fafc',
              padding: '0 8px',
              fontSize: 11,
              outline: 'none',
            }}
          >
            <option value={1}>1-Hop</option>
            <option value={2}>2-Hops</option>
            <option value={3}>3-Hops</option>
          </select>

          <button
            onClick={handleSearch}
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              backgroundColor: '#0284c7',
              border: 'none',
              color: '#fff',
              fontWeight: 600,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <SearchRegular fontSize={14} /> Traverse
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid rgba(148, 163, 184, 0.2)', gap: 16 }}>
          <button
            onClick={() => setActiveTab('entities')}
            style={{
              padding: '6px 0',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'entities' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'entities' ? '#38bdf8' : '#94a3b8',
              fontWeight: 600,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            ASSOCIATIVE ENTITIES & RELATIONS
          </button>
          <button
            onClick={() => setActiveTab('episodes')}
            style={{
              padding: '6px 0',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'episodes' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'episodes' ? '#38bdf8' : '#94a3b8',
              fontWeight: 600,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            EPISODIC HISTORY (GIT • CLI • OBSIDIAN)
          </button>
        </div>

        {/* Tab 1: Entities and Relations */}
        {activeTab === 'entities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 240, overflowY: 'auto' }}>
            {entities.map((ent) => (
              <div
                key={ent.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(148, 163, 184, 0.15)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: 4,
                        fontSize: 9,
                        fontWeight: 700,
                        backgroundColor: 'rgba(255,255,255,0.08)',
                        color: getEntityBadgeColor(ent.entity_type),
                        border: `1px solid ${getEntityBadgeColor(ent.entity_type)}40`,
                      }}
                    >
                      {ent.entity_type}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#f8fafc' }}>{ent.name}</span>
                    <span style={{ fontSize: 10, color: '#64748b' }}>hop: {ent.hop_distance}</span>
                  </div>
                  <div style={{ fontSize: 10.5, color: '#94a3b8', marginTop: 4, fontFamily: 'Consolas, monospace' }}>
                    {JSON.stringify(ent.properties)}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>Decayed Score</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#38bdf8' }}>
                    {(ent.decayed_score * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 2: Episodes */}
        {activeTab === 'episodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflowY: 'auto' }}>
            {episodes.map((ep) => (
              <div
                key={ep.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(148, 163, 184, 0.15)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#a855f7' }}>
                    {ep.episode_type === 'OBSIDIAN_NOTE' && <NoteRegular fontSize={12} style={{ marginRight: 4 }} />}
                    {ep.episode_type === 'TERMINAL_RUN' && <CodeRegular fontSize={12} style={{ marginRight: 4 }} />}
                    {ep.episode_type === 'GIT_COMMIT' && <BranchForkRegular fontSize={12} style={{ marginRight: 4 }} />}
                    {ep.episode_type} • {ep.session_id}
                  </span>
                  <span style={{ fontSize: 10, color: '#64748b' }}>{ep.timestamp}</span>
                </div>
                <div style={{ fontSize: 11, color: '#e2e8f0', fontFamily: 'Consolas, monospace' }}>
                  {ep.summary}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
