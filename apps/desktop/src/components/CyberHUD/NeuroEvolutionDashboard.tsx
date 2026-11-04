import React, { useState } from 'react';
import {
  BrainCircuitRegular,
  ArrowResetRegular,
  PlayRegular,
  CheckmarkCircleRegular,
  ShieldDismissRegular,
} from '@fluentui/react-icons';
import {
  EvolutionEngineStatusPayload,
} from '../../types/protocol';

interface NeuroEvolutionDashboardProps {
  status: EvolutionEngineStatusPayload | null;
  onTrainAdapter?: (adapterId: string, domain: string, rank?: number, epochs?: number) => void;
  onActivateAdapter?: (adapterId: string) => void;
  onRollbackAdapter?: () => void;
}

export const NeuroEvolutionDashboard: React.FC<NeuroEvolutionDashboardProps> = ({
  status,
  onTrainAdapter,
  onActivateAdapter,
  onRollbackAdapter,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!status) {
    return null;
  }

  const {
    is_running,
    is_halted,
    active_adapter,
    registered_adapters,
    total_instructions_distilled,
    last_benchmark_report,
  } = status;

  const getStatusColor = () => {
    if (is_halted) return '#ff3366';
    if (active_adapter) return '#00ffcc';
    if (is_running) return '#80b8ff';
    return '#64748b';
  };

  const statusColor = getStatusColor();

  return (
    <div
      style={{
        background: 'rgba(12, 16, 30, 0.90)',
        border: `1px solid ${statusColor}44`,
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(12px)',
        boxShadow: active_adapter ? '0 0 20px rgba(0, 255, 204, 0.2)' : '0 2px 12px rgba(0,0,0,0.5)',
        transition: 'all 0.3s ease',
        maxWidth: 480,
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BrainCircuitRegular style={{ color: statusColor, fontSize: 16 }} />
          <span style={{ fontWeight: 600, letterSpacing: 0.5, color: '#00ffcc' }}>
            NEURO-EVOLUTION (LoRA)
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: active_adapter ? 'rgba(0, 255, 204, 0.2)' : 'rgba(255, 255, 255, 0.08)',
              color: active_adapter ? '#00ffcc' : '#94a3b8',
              fontWeight: 'bold',
            }}
          >
            {is_halted ? 'HALTED' : active_adapter ? `MOUNTED: ${active_adapter.adapter_id}` : 'BASE WEIGHTS'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {onRollbackAdapter && active_adapter && (
            <button
              onClick={onRollbackAdapter}
              title="Rollback active adapter to previous checkpoint / base model"
              style={{
                background: 'rgba(255, 184, 0, 0.15)',
                border: '1px solid #ffb80055',
                color: '#ffb800',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: 10,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ArrowResetRegular style={{ fontSize: 11 }} />
              Rollback
            </button>
          )}

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
            {isMinimized ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Active Mounted Adapter Card */}
          {active_adapter ? (
            <div
              style={{
                background: 'rgba(0, 255, 204, 0.08)',
                border: '1px solid #00ffcc44',
                borderRadius: 6,
                padding: '8px 10px',
                marginBottom: 10,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 600, color: '#00ffcc' }}>
                  {active_adapter.adapter_id} ({active_adapter.domain})
                </span>
                <span style={{ fontSize: 10, color: '#38bdf8' }}>
                  Rank: {active_adapter.lora_rank} | Alpha: {active_adapter.lora_alpha}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8' }}>
                <span>Loss: {active_adapter.training_loss.toFixed(4)}</span>
                <span>Benchmark Score: {(active_adapter.benchmark_score * 100).toFixed(1)}%</span>
              </div>
            </div>
          ) : (
            <div
              style={{
                background: 'rgba(0,0,0,0.25)',
                borderRadius: 6,
                padding: '8px 10px',
                marginBottom: 10,
                fontSize: 11,
                color: '#94a3b8',
                textAlign: 'center',
              }}
            >
              No LoRA adapter currently mounted (Running on sovereign 8B base weights).
            </div>
          )}

          {/* Telemetry Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 10,
              color: '#64748b',
              marginBottom: 8,
              padding: '0 2px',
            }}
          >
            <span>Synthetic Instruction Pairs: {total_instructions_distilled}</span>
            <span>Registered Adapters: {registered_adapters.length}</span>
          </div>

          {/* Latest Benchmark Result */}
          {last_benchmark_report && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.65)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 4,
                padding: '6px 8px',
                fontSize: 10,
                marginBottom: 10,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>Probe: {last_benchmark_report.adapter_id}</span>
              <span style={{ color: last_benchmark_report.passed_threshold ? '#00ffcc' : '#ff3366' }}>
                Accuracy: {(last_benchmark_report.accuracy_score * 100).toFixed(1)}% ({last_benchmark_report.passed_threshold ? 'PASSED' : 'REJECTED'})
              </span>
            </div>
          )}

          {/* Registered Adapters List */}
          {registered_adapters.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 160, overflowY: 'auto' }}>
              {registered_adapters.map((ad) => (
                <div
                  key={ad.adapter_id}
                  style={{
                    background: 'rgba(15, 23, 42, 0.5)',
                    border: `1px solid ${ad.is_active ? '#00ffcc55' : 'rgba(255,255,255,0.06)'}`,
                    borderRadius: 4,
                    padding: '6px 8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: 11,
                  }}
                >
                  <div>
                    <span style={{ fontWeight: 600, color: ad.is_active ? '#00ffcc' : '#cbd5e1' }}>
                      {ad.adapter_id}
                    </span>
                    <span style={{ color: '#64748b', fontSize: 10, marginLeft: 6 }}>
                      ({ad.domain} | {(ad.benchmark_score * 100).toFixed(0)}%)
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: 4 }}>
                    {ad.status === 'QUARANTINED' ? (
                      <span style={{ color: '#ff3366', fontSize: 9, display: 'flex', alignItems: 'center', gap: 2 }}>
                        <ShieldDismissRegular style={{ fontSize: 11 }} /> QUARANTINED
                      </span>
                    ) : !ad.is_active && onActivateAdapter ? (
                      <button
                        onClick={() => onActivateAdapter(ad.adapter_id)}
                        style={{
                          background: 'rgba(0, 255, 204, 0.15)',
                          border: '1px solid #00ffcc44',
                          color: '#00ffcc',
                          borderRadius: 3,
                          padding: '1px 6px',
                          cursor: 'pointer',
                          fontSize: 9,
                        }}
                      >
                        Mount
                      </button>
                    ) : (
                      <span style={{ color: '#00ffcc', fontSize: 9, display: 'flex', alignItems: 'center', gap: 2 }}>
                        <CheckmarkCircleRegular style={{ fontSize: 11 }} /> ACTIVE
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Action Trigger */}
          {onTrainAdapter && (
            <div style={{ marginTop: 10, textAlign: 'right' }}>
              <button
                onClick={() => onTrainAdapter(`lora_custom_${Date.now().toString().slice(-4)}`, 'coding', 8, 3)}
                style={{
                  background: 'rgba(0, 240, 255, 0.15)',
                  border: '1px solid #00f0ff55',
                  color: '#00f0ff',
                  borderRadius: 4,
                  padding: '4px 10px',
                  cursor: 'pointer',
                  fontSize: 10,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <PlayRegular style={{ fontSize: 11 }} />
                Train New Adapter
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
