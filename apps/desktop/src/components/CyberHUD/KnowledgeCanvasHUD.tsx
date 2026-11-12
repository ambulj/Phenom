import React, { useState, useEffect } from 'react';
import {
  SearchRegular,
  DismissRegular,
  BranchRegular,
  ArrowSyncRegular,
  BookRegular,
  DocumentBulletListRegular
} from '@fluentui/react-icons';

export interface GraphNode {
  id: string;
  label: string;
  vault: 'dev' | 'research' | 'daily' | string;
  tags: string[];
  linkCount: number;
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string;
  target: string;
}

export interface KnowledgeCanvasHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const KnowledgeCanvasHUD: React.FC<KnowledgeCanvasHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedVault, setSelectedVault] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [ragQuery, setRagQuery] = useState<string>('');
  const [ragAnswer, setRagAnswer] = useState<string | null>(null);

  // Initial seed nodes
  const [nodes, setNodes] = useState<GraphNode[]>([
    { id: 'dev:ADR-001_ast_indexing', label: 'ADR-001 AST Indexing', vault: 'dev', tags: ['adr', 'ast', 'architecture'], linkCount: 4, x: 120, y: 100 },
    { id: 'dev:ADR-002_worktree_agent', label: 'ADR-002 Worktree Agent', vault: 'dev', tags: ['adr', 'worktree', 'git'], linkCount: 3, x: 280, y: 80 },
    { id: 'research:MiniLM_Embedding_Opt', label: 'MiniLM Embedding Opt', vault: 'research', tags: ['concept', 'vector', 'onnx'], linkCount: 5, x: 200, y: 220 },
    { id: 'research:Okapi_BM25_Fusion', label: 'Okapi BM25 Fusion', vault: 'research', tags: ['concept', 'bm25', 'rrf'], linkCount: 4, x: 360, y: 200 },
    { id: 'daily:2026-11-11_debrief', label: '2026-11-11 Debrief', vault: 'daily', tags: ['daily', 'debrief'], linkCount: 2, x: 260, y: 320 },
  ]);

  const [links] = useState<GraphLink[]>([
    { source: 'dev:ADR-001_ast_indexing', target: 'research:Okapi_BM25_Fusion' },
    { source: 'dev:ADR-002_worktree_agent', target: 'dev:ADR-001_ast_indexing' },
    { source: 'research:Okapi_BM25_Fusion', target: 'research:MiniLM_Embedding_Opt' },
    { source: 'daily:2026-11-11_debrief', target: 'dev:ADR-002_worktree_agent' },
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'obsidian.graph_updated' && externalEvent.payload) {
      if (Array.isArray(externalEvent.payload.nodes)) {
        setNodes(externalEvent.payload.nodes);
      }
    }
  }, [externalEvent]);

  const filteredNodes = nodes.filter(n => {
    const matchesVault = selectedVault === 'all' || n.vault === selectedVault;
    const matchesQuery = !searchQuery || 
      n.label.toLowerCase().includes(searchQuery.toLowerCase()) || 
      n.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesVault && matchesQuery;
  });

  const getVaultColor = (vault: string) => {
    switch (vault) {
      case 'dev': return '#00f3ff';
      case 'research': return '#bf5af2';
      case 'daily': return '#30d158';
      default: return '#ffd60a';
    }
  };

  const handleSimulateRag = () => {
    if (!ragQuery.trim()) return;
    setRagAnswer(
      `Synthesized offline answer for "${ragQuery}": Verified across [[dev:ADR-001_ast_indexing]] and [[research:Okapi_BM25_Fusion]] [1]. Dual-channel RRF confirms sub-5ms lexical matching with 384d offline vector embeddings [2].`
    );
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'rgba(10, 14, 23, 0.96)',
      backdropFilter: 'blur(20px)',
      color: '#e2e8f0',
      fontFamily: 'Segoe UI Variable, -apple-system, sans-serif',
      boxSizing: 'border-box',
      borderLeft: '1px solid rgba(0, 243, 255, 0.2)'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BookRegular style={{ color: '#00f3ff', fontSize: '20px' }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px' }}>
              OBSIDIAN CROSS-VAULT GRAPH & DEV CANVAS
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Multi-Vault Wikilinks • Hybrid RAG Inspector • Worktree Sandboxes
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => sendMessage?.({ type: 'obsidian.sync_cross_vaults' })}
            style={{
              background: 'rgba(0, 243, 255, 0.1)',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              color: '#00f3ff',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ArrowSyncRegular style={{ fontSize: '14px' }} />
            Sync Vaults
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <DismissRegular style={{ fontSize: '18px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Vault Filters & Search */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex',
        gap: '12px',
        alignItems: 'center',
        flexWrap: 'wrap'
      }}>
        <div style={{
          position: 'relative',
          flex: '1 1 240px',
          minWidth: '200px'
        }}>
          <SearchRegular style={{
            position: 'absolute',
            left: '10px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#64748b',
            fontSize: '14px'
          }} />
          <input
            type="text"
            placeholder="Search cross-vault notes, ADRs, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '7px 10px 7px 32px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '6px',
              color: '#f8fafc',
              fontSize: '12px',
              outline: 'none',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { id: 'all', label: 'All Vaults' },
            { id: 'dev', label: 'Developer', color: '#00f3ff' },
            { id: 'research', label: 'Research', color: '#bf5af2' },
            { id: 'daily', label: 'Daily', color: '#30d158' },
          ].map(v => (
            <button
              key={v.id}
              onClick={() => setSelectedVault(v.id)}
              style={{
                padding: '5px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                cursor: 'pointer',
                border: selectedVault === v.id ? '1px solid #00f3ff' : '1px solid rgba(255, 255, 255, 0.1)',
                background: selectedVault === v.id ? 'rgba(0, 243, 255, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                color: selectedVault === v.id ? '#00f3ff' : '#94a3b8'
              }}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Graph + Inspector */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left: Interactive Visual Graph */}
        <div style={{
          flex: '1 1 60%',
          position: 'relative',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'radial-gradient(circle at 50% 50%, rgba(0, 243, 255, 0.03) 0%, transparent 80%)'
        }}>
          <svg style={{ width: '100%', height: '100%' }}>
            {/* Links */}
            {links.map((link, idx) => {
              const srcNode = nodes.find(n => n.id === link.source);
              const tgtNode = nodes.find(n => n.id === link.target);
              if (!srcNode || !tgtNode) return null;
              return (
                <line
                  key={`link-${idx}`}
                  x1={srcNode.x || 100}
                  y1={srcNode.y || 100}
                  x2={tgtNode.x || 200}
                  y2={tgtNode.y || 200}
                  stroke="rgba(0, 243, 255, 0.25)"
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                />
              );
            })}

            {/* Nodes */}
            {filteredNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              const color = getVaultColor(node.vault);
              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x || 150}, ${node.y || 150})`}
                  onClick={() => setSelectedNode(node)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle
                    r={isSelected ? 18 : 12}
                    fill={color}
                    fillOpacity={isSelected ? 0.4 : 0.2}
                    stroke={color}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  <circle r={isSelected ? 6 : 4} fill={color} />
                  <text
                    x="18"
                    y="4"
                    fill="#e2e8f0"
                    fontSize="11px"
                    fontWeight={isSelected ? 600 : 400}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          <div style={{
            position: 'absolute',
            bottom: '12px',
            left: '16px',
            fontSize: '11px',
            color: '#64748b',
            display: 'flex',
            gap: '12px'
          }}>
            <span>● Dev Vault (#00f3ff)</span>
            <span>● Research (#bf5af2)</span>
            <span>● Daily (#30d158)</span>
          </div>
        </div>

        {/* Right: Inspector & Hybrid RAG Synthesis Panel */}
        <div style={{
          flex: '1 1 40%',
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(0, 0, 0, 0.2)',
          overflowY: 'auto',
          padding: '16px'
        }}>
          {selectedNode ? (
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '8px',
              padding: '14px',
              border: `1px solid ${getVaultColor(selectedNode.vault)}33`,
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1px', color: getVaultColor(selectedNode.vault) }}>
                {selectedNode.vault.toUpperCase()} VAULT NODE
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, marginTop: '4px', color: '#f8fafc' }}>
                {selectedNode.label}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                ID: {selectedNode.id}
              </div>

              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '10px' }}>
                {selectedNode.tags.map(t => (
                  <span key={t} style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#94a3b8'
                  }}>
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div style={{
              padding: '16px',
              borderRadius: '8px',
              border: '1px dashed rgba(255, 255, 255, 0.1)',
              textAlign: 'center',
              fontSize: '12px',
              color: '#64748b',
              marginBottom: '16px'
            }}>
              Select a graph node to inspect backlinks, metadata, and cross-vault wikilinks.
            </div>
          )}

          {/* Offline Hybrid RAG Inspector */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '14px',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: '#38bdf8' }}>
              <DocumentBulletListRegular style={{ fontSize: '14px' }} />
              HYBRID RAG RETRIEVAL & CITATION SYNTHESIS
            </div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px', marginBottom: '10px' }}>
              Query multi-format offline index via Okapi BM25 & 384d Dense Vectors (RRF k=60).
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              <input
                type="text"
                placeholder="Ask documentation or code question..."
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSimulateRag()}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '12px',
                  outline: 'none'
                }}
              />
              <button
                onClick={handleSimulateRag}
                style={{
                  padding: '6px 12px',
                  background: 'rgba(56, 189, 248, 0.2)',
                  border: '1px solid #38bdf8',
                  borderRadius: '6px',
                  color: '#38bdf8',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Inspect
              </button>
            </div>

            {ragAnswer && (
              <div style={{
                marginTop: '12px',
                padding: '10px',
                background: 'rgba(0, 0, 0, 0.4)',
                borderRadius: '6px',
                fontSize: '12px',
                lineHeight: 1.5,
                color: '#cbd5e1',
                borderLeft: '2px solid #38bdf8'
              }}>
                {ragAnswer}
              </div>
            )}
          </div>

          {/* Ephemeral Worktree Monitor */}
          <div style={{
            marginTop: '14px',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            padding: '14px',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: '#a78bfa' }}>
              <BranchRegular style={{ fontSize: '14px' }} />
              EPHEMERAL WORKTREE SANDBOX MONITOR
            </div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px', marginBottom: '8px' }}>
              Active test runner sandboxes in .phenom_worktrees/
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '11px',
              padding: '6px 10px',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '4px',
              border: '1px solid rgba(255, 255, 255, 0.05)'
            }}>
              <span style={{ color: '#30d158' }}>● No active sandboxes (All pruned cleanly)</span>
              <span style={{ color: '#64748b' }}>SLA &lt; 25ms</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
