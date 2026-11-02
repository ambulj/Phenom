import React from 'react';

export interface HUDCardAction {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
}

export interface HUDCardProps {
  title: string;
  message: string;
  badge?: string;
  type?: 'info' | 'approval' | 'diff' | 'health_reminder';
  diffContent?: string;
  actions?: HUDCardAction[];
  onClose?: () => void;
}

export const HUDCard: React.FC<HUDCardProps> = ({
  title,
  message,
  badge = 'PHENOM HUD',
  type = 'info',
  diffContent,
  actions = [],
  onClose
}) => {
  const getBadgeColor = () => {
    switch (type) {
      case 'approval':
        return '#CCFF00'; // Acid Lime
      case 'danger' as any:
        return '#EF4444'; // Red
      case 'health_reminder':
        return '#38BDF8'; // Sky Cobalt
      default:
        return '#CCFF00'; // Default Acid Lime
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '20px',
        right: '24px',
        width: '380px',
        maxHeight: '80vh',
        backgroundColor: 'rgba(8, 11, 16, 0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 82, 255, 0.35)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.6), 0 0 16px 0 rgba(0, 82, 255, 0.2)',
        borderRadius: '12px',
        padding: '16px',
        color: '#E2E8F0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        animation: 'fadeIn 0.2s ease-out'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '1px',
              padding: '2px 8px',
              borderRadius: '999px',
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              color: getBadgeColor(),
              border: `1px solid ${getBadgeColor()}55`
            }}
          >
            {badge}
          </span>
          <span style={{ fontWeight: 600, fontSize: '14px', color: '#F8FAFC' }}>{title}</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: 'pointer',
              fontSize: '16px',
              padding: '2px 6px',
              borderRadius: '4px'
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Message Body */}
      <div style={{ fontSize: '13px', lineHeight: '1.5', color: '#CBD5E1' }}>
        {message}
      </div>

      {/* Optional Unified Diff Preview */}
      {diffContent && (
        <pre
          style={{
            margin: '4px 0',
            padding: '8px',
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            border: '1px solid rgba(0, 82, 255, 0.25)',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: "'Cascadia Code', Consolas, monospace",
            overflowX: 'auto',
            maxHeight: '160px',
            color: '#CCFF00'
          }}
        >
          {diffContent}
        </pre>
      )}

      {/* Action Buttons */}
      {actions.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
          {actions.map((act, idx) => {
            const isPrimary = act.variant === 'primary' || !act.variant;
            const isDanger = act.variant === 'danger';
            return (
              <button
                key={idx}
                onClick={act.onClick}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isPrimary
                    ? '1px solid #0052FF'
                    : isDanger
                    ? '1px solid #EF4444'
                    : '1px solid rgba(0, 82, 255, 0.3)',
                  backgroundColor: isPrimary
                    ? '#0052FF'
                    : isDanger
                    ? '#EF444422'
                    : 'transparent',
                  color: isPrimary ? '#FFFFFF' : isDanger ? '#EF4444' : '#80B8FF',
                  boxShadow: isPrimary ? '0 0 12px rgba(0, 82, 255, 0.4)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                {act.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
