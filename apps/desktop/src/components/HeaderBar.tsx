import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import {
  DismissCircleFilled,
  PlayFilled,
  HistoryRegular,
  DocumentBulletListRegular,
  ShieldCheckmarkRegular,
  LightbulbRegular,
  SettingsRegular,
  MicRegular,
  MicOffRegular
} from '@fluentui/react-icons';
import { OrbState } from '../types/protocol';

interface HeaderBarProps {
  orbState: OrbState;
  activePanel: string | null;
  onSelectPanel: (panel: string | null) => void;
  onTriggerKillswitch: () => void;
  onResume: () => void;
  isConnected: boolean;
  isMuted?: boolean;
  onToggleMute?: () => void;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  orbState,
  activePanel,
  onSelectPanel,
  onTriggerKillswitch,
  onResume,
  isConnected,
  isMuted = false,
  onToggleMute
}) => {
  const isHalted = orbState === 'halted';

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 24px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(11, 15, 25, 0.75)',
        backdropFilter: 'blur(12px)',
        zIndex: 20
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: '0.5px', color: '#60a5fa' }}>
          PHENOM
        </h1>
        <Badge
          appearance="tint"
          color={isConnected ? 'success' : 'danger'}
          size="small"
        >
          {isConnected ? 'LIVE' : 'DISCONNECTED'}
        </Badge>
        {isHalted && (
          <Badge appearance="filled" color="danger" size="medium">
            GUARDIAN HALTED
          </Badge>
        )}
        {!isMuted && orbState === 'listening' && (
          <Badge appearance="filled" color="informative" size="small">
            LISTENING
          </Badge>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button
          appearance={activePanel === 'history' ? 'primary' : 'subtle'}
          icon={<HistoryRegular />}
          onClick={() => onSelectPanel(activePanel === 'history' ? null : 'history')}
        >
          History
        </Button>
        <Button
          appearance={activePanel === 'action_log' ? 'primary' : 'subtle'}
          icon={<ShieldCheckmarkRegular />}
          onClick={() => onSelectPanel(activePanel === 'action_log' ? null : 'action_log')}
        >
          Action Log
        </Button>
        <Button
          appearance={activePanel === 'rules' ? 'primary' : 'subtle'}
          icon={<LightbulbRegular />}
          onClick={() => onSelectPanel(activePanel === 'rules' ? null : 'rules')}
        >
          Learned Rules
        </Button>
        <Button
          appearance={activePanel === 'approvals' ? 'primary' : 'subtle'}
          icon={<DocumentBulletListRegular />}
          onClick={() => onSelectPanel(activePanel === 'approvals' ? null : 'approvals')}
        >
          Approvals
        </Button>
        <Button
          appearance={activePanel === 'settings' ? 'primary' : 'subtle'}
          icon={<SettingsRegular />}
          onClick={() => onSelectPanel(activePanel === 'settings' ? null : 'settings')}
        >
          Settings
        </Button>
        <Button
          appearance="subtle"
          icon={isMuted ? <MicOffRegular /> : <MicRegular />}
          onClick={onToggleMute}
          style={{ color: isMuted ? '#f87171' : '#34d399', fontWeight: 500 }}
          title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
        >
          {isMuted ? 'Muted' : 'Mic Active'}
        </Button>
      </div>

      <div>
        {isHalted ? (
          <Button
            appearance="primary"
            style={{ backgroundColor: '#10b981', color: '#fff', fontWeight: 600 }}
            icon={<PlayFilled />}
            onClick={onResume}
          >
            Resume Operations
          </Button>
        ) : (
          <Button
            appearance="primary"
            style={{ backgroundColor: '#ef4444', color: '#fff', fontWeight: 600 }}
            icon={<DismissCircleFilled />}
            onClick={onTriggerKillswitch}
          >
            GUARDIAN KILL
          </Button>
        )}
      </div>
    </header>
  );
};
