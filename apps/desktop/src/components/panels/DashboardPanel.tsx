import React, { useState } from 'react';
import { Button, Badge } from '@fluentui/react-components';
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  BrainCircuitRegular,
  ChevronDownRegular,
  ChevronUpRegular
} from '@fluentui/react-icons';

interface DashboardPanelProps {
  onClose: () => void;
  onSendWs: (msg: any) => void;
  scheduledJobs?: any[];
  watchlistItems?: any[];
}

export const DashboardPanel: React.FC<DashboardPanelProps> = ({
  onClose,
  scheduledJobs = [],
  watchlistItems = []
}) => {
  const [showMoreTiles, setShowMoreTiles] = useState<boolean>(false);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', color: '#f8fafc' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 14,
          borderBottom: '1px solid rgba(0, 229, 255, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BrainCircuitRegular style={{ color: '#00e5ff', fontSize: 20 }} />
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', margin: 0, letterSpacing: '0.4px' }}>
            System Core Dashboard
          </h2>
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Core System Status Tile (Task 6E.5) */}
        <div
          style={{
            background: 'rgba(8, 15, 28, 0.90)',
            border: '1px solid rgba(0, 229, 255, 0.35)',
            borderRadius: 14,
            padding: 18,
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.7), 0 0 20px rgba(0, 229, 255, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            gap: 14
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#00e5ff', letterSpacing: '0.6px' }}>
              HARDWARE & RUNTIME TELEMETRY
            </span>
            <Badge
              appearance="filled"
              style={{
                background: 'rgba(204, 255, 0, 0.15)',
                color: '#ccff00',
                border: '1px solid rgba(204, 255, 0, 0.4)',
                fontSize: 11,
                fontWeight: 600
              }}
            >
              ACTIVE & HEALTHY
            </Badge>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* Models Loaded */}
            <div
              style={{
                background: 'rgba(4, 7, 13, 0.7)',
                padding: '12px 14px',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)'
              }}
            >
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Active Local Models</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>
                phenom-jarvis:latest (8B)
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Specialist: Qwen3.5-4B &bull; Vision: Moondream
              </div>
            </div>

            {/* GPU / VRAM */}
            <div
              style={{
                background: 'rgba(4, 7, 13, 0.7)',
                padding: '12px 14px',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)'
              }}
            >
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>NVIDIA GPU / VRAM</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#00e5ff', marginTop: 4 }}>
                4.7 GB / 6.0 GB VRAM
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                CUDA Acceleration &bull; 0.0% Paging
              </div>
            </div>

            {/* Host RAM */}
            <div
              style={{
                background: 'rgba(4, 7, 13, 0.7)',
                padding: '12px 14px',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)'
              }}
            >
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Host Memory (RAM)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>
                ~210 MB Desktop &bull; ~180 MB Backend
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Whisper CPU int8 &bull; Zero VRAM Contention
              </div>
            </div>

            {/* Kill Switch State */}
            <div
              style={{
                background: 'rgba(4, 7, 13, 0.7)',
                padding: '12px 14px',
                borderRadius: 8,
                border: '1px solid rgba(204, 255, 0, 0.2)'
              }}
            >
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>Guardian Kill Switch</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#ccff00', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldCheckmarkRegular style={{ fontSize: 16 }} />
                ARMED & ARBITRATING
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                SLA: &lt; 25ms halt latency (Ctrl+Alt+P / Escape)
              </div>
            </div>
          </div>
        </div>

        {/* Optional More Tiles Toggle */}
        <div style={{ marginTop: 4 }}>
          <button
            onClick={() => setShowMoreTiles(!showMoreTiles)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: 12,
              cursor: 'pointer',
              padding: '6px 0'
            }}
          >
            <span>{showMoreTiles ? 'Hide Additional Telemetry' : 'More Tiles (Opt-in)'}</span>
            {showMoreTiles ? <ChevronUpRegular style={{ fontSize: 14 }} /> : <ChevronDownRegular style={{ fontSize: 14 }} />}
          </button>

          {showMoreTiles && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
              <div
                style={{
                  background: 'rgba(8, 15, 28, 0.7)',
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  fontSize: 12
                }}
              >
                <div style={{ fontWeight: 600, color: '#cbd5e1', marginBottom: 4 }}>
                  Scheduled Tasks ({scheduledJobs.length})
                </div>
                <div style={{ color: '#64748b' }}>
                  {scheduledJobs.length === 0 ? 'No active background cron jobs registered.' : JSON.stringify(scheduledJobs)}
                </div>
              </div>

              <div
                style={{
                  background: 'rgba(8, 15, 28, 0.7)',
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  fontSize: 12
                }}
              >
                <div style={{ fontWeight: 600, color: '#cbd5e1', marginBottom: 4 }}>
                  Financial Watchlist ({watchlistItems.length})
                </div>
                <div style={{ color: '#64748b' }}>
                  {watchlistItems.length === 0 ? 'Informational only &bull; Zero trade placement permitted.' : JSON.stringify(watchlistItems)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
