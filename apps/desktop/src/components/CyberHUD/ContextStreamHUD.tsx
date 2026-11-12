import React, { useState, useEffect } from 'react';
import {
  BrainCircuitRegular,
  CodeRegular,
  GlobeRegular,
  WindowConsoleRegular,
  DocumentBulletListRegular,
  ChatRegular,
  DeleteRegular,
  ArrowSyncRegular,
  DismissRegular,
  DesktopRegular
} from '@fluentui/react-icons';

export interface ContextStreamHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

interface ContextItemDTO {
  id: string;
  timestamp: number;
  source: string;
  category: string;
  summary: string;
}

interface ForegroundWindowDTO {
  hwnd: number;
  title: string;
  process_name: string;
  pid: number;
  category: string;
  active_document?: string | null;
}

export const ContextStreamHUD: React.FC<ContextStreamHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [foreground, setForeground] = useState<ForegroundWindowDTO | null>({
    hwnd: 100,
    title: 'main.py - Phenom - Visual Studio Code',
    process_name: 'code.exe',
    pid: 1420,
    category: 'ide',
    active_document: 'main.py',
  });
  const [recentItems, setRecentItems] = useState<ContextItemDTO[]>([
    {
      id: 'ctx-1',
      timestamp: Date.now() / 1000 - 30,
      source: 'window_focus',
      category: 'ide',
      summary: 'Focus switched to code.exe (main.py)',
    },
    {
      id: 'ctx-2',
      timestamp: Date.now() / 1000 - 15,
      source: 'window_focus',
      category: 'browser',
      summary: 'Focus switched to chrome.exe (FastAPI Documentation)',
    },
  ]);
  const [categories, setCategories] = useState<Record<string, string[]>>({
    ide: ['code.exe'],
    browser: ['chrome.exe'],
    terminal: ['windowsterminal.exe'],
  });
  const [isFrozen, setIsFrozen] = useState<boolean>(false);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'CONTEXT_STREAM_UPDATED') {
      if (payload?.foreground) setForeground(payload.foreground);
      if (payload?.recent_items) setRecentItems(payload.recent_items);
      if (payload?.categories) setCategories(payload.categories);
      setIsFrozen(false);
    } else if (type === 'CONTEXT_STREAM_CLEARED') {
      setRecentItems([]);
    } else if (type === 'CONTEXT_TRACKER_HALTED') {
      setIsFrozen(true);
      setRecentItems([]);
    }
  }, [externalEvent]);

  const handleRefresh = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'get_active_workspace_context',
          args: {},
        },
      });
    }
  };

  const handleClearContext = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'clear_workspace_context',
          args: {},
        },
      });
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'ide':
        return <CodeRegular style={{ color: '#38BDF8' }} />;
      case 'browser':
        return <GlobeRegular style={{ color: '#34D399' }} />;
      case 'terminal':
        return <WindowConsoleRegular style={{ color: '#FBBF24' }} />;
      case 'notes':
        return <DocumentBulletListRegular style={{ color: '#A78BFA' }} />;
      case 'communication':
        return <ChatRegular style={{ color: '#F472B6' }} />;
      default:
        return <DesktopRegular style={{ color: '#94A3B8' }} />;
    }
  };

  return (
    <div
      style={{
        width: '340px',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        borderRadius: '12px',
        padding: '14px',
        color: '#F8FAFC',
        fontFamily: 'Segoe UI, sans-serif',
        fontSize: '12px',
        zIndex: 50,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <BrainCircuitRegular style={{ color: '#38BDF8', fontSize: '16px' }} />
          <span style={{ fontWeight: 600, fontSize: '13px', letterSpacing: '0.5px' }}>CONTEXT FUSION HUD</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={handleRefresh}
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '3px 7px',
              cursor: 'pointer',
              color: '#E2E8F0',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
            }}
            title="Sample active workspace"
          >
            <ArrowSyncRegular style={{ fontSize: '12px' }} />
          </button>
          <button
            onClick={handleClearContext}
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '6px',
              padding: '3px 7px',
              cursor: 'pointer',
              color: '#EF4444',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
            }}
            title="Flush in-RAM context ring buffer"
          >
            <DeleteRegular style={{ fontSize: '12px' }} />
            <span>Flush</span>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '2px',
              }}
            >
              <DismissRegular style={{ fontSize: '14px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Foreground Active App Badge */}
      <div
        style={{
          background: 'rgba(56, 189, 248, 0.1)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: '8px',
          padding: '8px 10px',
          marginBottom: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
          <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Active Foreground App</span>
          <span
            style={{
              fontSize: '10px',
              padding: '1px 6px',
              borderRadius: '4px',
              background: 'rgba(56, 189, 248, 0.2)',
              color: '#38BDF8',
              fontWeight: 600,
              textTransform: 'uppercase',
            }}
          >
            {foreground ? foreground.category : 'None'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12px', color: '#F8FAFC' }}>
          {foreground ? getCategoryIcon(foreground.category) : <DesktopRegular />}
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {foreground?.active_document || foreground?.process_name || 'No active window'}
          </span>
        </div>
        {foreground?.title && (
          <div style={{ fontSize: '11px', color: '#94A3B8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '2px' }}>
            {foreground.title}
          </div>
        )}
      </div>

      {/* Connected Domain Pills */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', marginBottom: '4px' }}>
          Running Domains
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {Object.entries(categories).map(([cat, procs]) => (
            <div
              key={cat}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '10px',
                color: '#CBD5E1',
              }}
            >
              {getCategoryIcon(cat)}
              <span style={{ textTransform: 'capitalize' }}>{cat}</span>
              <span style={{ color: '#64748B' }}>({procs.length})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Context Stream */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>In-RAM Semantic Stream</span>
          <span style={{ fontSize: '10px', color: isFrozen ? '#EF4444' : '#10B981' }}>
            {isFrozen ? '● FROZEN' : '● ACTIVE'}
          </span>
        </div>

        <div
          style={{
            maxHeight: '130px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          {recentItems.length === 0 ? (
            <div style={{ fontSize: '11px', color: '#64748B', fontStyle: 'italic', padding: '6px' }}>
              Buffer empty. Switch windows to sample context.
            </div>
          ) : (
            recentItems.map((item) => (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '6px',
                  padding: '5px 8px',
                  borderRadius: '6px',
                  background: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  fontSize: '11px',
                }}
              >
                <div style={{ marginTop: '2px' }}>{getCategoryIcon(item.category)}</div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ color: '#E2E8F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.summary}
                  </div>
                  <div style={{ fontSize: '9px', color: '#64748B' }}>
                    {new Date(item.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
