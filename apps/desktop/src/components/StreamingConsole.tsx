import React, { useState, useRef, useEffect } from 'react';

export interface ConsoleLine {
  text: string;
  type?: 'stdout' | 'stderr' | 'system' | 'command';
  timestamp?: string;
}

export interface StreamingConsoleProps {
  isOpen: boolean;
  onToggle: () => void;
  lines: ConsoleLine[];
  onClear?: () => void;
  title?: string;
}

export const StreamingConsole: React.FC<StreamingConsoleProps> = ({
  isOpen,
  onToggle,
  lines,
  onClear,
  title = 'TERMINAL OUTPUT'
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const consoleBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && consoleBottomRef.current) {
      consoleBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, autoScroll]);

  const copyToClipboard = () => {
    const raw = lines.map(l => l.text).join('\n');
    navigator.clipboard.writeText(raw);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: '16px',
          left: '20px',
          zIndex: 9998,
          backgroundColor: 'rgba(8, 11, 16, 0.90)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(0, 82, 255, 0.4)',
          color: '#66a3ff',
          padding: '6px 14px',
          borderRadius: '8px',
          fontSize: '12px',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.5), 0 0 12px rgba(0, 82, 255, 0.25)'
        }}
      >
        <span style={{ color: '#ccff00' }}>▲</span>
        <span>{title} ({lines.length})</span>
      </button>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '16px',
        left: '20px',
        width: '560px',
        height: '240px',
        zIndex: 9998,
        backgroundColor: 'rgba(8, 11, 16, 0.95)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 82, 255, 0.45)',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 82, 255, 0.2)',
        borderRadius: '10px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: "'Cascadia Code', Consolas, monospace"
      }}
    >
      {/* Console Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          backgroundColor: 'rgba(13, 17, 26, 0.85)',
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#ccff00', fontWeight: 700, letterSpacing: '0.5px' }}>
            ● {title}
          </span>
          <span style={{ fontSize: '10px', color: '#94a3b8' }}>
            {lines.length} lines
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            style={{
              background: autoScroll ? 'rgba(204, 255, 0, 0.12)' : 'transparent',
              border: `1px solid ${autoScroll ? '#ccff00' : 'rgba(255, 255, 255, 0.15)'}`,
              color: autoScroll ? '#ccff00' : '#94A3B8',
              fontSize: '10px',
              padding: '2px 8px',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={copyToClipboard}
            style={{
              background: 'transparent',
              border: '1px solid rgba(0, 82, 255, 0.3)',
              color: '#80b8ff',
              fontSize: '10px',
              padding: '2px 8px',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Copy
          </button>
          {onClear && (
            <button
              onClick={onClear}
              style={{
                background: 'transparent',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontSize: '10px',
                padding: '2px 8px',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Clear
            </button>
          )}
          <button
            onClick={onToggle}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              fontSize: '14px',
              padding: '2px 6px',
              cursor: 'pointer'
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Terminal Stream Body */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '10px 14px',
          fontSize: '11px',
          lineHeight: '1.6',
          color: '#F8FAFC',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px'
        }}
      >
        {lines.length === 0 ? (
          <div style={{ color: '#64748B', fontStyle: 'italic' }}>
            No output generated yet. Stream is idle.
          </div>
        ) : (
          lines.map((line, idx) => {
            const getColor = () => {
              switch (line.type) {
                case 'stderr':
                  return '#F87171'; // Red
                case 'command':
                  return '#ccff00'; // Acid Lime
                case 'system':
                  return '#66a3ff'; // Electric Cobalt
                default:
                  return '#E2E8F0'; // Default stdout
              }
            };

            return (
              <div key={idx} style={{ display: 'flex', gap: '8px', wordBreak: 'break-all' }}>
                {line.timestamp && (
                  <span style={{ color: '#475569', userSelect: 'none', minWidth: '55px' }}>
                    {line.timestamp}
                  </span>
                )}
                <span style={{ color: getColor() }}>
                  {line.type === 'command' && <span style={{ color: '#ccff00', marginRight: '4px' }}>❯</span>}
                  {line.text}
                </span>
              </div>
            );
          })
        )}
        <div ref={consoleBottomRef} />
      </div>
    </div>
  );
};
