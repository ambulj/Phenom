import React from 'react';

export interface ProactiveCardData {
  id: string;
  event_type: string;
  priority: number; // 1: BACKGROUND, 2: NORMAL, 3: URGENT
  title: string;
  description: string;
  action_chip?: string | null;
  action_payload?: Record<string, any> | null;
  timestamp?: number;
}

export interface ProactiveCardToastProps {
  card: ProactiveCardData;
  onExecuteAction?: (card: ProactiveCardData) => void;
  onDismiss?: (cardId: string) => void;
}

export const ProactiveCardToast: React.FC<ProactiveCardToastProps> = ({
  card,
  onExecuteAction,
  onDismiss,
}) => {
  const isUrgent = card.priority >= 3;

  return (
    <div
      className="phenom-proactive-toast-container"
      style={{
        pointerEvents: 'auto',
        background: 'rgba(8, 15, 28, 0.92)',
        border: `1px solid ${isUrgent ? 'rgba(239, 68, 68, 0.5)' : 'rgba(0, 229, 255, 0.4)'}`,
        borderRadius: 12,
        padding: '12px 16px',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.8)',
        color: '#f8fafc',
        maxWidth: 400,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: isUrgent ? '#ef4444' : '#00e5ff', textTransform: 'uppercase' }}>
          PROACTIVE: {card.event_type}
        </span>
        <button
          onClick={() => onDismiss?.(card.id)}
          style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}
        >
          &times;
        </button>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600 }}>{card.title}</div>
      <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.4 }}>{card.description}</div>
      {card.action_chip && (
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button
            onClick={() => onExecuteAction?.(card)}
            style={{
              background: isUrgent ? '#ef4444' : '#0052ff',
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {card.action_chip}
          </button>
        </div>
      )}
    </div>
  );
};
