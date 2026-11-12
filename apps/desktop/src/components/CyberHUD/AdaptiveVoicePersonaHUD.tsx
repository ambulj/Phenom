import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PlayRegular,
  PulseRegular,
  SparkleRegular,
  FlashRegular,
  GaugeRegular
} from '@fluentui/react-icons';

export interface PersonaProfileHUD {
  id: string;
  name: string;
  tagline: string;
  pitch: string;
  rate: string;
  volume: string;
  energy: 'calm' | 'moderate' | 'high' | 'intense';
}

export interface AdaptiveVoicePersonaHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AdaptiveVoicePersonaHUD: React.FC<AdaptiveVoicePersonaHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activePersona, setActivePersona] = useState<string>('witty_jarvis');
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isDucked, setIsDucked] = useState<boolean>(false);
  const [attenuation, setAttenuation] = useState<number>(1.0);
  const [firstChunkLatencyMs, setFirstChunkLatencyMs] = useState<number>(42.8);

  const profiles: PersonaProfileHUD[] = [
    {
      id: 'witty_jarvis',
      name: 'Witty Jarvis',
      tagline: 'Clever cadence, subtle pitch variation, playful British butler banter.',
      pitch: '+5.0%',
      rate: '1.10x',
      volume: '100%',
      energy: 'high'
    },
    {
      id: 'focused_coder',
      name: 'Focused Coder',
      tagline: 'High-speed technical delivery, neutral pitch, zero fluff.',
      pitch: '0.0%',
      rate: '1.25x',
      volume: '85%',
      energy: 'moderate'
    },
    {
      id: 'urgent_alert',
      name: 'Urgent Alert',
      tagline: 'Crisp elevated pitch, maximum velocity, immediate attention.',
      pitch: '+10.0%',
      rate: '1.35x',
      volume: '115%',
      energy: 'intense'
    },
    {
      id: 'calm_briefing',
      name: 'Calm Briefing',
      tagline: 'Warm, low-energy cadence for morning routines and debriefs.',
      pitch: '-5.0%',
      rate: '0.95x',
      volume: '80%',
      energy: 'calm'
    }
  ];

  useEffect(() => {
    if (externalEvent?.type === 'voice.persona_update' && externalEvent.payload) {
      if (externalEvent.payload.persona) setActivePersona(externalEvent.payload.persona);
      if (externalEvent.payload.is_speaking !== undefined) setIsSpeaking(externalEvent.payload.is_speaking);
      if (externalEvent.payload.is_ducked !== undefined) setIsDucked(externalEvent.payload.is_ducked);
      if (externalEvent.payload.attenuation !== undefined) setAttenuation(externalEvent.payload.attenuation);
      if (externalEvent.payload.latency_ms !== undefined) setFirstChunkLatencyMs(externalEvent.payload.latency_ms);
    }
  }, [externalEvent]);

  const handleSelectPersona = (pId: string) => {
    setActivePersona(pId);
    if (sendMessage) {
      sendMessage({
        type: 'voice.set_persona',
        payload: { persona_id: pId }
      });
    }
  };

  const handleTestSpeech = () => {
    setIsSpeaking(true);
    setIsDucked(true);
    setAttenuation(0.20);
    setFirstChunkLatencyMs(Math.round(35 + Math.random() * 20));

    if (sendMessage) {
      sendMessage({
        type: 'voice.synthesize',
        payload: { text: 'Everything is running smoothly, Bro. Systems nominal.', persona: activePersona }
      });
    }

    setTimeout(() => {
      setIsSpeaking(false);
      setIsDucked(false);
      setAttenuation(1.0);
    }, 2500);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(8, 12, 22, 0.95)',
        border: '1px solid rgba(192, 132, 252, 0.4)',
        borderRadius: 14,
        boxShadow: '0 8px 36px rgba(0, 0, 0, 0.75), 0 0 20px rgba(192, 132, 252, 0.2)',
        backdropFilter: 'blur(28px)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        overflow: 'hidden'
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(0, 0, 0, 0.3)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SparkleRegular style={{ fontSize: 20, color: '#c084fc' }} />
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '0.04em', color: '#f8fafc' }}>
            ADAPTIVE NEURAL VOICE & PROSODY STUDIO
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(192, 132, 252, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(192, 132, 252, 0.3)',
              fontWeight: 600
            }}
          >
            VOX-05
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              padding: '2px 8px',
              borderRadius: 4,
              border: '1px solid rgba(16, 185, 129, 0.25)'
            }}
          >
            <FlashRegular style={{ fontSize: 13 }} />
            <span>SLA: {firstChunkLatencyMs}ms (&lt;150ms target)</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleTestSpeech}
            disabled={isSpeaking}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: isSpeaking ? 'rgba(192, 132, 252, 0.2)' : '#9333ea',
              border: 'none',
              color: '#ffffff',
              borderRadius: 6,
              padding: '5px 12px',
              fontSize: 12,
              cursor: isSpeaking ? 'not-allowed' : 'pointer',
              fontWeight: 600
            }}
          >
            <PlayRegular style={{ fontSize: 14 }} />
            <span>{isSpeaking ? 'Speaking...' : 'Test Voice'}</span>
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 4,
              borderRadius: 6
            }}
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left Column: Persona Profiles */}
        <div
          style={{
            flex: 1,
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em' }}>
            SELECT ACTIVE PERSONA PROSODY PROFILE
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {profiles.map((p) => {
              const isSelected = activePersona === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => handleSelectPersona(p.id)}
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    cursor: 'pointer',
                    backgroundColor: isSelected ? 'rgba(192, 132, 252, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${isSelected ? '#c084fc' : 'rgba(255, 255, 255, 0.06)'}`,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? '#c084fc' : '#f8fafc' }}>
                        {p.name}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '1px 6px',
                          borderRadius: 4,
                          backgroundColor:
                            p.energy === 'intense'
                              ? 'rgba(239, 68, 68, 0.2)'
                              : p.energy === 'high'
                              ? 'rgba(234, 179, 8, 0.2)'
                              : 'rgba(56, 189, 248, 0.2)',
                          color:
                            p.energy === 'intense'
                              ? '#fca5a5'
                              : p.energy === 'high'
                              ? '#fbbf24'
                              : '#38bdf8'
                        }}
                      >
                        {p.energy.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6, lineHeight: 1.3 }}>
                      {p.tagline}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                    <span style={{ fontSize: 10, color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: 4 }}>
                      Pitch: {p.pitch}
                    </span>
                    <span style={{ fontSize: 10, color: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: 4 }}>
                      Rate: {p.rate}
                    </span>
                    <span style={{ fontSize: 10, color: '#e2e8f0', backgroundColor: 'rgba(255, 255, 255, 0.1)', padding: '2px 6px', borderRadius: 4 }}>
                      Vol: {p.volume}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Audio Ducking & Waveform Reaction */}
        <div style={{ width: 340, display: 'flex', flexDirection: 'column', backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <GaugeRegular style={{ fontSize: 16, color: '#c084fc' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
              AUDIO DUCKING & 3D FREQUENCY MESH
            </span>
          </div>
          <div style={{ flex: 1, padding: 14, display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Ducking Telemetry Gauge */}
            <div
              style={{
                padding: 12,
                borderRadius: 8,
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.06)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: '#94a3b8' }}>Desktop Audio Ducking</span>
                <span
                  style={{
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    backgroundColor: isDucked ? 'rgba(234, 179, 8, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                    color: isDucked ? '#fbbf24' : '#10b981',
                    fontWeight: 600
                  }}
                >
                  {isDucked ? 'DUCKED (20%)' : 'NORMAL (100%)'}
                </span>
              </div>
              <div style={{ marginTop: 8, height: 6, width: '100%', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 3, overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${attenuation * 100}%`,
                    backgroundColor: isDucked ? '#eab308' : '#10b981',
                    transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b', marginTop: 4 }}>
                <span>Music / Video Sessions</span>
                <span>{Math.round(attenuation * 100)}% Volume</span>
              </div>
            </div>

            {/* Prosody Waveform Simulation */}
            <div
              style={{
                flex: 1,
                padding: 12,
                borderRadius: 8,
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(192, 132, 252, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 8
              }}
            >
              <PulseRegular
                style={{
                  fontSize: 32,
                  color: isSpeaking ? '#c084fc' : '#475569',
                  animation: isSpeaking ? 'pulse 1s infinite' : 'none'
                }}
              />
              <span style={{ fontSize: 11, color: isSpeaking ? '#c084fc' : '#64748b', fontWeight: 500 }}>
                {isSpeaking ? 'Streaming Speech Synthesis (24kHz Mono PCM)' : 'Voice Synthesizer Idle'}
              </span>
              <div style={{ display: 'flex', gap: 3, alignItems: 'center', height: 28, marginTop: 6 }}>
                {[12, 18, 24, 16, 28, 22, 14, 26, 19, 15, 23, 17].map((h, i) => (
                  <div
                    key={i}
                    style={{
                      width: 4,
                      height: isSpeaking ? h : 4,
                      backgroundColor: isSpeaking ? '#c084fc' : '#334155',
                      borderRadius: 2,
                      transition: 'height 0.15s ease'
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
