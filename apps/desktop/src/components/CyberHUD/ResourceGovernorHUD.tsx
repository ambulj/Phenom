import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PulseRegular,
  GaugeRegular,
  ArrowResetRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
} from '@fluentui/react-icons';

export interface HostTelemetryState {
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  vram_allocated_mb: number;
  vram_total_mb: number;
  vram_percent: number;
  temperature_c: number;
  composite_load_rating: number;
  throttle_state: 'NORMAL' | 'CONSERVE' | 'EMERGENCY_THROTTLE';
  timestamp: string;
}

export interface ThrottleConfigState {
  state: 'NORMAL' | 'CONSERVE' | 'EMERGENCY_THROTTLE';
  max_concurrency: number;
  background_indexing_paused: boolean;
  context_window_cap: number;
  vram_headroom_mb: number;
  manual_override: boolean;
}

interface ResourceGovernorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const ResourceGovernorHUD: React.FC<ResourceGovernorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [telemetry, setTelemetry] = useState<HostTelemetryState>({
    cpu_percent: 24.5,
    ram_used_gb: 9.8,
    ram_total_gb: 32.0,
    ram_percent: 30.6,
    vram_allocated_mb: 2840.0,
    vram_total_mb: 8192.0,
    vram_percent: 34.7,
    temperature_c: 48.2,
    composite_load_rating: 0.32,
    throttle_state: 'NORMAL',
    timestamp: new Date().toISOString(),
  });

  const [config, setConfig] = useState<ThrottleConfigState>({
    state: 'NORMAL',
    max_concurrency: 4,
    background_indexing_paused: false,
    context_window_cap: 8192,
    vram_headroom_mb: 1024.0,
    manual_override: false,
  });

  const [headroomInput, setHeadroomInput] = useState<number>(1024);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'governor.telemetry_update' && externalEvent.payload) {
      if (externalEvent.payload.telemetry) setTelemetry(externalEvent.payload.telemetry);
      if (externalEvent.payload.config) setConfig(externalEvent.payload.config);
    }
  }, [externalEvent]);

  const handleSimulateLoad = (load: number) => {
    let state: 'NORMAL' | 'CONSERVE' | 'EMERGENCY_THROTTLE' = 'NORMAL';
    let concurrency = 4;
    let bgPaused = false;
    let ctxCap = 8192;
    let vramMb = 1024.0;

    if (load >= 0.85) {
      state = 'EMERGENCY_THROTTLE';
      concurrency = 1;
      bgPaused = true;
      ctxCap = 2048;
      vramMb = 2048.0;
    } else if (load >= 0.65) {
      state = 'CONSERVE';
      concurrency = 2;
      bgPaused = false;
      ctxCap = 4096;
      vramMb = 1536.0;
    }

    const cpu = Math.round(load * 100);
    const ram = +(load * 32.0).toFixed(1);
    const vram = +(load * 8192.0).toFixed(1);
    const temp = +(40.0 + load * 45.0).toFixed(1);

    setTelemetry({
      cpu_percent: cpu,
      ram_used_gb: ram,
      ram_total_gb: 32.0,
      ram_percent: cpu,
      vram_allocated_mb: vram,
      vram_total_mb: 8192.0,
      vram_percent: cpu,
      temperature_c: temp,
      composite_load_rating: load,
      throttle_state: state,
      timestamp: new Date().toISOString(),
    });

    if (!config.manual_override) {
      setConfig({
        state,
        max_concurrency: concurrency,
        background_indexing_paused: bgPaused,
        context_window_cap: ctxCap,
        vram_headroom_mb: vramMb,
        manual_override: false,
      });
    }

    setFeedback(`Simulated host stress rating: ${(load * 100).toFixed(0)}% -> State: ${state}`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleSetMode = (mode: 'NORMAL' | 'CONSERVE' | 'EMERGENCY_THROTTLE') => {
    let concurrency = 4;
    let bgPaused = false;
    let ctxCap = 8192;
    let vramMb = 1024.0;

    if (mode === 'EMERGENCY_THROTTLE') {
      concurrency = 1;
      bgPaused = true;
      ctxCap = 2048;
      vramMb = 2048.0;
    } else if (mode === 'CONSERVE') {
      concurrency = 2;
      bgPaused = false;
      ctxCap = 4096;
      vramMb = 1536.0;
    }

    setConfig({
      state: mode,
      max_concurrency: concurrency,
      background_indexing_paused: bgPaused,
      context_window_cap: ctxCap,
      vram_headroom_mb: vramMb,
      manual_override: true,
    });

    if (sendMessage) {
      sendMessage({
        type: 'governor.set_mode',
        payload: { throttle_mode: mode },
      });
    }

    setFeedback(`Manual throttle override engaged: ${mode}`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleResetOverride = () => {
    let state: 'NORMAL' | 'CONSERVE' | 'EMERGENCY_THROTTLE' = 'NORMAL';
    if (telemetry.composite_load_rating >= 0.85) state = 'EMERGENCY_THROTTLE';
    else if (telemetry.composite_load_rating >= 0.65) state = 'CONSERVE';

    let concurrency = state === 'EMERGENCY_THROTTLE' ? 1 : state === 'CONSERVE' ? 2 : 4;
    let bgPaused = state === 'EMERGENCY_THROTTLE';
    let ctxCap = state === 'EMERGENCY_THROTTLE' ? 2048 : state === 'CONSERVE' ? 4096 : 8192;

    setConfig({
      state,
      max_concurrency: concurrency,
      background_indexing_paused: bgPaused,
      context_window_cap: ctxCap,
      vram_headroom_mb: 1024.0,
      manual_override: false,
    });

    if (sendMessage) {
      sendMessage({
        type: 'governor.reset_override',
        payload: {},
      });
    }

    setFeedback('Manual override cleared. Re-anchored to auto telemetry governor.');
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleApplyHeadroom = () => {
    setConfig(prev => ({
      ...prev,
      vram_headroom_mb: headroomInput,
      manual_override: true,
    }));

    if (sendMessage) {
      sendMessage({
        type: 'governor.override_headroom',
        payload: { vram_headroom_mb: headroomInput },
      });
    }

    setFeedback(`VRAM safety headroom overridden to ${headroomInput} MB.`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const getStateColor = (s: string) => {
    switch (s) {
      case 'NORMAL':
        return '#00ffcc';
      case 'CONSERVE':
        return '#f59e0b';
      case 'EMERGENCY_THROTTLE':
        return '#ff0055';
      default:
        return '#38bdf8';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 480,
        backgroundColor: '#0a0d14',
        border: '1px solid #1f293d',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.8), 0 0 16px rgba(0, 255, 204, 0.1)',
        color: '#e2e8f0',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        zIndex: 9999,
        overflow: 'hidden',
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'linear-gradient(90deg, rgba(0, 255, 204, 0.08) 0%, rgba(10, 13, 20, 0) 100%)',
          borderBottom: '1px solid #1f293d',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <GaugeRegular style={{ color: '#00ffcc', fontSize: 18 }} />
          <span style={{ fontWeight: 600, fontSize: 13, letterSpacing: '0.05em', color: '#f8fafc' }}>
            PREDICTIVE RESOURCE GOVERNOR
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: config.manual_override ? 'rgba(245, 158, 11, 0.2)' : 'rgba(0, 255, 204, 0.2)',
              color: config.manual_override ? '#f59e0b' : '#00ffcc',
              fontWeight: 600,
            }}
          >
            {config.manual_override ? 'MANUAL' : 'AUTOPILOT'}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
          >
            <DismissRegular style={{ fontSize: 16 }} />
          </button>
        )}
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Throttle State Banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 14px',
            borderRadius: 8,
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            border: `1px solid ${getStateColor(config.state)}44`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <PulseRegular style={{ color: getStateColor(config.state), fontSize: 20 }} />
            <div>
              <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Governor Policy State
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: getStateColor(config.state) }}>
                {config.state}
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>Load Rating</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9' }}>
              {(telemetry.composite_load_rating * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Telemetry Metric Bars */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 10,
            backgroundColor: '#070a0f',
            padding: 12,
            borderRadius: 8,
            border: '1px solid #1e293b',
          }}
        >
          {/* CPU */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>Host CPU</span>
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>{telemetry.cpu_percent}%</span>
            </div>
            <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
              <div
                style={{
                  width: `${Math.min(100, telemetry.cpu_percent)}%`,
                  height: '100%',
                  backgroundColor: '#38bdf8',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>

          {/* RAM */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>RAM Usage</span>
              <span style={{ color: '#a855f7', fontWeight: 600 }}>
                {telemetry.ram_used_gb.toFixed(1)} / {telemetry.ram_total_gb.toFixed(0)} GB
              </span>
            </div>
            <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
              <div
                style={{
                  width: `${Math.min(100, telemetry.ram_percent)}%`,
                  height: '100%',
                  backgroundColor: '#a855f7',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>

          {/* VRAM */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>CUDA VRAM</span>
              <span style={{ color: '#00ffcc', fontWeight: 600 }}>
                {telemetry.vram_allocated_mb.toFixed(0)} / {telemetry.vram_total_mb.toFixed(0)} MB
              </span>
            </div>
            <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
              <div
                style={{
                  width: `${Math.min(100, telemetry.vram_percent)}%`,
                  height: '100%',
                  backgroundColor: '#00ffcc',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>

          {/* Thermal */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>Package Temp</span>
              <span style={{ color: telemetry.temperature_c > 75 ? '#ff0055' : '#e2e8f0', fontWeight: 600 }}>
                {telemetry.temperature_c.toFixed(1)}°C
              </span>
            </div>
            <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
              <div
                style={{
                  width: `${Math.min(100, (telemetry.temperature_c / 95) * 100)}%`,
                  height: '100%',
                  backgroundColor: telemetry.temperature_c > 75 ? '#ff0055' : '#22c55e',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>
        </div>

        {/* Dynamic Allocations & Bounds */}
        <div
          style={{
            backgroundColor: '#070a0f',
            padding: 12,
            borderRadius: 8,
            border: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Adaptive Concurrency & Memory Budget
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, textAlign: 'center' }}>
            <div style={{ backgroundColor: '#0f172a', padding: '6px 4px', borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: '#64748b' }}>CONCURRENCY</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8' }}>{config.max_concurrency} workers</div>
            </div>
            <div style={{ backgroundColor: '#0f172a', padding: '6px 4px', borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: '#64748b' }}>CTX CAP</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#a855f7' }}>{config.context_window_cap} tok</div>
            </div>
            <div style={{ backgroundColor: '#0f172a', padding: '6px 4px', borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: '#64748b' }}>INDEXING</div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: config.background_indexing_paused ? '#f59e0b' : '#22c55e',
                }}
              >
                {config.background_indexing_paused ? 'PAUSED' : 'ACTIVE'}
              </div>
            </div>
            <div style={{ backgroundColor: '#0f172a', padding: '6px 4px', borderRadius: 6 }}>
              <div style={{ fontSize: 9, color: '#64748b' }}>HEADROOM</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#00ffcc' }}>{config.vram_headroom_mb} MB</div>
            </div>
          </div>
        </div>

        {/* Manual Throttle Override Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Manual Throttle Policy Overrides</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => handleSetMode('NORMAL')}
              style={{
                flex: 1,
                padding: '6px 8px',
                borderRadius: 6,
                backgroundColor: config.state === 'NORMAL' && config.manual_override ? '#00ffcc22' : '#0f172a',
                border: `1px solid ${config.state === 'NORMAL' && config.manual_override ? '#00ffcc' : '#334155'}`,
                color: '#00ffcc',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Normal
            </button>
            <button
              onClick={() => handleSetMode('CONSERVE')}
              style={{
                flex: 1,
                padding: '6px 8px',
                borderRadius: 6,
                backgroundColor: config.state === 'CONSERVE' && config.manual_override ? '#f59e0b22' : '#0f172a',
                border: `1px solid ${config.state === 'CONSERVE' && config.manual_override ? '#f59e0b' : '#334155'}`,
                color: '#f59e0b',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Conserve
            </button>
            <button
              onClick={() => handleSetMode('EMERGENCY_THROTTLE')}
              style={{
                flex: 1,
                padding: '6px 8px',
                borderRadius: 6,
                backgroundColor: config.state === 'EMERGENCY_THROTTLE' && config.manual_override ? '#ff005522' : '#0f172a',
                border: `1px solid ${config.state === 'EMERGENCY_THROTTLE' && config.manual_override ? '#ff0055' : '#334155'}`,
                color: '#ff0055',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Emergency
            </button>
            <button
              onClick={handleResetOverride}
              title="Resume automatic governor"
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                color: '#94a3b8',
                fontSize: 10,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ArrowResetRegular style={{ fontSize: 12 }} />
              Auto
            </button>
          </div>
        </div>

        {/* Headroom Override Slider / Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: -4 }}>
          <span style={{ fontSize: 11, color: '#64748b', whiteSpace: 'nowrap' }}>Headroom:</span>
          <input
            type="number"
            min={256}
            max={4096}
            step={256}
            value={headroomInput}
            onChange={e => setHeadroomInput(Number(e.target.value))}
            style={{
              width: 80,
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 4,
              padding: '3px 6px',
              color: '#e2e8f0',
              fontSize: 11,
            }}
          />
          <span style={{ fontSize: 11, color: '#64748b' }}>MB</span>
          <button
            onClick={handleApplyHeadroom}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              backgroundColor: '#00ffcc22',
              border: '1px solid #00ffcc88',
              color: '#00ffcc',
              fontSize: 10,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Apply
          </button>
        </div>

        {/* Stress Simulation Presets */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 10, color: '#64748b' }}>Simulate Dynamic Load Scenarios:</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => handleSimulateLoad(0.35)}
              style={{
                flex: 1,
                padding: '5px 8px',
                borderRadius: 4,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#94a3b8',
                fontSize: 10,
                cursor: 'pointer',
              }}
            >
              Idle (35%)
            </button>
            <button
              onClick={() => handleSimulateLoad(0.72)}
              style={{
                flex: 1,
                padding: '5px 8px',
                borderRadius: 4,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#f59e0b',
                fontSize: 10,
                cursor: 'pointer',
              }}
            >
              Multi-Agent (72%)
            </button>
            <button
              onClick={() => handleSimulateLoad(0.92)}
              style={{
                flex: 1,
                padding: '5px 8px',
                borderRadius: 4,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#ff0055',
                fontSize: 10,
                cursor: 'pointer',
              }}
            >
              Peak Saturation (92%)
            </button>
          </div>
        </div>

        {/* Feedback / Safety Notice */}
        {feedback && (
          <div
            style={{
              padding: '6px 10px',
              backgroundColor: 'rgba(0, 255, 204, 0.1)',
              border: '1px solid #00ffcc44',
              borderRadius: 6,
              fontSize: 11,
              color: '#00ffcc',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 13 }} />
            <span>{feedback}</span>
          </div>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 9,
            color: '#475569',
            borderTop: '1px solid #1e293b',
            paddingTop: 8,
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheckmarkRegular style={{ color: '#00ffcc', fontSize: 11 }} />
            Sovereign Adaptive Resource Balancing Active
          </span>
          <span>Guardian SLA &lt; 25ms</span>
        </div>
      </div>
    </div>
  );
};
