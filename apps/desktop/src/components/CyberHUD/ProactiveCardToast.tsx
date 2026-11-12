import React from 'react';
import { HUDCard, HUDCardAction } from '../HUDCard';

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
  const actions: HUDCardAction[] = [];

  if (card.action_chip) {
    actions.push({
      label: card.action_chip,
      onClick: () => onExecuteAction?.(card),
      variant: card.priority >= 3 ? 'danger' : 'primary',
    });
  }

  actions.push({
    label: 'Dismiss',
    onClick: () => onDismiss?.(card.id),
    variant: 'secondary',
  });

  const badgeText = `PROACTIVE ${card.event_type.toUpperCase()}`;
  const cardType = card.priority >= 3 ? 'approval' : 'info';

  return (
    <div className="phenom-proactive-toast-container" style={{ pointerEvents: 'auto' }}>
      <HUDCard
        title={card.title}
        message={card.description}
        badge={badgeText}
        type={cardType}
        actions={actions}
        onClose={() => onDismiss?.(card.id)}
      />
    </div>
  );
};
