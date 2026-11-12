import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BrainCircuitRegular,
  DocumentSparkleRegular,
  CheckmarkCircleRegular,
  FlashRegular,
} from '@fluentui/react-icons';

export interface LoRAAdapterHUDItem {
  adapter_id: string;
  name: string;
  domain: string;
  rank: number;
  alpha: number;
  vram_mb: number;
  is_active: boolean;
  description: string;
}

interface LoRAAdapterHubHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const LoRAAdapterHubHUD: React.FC<LoRAAdapterHubHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activeAdapterId, setActiveAdapterId] = useState<string>('coding_adapter');
  const [totalVramUsed, setTotalVramUsed] = useState<number>(4340); // MB
  const totalBudget = 8192; // 8GB

  const [adapters, setAdapters] = useState<LoRAAdapterHUDItem[]>([
    {
      adapter_id: 'coding_adapter',
      name: 'DeepCode AST Specialist',
      domain: 'coding',
      rank: 16,
      alpha: 32,
      vram_mb: 140,
      is_active: true,
      description: 'Specialized in TypeScript strict types, Python AST refactoring, and test fixtures',
    },
    {
      adapter_id: 'reasoning_adapter',
      name: 'Topological Reasoning & Logic',
      domain: 'reasoning',
      rank: 16,
      alpha: 32,
      vram_mb: 160,
      is_active: false,
      description: 'Specialized in DAG wave partitioning, counterfactual analysis, and dependency verification',
    },
    {
      adapter_id: 'witty_persona_adapter',
      name: 'Jarvis British Wit & Playfulness',
      domain: 'persona',
      rank: 8,
      alpha: 16,
      vram_mb: 80,
      is_active: false,
      description: 'Specialized in witty, playful British assistant persona and conversational banter',
    },
  ]);

  const [datasetCount, setDatasetCount] = useState<number>(142);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'evolution.adapter_update' && externalEvent.payload) {
      if (externalEvent.payload.active_adapter_id) {
        setActiveAdapterId(externalEvent.payload.active_adapter_id);
      }
      if (externalEvent.payload.vram_telemetry?.total_used_mb) {
        setTotalVramUsed(externalEvent.payload.vram_telemetry.total_used_mb);
      }
      if (externalEvent.payload.dataset_stats?.total_samples) {
        setDatasetCount(externalEvent.payload.dataset_stats.total_samples);
      }
    }
  }, [externalEvent]);

  const handleActivate = (adapterId: string) => {
    setActiveAdapterId(adapterId);
    setAdapters((prev) =>
      prev.map((a) => ({
        ...a,
        is_active: a.adapter_id === adapterId,
      }))
    );
    const target = adapters.find((a) => a.adapter_id === adapterId);
    const extra = target ? target.vram_mb : 0;
    setTotalVramUsed(4200 + extra);

    setActionFeedback(`Activated LoRA adapter: ${target ? target.name : 'Base Model'}`);

    if (sendMessage) {
      sendMessage({
        type: 'evolution.activate_adapter',
        payload: { adapter_id: adapterId },
      });
    }

    setTimeout(() => setActionFeedback(null), 3000);
  };

  const vramPercent = Math.min(100, (totalVramUsed / totalBudget) * 100);

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(10, 15, 26, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(14, 165, 233, 0.35)',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(14, 165, 233, 0.18)',
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
          borderBottom: '1px solid rgba(14, 165, 233, 0.2)',
          background: 'rgba(3, 105, 161, 0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BrainCircuitRegular style={{ fontSize: 22, color: '#38bdf8' }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: 0.5, color: '#7dd3fc' }}>
              LORA ADAPTER HUB &amp; NEURAL EVOLUTION ENGINE
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 23-02 • Task-Specific PEFT Adapters &amp; Local GPU VRAM Budget (ADA-01 / MOD-02)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => handleActivate('base_model')}
            style={{
              background: activeAdapterId === 'base_model' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255, 255, 255, 0.05)',
              color: activeAdapterId === 'base_model' ? '#38bdf8' : '#94a3b8',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            Base 8B Only
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
        {/* VRAM Gauge Bar */}
        <div
          style={{
            padding: 14,
            borderRadius: 8,
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
            <span style={{ color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Local GPU VRAM Allocation</span>
            <span style={{ fontFamily: 'monospace', color: '#38bdf8' }}>
              {(totalVramUsed / 1024).toFixed(2)} GB / {(totalBudget / 1024).toFixed(0)} GB ({vramPercent.toFixed(1)}%)
            </span>
          </div>

          <div style={{ width: '100%', height: 8, background: 'rgba(255, 255, 255, 0.1)', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                width: `${vramPercent}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #0284c7, #38bdf8)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b' }}>
            <span>Base Model: 4.20 GB</span>
            <span>Active LoRA: {((totalVramUsed - 4200) / 1024).toFixed(2)} GB</span>
            <span>Headroom: {((totalBudget - totalVramUsed) / 1024).toFixed(2)} GB free</span>
          </div>
        </div>

        {/* Adapters Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            Specialized Domain LoRA Adapters
          </div>

          {adapters.map((adapter) => {
            const isSel = activeAdapterId === adapter.adapter_id;
            return (
              <div
                key={adapter.adapter_id}
                style={{
                  padding: 14,
                  borderRadius: 8,
                  background: isSel ? 'rgba(14, 165, 233, 0.1)' : 'rgba(255, 255, 255, 0.025)',
                  border: isSel ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FlashRegular style={{ color: isSel ? '#38bdf8' : '#94a3b8', fontSize: 16 }} />
                    <span style={{ fontSize: 14, fontWeight: 700, color: isSel ? '#f8fafc' : '#cbd5e1' }}>
                      {adapter.name}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: 'monospace',
                        background: 'rgba(255, 255, 255, 0.08)',
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: '#94a3b8',
                      }}
                    >
                      r={adapter.rank}, &alpha;={adapter.alpha}
                    </span>
                  </div>

                  <div style={{ fontSize: 12, color: '#94a3b8' }}>
                    {adapter.description}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#38bdf8' }}>
                    +{adapter.vram_mb} MB
                  </span>

                  <button
                    onClick={() => handleActivate(adapter.adapter_id)}
                    style={{
                      background: isSel ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(255, 255, 255, 0.05)',
                      color: isSel ? '#ffffff' : '#94a3b8',
                      border: 'none',
                      borderRadius: 6,
                      padding: '6px 14px',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {isSel ? 'Active' : 'Activate'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Dataset Telemetry Banner */}
        <div
          style={{
            padding: 12,
            borderRadius: 8,
            background: 'rgba(52, 211, 153, 0.06)',
            border: '1px solid rgba(52, 211, 153, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <DocumentSparkleRegular style={{ fontSize: 20, color: '#34d399' }} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#a7f3d0' }}>
                Instruction Tuning Dataset (.phenom/datasets/)
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>
                {datasetCount} privacy-sanitized samples ready for local LoRA fine-tuning
              </div>
            </div>
          </div>

          <span style={{ fontSize: 11, color: '#34d399', fontFamily: 'monospace' }}>
            Rule 11 Scrubbed • Rule 4 Local
          </span>
        </div>

        {/* Feedback Banner */}
        {actionFeedback && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: '#38bdf8',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckmarkCircleRegular style={{ fontSize: 14 }} />
            <span>{actionFeedback}</span>
          </div>
        )}
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
        <div>8B Instruct Base • PEFT Rank 16 • Max 8.0 GB VRAM Safety Ceiling</div>
        <div>Guardian SLA &lt; 25.0ms • Local Offline Tuning</div>
      </div>
    </div>
  );
};
