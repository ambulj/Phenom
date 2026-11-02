import React, { useState, useEffect, useRef } from 'react';

export interface CommandItem {
  id: string;
  title: string;
  subtitle?: string;
  category: 'Dev' | 'Git' | 'System' | 'Journal' | 'Assistant';
  shortcut?: string;
  onExecute: () => void;
}

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  commands: CommandItem[];
  onSubmitQuery?: (query: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  commands,
  onSubmitQuery
}) => {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filtered = commands.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    (c.subtitle && c.subtitle.toLowerCase().includes(search.toLowerCase())) ||
    c.category.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (filtered.length ? (prev + 1) % filtered.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (filtered.length ? (prev - 1 + filtered.length) % filtered.length : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered.length > 0 && filtered[selectedIndex]) {
        filtered[selectedIndex].onExecute();
        onClose();
      } else if (search.trim() && onSubmitQuery) {
        onSubmitQuery(search.trim());
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.70)',
        backdropFilter: 'blur(12px)',
        zIndex: 10000,
        display: 'flex',
        justifyContent: 'center',
        paddingTop: '15vh'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '600px',
          maxHeight: '440px',
          backgroundColor: 'rgba(8, 11, 16, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 82, 255, 0.4)',
          borderRadius: '14px',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.8), 0 0 24px rgba(0, 82, 255, 0.2)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          fontFamily: "'Segoe UI', -apple-system, sans-serif"
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Search Bar Input */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '14px 18px',
            borderBottom: '1px solid rgba(0, 82, 255, 0.2)',
            gap: '12px'
          }}
        >
          <span style={{ color: '#0052FF', fontSize: '18px', fontWeight: 'bold' }}>⌕</span>
          <input
            ref={inputRef}
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or ask Phenom..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#F8FAFC',
              fontSize: '15px'
            }}
          />
          <span
            style={{
              fontSize: '11px',
              color: '#94A3B8',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              padding: '2px 6px',
              borderRadius: '4px'
            }}
          >
            ESC to close
          </span>
        </div>

        {/* Command Items List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontSize: '13px' }}>
              Press <b style={{ color: '#ccff00' }}>Enter</b> to submit: "{search}"
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.onExecute();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    backgroundColor: isSelected ? 'rgba(0, 82, 255, 0.16)' : 'transparent',
                    border: isSelected ? '1px solid rgba(0, 82, 255, 0.4)' : '1px solid transparent',
                    borderLeft: isSelected ? '3px solid #ccff00' : '3px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.1s ease'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: isSelected ? '#ccff00' : '#F1F5F9' }}>
                        {item.title}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          color: '#80b8ff',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(0, 82, 255, 0.12)',
                          border: '1px solid rgba(0, 82, 255, 0.25)'
                        }}
                      >
                        {item.category}
                      </span>
                    </div>
                    {item.subtitle && (
                      <span style={{ fontSize: '11px', color: '#64748B' }}>{item.subtitle}</span>
                    )}
                  </div>

                  {item.shortcut && (
                    <span
                      style={{
                        fontSize: '11px',
                        color: '#ccff00',
                        backgroundColor: 'rgba(204, 255, 0, 0.08)',
                        border: '1px solid rgba(204, 255, 0, 0.3)',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontFamily: 'monospace'
                      }}
                    >
                      {item.shortcut}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
