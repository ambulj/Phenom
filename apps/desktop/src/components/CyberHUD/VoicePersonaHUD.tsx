import React, { useState, useEffect } from 'react';
import {
  MicRegular,
  SpeakerMuteRegular,
  Speaker2Regular,
  SparkleRegular,
  ChevronDownRegular,
  DismissRegular,
  AlertUrgentRegular,
  BrainCircuitRegular,
  HeartPulseRegular,
  TimerRegular
} from '@fluentui/react-icons';

export interface VoicePersonaHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const VoicePersonaHUD: React.FC<VoicePersonaHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [emotion, setEmotion] = useState<string>('casual');
  const [lockedStyle, setLockedStyle] = useState<string | null>(null);
  const [rate, setRate] = useState<number>(0);
  const [volume, setVolume] = useState<number>(1.0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [lastPrefix, setLastPrefix] = useState<string>('Right you are, Bro.');
  const [isStyleDropdownOpen, setIsStyleDropdownOpen] = useState<boolean>(false);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'VOICE_PERSONA_UPDATED') {
      if (payload?.active_emotion) setEmotion(payload.active_emotion);
      if (payload?.locked_style !== undefined) setLockedStyle(payload.locked_style);
      if (payload?.rate !== undefined) setRate(payload.rate);
      if (payload?.volume !== undefined) setVolume(payload.volume);
      if (payload?.is_muted !== undefined) setIsMuted(payload.is_muted);
      if (payload?.last_prefix) setLastPrefix(payload.last_prefix);
    } else if (type === 'VOICE_PERSONA_HALTED') {
      setIsMuted(true);
      setEmotion('urgent');
      setLastPrefix('Guardian halt engaged.');
    }
  }, [externalEvent]);

  const handleSelectStyle = (style: string | null) => {
    setIsStyleDropdownOpen(false);
    setLockedStyle(style);
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'set_voice_persona_style',
          args: { style: style || 'auto' },
        },
      });
    }
  };

  const handleAdjustRate = (newRate: number) => {
    setRate(newRate);
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'adjust_voice_prosody',
          args: { rate_delta: newRate - rate },
        },
      });
    }
  };

  const handleAdjustVolume = (newVol: number) => {
    setVolume(newVol);
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'adjust_voice_prosody',
          args: { volume_scale: newVol },
        },
      });
    }
  };

  const handleToggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'adjust_voice_prosody',
          args: { volume_scale: nextMuted ? 0.0 : 1.0 },
        },
      });
    }
  };

  const handleReset = () => {
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'reset_voice_persona',
          args: {},
        },
      });
    }
  };

  const getEmotionBadge = () => {
    switch (emotion) {
      case 'urgent':
        return {
          label: 'URGENT',
          color: '#EF4444',
          bg: 'rgba(239, 68, 68, 0.15)',
          border: 'rgba(239, 68, 68, 0.4)',
          icon: <AlertUrgentRegular className="w-3.5 h-3.5 mr-1" />
        };
      case 'frustrated':
        return {
          label: 'FRUSTRATED (CALMING)',
          color: '#F59E0B',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.4)',
          icon: <HeartPulseRegular className="w-3.5 h-3.5 mr-1" />
        };
      case 'excited':
        return {
          label: 'EXCITED',
          color: '#10B981',
          bg: 'rgba(16, 185, 129, 0.15)',
          border: 'rgba(16, 185, 129, 0.4)',
          icon: <SparkleRegular className="w-3.5 h-3.5 mr-1" />
        };
      case 'focused':
        return {
          label: 'FOCUSED (CODE/AST)',
          color: '#06B6D4',
          bg: 'rgba(6, 182, 212, 0.15)',
          border: 'rgba(6, 182, 212, 0.4)',
          icon: <BrainCircuitRegular className="w-3.5 h-3.5 mr-1" />
        };
      case 'calm':
        return {
          label: 'CALM',
          color: '#3B82F6',
          bg: 'rgba(59, 130, 246, 0.15)',
          border: 'rgba(59, 130, 246, 0.4)',
          icon: <TimerRegular className="w-3.5 h-3.5 mr-1" />
        };
      case 'casual':
      default:
        return {
          label: 'WITTY JARVIS',
          color: '#8B5CF6',
          bg: 'rgba(139, 92, 246, 0.15)',
          border: 'rgba(139, 92, 246, 0.4)',
          icon: <MicRegular className="w-3.5 h-3.5 mr-1" />
        };
    }
  };

  const badge = getEmotionBadge();

  return (
    <div
      style={{
        width: '320px',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        borderRadius: '12px',
        padding: '14px',
        color: '#F8FAFC',
        fontFamily: 'Segoe UI, sans-serif',
        fontSize: '12px',
        zIndex: 50,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <SparkleRegular style={{ color: '#0052FF', fontSize: '16px' }} />
          <span style={{ fontWeight: 600, fontSize: '13px', letterSpacing: '0.5px' }}>VOICE PERSONA HUD</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={handleToggleMute}
            style={{
              background: isMuted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              border: isMuted ? '1px solid #EF4444' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '3px 7px',
              cursor: 'pointer',
              color: isMuted ? '#EF4444' : '#E2E8F0',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
            }}
            title={isMuted ? 'Unmute voice' : 'Mute voice'}
          >
            {isMuted ? <SpeakerMuteRegular /> : <Speaker2Regular />}
            <span>{isMuted ? 'Muted' : 'Live'}</span>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94A3B8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '2px',
              }}
            >
              <DismissRegular style={{ fontSize: '14px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Emotion Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 10px',
          borderRadius: '8px',
          background: badge.bg,
          border: `1px solid ${badge.border}`,
          marginBottom: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', color: badge.color, fontWeight: 600 }}>
          {badge.icon}
          <span style={{ fontSize: '11px', letterSpacing: '0.3px' }}>{badge.label}</span>
        </div>
        <span style={{ fontSize: '10px', color: '#94A3B8' }}>
          {lockedStyle ? `Locked: ${lockedStyle}` : 'Dynamic Auto'}
        </span>
      </div>

      {/* Jarvis Witty Prefix Preview */}
      <div
        style={{
          padding: '6px 8px',
          borderRadius: '6px',
          background: 'rgba(0, 0, 0, 0.25)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          marginBottom: '12px',
          fontStyle: 'italic',
          color: '#CBD5E1',
          fontSize: '11px',
        }}
      >
        "{lastPrefix}"
      </div>

      {/* Style Preset Selector */}
      <div style={{ position: 'relative', marginBottom: '12px' }}>
        <label style={{ display: 'block', fontSize: '10px', color: '#94A3B8', marginBottom: '4px', textTransform: 'uppercase' }}>
          Persona Style Preset
        </label>
        <button
          onClick={() => setIsStyleDropdownOpen(!isStyleDropdownOpen)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            padding: '6px 10px',
            color: '#F8FAFC',
            fontSize: '11px',
            cursor: 'pointer',
          }}
        >
          <span>{lockedStyle ? `Locked: ${lockedStyle.toUpperCase()}` : '⚡ Dynamic Adaptive (Auto)'}</span>
          <ChevronDownRegular style={{ fontSize: '12px' }} />
        </button>

        {isStyleDropdownOpen && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              marginTop: '4px',
              background: '#0F172A',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.6)',
              overflow: 'hidden',
              zIndex: 60,
            }}
          >
            {[
              { id: null, label: '⚡ Dynamic Adaptive (Auto)' },
              { id: 'witty_jarvis', label: '🎩 Witty British Jarvis' },
              { id: 'whisper', label: '🌙 Soft Whisper Mode' },
              { id: 'calm', label: '☕ Gentle Calm Cadence' },
              { id: 'fast', label: '⚡ Fast Brisk Briefing' },
              { id: 'urgent', label: '🚨 Priority Emergency' },
              { id: 'normal', label: '🎙️ Baseline Neutral' },
            ].map((s) => (
              <div
                key={s.id || 'auto'}
                onClick={() => handleSelectStyle(s.id)}
                style={{
                  padding: '7px 10px',
                  cursor: 'pointer',
                  fontSize: '11px',
                  color: (lockedStyle === s.id) ? '#38BDF8' : '#E2E8F0',
                  background: (lockedStyle === s.id) ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                }}
              >
                {s.label}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cadence Rate & Volume Sliders */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', fontSize: '10px', color: '#94A3B8' }}>
          <span>CADENCE SPEED</span>
          <span>{rate > 0 ? `+${rate}` : rate}</span>
        </div>
        <input
          type="range"
          min="-5"
          max="5"
          step="1"
          value={rate}
          onChange={(e) => handleAdjustRate(parseInt(e.target.value, 10))}
          style={{ width: '100%', accentColor: '#0052FF', cursor: 'pointer' }}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', fontSize: '10px', color: '#94A3B8' }}>
          <span>VOICE VOLUME</span>
          <span>{Math.round(volume * 100)}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={volume}
          onChange={(e) => handleAdjustVolume(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: '#10B981', cursor: 'pointer' }}
        />
      </div>

      {/* Waveform Bars & Reset */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '14px' }}>
          {[4, 8, 12, 14, 10, 6, 12, 8].map((h, i) => (
            <div
              key={i}
              style={{
                width: '3px',
                height: isMuted ? '2px' : `${h}px`,
                background: isMuted ? '#64748B' : '#0052FF',
                borderRadius: '1px',
                transition: 'height 0.15s ease',
              }}
            />
          ))}
        </div>
        <button
          onClick={handleReset}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#64748B',
            cursor: 'pointer',
            fontSize: '10px',
            textDecoration: 'underline',
          }}
        >
          Reset Baseline
        </button>
      </div>
    </div>
  );
};
