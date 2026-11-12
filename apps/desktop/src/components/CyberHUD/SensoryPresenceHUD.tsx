import React, { useState } from 'react';
import {
  DismissRegular,
  EyeRegular,
  CameraOffRegular,
  CameraRegular,
  Speaker2Regular,
  ShieldCheckmarkRegular,
  FlashRegular,
  ArrowSyncRegular,
} from '@fluentui/react-icons';

export interface SensoryPresenceHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SensoryPresenceHUD: React.FC<SensoryPresenceHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage,
  onClose,
}) => {
  // Gaze state
  const [eyeContact, setEyeContact] = useState<boolean>(true);
  const [yaw, setYaw] = useState<number>(3.5);
  const [pitch, setPitch] = useState<number>(-2.1);
  const [attentionScore, setAttentionScore] = useState<number>(0.92);
  const [touchlessListening, setTouchlessListening] = useState<boolean>(true);
  const [conversationalPaused, setConversationalPaused] = useState<boolean>(false);

  // Gesture state
  const [detectedGesture, setDetectedGesture] = useState<string>('INDEX_POINT');
  const [gestureConfidence, setGestureConfidence] = useState<number>(0.94);
  const [pointingTarget, setPointingTarget] = useState<{ x: number; y: number } | null>({ x: 0.62, y: 0.45 });
  const [emergencyHaltTriggered, setEmergencyHaltTriggered] = useState<boolean>(false);

  // Proximity & acoustic state
  const [distanceMeters, setDistanceMeters] = useState<number>(0.68);
  const [acousticVolume, setAcousticVolume] = useState<number>(0.38);
  const [speechRate, setSpeechRate] = useState<number>(1.02);
  const [orbScale, setOrbScale] = useState<number>(1.35);
  const [privacyShutterActive, setPrivacyShutterActive] = useState<boolean>(false);
  const [guardianHalted, setGuardianHalted] = useState<boolean>(false);

  const handleTogglePrivacyShutter = () => {
    const nextState = !privacyShutterActive;
    setPrivacyShutterActive(nextState);
    if (nextState) {
      setEyeContact(false);
      setDetectedGesture('NONE');
      setPointingTarget(null);
    }
    sendMessage?.({
      type: 'action',
      action: 'toggle_camera_privacy_shutter',
      args: { enabled: nextState },
    });
  };

  const handleTriggerEmergencyHalt = () => {
    setGuardianHalted(true);
    setEmergencyHaltTriggered(true);
    sendMessage?.({
      type: 'action',
      action: 'trigger_gesture_safety_halt',
      args: { reason: 'Manual CyberHUD Sensory Presence emergency halt' },
    });
  };

  const handleSimulateLookAway = () => {
    if (eyeContact) {
      setEyeContact(false);
      setYaw(42.0);
      setPitch(-15.0);
      setAttentionScore(0.18);
      setTouchlessListening(false);
      setConversationalPaused(true);
    } else {
      setEyeContact(true);
      setYaw(2.0);
      setPitch(-1.5);
      setAttentionScore(0.95);
      setTouchlessListening(true);
      setConversationalPaused(false);
    }
  };

  const handleCycleGesture = () => {
    const gestures = ['OPEN_PALM', 'RAISED_PALM', 'INDEX_POINT', 'SWIPE_LEFT', 'SWIPE_RIGHT', 'THUMBS_UP', 'NONE'];
    const nextIdx = (gestures.indexOf(detectedGesture) + 1) % gestures.length;
    const nextGesture = gestures[nextIdx];
    setDetectedGesture(nextGesture);
    setGestureConfidence(nextGesture === 'NONE' ? 0.0 : 0.94);
    if (nextGesture === 'INDEX_POINT') {
      setPointingTarget({ x: 0.55, y: 0.40 });
    } else if (nextGesture === 'RAISED_PALM') {
      setPointingTarget(null);
      setEmergencyHaltTriggered(true);
      setGuardianHalted(true);
    } else {
      setPointingTarget(null);
    }
  };

  const handleAdjustDistance = (delta: number) => {
    const newDist = Math.max(0.3, Math.min(3.5, distanceMeters + delta));
    setDistanceMeters(parseFloat(newDist.toFixed(2)));
    const ratio = (newDist - 0.3) / 3.2;
    setAcousticVolume(parseFloat((0.25 + ratio * 0.75).toFixed(2)));
    setSpeechRate(parseFloat((1.05 - ratio * 0.12).toFixed(2)));
    setOrbScale(parseFloat((1.60 - ratio * 0.75).toFixed(2)));
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        right: '24px',
        width: '680px',
        maxHeight: 'calc(100vh - 100px)',
        backgroundColor: 'rgba(12, 17, 29, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 240, 255, 0.28)',
        borderRadius: '14px',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.75), 0 0 25px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        zIndex: 9999,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: guardianHalted ? '#ff3b30' : privacyShutterActive ? '#ff9500' : '#00f0ff',
              boxShadow: `0 0 10px ${guardianHalted ? '#ff3b30' : privacyShutterActive ? '#ff9500' : '#00f0ff'}`,
            }}
          />
          <span style={{ fontSize: '15px', fontWeight: 600, letterSpacing: '0.5px' }}>
            CyberHUD Sensory Presence OS
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '10px',
              backgroundColor: 'rgba(0, 240, 255, 0.15)',
              color: '#00f0ff',
              border: '1px solid rgba(0, 240, 255, 0.3)',
            }}
          >
            Milestone 33.0
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Main Content */}
      <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Top Control Bar: Privacy Shutter & Guardian Emergency Stop */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleTogglePrivacyShutter}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 16px',
              borderRadius: '8px',
              border: privacyShutterActive
                ? '1px solid rgba(255, 59, 48, 0.5)'
                : '1px solid rgba(0, 240, 255, 0.4)',
              backgroundColor: privacyShutterActive
                ? 'rgba(255, 59, 48, 0.15)'
                : 'rgba(0, 240, 255, 0.1)',
              color: privacyShutterActive ? '#ff3b30' : '#00f0ff',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '13px',
              transition: 'all 0.2s',
            }}
          >
            {privacyShutterActive ? <CameraOffRegular /> : <CameraRegular />}
            {privacyShutterActive ? 'Camera Shutter CLOSED (Buffers Wiped)' : 'Camera Shutter OPEN (Active)'}
          </button>

          <button
            onClick={handleTriggerEmergencyHalt}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 18px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 59, 48, 0.6)',
              backgroundColor: guardianHalted ? '#ff3b30' : 'rgba(255, 59, 48, 0.2)',
              color: '#ffffff',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '13px',
            }}
          >
            <FlashRegular />
            {guardianHalted ? 'GUARDIAN HALTED' : 'Emergency Halt (<15ms)'}
          </button>
        </div>

        {/* Sensory Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
          {/* Card 1: Attentive Gaze & Engagement */}
          <div
            style={{
              padding: '16px',
              borderRadius: '10px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <EyeRegular style={{ color: eyeContact ? '#34c759' : '#ff9500', fontSize: '18px' }} />
                <span style={{ fontSize: '13px', fontWeight: 600 }}>Attentive Gaze</span>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: eyeContact ? 'rgba(52, 199, 89, 0.15)' : 'rgba(255, 149, 0, 0.15)',
                  color: eyeContact ? '#34c759' : '#ff9500',
                }}
              >
                {eyeContact ? 'DIRECT CONTACT' : 'LOOKING AWAY'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8' }}>
              <span>Yaw: <strong style={{ color: '#e2e8f0' }}>{yaw}°</strong></span>
              <span>Pitch: <strong style={{ color: '#e2e8f0' }}>{pitch}°</strong></span>
              <span>Score: <strong style={{ color: '#00f0ff' }}>{(attentionScore * 100).toFixed(0)}%</strong></span>
            </div>

            {/* Engagement Progress Bar */}
            <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '3px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${(attentionScore * 100).toFixed(0)}%`,
                  height: '100%',
                  backgroundColor: eyeContact ? '#34c759' : '#ff9500',
                  transition: 'width 0.3s',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
              <button
                onClick={handleSimulateLookAway}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  fontSize: '11px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: '#e2e8f0',
                  cursor: 'pointer',
                }}
              >
                Toggle Eye Contact
              </button>
            </div>
          </div>

          {/* Card 2: Touchless Spatial Gestures */}
          <div
            style={{
              padding: '16px',
              borderRadius: '10px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheckmarkRegular style={{ color: '#00f0ff', fontSize: '18px' }} />
                <span style={{ fontSize: '13px', fontWeight: 600 }}>Spatial Gestures</span>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(0, 240, 255, 0.15)',
                  color: '#00f0ff',
                }}
              >
                {detectedGesture}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8' }}>
              <span>Confidence: <strong style={{ color: '#e2e8f0' }}>{(gestureConfidence * 100).toFixed(0)}%</strong></span>
              <span>Target: <strong style={{ color: '#00f0ff' }}>{pointingTarget ? `(${pointingTarget.x}, ${pointingTarget.y})` : 'None'}</strong></span>
            </div>

            <div style={{ fontSize: '11px', color: emergencyHaltTriggered ? '#ff3b30' : '#94a3b8' }}>
              {emergencyHaltTriggered ? 'Raised Palm Emergency Stop Tripped' : 'Open-Palm Kill Switch: Armed (<15ms)'}
            </div>

            <button
              onClick={handleCycleGesture}
              style={{
                padding: '6px 10px',
                fontSize: '11px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: '#e2e8f0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              <ArrowSyncRegular /> Cycle Gesture State
            </button>
          </div>
        </div>

        {/* Card 3: Proximity Adaptation & Acoustic Scaling */}
        <div
          style={{
            padding: '16px',
            borderRadius: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Speaker2Regular style={{ color: '#38bdf8', fontSize: '18px' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Metric Proximity & Dynamic Acoustics</span>
            </div>
            <span style={{ fontSize: '12px', color: '#38bdf8', fontWeight: 600 }}>
              Distance: {distanceMeters}m ({distanceMeters < 0.8 ? 'Desk Range' : 'Room Range'})
            </span>
          </div>

          {/* Metric Meters Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', textAlign: 'center' }}>
            <div style={{ padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>TTS Volume Multiplier</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#38bdf8', marginTop: '2px' }}>
                {(acousticVolume * 100).toFixed(0)}%
              </div>
            </div>
            <div style={{ padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Speech Cadence Scale</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#38bdf8', marginTop: '2px' }}>
                {speechRate}x
              </div>
            </div>
            <div style={{ padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Orb Particle Multiplier</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#38bdf8', marginTop: '2px' }}>
                {orbScale}x
              </div>
            </div>
          </div>

          {/* Distance Adjusters */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => handleAdjustDistance(-0.25)}
              style={{
                flex: 1,
                padding: '6px 12px',
                fontSize: '11px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: '#e2e8f0',
                cursor: 'pointer',
              }}
            >
              Step Closer (-0.25m)
            </button>
            <button
              onClick={() => handleAdjustDistance(0.25)}
              style={{
                flex: 1,
                padding: '6px 12px',
                fontSize: '11px',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: '#e2e8f0',
                cursor: 'pointer',
              }}
            >
              Step Further (+0.25m)
            </button>
          </div>
        </div>

        {/* Privacy & Invariant Telemetry Footer */}
        <div
          style={{
            padding: '10px 14px',
            borderRadius: '8px',
            backgroundColor: 'rgba(0, 240, 255, 0.05)',
            border: '1px solid rgba(0, 240, 255, 0.15)',
            fontSize: '11px',
            color: '#94a3b8',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <span>Privacy: <strong>100% On-Device In-RAM Ring Buffer (Zero Disk)</strong></span>
          <span>Touchless Listening: <strong style={{ color: touchlessListening ? '#34c759' : '#94a3b8' }}>{touchlessListening ? 'ACTIVE' : 'IDLE'}</strong></span>
          <span>Speech Pause: <strong style={{ color: conversationalPaused ? '#ff9500' : '#34c759' }}>{conversationalPaused ? 'PAUSED' : 'RESUMED'}</strong></span>
        </div>
      </div>
    </div>
  );
};
