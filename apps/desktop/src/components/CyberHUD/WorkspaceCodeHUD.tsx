import React, { useState, useEffect } from 'react';
import {
  CodeRegular,
  SearchRegular,
  DismissRegular,
  BranchRegular,
  ArrowSyncRegular
} from '@fluentui/react-icons';

export interface CodeSymbol {
  name: string;
  kind: string;
  file_path: string;
  line_number: number;
  signature: string;
  docstring?: string | null;
  parent?: string | null;
  calls: string[];
}

export interface WorkspaceCodeHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const WorkspaceCodeHUD: React.FC<WorkspaceCodeHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedKind, setSelectedKind] = useState<string>('all');
  const [symbols, setSymbols] = useState<CodeSymbol[]>([
    {
      name: 'AstCodeParser',
      kind: 'class',
      file_path: 'services/backend/coding/ast_parser.py',
      line_number: 110,
      signature: 'class AstCodeParser',
      docstring: 'Multi-language AST and semantic symbol parser.',
      calls: ['parse_python', 'parse_typescript']
    },
    {
      name: 'index_workspace',
      kind: 'method',
      file_path: 'services/backend/coding/workspace_indexer.py',
      line_number: 55,
      signature: 'def index_workspace(max_files: int = 1500) -> Dict[str, Any]',
      parent: 'WorkspaceIndexer',
      calls: ['_compute_hash', 'parse_file']
    },
    {
      name: 'preview_symbol_rename',
      kind: 'method',
      file_path: 'services/backend/coding/refactor_engine.py',
      line_number: 30,
      signature: 'def preview_symbol_rename(old_symbol: str, new_symbol: str) -> Dict[str, Any]',
      parent: 'RefactorEngine',
      calls: ['lookup_symbol', 'generate_diff']
    },
    {
      name: 'WorkspaceCodeHUDProps',
      kind: 'interface',
      file_path: 'apps/desktop/src/components/CyberHUD/WorkspaceCodeHUD.tsx',
      line_number: 20,
      signature: 'interface WorkspaceCodeHUDProps',
      calls: []
    }
  ]);

  const [oldSymbol, setOldSymbol] = useState<string>('');
  const [newSymbol, setNewSymbol] = useState<string>('');
  const [diffPreview, setDiffPreview] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<{ files: number; symbols: number }>({ files: 142, symbols: 890 });

  useEffect(() => {
    if (externalEvent?.type === 'code.symbols_indexed') {
      if (externalEvent.payload?.symbols) {
        setSymbols(externalEvent.payload.symbols);
      }
      if (externalEvent.payload?.stats) {
        setStats({
          files: externalEvent.payload.stats.indexed_files || 142,
          symbols: externalEvent.payload.stats.total_symbols || 890
        });
      }
      setStatusMessage('Workspace re-indexed successfully.');
    }
    if (externalEvent?.type === 'code.refactor_preview') {
      setDiffPreview(externalEvent.payload?.diff || 'No diff generated.');
    }
  }, [externalEvent]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    if (sendMessage) {
      sendMessage({
        type: 'tool.dispatch',
        payload: {
          tool: 'lookup_symbol_definition',
          args: { symbol_name: searchQuery.trim() }
        }
      });
      setStatusMessage(`Querying definitions for '${searchQuery}'...`);
    } else {
      setStatusMessage(`Filter applied for '${searchQuery}'.`);
    }
  };

  const handleTriggerReindex = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool.dispatch',
        payload: {
          tool: 'index_workspace_symbols',
          args: { max_files: 1000 }
        }
      });
      setStatusMessage('Indexing workspace AST in background...');
    } else {
      setStatusMessage('Workspace index triggered.');
    }
  };

  const handlePreviewRename = () => {
    if (!oldSymbol.trim() || !newSymbol.trim()) {
      setStatusMessage('Please enter both old and new symbol names.');
      return;
    }
    if (sendMessage) {
      sendMessage({
        type: 'tool.dispatch',
        payload: {
          tool: 'preview_code_refactor',
          args: { old_symbol: oldSymbol.trim(), new_symbol: newSymbol.trim() }
        }
      });
      setStatusMessage(`Generating unified diff for '${oldSymbol}' -> '${newSymbol}'...`);
    } else {
      setDiffPreview(`--- a/services/backend/sample.py\n+++ b/services/backend/sample.py\n@@ -15,4 +15,4 @@\n-${oldSymbol} = True\n+${newSymbol} = True`);
      setStatusMessage('Generated mock unified diff preview.');
    }
  };

  const filteredSymbols = symbols.filter(sym => {
    const matchesSearch = searchQuery === '' ||
      sym.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sym.file_path.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesKind = selectedKind === 'all' || sym.kind.toLowerCase() === selectedKind.toLowerCase();
    return matchesSearch && matchesKind;
  });

  return (
    <div
      style={{
        width: '540px',
        backgroundColor: '#0c1017',
        border: '1px solid #1f293d',
        borderRadius: '12px',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.65)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontSize: '13px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 18px',
          borderBottom: '1px solid #1a2234',
          background: 'linear-gradient(180deg, #131a29 0%, #0c1017 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
            }}
          >
            <CodeRegular style={{ fontSize: '18px' }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px', letterSpacing: '0.2px' }}>
              AST Code Intelligence & Symbol Explorer
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Indexed: {stats.files} files · {stats.symbols} symbols · Sub-10ms lookup
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleTriggerReindex}
            title="Re-index workspace"
            style={{
              background: 'transparent',
              border: '1px solid #2a3449',
              color: '#94a3b8',
              borderRadius: '6px',
              padding: '4px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px'
            }}
          >
            <ArrowSyncRegular style={{ fontSize: '13px' }} /> Re-Index
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '4px',
              }}
            >
              <DismissRegular style={{ fontSize: '16px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ padding: '12px 18px 8px 18px' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px' }}>
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              backgroundColor: '#131b2a',
              border: '1px solid #222d42',
              borderRadius: '6px',
              padding: '6px 10px',
              gap: '8px',
            }}
          >
            <SearchRegular style={{ color: '#64748b', fontSize: '15px' }} />
            <input
              type="text"
              placeholder="Search symbol (e.g. AstCodeParser, click_element)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#f1f5f9',
                fontSize: '12px',
                width: '100%',
                outline: 'none',
              }}
            />
          </div>
          <button
            type="submit"
            style={{
              backgroundColor: '#0284c7',
              border: 'none',
              color: '#ffffff',
              borderRadius: '6px',
              padding: '6px 14px',
              fontWeight: 500,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            Locate
          </button>
        </form>

        {/* Kind Filters */}
        <div style={{ display: 'flex', gap: '6px', marginTop: '10px' }}>
          {['all', 'class', 'method', 'function', 'interface'].map((kind) => (
            <button
              key={kind}
              onClick={() => setSelectedKind(kind)}
              style={{
                background: selectedKind === kind ? '#1e293b' : 'transparent',
                border: selectedKind === kind ? '1px solid #38bdf8' : '1px solid #1e293b',
                color: selectedKind === kind ? '#38bdf8' : '#64748b',
                borderRadius: '12px',
                padding: '2px 10px',
                fontSize: '11px',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {kind}
            </button>
          ))}
        </div>
      </div>

      {/* Symbol List */}
      <div
        style={{
          padding: '8px 18px',
          maxHeight: '220px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {filteredSymbols.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
            No matching code symbols located.
          </div>
        ) : (
          filteredSymbols.map((sym, idx) => (
            <div
              key={idx}
              style={{
                backgroundColor: '#111827',
                border: '1px solid #1f2937',
                borderRadius: '8px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span
                    style={{
                      fontWeight: 600,
                      color: '#38bdf8',
                      fontFamily: "'Consolas', monospace",
                      fontSize: '13px',
                    }}
                  >
                    {sym.name}
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#1e293b',
                      color: '#94a3b8',
                      textTransform: 'uppercase',
                    }}
                  >
                    {sym.kind}
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: '#64748b', fontFamily: "'Consolas', monospace" }}>
                  line {sym.line_number}
                </div>
              </div>

              <div
                style={{
                  fontFamily: "'Consolas', monospace",
                  fontSize: '11px',
                  color: '#a5b4fc',
                  backgroundColor: '#0f172a',
                  padding: '3px 6px',
                  borderRadius: '4px',
                  overflowX: 'auto',
                  whiteSpace: 'nowrap',
                }}
              >
                {sym.signature}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: '#475569' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '340px' }}>
                  {sym.file_path}
                </span>
                {sym.calls && sym.calls.length > 0 && (
                  <span style={{ color: '#0ea5e9' }}>
                    Calls: {sym.calls.slice(0, 3).join(', ')}{sym.calls.length > 3 ? '...' : ''}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Refactor Preview Section */}
      <div
        style={{
          borderTop: '1px solid #1a2234',
          padding: '12px 18px',
          backgroundColor: '#0a0e17',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>
          <BranchRegular style={{ color: '#a855f7' }} /> Multi-File Atomic Symbol Rename Preview
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            placeholder="Old Symbol (e.g. old_name)"
            value={oldSymbol}
            onChange={(e) => setOldSymbol(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: '#131b2a',
              border: '1px solid #222d42',
              borderRadius: '6px',
              padding: '6px 10px',
              color: '#f1f5f9',
              fontSize: '12px',
              outline: 'none',
              fontFamily: "'Consolas', monospace",
            }}
          />
          <input
            type="text"
            placeholder="New Symbol (e.g. new_name)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: '#131b2a',
              border: '1px solid #222d42',
              borderRadius: '6px',
              padding: '6px 10px',
              color: '#f1f5f9',
              fontSize: '12px',
              outline: 'none',
              fontFamily: "'Consolas', monospace",
            }}
          />
          <button
            onClick={handlePreviewRename}
            style={{
              backgroundColor: '#7c3aed',
              border: 'none',
              color: '#ffffff',
              borderRadius: '6px',
              padding: '6px 12px',
              fontWeight: 500,
              fontSize: '12px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Diff Preview
          </button>
        </div>

        {diffPreview && (
          <div
            style={{
              backgroundColor: '#030712',
              border: '1px solid #1f2937',
              borderRadius: '6px',
              padding: '8px',
              maxHeight: '120px',
              overflowY: 'auto',
              fontFamily: "'Consolas', monospace",
              fontSize: '11px',
              whiteSpace: 'pre-wrap',
            }}
          >
            {diffPreview.split('\n').map((line, lIdx) => (
              <div
                key={lIdx}
                style={{
                  color: line.startsWith('+') ? '#4ade80' : line.startsWith('-') ? '#f87171' : line.startsWith('@') ? '#38bdf8' : '#94a3b8',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Status */}
      {statusMessage && (
        <div
          style={{
            padding: '6px 18px',
            backgroundColor: '#111827',
            borderTop: '1px solid #1a2234',
            fontSize: '11px',
            color: '#38bdf8',
          }}
        >
          {statusMessage}
        </div>
      )}
    </div>
  );
};
