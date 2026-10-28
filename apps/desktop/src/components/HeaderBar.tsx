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
  MicOffRegular,
  EyeRegular,
  ClockRegular,
  BriefcaseRegular,
  HatGraduationRegular,
  WeatherMoonRegular,
  WindowAppsRegular
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
  currentMode?: string;
  onCycleMode?: () => void;
  showMiniOverlay?: boolean;
  onToggleMiniOverlay?: () => void;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  orbState,
  activePanel,
  onSelectPanel,
  onTriggerKillswitch,
  onResume,
  isConnected,
  isMuted = false,
  onToggleMute,
  currentMode = 'work',
  onCycleMode,
  showMiniOverlay = false,
  onToggleMiniOverlay
}) => {
  const isHalted = orbState === 'halted';

  const getModeColor = (): "brand" | "danger" | "important" | "informative" | "severe" | "subtle" | "success" | "warning" => {
    switch (currentMode.toLowerCase()) {
      case 'work':
        return 'informative';
      case 'study':
        return 'important';
      case 'chill':
        return 'warning';
      default:
        return 'brand';
    }
  };

  const getModeIcon = () => {
    switch (currentMode.toLowerCase()) {
      case 'work':
        return <BriefcaseRegular />;
      case 'study':
        return <HatGraduationRegular />;
      case 'chill':
        return <WeatherMoonRegular />;
      default:
        return <BriefcaseRegular />;
    }
  };

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
        <h1
          style={{
            fontSize: 19,
            fontWeight: 800,
            letterSpacing: '1.2px',
            background: 'linear-gradient(135deg, #38bdf8, #818cf8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0
          }}
        >
          ⚡ PHENOM
        </h1>
        <Badge
          appearance="tint"
          color={isConnected ? 'success' : 'danger'}
          size="small"
        >
          {isConnected ? 'ONLINE' : 'OFFLINE'}
        </Badge>
        <span
          style={{
            fontSize: 11,
            color: '#64748b',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '3px 8px',
            borderRadius: 6,
            border: '1px solid rgba(255, 255, 255, 0.08)',
            fontFamily: 'monospace'
          }}
          title="Local Llama 3 8B model pinned in NVIDIA GPU VRAM"
        >
          CUDA • 8B VRAM
        </span>
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
        {/* Mode Switcher Button */}
        <Badge
          appearance="filled"
          color={getModeColor()}
          icon={getModeIcon()}
          size="medium"
          style={{ cursor: 'pointer', textTransform: 'uppercase', fontWeight: 600, fontSize: 11 }}
          onClick={onCycleMode}
          title="Click to switch assistant mode (Work / Study / Chill)"
        >
          {currentMode} MODE
        </Badge>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button
          appearance={activePanel === 'dashboard' ? 'primary' : 'subtle'}
          icon={<ClockRegular />}
          onClick={() => onSelectPanel(activePanel === 'dashboard' ? null : 'dashboard')}
          title="Open Dashboard & Scheduler"
        >
          Dashboard
        </Button>
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
          appearance={activePanel === 'live_view' ? 'primary' : 'subtle'}
          icon={<EyeRegular />}
          onClick={() => onSelectPanel(activePanel === 'live_view' ? null : 'live_view')}
        >
          Live View
        </Button>
        <Button
          appearance={showMiniOverlay ? 'primary' : 'subtle'}
          icon={<WindowAppsRegular />}
          onClick={onToggleMiniOverlay}
          title="Toggle Mini Overlay widget"
        >
          Overlay
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
