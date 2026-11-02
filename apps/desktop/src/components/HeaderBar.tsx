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
  WindowAppsRegular,
  SearchRegular,
  CodeRegular
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
  onOpenPalette?: () => void;
  onToggleConsole?: () => void;
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
  onToggleMiniOverlay,
  onOpenPalette,
  onToggleConsole
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
        borderBottom: '1px solid rgba(0, 82, 255, 0.22)',
        background: 'rgba(13, 17, 26, 0.82)',
        backdropFilter: 'blur(16px)',
        zIndex: 20
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1
          style={{
            fontSize: 19,
            fontWeight: 800,
            letterSpacing: '1.2px',
            background: 'linear-gradient(135deg, #0052FF 0%, #337AFF 50%, #CCFF00 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0
          }}
        >
          ⚡ PHENOM
        </h1>
        <Badge
          appearance="tint"
          size="small"
          style={{
            background: isConnected ? 'rgba(204, 255, 0, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            color: isConnected ? '#CCFF00' : '#ef4444',
            border: isConnected ? '1px solid rgba(204, 255, 0, 0.45)' : '1px solid rgba(239, 68, 68, 0.45)',
            fontWeight: 700,
            letterSpacing: '0.5px'
          }}
        >
          {isConnected ? 'ONLINE' : 'OFFLINE'}
        </Badge>
        <span
          style={{
            fontSize: 11,
            color: '#80b8ff',
            background: 'rgba(0, 82, 255, 0.08)',
            padding: '3px 8px',
            borderRadius: 6,
            border: '1px solid rgba(0, 82, 255, 0.3)',
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
          <Badge
            appearance="filled"
            size="small"
            style={{
              backgroundColor: '#0052FF',
              color: '#ffffff',
              boxShadow: '0 0 10px rgba(0, 82, 255, 0.6)'
            }}
          >
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
        {onOpenPalette && (
          <Button
            appearance="subtle"
            icon={<SearchRegular />}
            onClick={onOpenPalette}
            style={{ color: '#66a3ff' }}
            title="Command Palette (Alt+Space)"
          >
            Palette
          </Button>
        )}
        {onToggleConsole && (
          <Button
            appearance="subtle"
            icon={<CodeRegular />}
            onClick={onToggleConsole}
            style={{ color: '#ccff00' }}
            title="Streaming Terminal Console (Ctrl+`)"
          >
            Console
          </Button>
        )}
        <Button
          appearance="subtle"
          icon={isMuted ? <MicOffRegular /> : <MicRegular />}
          onClick={onToggleMute}
          style={{ color: isMuted ? '#ef4444' : '#ccff00', fontWeight: 600 }}
          title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
        >
          {isMuted ? 'Muted' : 'Mic Active'}
        </Button>
      </div>

      <div>
        {isHalted ? (
          <Button
            appearance="primary"
            style={{ backgroundColor: '#ccff00', color: '#080B10', fontWeight: 700 }}
            icon={<PlayFilled />}
            onClick={onResume}
          >
            Resume Operations
          </Button>
        ) : (
          <Button
            appearance="primary"
            style={{ backgroundColor: '#ef4444', color: '#fff', fontWeight: 700 }}
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
