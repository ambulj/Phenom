import React, { useState, useEffect } from 'react';
import {
  EyeRegular,
  ShieldCheckmarkRegular,
  DismissRegular,
  PlayRegular,
  PauseRegular,
  CameraRegular,
  DesktopRegular,
  WindowRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface ScreenVisionHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export interface TargetOverlay {
  id: string;
  name: string;
  strategy: 'uia_deterministic' | 'visual_fallback';
  rect: { x: number; y: number; width: number; height: number };
  status: 'active' | 'success' | 'blocked';
}

export const ScreenVisionHUD: React.FC<ScreenVisionHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [mode, setMode] = useState<'focused_window' | 'full_desktop'>('focused_window');
  const [activeWindow, setActiveWindow] = useState<string>('Visual Studio Code');
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [lastLatency, setLastLatency] = useState<number>(42.5);
  const [overlayTargets, setOverlayTargets] = useState<TargetOverlay[]>([
    {
      id: 'target-01',
      name: 'Save Document Button',
      strategy: 'uia_deterministic',
      rect: { x: 120, y: 80, width: 140, height: 38 },
      status: 'active'
    }
  ]);
  const [previewUri, setPreviewUri] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'screen.vision_update') {
      const p = externalEvent.payload || {};
      if (p.window_title) setActiveWindow(p.window_title);
      if (p.latency_ms) setLastLatency(p.latency_ms);
      if (p.preview_uri) setPreviewUri(p.preview_uri);
      if (p.targets) setOverlayTargets(p.targets);
    }
  }, [externalEvent]);

  const handleManualCapture = () => {
    setIsCapturing(true);
    if (sendMessage) {
      sendMessage({
        type: 'gui.capture_smart_screen',
        payload: { mode, mask_privacy: true }
      });
    }
    setTimeout(() => setIsCapturing(false), 500);
  };

  const handleTakeoverToggle = () => {
    const nextState = !isPaused;
    setIsPaused(nextState);
    if (sendMessage) {
      sendMessage({
        type: nextState ? 'automation.takeover_pause' : 'automation.takeover_resume',
        payload: { source: 'ScreenVisionHUD' }
      });
    }
  };

  return (
    <div
      style={{
        background: 'rgba(10, 15, 25, 0.95)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.25)',
        borderRadius: '12px',
        padding: '18px',
        color: '#e2e8f0',
        width: '540px',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(0, 240, 255, 0.15)',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #00f0ff 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(0, 240, 255, 0.4)',
            }}
          >
            <EyeRegular style={{ color: '#050b14', fontSize: '18px' }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px', color: '#f8fafc' }}>
              Multimodal Screen Vision Viewport
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Hybrid UIA Deterministic & VLM Vision Agent (VIS-01, GUI-01)
            </div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <DismissRegular style={{ fontSize: '18px' }} />
          </button>
        )}
      </div>

      {/* Status & Rule 8 Banner */}
      <div
        style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '14px',
        }}
      >
        <div
          style={{
            flex: 1,
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px',
            color: '#10b981',
          }}
        >
          <ShieldCheckmarkRegular style={{ fontSize: '16px' }} />
          <span>Rule 8 Shield Active: Payments & Passwords Hard-Blocked</span>
        </div>
        <div
          style={{
            background: 'rgba(0, 240, 255, 0.1)',
            border: '1px solid rgba(0, 240, 255, 0.3)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            color: '#38bdf8',
          }}
        >
          <SparkleRegular style={{ fontSize: '14px' }} />
          <span>{lastLatency.toFixed(1)} ms</span>
        </div>
      </div>

      {/* Screen Mirror Viewport Container */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '240px',
          background: '#040711',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '14px',
        }}
      >
        {previewUri ? (
          <img
            src={previewUri}
            alt="Screen Vision Preview"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div style={{ textAlign: 'center', color: '#64748b' }}>
            <DesktopRegular style={{ fontSize: '40px', marginBottom: '8px', opacity: 0.5 }} />
            <div style={{ fontSize: '12px' }}>Live Smart Context: {activeWindow}</div>
            <div style={{ fontSize: '10px', color: '#475569', marginTop: '4px' }}>In-RAM Zero-Disk Buffer</div>
          </div>
        )}

        {/* Target Bounding Box Overlays */}
        {overlayTargets.map((tgt) => (
          <div
            key={tgt.id}
            style={{
              position: 'absolute',
              left: `${tgt.rect.x}px`,
              top: `${tgt.rect.y}px`,
              width: `${tgt.rect.width}px`,
              height: `${tgt.rect.height}px`,
              border: '2px solid #00f0ff',
              background: 'rgba(0, 240, 255, 0.15)',
              borderRadius: '4px',
              pointerEvents: 'none',
              boxShadow: '0 0 10px rgba(0, 240, 255, 0.5)',
              display: 'flex',
              alignItems: 'flex-start',
              padding: '2px 4px',
            }}
          >
            <span
              style={{
                fontSize: '9px',
                background: '#00f0ff',
                color: '#050b14',
                fontWeight: 'bold',
                padding: '1px 3px',
                borderRadius: '2px',
              }}
            >
              UIA Center
            </span>
          </div>
        ))}
      </div>

      {/* Mode Selector & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setMode('focused_window')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: mode === 'focused_window' ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
              background: mode === 'focused_window' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
              color: mode === 'focused_window' ? '#00f0ff' : '#94a3b8',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <WindowRegular style={{ fontSize: '13px' }} />
            Active Window
          </button>
          <button
            onClick={() => setMode('full_desktop')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: mode === 'full_desktop' ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
              background: mode === 'full_desktop' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
              color: mode === 'full_desktop' ? '#00f0ff' : '#94a3b8',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <DesktopRegular style={{ fontSize: '13px' }} />
            Full Desktop
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleManualCapture}
            disabled={isCapturing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: '1px solid rgba(0, 240, 255, 0.4)',
              background: 'rgba(0, 240, 255, 0.1)',
              color: '#38bdf8',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            <CameraRegular style={{ fontSize: '13px' }} />
            {isCapturing ? 'Capturing...' : 'Capture'}
          </button>

          <button
            onClick={handleTakeoverToggle}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '6px',
              border: isPaused ? '1px solid #10b981' : '1px solid #f59e0b',
              background: isPaused ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: isPaused ? '#10b981' : '#f59e0b',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            {isPaused ? <PlayRegular style={{ fontSize: '13px' }} /> : <PauseRegular style={{ fontSize: '13px' }} />}
            {isPaused ? 'Resume AI' : 'Takeover'}
          </button>
        </div>
      </div>
    </div>
  );
};
