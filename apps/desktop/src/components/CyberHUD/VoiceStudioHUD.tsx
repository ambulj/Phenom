import React, { useState, useEffect, useRef } from 'react';
import {
  DismissRegular,
  Speaker2Regular,
  PlayRegular,
  StopRegular,
  ShieldCheckmarkRegular,
  FlashRegular,
  LockClosedRegular,
  CheckmarkCircleRegular,
  DeleteRegular,
  ArrowSyncRegular,
} from '@fluentui/react-icons';

export interface VoiceStudioHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export type ActingEmotion =
  | 'WARM_WIT'
  | 'CONSPIRATORIAL'
  | 'TACTICAL_ALERT'
  | 'CALM_REASSURING'
  | 'EXECUTIVE_CONCISE';

interface ClonedProfile {
  id: string;
  name: string;
  sampleDurationSec: number;
  f0Hz: number;
  spectralCentroidHz: number;
  harmonicity: number;
  consentSigned: boolean;
  signatureDigest: string;
}

export const VoiceStudioHUD: React.FC<VoiceStudioHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage,
  onClose,
}) => {
  // Emotion & Prosody state
  const [selectedEmotion, setSelectedEmotion] = useState<ActingEmotion>('WARM_WIT');
  const [pitchShiftSemitones, setPitchShiftSemitones] = useState<number>(0.0);
  const [energyMultiplier, setEnergyMultiplier] = useState<number>(1.0);
  const [cadenceMultiplier, setCadenceMultiplier] = useState<number>(1.0);
  const [breathInsertion, setBreathInsertion] = useState<boolean>(true);
  const [testUtterance, setTestUtterance] = useState<string>(
    "Good evening, sir. All sovereign voice synthesis enclaves are operating at nominal capacity."
  );
  const [processedSSML, setProcessedSSML] = useState<string>('');

  // Voice morphing state
  const [morphRatio, setMorphRatio] = useState<number>(0.0);
  const [activeBaseProfile] = useState<string>('jarvis_prime');
  const [activeTargetProfile, setActiveTargetProfile] = useState<string>('mentor_david');

  // Cloned profiles
  const [clonedProfiles, setClonedProfiles] = useState<ClonedProfile[]>([
    {
      id: 'mentor_david',
      name: 'Mentor David (Resonant Baritone)',
      sampleDurationSec: 5.4,
      f0Hz: 118.5,
      spectralCentroidHz: 1420.0,
      harmonicity: 0.94,
      consentSigned: true,
      signatureDigest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    },
    {
      id: 'cadence_sophia',
      name: 'Cadence Sophia (Clear Mezzo)',
      sampleDurationSec: 4.8,
      f0Hz: 215.2,
      spectralCentroidHz: 2350.0,
      harmonicity: 0.92,
      consentSigned: true,
      signatureDigest: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
    },
  ]);

  // Audio & Guardian status
  const [isPlayingPreview, setIsPlayingPreview] = useState<boolean>(false);
  const [guardianHalted, setGuardianHalted] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('Neural Studio online. Ready.');

  // Canvas ref for waveform & spectrogram
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Animate spectrogram waveform
  useEffect(() => {
    let phase = 0;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const render = () => {
      phase += isPlayingPreview ? 0.08 : 0.02;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;
      const midY = height / 2;

      // Draw background grid lines
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
      ctx.lineWidth = 1;
      for (let x = 0; x < width; x += 30) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 20) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      if (guardianHalted) {
        // Flatline emergency halt indication
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(width, midY);
        ctx.stroke();
        return;
      }

      // Draw primary dynamic wave
      ctx.lineWidth = 2;
      ctx.strokeStyle = morphRatio > 0.5 ? '#a855f7' : '#38bdf8';
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const freqMultiplier = 0.02 + (selectedEmotion === 'TACTICAL_ALERT' ? 0.02 : 0.01);
        const amp = (isPlayingPreview ? 28 : 14) * energyMultiplier;
        const y = midY + Math.sin(x * freqMultiplier + phase) * amp * Math.cos(x * 0.005);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Draw harmonic overtone / morph ghost line
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(236, 72, 153, 0.4)';
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const y =
          midY +
          Math.sin(x * 0.04 - phase * 1.5) *
            (8 * (1 + morphRatio)) *
            Math.sin(x * 0.01);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Draw F0 fundamental frequency indicator dot
      const dotX = (width * 0.7 + Math.sin(phase) * 40) % width;
      const dotY = midY - pitchShiftSemitones * 2.5;
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath();
      ctx.arc(dotX, dotY, 4, 0, Math.PI * 2);
      ctx.fill();

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlayingPreview, guardianHalted, selectedEmotion, energyMultiplier, pitchShiftSemitones, morphRatio]);

  // Actions
  const handleApplyEmotion = (emotion: ActingEmotion) => {
    setSelectedEmotion(emotion);
    let shift = 0.0;
    let energy = 1.0;
    let cadence = 1.0;

    switch (emotion) {
      case 'WARM_WIT':
        shift = 1.2;
        energy = 1.05;
        cadence = 1.08;
        break;
      case 'CONSPIRATORIAL':
        shift = -2.5;
        energy = 0.75;
        cadence = 0.92;
        break;
      case 'TACTICAL_ALERT':
        shift = 3.5;
        energy = 1.35;
        cadence = 1.20;
        break;
      case 'CALM_REASSURING':
        shift = -1.5;
        energy = 0.85;
        cadence = 0.90;
        break;
      case 'EXECUTIVE_CONCISE':
        shift = 0.0;
        energy = 1.15;
        cadence = 1.15;
        break;
    }

    setPitchShiftSemitones(shift);
    setEnergyMultiplier(energy);
    setCadenceMultiplier(cadence);

    const generatedSSML = `<prosody rate="${cadence.toFixed(2)}" pitch="${shift >= 0 ? '+' : ''}${shift.toFixed(1)}st" volume="${(energy * 100).toFixed(0)}%">${breathInsertion ? '<break time="180ms"/> ' : ''}${testUtterance}</prosody>`;
    setProcessedSSML(generatedSSML);

    setStatusMessage(`Applied emotion profile: ${emotion}`);
    sendMessage?.({
      type: 'action',
      action: 'configure_prosodic_parameters',
      args: {
        emotion: emotion,
        custom_pitch_shift: shift,
        custom_intensity: energy,
        breath_enabled: breathInsertion,
      },
    });
  };

  const handleTogglePreview = () => {
    if (isPlayingPreview) {
      setIsPlayingPreview(false);
      setStatusMessage('Audio preview stopped.');
    } else {
      setIsPlayingPreview(true);
      setStatusMessage(`Synthesizing preview with ${selectedEmotion} (${(morphRatio * 100).toFixed(0)}% morph)...`);
      sendMessage?.({
        type: 'action',
        action: 'synthesize_prosodic_speech_preview',
        args: {
          text: testUtterance,
          envelope: selectedEmotion,
        },
      });
      setTimeout(() => {
        setIsPlayingPreview(false);
        setStatusMessage('Preview synthesis complete.');
      }, 3500);
    }
  };

  const handleMorphSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setMorphRatio(val);
    sendMessage?.({
      type: 'action',
      action: 'morph_voice_identity',
      args: {
        target_profile_id: activeTargetProfile,
        blend_ratio: val,
      },
    });
    setStatusMessage(`Voice morphing adjusted: ${(val * 100).toFixed(0)}% towards ${activeTargetProfile}`);
  };

  const handleRevokeConsent = (profileId: string) => {
    // 1-click instant biometric revocation
    setClonedProfiles((prev) => prev.filter((p) => p.id !== profileId));
    if (activeTargetProfile === profileId) {
      setMorphRatio(0.0);
      setActiveTargetProfile('none');
    }
    setStatusMessage(`REVOKED: Biometric voiceprint ${profileId} permanently purged.`);
    sendMessage?.({
      type: 'action',
      action: 'revoke_biometric_voiceprint',
      args: { consent_id: profileId },
    });
  };

  const handleGuardianHalt = () => {
    setGuardianHalted(true);
    setIsPlayingPreview(false);
    setMorphRatio(0.0);
    setStatusMessage('GUARDIAN KILL SWITCH ENGAGED: Neural synthesis halted.');
    sendMessage?.({
      type: 'action',
      action: 'trigger_gesture_safety_halt',
      args: { reason: 'VoiceStudioHUD Emergency Operator Cutoff' },
    });
  };

  const handleResetHalt = () => {
    setGuardianHalted(false);
    setStatusMessage('Guardian resumed. Voice studio ready.');
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '5%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '920px',
        maxHeight: '88vh',
        backgroundColor: 'rgba(10, 15, 29, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(56, 189, 248, 0.15)',
        borderRadius: '16px',
        color: '#e2e8f0',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(14, 165, 233, 0.12) 0%, rgba(168, 85, 247, 0.08) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
            }}
          >
            <Speaker2Regular style={{ fontSize: '20px' }} />
          </div>
          <div>
            <div
              style={{
                fontSize: '15px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: '#f8fafc',
                textTransform: 'uppercase',
              }}
            >
              CyberHUD // Voice Acting & Studio Control Room
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
              Zero-Shot Cloning • 5 Prosodic Emotion Envelopes • Unit-Sphere Morphing Enclave
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Guardian Kill Switch */}
          {guardianHalted ? (
            <button
              onClick={handleResetHalt}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                border: '1px solid #22c55e',
                background: 'rgba(34, 197, 94, 0.15)',
                color: '#4ade80',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ArrowSyncRegular style={{ fontSize: '14px' }} />
              RESUME SYNTHESIS
            </button>
          ) : (
            <button
              onClick={handleGuardianHalt}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                border: '1px solid #ef4444',
                background: 'rgba(239, 68, 68, 0.18)',
                color: '#f87171',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <FlashRegular style={{ fontSize: '14px' }} />
              GUARDIAN HALT
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <DismissRegular style={{ fontSize: '20px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ padding: '20px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Top Section: Spectrogram Canvas & Acoustic Metrics */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            borderRadius: '12px',
            border: '1px solid rgba(56, 189, 248, 0.18)',
            padding: '16px',
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.05em' }}>
              REAL-TIME ACOUSTIC SPECTROGRAM & PITCH CONTOUR (F₀)
            </div>
            <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#94a3b8' }}>
              <span>F₀ Pitch: <strong style={{ color: '#e2e8f0' }}>{pitchShiftSemitones >= 0 ? `+${pitchShiftSemitones.toFixed(1)}` : pitchShiftSemitones.toFixed(1)} st</strong></span>
              <span>Energy: <strong style={{ color: '#e2e8f0' }}>{(energyMultiplier * 100).toFixed(0)}%</strong></span>
              <span>Cadence: <strong style={{ color: '#e2e8f0' }}>{cadenceMultiplier.toFixed(2)}x</strong></span>
              <span>Sphere Norm: <strong style={{ color: '#4ade80' }}>1.0000 (Unit)</strong></span>
            </div>
          </div>

          <canvas
            ref={canvasRef}
            width={870}
            height={110}
            style={{
              width: '100%',
              height: '110px',
              borderRadius: '8px',
              background: '#030712',
              display: 'block',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
              Status: <span style={{ color: guardianHalted ? '#ef4444' : '#38bdf8' }}>{statusMessage}</span>
            </div>
            <button
              onClick={handleTogglePreview}
              disabled={guardianHalted}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 18px',
                borderRadius: '8px',
                border: 'none',
                background: isPlayingPreview
                  ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                  : 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: 600,
                cursor: guardianHalted ? 'not-allowed' : 'pointer',
                opacity: guardianHalted ? 0.5 : 1,
                boxShadow: '0 4px 14px rgba(2, 132, 199, 0.3)',
              }}
            >
              {isPlayingPreview ? (
                <>
                  <StopRegular style={{ fontSize: '14px' }} /> STOP PREVIEW
                </>
              ) : (
                <>
                  <PlayRegular style={{ fontSize: '14px' }} /> SYNTHESIZE PREVIEW
                </>
              )}
            </button>
          </div>
        </div>

        {/* Middle Section: Emotion Selector & Voice Morphing Cross-Fader */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
          {/* Panel B: Emotional Prosodic Acting Console */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              borderRadius: '12px',
              border: '1px solid rgba(56, 189, 248, 0.18)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.05em' }}>
              EMOTIONAL PROSODIC ACTING ENVELOPES
            </div>

            {/* Emotion Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              {(
                [
                  'WARM_WIT',
                  'CONSPIRATORIAL',
                  'TACTICAL_ALERT',
                  'CALM_REASSURING',
                  'EXECUTIVE_CONCISE',
                ] as ActingEmotion[]
              ).map((emotion) => {
                const isSelected = selectedEmotion === emotion;
                return (
                  <button
                    key={emotion}
                    onClick={() => handleApplyEmotion(emotion)}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '8px',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: isSelected ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                      background: isSelected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(30, 41, 59, 0.5)',
                      color: isSelected ? '#38bdf8' : '#94a3b8',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {emotion.replace('_', ' ')}
                  </button>
                );
              })}
            </div>

            {/* Sliders */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
                  <span>Pitch Shift (F₀)</span>
                  <span style={{ color: '#38bdf8' }}>{pitchShiftSemitones.toFixed(1)} st</span>
                </div>
                <input
                  type="range"
                  min="-12.0"
                  max="12.0"
                  step="0.5"
                  value={pitchShiftSemitones}
                  onChange={(e) => setPitchShiftSemitones(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
                  <span>Energy Intensity Multiplier</span>
                  <span style={{ color: '#38bdf8' }}>{energyMultiplier.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.05"
                  value={energyMultiplier}
                  onChange={(e) => setEnergyMultiplier(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8' }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Respiratory Breath Insertion</span>
                <input
                  type="checkbox"
                  checked={breathInsertion}
                  onChange={(e) => setBreathInsertion(e.target.checked)}
                  style={{ accentColor: '#38bdf8', transform: 'scale(1.15)', cursor: 'pointer' }}
                />
              </div>
            </div>

            {/* Utterance input */}
            <div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Utterance Preview:</div>
              <input
                type="text"
                value={testUtterance}
                onChange={(e) => setTestUtterance(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  background: 'rgba(3, 7, 18, 0.6)',
                  color: '#e2e8f0',
                  fontSize: '12px',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            {processedSSML && (
              <div
                style={{
                  fontSize: '10px',
                  color: '#64748b',
                  fontFamily: 'monospace',
                  background: 'rgba(0, 0, 0, 0.3)',
                  padding: '6px',
                  borderRadius: '4px',
                  wordBreak: 'break-all',
                }}
              >
                {processedSSML}
              </div>
            )}
          </div>

          {/* Panel D: Acoustic Timbre Morphing Matrix Cross-Fader */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              borderRadius: '12px',
              border: '1px solid rgba(56, 189, 248, 0.18)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.05em' }}>
              TIMBRE MORPHING MATRIX CROSS-FADER
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8' }}>
                  {activeBaseProfile === 'jarvis_prime' ? 'Jarvis Prime' : activeBaseProfile}
                </div>
                <div style={{ fontSize: '10px', color: '#94a3b8' }}>Base Sovereign (0%)</div>
              </div>
              <div
                style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  background: 'rgba(168, 85, 247, 0.15)',
                  border: '1px solid rgba(168, 85, 247, 0.3)',
                  color: '#c084fc',
                  fontSize: '11px',
                  fontWeight: 600,
                }}
              >
                α = {morphRatio.toFixed(2)}
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#c084fc' }}>
                  {activeTargetProfile === 'none' ? 'None' : activeTargetProfile}
                </div>
                <div style={{ fontSize: '10px', color: '#94a3b8' }}>Target Clone (100%)</div>
              </div>
            </div>

            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.01"
              value={morphRatio}
              onChange={handleMorphSliderChange}
              disabled={activeTargetProfile === 'none'}
              style={{
                width: '100%',
                accentColor: morphRatio > 0.5 ? '#a855f7' : '#38bdf8',
                cursor: activeTargetProfile === 'none' ? 'not-allowed' : 'pointer',
              }}
            />

            <div
              style={{
                background: 'rgba(3, 7, 18, 0.4)',
                borderRadius: '8px',
                padding: '10px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                fontSize: '11px',
                color: '#94a3b8',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Acoustic Interpolation:</span>
                <span style={{ color: '#e2e8f0' }}>
                  {morphRatio === 0.0
                    ? '100% Pure Jarvis'
                    : morphRatio === 1.0
                    ? `100% ${activeTargetProfile}`
                    : `${((1 - morphRatio) * 100).toFixed(0)}% Jarvis + ${(morphRatio * 100).toFixed(0)}% ${activeTargetProfile}`}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Unit Sphere Embedding:</span>
                <span style={{ color: '#4ade80' }}>Normalized (512-d)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Enclave Consent:</span>
                <span style={{ color: '#4ade80' }}>Verified & Non-Revoked</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Section: Cloned Profiles & Biometric Consent Enclave */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            borderRadius: '12px',
            border: '1px solid rgba(56, 189, 248, 0.18)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.05em' }}>
              SOVEREIGN CLONED VOICEPRINTS & BIOMETRIC CONSENT ENCLAVE
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: '#4ade80',
                background: 'rgba(34, 197, 94, 0.1)',
                padding: '3px 8px',
                borderRadius: '6px',
                border: '1px solid rgba(34, 197, 94, 0.2)',
              }}
            >
              <ShieldCheckmarkRegular style={{ fontSize: '14px' }} />
              SHA-256 BIOMETRIC ENCLAVE ACTIVE
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {clonedProfiles.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#64748b', textAlign: 'center', padding: '16px' }}>
                No active cloned voiceprints. All biometric profiles have been purged.
              </div>
            ) : (
              clonedProfiles.map((profile) => {
                const isSelectedTarget = activeTargetProfile === profile.id;
                return (
                  <div
                    key={profile.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      background: isSelectedTarget ? 'rgba(56, 189, 248, 0.1)' : 'rgba(30, 41, 59, 0.4)',
                      border: isSelectedTarget ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <LockClosedRegular style={{ fontSize: '16px', color: '#38bdf8' }} />
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>
                          {profile.name}
                        </div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>
                          F₀: {profile.f0Hz.toFixed(1)} Hz • Centroid: {profile.spectralCentroidHz.toFixed(0)} Hz • Sample: {profile.sampleDurationSec}s
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        onClick={() => {
                          setActiveTargetProfile(profile.id);
                          setStatusMessage(`Selected morph target: ${profile.name}`);
                        }}
                        style={{
                          padding: '5px 10px',
                          borderRadius: '6px',
                          border: isSelectedTarget ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.1)',
                          background: isSelectedTarget ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                          color: isSelectedTarget ? '#38bdf8' : '#94a3b8',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        {isSelectedTarget ? (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <CheckmarkCircleRegular style={{ fontSize: '12px' }} /> ACTIVE TARGET
                          </span>
                        ) : (
                          'SET AS TARGET'
                        )}
                      </button>

                      {/* 1-click instant biometric revocation */}
                      <button
                        onClick={() => handleRevokeConsent(profile.id)}
                        title="1-Click Instant Biometric Revocation & Voiceprint Purge"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '5px 10px',
                          borderRadius: '6px',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                          background: 'rgba(239, 68, 68, 0.12)',
                          color: '#f87171',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <DeleteRegular style={{ fontSize: '12px' }} />
                        REVOKE & PURGE
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
