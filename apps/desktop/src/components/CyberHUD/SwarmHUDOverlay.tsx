import React from 'react';
import { Badge, Button } from '@fluentui/react-components';
import { BotRegular, StopRegular, PauseRegular, PlayRegular } from '@fluentui/react-icons';

export interface SwarmHUDOverlayProps {
  activeRole?: string;
  taskTitle?: string;
  quorumState?: string;
  vramUsedMb?: number;
  maxVramMb?: number;
  isPaused?: boolean;
  onHalt?: () => void;
  onTogglePause?: () => void;
  onOpenPanel?: () => void;
}

export const SwarmHUDOverlay: React.FC<SwarmHUDOverlayProps> = ({
  activeRole = 'coder',
  taskTitle = 'Executing AST Validation',
  quorumState = 'quorum_reached',
  vramUsedMb = 4850,
  maxVramMb = 5632,
  isPaused = false,
  onHalt,
  onTogglePause,
  onOpenPanel,
}) => {
  const isQuorumPass = quorumState === 'quorum_reached';
  const roleColor = {
    architect: '#06b6d4',
    coder: '#10b981',
    security_auditor: '#f59e0b',
    web_scout: '#a855f7',
  }[activeRole.toLowerCase()] || '#38bdf8';

  const vramPercent = Math.min(100, Math.round((vramUsedMb / maxVramMb) * 100));

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: '10px',
        padding: '12px 16px',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, sans-serif',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        minWidth: '380px',
      }}
    >
      <div
        onClick={onOpenPanel}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
      >
        <div
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: roleColor,
            boxShadow: `0 0 10px ${roleColor}`,
          }}
        />
        <BotRegular style={{ fontSize: '20px', color: '#38bdf8' }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: roleColor, fontWeight: 700 }}>
            {activeRole.replace('_', ' ')}
          </span>
          <Badge
            appearance="filled"
            color={isQuorumPass ? 'success' : 'warning'}
            style={{ fontSize: '10px', height: '18px' }}
          >
            {isQuorumPass ? 'Quorum Pass' : 'Quorum Pending'}
          </Badge>
          <span style={{ fontSize: '10px', color: '#94a3b8' }}>
            VRAM: {vramPercent}%
          </span>
        </div>
        <div
          style={{
            fontSize: '12px',
            color: '#cbd5e1',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '220px',
          }}
        >
          {taskTitle}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Button
          size="small"
          appearance="subtle"
          icon={isPaused ? <PlayRegular /> : <PauseRegular />}
          onClick={onTogglePause}
        />
        <Button
          size="small"
          appearance="primary"
          style={{ backgroundColor: '#ef4444', color: '#ffffff' }}
          icon={<StopRegular />}
          onClick={onHalt}
        >
          HALT
        </Button>
      </div>
    </div>
  );
};
