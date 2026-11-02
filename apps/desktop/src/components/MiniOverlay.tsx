import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import {
  DismissCircleFilled,
  PlayFilled,
  ClockRegular,
  FlashRegular,
  WeatherMoonRegular,
  BriefcaseRegular,
  HatGraduationRegular,
  DismissRegular
} from '@fluentui/react-icons';
import { OrbState } from '../types/protocol';

interface MiniOverlayProps {
  orbState: OrbState;
  currentMode: string;
  nextScheduledItem: { title: string; next_run_at: string } | null;
  currentTaskName?: string;
  onCycleMode: () => void;
  onTriggerKillswitch: () => void;
  onResume: () => void;
  onClose: () => void;
}

export const MiniOverlay: React.FC<MiniOverlayProps> = ({
  orbState,
  currentMode,
  nextScheduledItem,
  currentTaskName,
  onCycleMode,
  onTriggerKillswitch,
  onResume,
  onClose
}) => {
  const isHalted = orbState === 'halted';

  const getModeIcon = () => {
    switch (currentMode.toLowerCase()) {
      case 'work':
        return <BriefcaseRegular />;
      case 'study':
        return <HatGraduationRegular />;
      case 'chill':
        return <WeatherMoonRegular />;
      default:
        return <FlashRegular />;
    }
  };

  const getOrbDotColor = () => {
    if (isHalted) return '#EF4444';
    switch (orbState) {
      case 'thinking':
        return '#CCFF00';
      case 'speaking':
        return '#1A66FF';
      case 'listening':
        return '#1A66FF';
      default:
        return '#0052FF';
    }
  };

  const dotColor = getOrbDotColor();

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 16px',
        borderRadius: 14,
        background: 'rgba(8, 11, 16, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 82, 255, 0.35)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.7), 0 0 16px rgba(0, 82, 255, 0.2)',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif'
      }}
    >
      {/* Current Task / State */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: dotColor,
            boxShadow: `0 0 8px ${dotColor}`
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 10, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: 0.5 }}>
            Task
          </span>
          <span style={{ fontSize: 12, fontWeight: 600, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#f8fafc' }}>
            {currentTaskName || (isHalted ? 'Halted' : orbState.toUpperCase())}
          </span>
        </div>
      </div>

      <div style={{ width: 1, height: 24, background: 'rgba(0, 82, 255, 0.2)' }} />

      {/* Next Scheduled Item */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, maxWidth: 180 }}>
        <ClockRegular style={{ fontSize: 16, color: '#CCFF00' }} />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 10, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: 0.5 }}>
            Next Reminder
          </span>
          <span style={{ fontSize: 11, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {nextScheduledItem ? nextScheduledItem.title : 'None scheduled'}
          </span>
        </div>
      </div>

      <div style={{ width: 1, height: 24, background: 'rgba(0, 82, 255, 0.2)' }} />

      {/* Mode Badge & Cycle Toggle */}
      <Badge
        appearance="filled"
        icon={getModeIcon()}
        size="medium"
        style={{
          cursor: 'pointer',
          textTransform: 'uppercase',
          fontWeight: 600,
          fontSize: 11,
          background: 'rgba(0, 82, 255, 0.25)',
          color: '#CCFF00',
          border: '1px solid rgba(0, 82, 255, 0.4)'
        }}
        onClick={onCycleMode}
        title="Click to cycle mode (Work -> Study -> Chill)"
      >
        {currentMode}
      </Badge>

      <div style={{ width: 1, height: 24, background: 'rgba(0, 82, 255, 0.2)' }} />

      {/* Kill Switch */}
      {isHalted ? (
        <Button
          appearance="primary"
          size="small"
          icon={<PlayFilled />}
          style={{ background: 'linear-gradient(135deg, #0052FF, #1a66ff)', color: '#ffffff', fontWeight: 600, border: 'none' }}
          onClick={onResume}
        >
          Resume
        </Button>
      ) : (
        <Button
          appearance="primary"
          size="small"
          icon={<DismissCircleFilled />}
          style={{ background: '#EF4444', color: '#ffffff', fontWeight: 600, border: 'none', boxShadow: '0 0 10px rgba(239, 68, 68, 0.4)' }}
          onClick={onTriggerKillswitch}
        >
          HALT
        </Button>
      )}

      {/* Close Overlay */}
      <Button
        appearance="subtle"
        size="small"
        icon={<DismissRegular />}
        onClick={onClose}
        title="Hide Mini Overlay"
      />
    </div>
  );
};
