import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  DesktopRegular,
  LayoutRowTwoRegular,
  GridDotsRegular,
  ArrowResetRegular,
  CheckmarkCircleRegular,
} from '@fluentui/react-icons';

export interface DisplayInfoHUD {
  display_id: string;
  name: string;
  is_primary: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
  dpi_scale: number;
}

export interface WindowPlacementHUD {
  app_identifier: string;
  display_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface SpatialLayoutHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SpatialLayoutHUD: React.FC<SpatialLayoutHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activePreset, setActivePreset] = useState<string>('coding_focus');
  const [displays] = useState<DisplayInfoHUD[]>([
    {
      display_id: 'DISPLAY_1',
      name: 'Primary Studio Display (4K)',
      is_primary: true,
      x: 0,
      y: 0,
      width: 2560,
      height: 1440,
      dpi_scale: 1.25,
    },
    {
      display_id: 'DISPLAY_2',
      name: 'Secondary Reference (Portrait)',
      is_primary: false,
      x: 2560,
      y: 0,
      width: 1080,
      height: 1920,
      dpi_scale: 1.0,
    },
  ]);

  const [placements, setPlacements] = useState<WindowPlacementHUD[]>([
    { app_identifier: 'code', display_id: 'DISPLAY_1', x: 0, y: 0, width: 1792, height: 1440 },
    { app_identifier: 'terminal', display_id: 'DISPLAY_1', x: 1792, y: 0, width: 768, height: 1440 },
    { app_identifier: 'chrome', display_id: 'DISPLAY_2', x: 2560, y: 0, width: 1080, height: 1920 },
  ]);

  const [lastAction, setLastAction] = useState<string>('Preset applied: Deep Coding Focus');

  useEffect(() => {
    if (externalEvent?.type === 'spatial.layout_update' && externalEvent.payload) {
      if (externalEvent.payload.preset_id) setActivePreset(externalEvent.payload.preset_id);
      if (externalEvent.payload.placements) setPlacements(externalEvent.payload.placements);
    }
  }, [externalEvent]);

  const handleApplyPreset = (presetId: string, name: string) => {
    setActivePreset(presetId);
    setLastAction(`Preset applied: ${name}`);

    if (presetId === 'coding_focus') {
      setPlacements([
        { app_identifier: 'code', display_id: 'DISPLAY_1', x: 0, y: 0, width: 1792, height: 1440 },
        { app_identifier: 'terminal', display_id: 'DISPLAY_1', x: 1792, y: 0, width: 768, height: 1440 },
        { app_identifier: 'chrome', display_id: 'DISPLAY_2', x: 2560, y: 0, width: 1080, height: 1920 },
      ]);
    } else if (presetId === 'debugging_split') {
      setPlacements([
        { app_identifier: 'code', display_id: 'DISPLAY_1', x: 0, y: 0, width: 1280, height: 1440 },
        { app_identifier: 'chrome', display_id: 'DISPLAY_1', x: 1280, y: 0, width: 1280, height: 1440 },
        { app_identifier: 'terminal', display_id: 'DISPLAY_2', x: 2560, y: 0, width: 1080, height: 1920 },
      ]);
    } else if (presetId === 'research_reading') {
      setPlacements([
        { app_identifier: 'chrome', display_id: 'DISPLAY_1', x: 0, y: 0, width: 1536, height: 1440 },
        { app_identifier: 'obsidian', display_id: 'DISPLAY_1', x: 1536, y: 0, width: 1024, height: 1440 },
      ]);
    } else if (presetId === 'monitoring_grid') {
      setPlacements([
        { app_identifier: 'terminal', display_id: 'DISPLAY_1', x: 0, y: 0, width: 1280, height: 720 },
        { app_identifier: 'metrics', display_id: 'DISPLAY_1', x: 1280, y: 0, width: 1280, height: 720 },
        { app_identifier: 'logs', display_id: 'DISPLAY_1', x: 0, y: 720, width: 1280, height: 720 },
        { app_identifier: 'hud', display_id: 'DISPLAY_1', x: 1280, y: 720, width: 1280, height: 720 },
      ]);
    }

    if (sendMessage) {
      sendMessage({
        type: 'spatial.apply_layout_preset',
        payload: { preset_id: presetId },
      });
    }
  };

  const handleRollback = () => {
    setLastAction('Layout reverted to previous snapshot (Rule 7)');
    if (sendMessage) {
      sendMessage({ type: 'spatial.rollback_layout' });
    }
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(56, 189, 248, 0.18)',
        display: 'flex',
        flexDirection: 'column',
        color: '#e2e8f0',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'rgba(3, 105, 161, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <DesktopRegular style={{ fontSize: 22, color: '#38bdf8' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#7dd3fc' }}>
              MULTI-DISPLAY SPATIAL CANVAS & WINDOW CHOREOGRAPHY
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 22-03 • Multi-Monitor Topology & Reversible Task Presets (DSP-01 / WIN-03)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleRollback}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(234, 179, 8, 0.15)',
              color: '#facc15',
              border: '1px solid rgba(234, 179, 8, 0.3)',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <ArrowResetRegular style={{ fontSize: 14 }} />
            <span>Rollback (Rule 7)</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: 4,
                display: 'flex',
              }}
            >
              <DismissRegular style={{ fontSize: 18 }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Preset Selector Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          {[
            { id: 'coding_focus', name: 'Coding Focus', icon: LayoutRowTwoRegular, desc: '70/30 IDE & Terminal' },
            { id: 'debugging_split', name: 'Debugging Split', icon: LayoutRowTwoRegular, desc: '50/50 Dual Pane' },
            { id: 'research_reading', name: 'Research Reading', icon: LayoutRowTwoRegular, desc: '60/40 Docs & Notes' },
            { id: 'monitoring_grid', name: 'Telemetry Grid', icon: GridDotsRegular, desc: '2x2 Dashboard Quadrants' },
          ].map((preset) => {
            const isSel = activePreset === preset.id;
            const Icon = preset.icon;
            return (
              <button
                key={preset.id}
                onClick={() => handleApplyPreset(preset.id, preset.name)}
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: isSel ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  border: isSel ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                  color: isSel ? '#7dd3fc' : '#cbd5e1',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Icon style={{ fontSize: 18, color: isSel ? '#38bdf8' : '#94a3b8' }} />
                  {isSel && <CheckmarkCircleRegular style={{ fontSize: 14, color: '#38bdf8' }} />}
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 6 }}>{preset.name}</div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{preset.desc}</div>
              </button>
            );
          })}
        </div>

        {/* Spatial Display Topology Visualizer */}
        <div
          style={{
            flex: 1,
            minHeight: 260,
            background: 'rgba(0, 0, 0, 0.4)',
            borderRadius: 8,
            border: '1px solid rgba(56, 189, 248, 0.2)',
            padding: 16,
            display: 'flex',
            gap: 16,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* Display 1 (Landscape 16:9) */}
          <div
            style={{
              width: 380,
              height: 220,
              borderRadius: 6,
              background: 'rgba(15, 23, 42, 0.8)',
              border: '2px solid rgba(56, 189, 248, 0.6)',
              display: 'flex',
              flexDirection: 'column',
              padding: 8,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#7dd3fc', marginBottom: 4 }}>
              <span>DISPLAY 1 (PRIMARY)</span>
              <span>2560 × 1440 @ 1.25x</span>
            </div>

            {/* Placements visual representation */}
            <div style={{ flex: 1, display: 'flex', gap: 4 }}>
              {activePreset === 'coding_focus' && (
                <>
                  <div style={{ flex: 7, background: 'rgba(56, 189, 248, 0.25)', border: '1px solid #38bdf8', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#bae6fd' }}>
                    VS Code (70%)
                  </div>
                  <div style={{ flex: 3, background: 'rgba(16, 185, 129, 0.25)', border: '1px solid #10b981', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#a7f3d0' }}>
                    Terminal (30%)
                  </div>
                </>
              )}
              {activePreset === 'debugging_split' && (
                <>
                  <div style={{ flex: 5, background: 'rgba(56, 189, 248, 0.25)', border: '1px solid #38bdf8', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#bae6fd' }}>
                    Debugger (50%)
                  </div>
                  <div style={{ flex: 5, background: 'rgba(234, 179, 8, 0.25)', border: '1px solid #facc15', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fef08a' }}>
                    Browser (50%)
                  </div>
                </>
              )}
              {activePreset === 'research_reading' && (
                <>
                  <div style={{ flex: 6, background: 'rgba(234, 179, 8, 0.25)', border: '1px solid #facc15', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#fef08a' }}>
                    Chrome Docs (60%)
                  </div>
                  <div style={{ flex: 4, background: 'rgba(168, 85, 247, 0.25)', border: '1px solid #c084fc', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: '#e9d5ff' }}>
                    Obsidian Vault (40%)
                  </div>
                </>
              )}
              {activePreset === 'monitoring_grid' && (
                <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 4 }}>
                  <div style={{ background: 'rgba(56, 189, 248, 0.2)', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#7dd3fc' }}>Terminal</div>
                  <div style={{ background: 'rgba(16, 185, 129, 0.2)', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#6ee7b7' }}>Metrics</div>
                  <div style={{ background: 'rgba(234, 179, 8, 0.2)', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#fde047' }}>Logs</div>
                  <div style={{ background: 'rgba(168, 85, 247, 0.2)', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: '#d8b4fe' }}>HUD</div>
                </div>
              )}
            </div>
          </div>

          {/* Display 2 (Portrait 9:16) */}
          <div
            style={{
              width: 140,
              height: 220,
              borderRadius: 6,
              background: 'rgba(15, 23, 42, 0.8)',
              border: '2px solid rgba(148, 163, 184, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              padding: 8,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', fontSize: 9, color: '#94a3b8', marginBottom: 4 }}>
              <span>DISPLAY 2</span>
              <span>1080 × 1920 (Portrait)</span>
            </div>

            <div style={{ flex: 1, background: 'rgba(234, 179, 8, 0.15)', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fef08a', textAlign: 'center', padding: 4 }}>
              {activePreset === 'coding_focus' ? 'Browser Docs Reference' : 'Telemetry Stream'}
            </div>
          </div>
        </div>

        {/* Action Ticker & Reversibility Banner */}
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            fontSize: 12,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ color: '#38bdf8' }}>{lastAction}</span>
          <span style={{ color: '#94a3b8', fontSize: 11 }}>Reversible snapshot stored in memory</span>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '8px 20px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: '#64748b',
        }}
      >
        <div>Monitors: {displays.length} detected • Windows: {placements.length} choreographed • Virtual Desktop: 3640 × 1920 px</div>
        <div>Rule 7 Reversibility • Guardian Halt &lt; 25.0ms SLA</div>
      </div>
    </div>
  );
};
