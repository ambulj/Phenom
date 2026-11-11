import React, { useState } from 'react';
import {
  DismissRegular,
  CursorClickRegular,
  HandRightRegular,
  KeyboardRegular,
  ArrowCounterclockwiseRegular,
  WarningRegular,
  TargetRegular,
} from '@fluentui/react-icons';

interface GroundedActionUI {
  id: string;
  action_type: string;
  target_coords: [number, number];
  target_label: string;
  status: 'EXECUTED' | 'ABORTED_BY_HUMAN' | 'RULE8_BLOCKED';
  latency_ms: number;
  timestamp: string;
}

interface VisionActionGroundingHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const VisionActionGroundingHUD: React.FC<VisionActionGroundingHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [reticleCoords, setReticleCoords] = useState<{ x: number; y: number }>({ x: 960, y: 540 });
  const [targetLabel, setTargetLabel] = useState<string>('Terminal Run Button');
  const [humanTakeover, setHumanTakeover] = useState<boolean>(false);
  const [actionHistory, setActionHistory] = useState<GroundedActionUI[]>([
    {
      id: 'act-1',
      action_type: 'CLICK',
      target_coords: [960, 540],
      target_label: 'Terminal Run Button',
      status: 'EXECUTED',
      latency_ms: 2.14,
      timestamp: '22:01:10',
    },
    {
      id: 'act-2',
      action_type: 'TYPE_TEXT',
      target_coords: [450, 320],
      target_label: 'Search Query Box',
      status: 'EXECUTED',
      latency_ms: 4.88,
      timestamp: '22:01:25',
    },
  ]);

  const handleSimulateAction = (type: string, label: string, x: number, y: number) => {
    setReticleCoords({ x, y });
    setTargetLabel(label);

    const newAct: GroundedActionUI = {
      id: `act-${Date.now()}`,
      action_type: type,
      target_coords: [x, y],
      target_label: label,
      status: humanTakeover ? 'ABORTED_BY_HUMAN' : 'EXECUTED',
      latency_ms: Number((Math.random() * 3 + 1.2).toFixed(2)),
      timestamp: new Date().toLocaleTimeString(),
    };
    setActionHistory((prev) => [newAct, ...prev.slice(0, 9)]);
  };

  const handleSimulateTakeover = () => {
    setHumanTakeover(true);
    const newAct: GroundedActionUI = {
      id: `act-${Date.now()}`,
      action_type: 'CLICK',
      target_coords: [reticleCoords.x, reticleCoords.y],
      target_label: targetLabel,
      status: 'ABORTED_BY_HUMAN',
      latency_ms: 0.85,
      timestamp: new Date().toLocaleTimeString(),
    };
    setActionHistory((prev) => [newAct, ...prev.slice(0, 9)]);
  };

  const handleResetTakeover = () => {
    setHumanTakeover(false);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(8, 10, 18, 0.88)',
        backdropFilter: 'blur(16px)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        color: '#e0e0e0',
        padding: '24px',
        boxSizing: 'border-box',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(0, 229, 255, 0.25)',
          paddingBottom: '16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <TargetRegular style={{ fontSize: '28px', color: '#00e5ff' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, letterSpacing: '0.5px' }}>
              AUTONOMOUS VISION-ACTION GUI GROUNDING & OS-WORLD AUTOMATION
            </h2>
            <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
              Visual Coordinate Prediction • Safe Action Primitives • Instant Human Takeover Watchdog
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '12px',
              backgroundColor: 'rgba(0, 230, 118, 0.15)',
              border: '1px solid rgba(0, 230, 118, 0.4)',
              color: '#00e676',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            RULE 4 LOCAL
          </span>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '12px',
              backgroundColor: humanTakeover ? 'rgba(255, 23, 68, 0.2)' : 'rgba(0, 229, 255, 0.15)',
              border: `1px solid ${humanTakeover ? '#ff1744' : 'rgba(0, 229, 255, 0.4)'}`,
              color: humanTakeover ? '#ff1744' : '#00e5ff',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            {humanTakeover ? 'ABORTED BY HUMAN' : 'TAKEOVER WATCHDOG READY'}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#aaa',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '6px',
            }}
          >
            <DismissRegular style={{ fontSize: '20px' }} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Left Column: Visual Target Canvas */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Target Reticle Canvas */}
          <div
            style={{
              height: '240px',
              backgroundColor: 'rgba(16, 20, 32, 0.6)',
              borderRadius: '8px',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              position: 'relative',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Grid Lines */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                backgroundImage: 'radial-gradient(rgba(0, 229, 255, 0.15) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />

            {/* Reticle Overlay */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                zIndex: 2,
              }}
            >
              <div
                style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '50%',
                  border: `2px dashed ${humanTakeover ? '#ff1744' : '#00e5ff'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: `0 0 20px ${humanTakeover ? '#ff1744' : '#00e5ff'}`,
                }}
              >
                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: humanTakeover ? '#ff1744' : '#00e5ff',
                  }}
                />
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                {targetLabel}
              </div>
              <div style={{ fontSize: '11px', color: '#00e5ff' }}>
                X: {reticleCoords.x}px | Y: {reticleCoords.y}px
              </div>
            </div>
          </div>

          {/* Action Primitives Simulator */}
          <div
            style={{
              padding: '16px',
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#00e5ff' }}>
              Action Primitives Dispatcher
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              <button
                onClick={() => handleSimulateAction('CLICK', 'VS Code Run Test Button', 720, 140)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(0, 229, 255, 0.15)',
                  border: '1px solid #00e5ff',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <CursorClickRegular />
                Click Element
              </button>
              <button
                onClick={() => handleSimulateAction('TYPE_TEXT', 'Editor Buffer', 800, 450)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(213, 0, 249, 0.15)',
                  border: '1px solid #d500f9',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <KeyboardRegular />
                Type Text
              </button>
              <button
                onClick={handleSimulateTakeover}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(255, 23, 68, 0.15)',
                  border: '1px solid #ff1744',
                  color: '#ff1744',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <HandRightRegular />
                Simulate Takeover
              </button>
            </div>
          </div>

          {/* Safety Invariant Notice */}
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '12px',
              color: '#aaa',
            }}
          >
            <WarningRegular style={{ color: '#ffd600', fontSize: '20px' }} />
            <div>
              <strong>Rule 8 & Rule 11 Active:</strong> Anti-checkout filters reject clicks on payment,
              billing, and credit card buttons. Keystrokes on password fields are strictly forbidden.
            </div>
          </div>
        </div>

        {/* Right Column: Takeover Status & Waterfall */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Human Takeover Watchdog Card */}
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: 'rgba(16, 20, 32, 0.6)',
              borderRadius: '8px',
              border: `1px solid ${humanTakeover ? '#ff1744' : '#00e676'}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#888', textTransform: 'uppercase' }}>
                Human Takeover Watchdog
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: humanTakeover ? '#ff1744' : '#00e676',
                }}
              >
                {humanTakeover ? '● ACTIVE INTERRUPT' : '● READY (LISTENING)'}
              </span>
            </div>
            <div style={{ fontSize: '14px', color: '#fff' }}>
              {humanTakeover
                ? 'Physical mouse movement detected! All automated GUI actions are blocked.'
                : 'Hardware cursor motion is synchronized. Automated actions allowed.'}
            </div>
            {humanTakeover && (
              <button
                onClick={handleResetTakeover}
                style={{
                  marginTop: '6px',
                  padding: '8px 14px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(0, 230, 118, 0.2)',
                  border: '1px solid #00e676',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <ArrowCounterclockwiseRegular />
                Reset Takeover Latch
              </button>
            )}
          </div>

          {/* Action Waterfall */}
          <div
            style={{
              flex: 1,
              backgroundColor: 'rgba(16, 20, 32, 0.5)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '12px', color: '#00e5ff' }}>
              Recent Grounded Actions
            </div>
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {actionHistory.map((act) => (
                <div
                  key={act.id}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    borderLeft: `3px solid ${
                      act.status === 'ABORTED_BY_HUMAN'
                        ? '#ff1744'
                        : act.status === 'RULE8_BLOCKED'
                        ? '#ffd600'
                        : '#00e5ff'
                    }`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '12px',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: '#fff' }}>
                      [{act.action_type}] {act.target_label}
                    </div>
                    <div style={{ color: '#888', fontSize: '10px' }}>
                      ({act.target_coords[0]}, {act.target_coords[1]}) • {act.timestamp}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        color: act.status === 'ABORTED_BY_HUMAN' ? '#ff1744' : '#00e5ff',
                      }}
                    >
                      {act.status}
                    </span>
                    <div style={{ fontSize: '10px', color: '#aaa' }}>{act.latency_ms} ms</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
