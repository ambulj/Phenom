import React, { useState } from 'react';
import {
  MicRegular,
  MicOffRegular,
  CameraRegular,
  CameraOffRegular,
} from '@fluentui/react-icons';
import { TelepresenceSessionPayload } from '../../types/protocol';

interface OmniModalTelepresenceHUDProps {
  sessionState: TelepresenceSessionPayload | null;
  onToggleMicrophone?: (nextState: 'ACTIVE' | 'MUTED') => void;
  onToggleCamera?: (nextState: 'ACTIVE' | 'SHUTTERED') => void;
}

export const OmniModalTelepresenceHUD: React.FC<OmniModalTelepresenceHUDProps> = ({
  sessionState,
  onToggleMicrophone,
  onToggleCamera,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!sessionState) {
    return null;
  }

  const {
    session_id,
    is_active,
    microphone_state,
    camera_state,
    audio_metrics,
    video_metrics,
    ambient_presence,
  } = sessionState;

  const isMicMuted = microphone_state === 'MUTED' || microphone_state === 'DISABLED';
  const isCamShuttered = camera_state === 'SHUTTERED' || camera_state === 'DISABLED';

  return (
    <div
      style={{
        background: 'rgba(7, 14, 28, 0.94)',
        border: '1px solid #38bdf855',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(56, 189, 248, 0.12)',
        maxWidth: 440,
        width: '100%',
        marginBottom: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: is_active ? '#10b981' : '#f59e0b',
              boxShadow: is_active ? '0 0 8px #10b981' : 'none',
            }}
          />
          <span style={{ fontWeight: 'bold', letterSpacing: 1, color: '#38bdf8' }}>
            OMNI-MODAL AV TELEPRESENCE
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[+ EXPAND]' : '[- MINIMIZE]'}
        </button>
      </div>

      {!isMinimized && (
        <>
          {/* Hardware Sensor Controls & Badges */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 8,
              marginBottom: 12,
            }}
          >
            {/* Microphone Tile */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${isMicMuted ? '#f43f5e44' : '#10b98144'}`,
                borderRadius: 6,
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8', fontSize: 11 }}>MIC HARDWARE</span>
                {isMicMuted ? (
                  <MicOffRegular style={{ color: '#f43f5e' }} />
                ) : (
                  <MicRegular style={{ color: '#10b981' }} />
                )}
              </div>
              <div style={{ fontWeight: 'bold', color: isMicMuted ? '#f43f5e' : '#10b981' }}>
                {microphone_state}
              </div>
              {onToggleMicrophone && (
                <button
                  onClick={() => onToggleMicrophone(isMicMuted ? 'ACTIVE' : 'MUTED')}
                  style={{
                    background: isMicMuted ? '#10b98122' : '#f43f5e22',
                    border: `1px solid ${isMicMuted ? '#10b981' : '#f43f5e'}`,
                    borderRadius: 4,
                    color: isMicMuted ? '#10b981' : '#f43f5e',
                    fontSize: 10,
                    padding: '4px 6px',
                    cursor: 'pointer',
                    marginTop: 2,
                  }}
                >
                  {isMicMuted ? 'UNMUTE MIC' : 'MUTE MIC'}
                </button>
              )}
            </div>

            {/* Camera Tile */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${isCamShuttered ? '#f43f5e44' : '#10b98144'}`,
                borderRadius: 6,
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8', fontSize: 11 }}>CAM SHUTTER</span>
                {isCamShuttered ? (
                  <CameraOffRegular style={{ color: '#f43f5e' }} />
                ) : (
                  <CameraRegular style={{ color: '#10b981' }} />
                )}
              </div>
              <div style={{ fontWeight: 'bold', color: isCamShuttered ? '#f43f5e' : '#10b981' }}>
                {camera_state}
              </div>
              {onToggleCamera && (
                <button
                  onClick={() => onToggleCamera(isCamShuttered ? 'ACTIVE' : 'SHUTTERED')}
                  style={{
                    background: isCamShuttered ? '#10b98122' : '#f43f5e22',
                    border: `1px solid ${isCamShuttered ? '#10b981' : '#f43f5e'}`,
                    borderRadius: 4,
                    color: isCamShuttered ? '#10b981' : '#f43f5e',
                    fontSize: 10,
                    padding: '4px 6px',
                    cursor: 'pointer',
                    marginTop: 2,
                  }}
                >
                  {isCamShuttered ? 'OPEN SHUTTER' : 'CLOSE SHUTTER'}
                </button>
              )}
            </div>
          </div>

          {/* Audio Energy Waveform Meter */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 11 }}>
              <span style={{ color: '#94a3b8' }}>AUDIO RMS ENERGY</span>
              <span style={{ color: '#38bdf8' }}>{(audio_metrics.rms_energy * 100).toFixed(1)}%</span>
            </div>
            <div
              style={{
                width: '100%',
                height: 6,
                background: '#1e293b',
                borderRadius: 3,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, audio_metrics.rms_energy * 100))}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #10b981 0%, #38bdf8 70%, #f43f5e 100%)',
                  transition: 'width 0.1s ease',
                }}
              />
            </div>
          </div>

          {/* Ambient Presence & Vision Telemetry */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.4)',
              border: '1px solid rgba(56, 189, 248, 0.15)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 11,
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Ambient Presence:</span>
              <span style={{ color: ambient_presence ? '#10b981' : '#64748b', fontWeight: 'bold' }}>
                {ambient_presence ? 'USER DETECTED' : 'ROOM EMPTY'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Vision Resolution:</span>
              <span style={{ color: '#cbd5e1' }}>{video_metrics.resolution} @ {video_metrics.fps.toFixed(0)} FPS</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Face Landmarks:</span>
              <span style={{ color: '#cbd5e1' }}>{video_metrics.landmark_count} points</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Privacy Guarantee:</span>
              <span style={{ color: '#10b981' }}>Zero Frame Disk/Cloud Egress</span>
            </div>
          </div>

          <div
            style={{
              fontSize: 10,
              color: '#64748b',
              marginTop: 8,
              textAlign: 'right',
            }}
          >
            Session: {session_id}
          </div>
        </>
      )}
    </div>
  );
};
