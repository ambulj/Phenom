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
        background: 'rgba(15, 23, 42, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)',
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
            background:
              isHalted ? '#ef4444' :
              orbState === 'thinking' ? '#8b5cf6' :
              orbState === 'speaking' ? '#f59e0b' :
              orbState === 'listening' ? '#06b6d4' : '#10b981',
            boxShadow: `0 0 8px ${
              isHalted ? '#ef4444' :
              orbState === 'thinking' ? '#8b5cf6' :
              orbState === 'speaking' ? '#f59e0b' :
              orbState === 'listening' ? '#06b6d4' : '#10b981'
            }`
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 10, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: 0.5 }}>
            Task
          </span>
          <span style={{ fontSize: 12, fontWeight: 600, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {currentTaskName || (isHalted ? 'Halted' : orbState.toUpperCase())}
          </span>
        </div>
      </div>

      <div style={{ width: 1, height: 24, background: 'rgba(255, 255, 255, 0.1)' }} />

      {/* Next Scheduled Item */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, maxWidth: 180 }}>
        <ClockRegular style={{ fontSize: 16, color: '#38bdf8' }} />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 10, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: 0.5 }}>
            Next Reminder
          </span>
          <span style={{ fontSize: 11, color: '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {nextScheduledItem ? nextScheduledItem.title : 'None scheduled'}
          </span>
        </div>
      </div>

      <div style={{ width: 1, height: 24, background: 'rgba(255, 255, 255, 0.1)' }} />

      {/* Mode Badge & Cycle Toggle */}
      <Badge
        appearance="filled"
        color={getModeColor()}
        icon={getModeIcon()}
        size="medium"
        style={{ cursor: 'pointer', textTransform: 'uppercase', fontWeight: 600, fontSize: 11 }}
        onClick={onCycleMode}
        title="Click to cycle mode (Work -> Study -> Chill)"
      >
        {currentMode}
      </Badge>

      <div style={{ width: 1, height: 24, background: 'rgba(255, 255, 255, 0.1)' }} />

      {/* Kill Switch */}
      {isHalted ? (
        <Button
          appearance="primary"
          size="small"
          icon={<PlayFilled />}
          style={{ background: '#10b981', color: '#ffffff', fontWeight: 600 }}
          onClick={onResume}
        >
          Resume
        </Button>
      ) : (
        <Button
          appearance="primary"
          size="small"
          icon={<DismissCircleFilled />}
          style={{ background: '#ef4444', color: '#ffffff', fontWeight: 600 }}
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
