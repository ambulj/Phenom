import React, { useState, useEffect } from 'react';
import {
  BrainCircuitRegular,
  CodeRegular,
  ChatRegular,
  ChevronDownRegular,
  SparkleRegular,
} from '@fluentui/react-icons';

export interface ActiveModelIndicatorProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
}

export const ActiveModelIndicator: React.FC<ActiveModelIndicatorProps> = ({
  externalEvent,
  sendMessage,
}) => {
  const [activeModel, setActiveModel] = useState<string>(
    'hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M'
  );
  const [taskType, setTaskType] = useState<'code' | 'reasoning' | 'chat'>('chat');
  const [estimatedVramMb, setEstimatedVramMb] = useState<number>(2800);
  const [overrideModel, setOverrideModel] = useState<string | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'MODEL_ROUTED') {
      if (payload?.model_name) setActiveModel(payload.model_name);
      if (payload?.task_type) setTaskType(payload.task_type);
      if (payload?.estimated_vram_mb) setEstimatedVramMb(payload.estimated_vram_mb);
    } else if (type === 'MODEL_ROUTING_OVERRIDE_CHANGED') {
      setOverrideModel(payload?.override_model || null);
    }
  }, [externalEvent]);

  const handleSelectModel = (model: string | null) => {
    setIsDropdownOpen(false);
    setOverrideModel(model);
    if (sendMessage) {
      sendMessage({
        type: 'tool_call',
        payload: {
          tool: 'set_model_routing_override',
          args: { model_name: model },
        },
      });
    }
  };

  const getBadgeStyle = () => {
    if (taskType === 'code' || activeModel.includes('coder')) {
      return {
        bg: 'rgba(56, 189, 248, 0.12)',
        border: 'rgba(56, 189, 248, 0.4)',
        color: '#38bdf8',
        label: 'Coder 14B',
        icon: <CodeRegular style={{ fontSize: '14px' }} />,
      };
    }
    if (taskType === 'reasoning' || activeModel.includes('llama3:8b')) {
      return {
        bg: 'rgba(192, 132, 252, 0.12)',
        border: 'rgba(192, 132, 252, 0.4)',
        color: '#c084fc',
        label: 'Reasoner 8B',
        icon: <BrainCircuitRegular style={{ fontSize: '14px' }} />,
      };
    }
    return {
      bg: 'rgba(52, 211, 153, 0.12)',
      border: 'rgba(52, 211, 153, 0.4)',
      color: '#34d399',
      label: 'Fast 4B',
      icon: <ChatRegular style={{ fontSize: '14px' }} />,
    };
  };

  const badge = getBadgeStyle();

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 10px',
          borderRadius: '20px',
          background: badge.bg,
          border: `1px solid ${badge.border}`,
          color: badge.color,
          cursor: 'pointer',
          backdropFilter: 'blur(12px)',
          fontSize: '11px',
          fontWeight: 600,
          boxShadow: `0 0 12px ${badge.border}`,
          transition: 'all 0.2s ease',
          outline: 'none',
        }}
        title={`Active Model: ${activeModel}\nTask: ${taskType.toUpperCase()}\nVRAM: ${(estimatedVramMb / 1024).toFixed(1)} GB`}
      >
        {badge.icon}
        <span>{overrideModel ? `Locked: ${badge.label}` : badge.label}</span>
        <span
          style={{
            fontSize: '9px',
            padding: '1px 5px',
            borderRadius: '10px',
            background: 'rgba(0, 0, 0, 0.3)',
            color: '#94a3b8',
          }}
        >
          {(estimatedVramMb / 1024).toFixed(1)}GB
        </span>
        <ChevronDownRegular style={{ fontSize: '10px', opacity: 0.8 }} />
      </button>

      {isDropdownOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            width: '210px',
            background: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '10px',
            padding: '6px',
            zIndex: 10000,
            boxShadow: '0 12px 30px rgba(0, 0, 0, 0.7)',
            color: '#e2e8f0',
            fontSize: '11px',
          }}
        >
          <div
            style={{
              padding: '4px 8px',
              fontSize: '10px',
              color: '#64748b',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Model Routing Policy
          </div>

          {[
            {
              id: null,
              label: 'Auto Task-Aware Routing',
              desc: 'Dynamic 4B / 8B / 14B dispatch',
              icon: <SparkleRegular style={{ color: '#00f0ff' }} />,
            },
            {
              id: 'qwen2.5-coder:14b',
              label: 'Qwen 2.5 Coder 14B',
              desc: 'Coding & AST synthesis (9.2 GB)',
              icon: <CodeRegular style={{ color: '#38bdf8' }} />,
            },
            {
              id: 'llama3:8b-instruct-q8_0',
              label: 'Llama 3 8B Reasoner',
              desc: 'Deep analytical logic (8.5 GB)',
              icon: <BrainCircuitRegular style={{ color: '#c084fc' }} />,
            },
            {
              id: 'hf.co/tinyopsec/Qwen3.5-4B-Uncensored-Aggressive-GGUF:Q4_K_M',
              label: 'Qwen 3.5 4B Fast Chat',
              desc: 'Ultra-fast banter & chat (2.8 GB)',
              icon: <ChatRegular style={{ color: '#34d399' }} />,
            },
          ].map((opt) => (
            <button
              key={opt.id ?? 'auto'}
              onClick={() => handleSelectModel(opt.id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 8px',
                borderRadius: '6px',
                border: 'none',
                background:
                  overrideModel === opt.id
                    ? 'rgba(0, 240, 255, 0.15)'
                    : 'transparent',
                color: overrideModel === opt.id ? '#00f0ff' : '#cbd5e1',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'background 0.15s ease',
              }}
            >
              {opt.icon}
              <div>
                <div style={{ fontWeight: 600, fontSize: '11px' }}>{opt.label}</div>
                <div style={{ fontSize: '9px', color: '#64748b' }}>{opt.desc}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
