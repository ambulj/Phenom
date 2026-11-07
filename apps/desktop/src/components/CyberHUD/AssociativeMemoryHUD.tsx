import React, { useState, useEffect } from 'react';
import {
  BrainCircuitRegular,
  SearchRegular,
  DismissRegular,
  DeleteRegular,
  AddRegular,
  ShieldCheckmarkRegular,
  DatabaseRegular
} from '@fluentui/react-icons';

export interface MemoryItem {
  id: string;
  content: string;
  similarity?: number;
  tags: string[];
  source: string;
  created_at: number;
}

export interface AssociativeMemoryHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AssociativeMemoryHUD: React.FC<AssociativeMemoryHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [query, setQuery] = useState<string>('');
  const [newMemoryText, setNewMemoryText] = useState<string>('');
  const [newMemoryTags, setNewMemoryTags] = useState<string>('notes,work');
  const [memories, setMemories] = useState<MemoryItem[]>([
    {
      id: 'mem-001',
      content: 'User prefers concise, witty Jarvis-style male voice responses without markdown bloat.',
      similarity: 0.94,
      tags: ['explicit', 'preferences', 'voice'],
      source: 'user_command',
      created_at: Date.now() / 1000 - 86400
    },
    {
      id: 'mem-002',
      content: 'Milestone 19 architecture delivers sovereign Telegram uplink, screen vision, and proactive daemons.',
      similarity: 0.88,
      tags: ['obsidian', 'milestone19', 'daily_debrief'],
      source: 'obsidian_sync',
      created_at: Date.now() / 1000 - 3600
    }
  ]);
  const [activeCount, setActiveCount] = useState<number>(42);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'memory.recall_results') {
      const p = externalEvent.payload || {};
      if (p.results) setMemories(p.results);
    } else if (externalEvent?.type === 'memory.stats_update') {
      const p = externalEvent.payload || {};
      if (typeof p.active_memories === 'number') setActiveCount(p.active_memories);
    }
  }, [externalEvent]);

  const handleSearch = () => {
    if (!query.trim()) return;
    if (sendMessage) {
      sendMessage({
        type: 'memory.recall',
        payload: { query: query.trim(), top_k: 5 }
      });
    }
  };

  const handleStore = () => {
    if (!newMemoryText.trim()) return;
    const tagList = newMemoryTags.split(',').map((t) => t.trim()).filter(Boolean);
    if (sendMessage) {
      sendMessage({
        type: 'memory.store',
        payload: { content: newMemoryText.trim(), tags: tagList }
      });
    }
    setMemories((prev) => [
      {
        id: `mem-${Date.now().toString(16)}`,
        content: newMemoryText.trim(),
        similarity: 1.0,
        tags: [...tagList, 'explicit'],
        source: 'user_command',
        created_at: Date.now() / 1000
      },
      ...prev
    ]);
    setActiveCount((c) => c + 1);
    setNewMemoryText('');
    setStatusMessage('Permanent memory stored securely in encrypted SQLCipher.');
    setTimeout(() => setStatusMessage(null), 3500);
  };

  const handleDelete = (id: string) => {
    if (sendMessage) {
      sendMessage({
        type: 'memory.delete',
        payload: { memory_id: id }
      });
    }
    setMemories((prev) => prev.filter((m) => m.id !== id));
    setActiveCount((c) => Math.max(0, c - 1));
    setStatusMessage('Memory soft-deleted to recycle bin (Rule 7).');
    setTimeout(() => setStatusMessage(null), 3500);
  };

  return (
    <div
      style={{
        background: 'rgba(10, 15, 25, 0.95)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(129, 140, 248, 0.3)',
        borderRadius: '12px',
        padding: '18px',
        color: '#e2e8f0',
        width: '540px',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(129, 140, 248, 0.15)',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #818cf8 0%, #c084fc 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(129, 140, 248, 0.4)',
            }}
          >
            <BrainCircuitRegular style={{ color: '#050b14', fontSize: '18px' }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px', color: '#f8fafc' }}>
              Associative Long-Term Memory HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              384-d Dense Vector Knowledge Graph & Encrypted Storage (MEM-02, VEC-01)
            </div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <DismissRegular style={{ fontSize: '18px' }} />
          </button>
        )}
      </div>

      {/* Status Badges */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
        <div
          style={{
            flex: 1,
            background: 'rgba(129, 140, 248, 0.12)',
            border: '1px solid rgba(129, 140, 248, 0.35)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px',
            color: '#a5b4fc',
          }}
        >
          <DatabaseRegular style={{ fontSize: '15px' }} />
          <span>{activeCount} Active Indexed Memories (SQLCipher-256)</span>
        </div>
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: '#34d399',
          }}
        >
          <ShieldCheckmarkRegular style={{ fontSize: '15px' }} />
          <span>Rule 7 Recycle Bin Protected</span>
        </div>
      </div>

      {/* Notification Toast Message */}
      {statusMessage && (
        <div
          style={{
            background: 'rgba(129, 140, 248, 0.15)',
            border: '1px solid #818cf8',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '11px',
            color: '#a5b4fc',
            marginBottom: '12px',
          }}
        >
          {statusMessage}
        </div>
      )}

      {/* Semantic Search Box */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Semantic memory query (e.g. 'preferred voice tone', 'milestone plans')..."
          style={{
            flex: 1,
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            color: '#f8fafc',
            outline: 'none',
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '6px',
            border: '1px solid #818cf8',
            background: 'rgba(129, 140, 248, 0.2)',
            color: '#c7d2fe',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <SearchRegular style={{ fontSize: '14px' }} />
          Search
        </button>
      </div>

      {/* Recalled Memories List */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
          Contextual Semantic Memories ({memories.length})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
          {memories.map((m) => (
            <div
              key={m.id}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '6px',
                padding: '10px 12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <div style={{ fontSize: '12px', color: '#f1f5f9', flex: 1, marginRight: '10px' }}>
                  {m.content}
                </div>
                <button
                  onClick={() => handleDelete(m.id)}
                  title="Recycle Memory (Rule 7)"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: '2px',
                  }}
                >
                  <DeleteRegular style={{ fontSize: '14px' }} />
                </button>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {m.tags.map((t) => (
                    <span
                      key={t}
                      style={{
                        fontSize: '9px',
                        background: 'rgba(129, 140, 248, 0.15)',
                        color: '#a5b4fc',
                        padding: '1px 5px',
                        borderRadius: '4px',
                      }}
                    >
                      #{t}
                    </span>
                  ))}
                </div>
                {typeof m.similarity === 'number' && (
                  <div style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 600 }}>
                    {(m.similarity * 100).toFixed(0)}% Match
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Manual "Remember This" Input */}
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '8px',
          padding: '12px',
        }}
      >
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px' }}>
          Explicit Memory Ingestion ("Phenom, remember this:")
        </div>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '6px' }}>
          <input
            type="text"
            value={newMemoryText}
            onChange={(e) => setNewMemoryText(e.target.value)}
            placeholder="Type fact, guideline, or instruction to remember..."
            style={{
              flex: 1,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '11px',
              color: '#f8fafc',
              outline: 'none',
            }}
          />
          <button
            onClick={handleStore}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid #818cf8',
              background: 'rgba(129, 140, 248, 0.25)',
              color: '#f8fafc',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <AddRegular style={{ fontSize: '14px' }} />
            Remember
          </button>
        </div>
        <input
          type="text"
          value={newMemoryTags}
          onChange={(e) => setNewMemoryTags(e.target.value)}
          placeholder="Comma-separated tags (e.g. preferences, project, voice)"
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '4px 2px',
            fontSize: '10px',
            color: '#94a3b8',
            outline: 'none',
          }}
        />
      </div>
    </div>
  );
};
