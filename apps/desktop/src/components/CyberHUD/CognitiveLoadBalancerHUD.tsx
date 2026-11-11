import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PulseRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  HourglassHalfRegular,
  AlertUrgentRegular,
  ArrowSyncRegular,
  FlashRegular,
} from '@fluentui/react-icons';

export interface PacedNotificationUI {
  notification_id: string;
  title: string;
  body: string;
  priority: string;
  created_at: number;
}

interface CognitiveLoadBalancerHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const CognitiveLoadBalancerHUD: React.FC<CognitiveLoadBalancerHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [loadScore, setLoadScore] = useState<number>(0.82);
  const [attentionalState, setAttentionalState] = useState<string>('DEEP_FLOW');
  const [interactionRate, setInteractionRate] = useState<number>(68);
  const [windowSwitches] = useState<number>(4);
  const [dwellSeconds] = useState<number>(420);

  const [deferredQueue, setDeferredQueue] = useState<PacedNotificationUI[]>([
    {
      notification_id: 'notif_001',
      title: 'Obsidian Daily Digest Ready',
      body: 'Synthesized 4 active vault notes from morning session.',
      priority: 'STANDARD_PROACTIVE',
      created_at: Date.now() - 180000,
    },
    {
      notification_id: 'notif_002',
      title: 'Python Dependency Audit Complete',
      body: 'Verified 42 packages against CVE vulnerability database.',
      priority: 'LOW_AMBIENT',
      created_at: Date.now() - 60000,
    },
  ]);

  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'pacing.update' && externalEvent.payload) {
      if (typeof externalEvent.payload.loadScore === 'number') setLoadScore(externalEvent.payload.loadScore);
      if (externalEvent.payload.state) setAttentionalState(externalEvent.payload.state);
      if (externalEvent.payload.queue) setDeferredQueue(externalEvent.payload.queue);
    }
  }, [externalEvent]);

  const handleSimulateState = (mode: 'flow' | 'idle') => {
    if (mode === 'flow') {
      setLoadScore(0.85);
      setAttentionalState('DEEP_FLOW');
      setInteractionRate(74);
      setFeedback('Simulated High Activity: User entered DEEP_FLOW. Non-critical alerts queued.');
    } else {
      setLoadScore(0.20);
      setAttentionalState('IDLE_EXPLORING');
      setInteractionRate(8);
      setFeedback('Simulated Low Activity: User entered IDLE_EXPLORING. Direct delivery active.');
    }
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleFlushQueue = () => {
    const count = deferredQueue.length;
    setDeferredQueue([]);
    setFeedback(`Flushed ${count} deferred notification${count === 1 ? '' : 's'} to desktop display.`);

    if (sendMessage) {
      sendMessage({
        type: 'pacing.flush_queue',
        payload: {},
      });
    }
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 40,
        right: 40,
        width: 660,
        maxHeight: 'calc(100vh - 80px)',
        backgroundColor: 'rgba(10, 18, 28, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(0, 240, 255, 0.35)',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'Segoe UI, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 240, 255, 0.05)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <PulseRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              COGNITIVE LOAD BALANCER & ATTENTIONAL PACER
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 26-04 • Ambient Focus Pacing • Deferred Notification Buffer
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: 18 }} />
        </button>
      </div>

      {feedback && (
        <div
          style={{
            padding: '8px 18px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderBottom: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckmarkCircleRegular style={{ fontSize: 16 }} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Content scroll area */}
      <div style={{ padding: 18, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Attentional State & Load Gauge Card */}
        <div
          style={{
            padding: 14,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(0, 240, 255, 0.2)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: '#94a3b8' }}>Attentional Focus State:</span>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  padding: '3px 10px',
                  borderRadius: 12,
                  backgroundColor:
                    attentionalState === 'DEEP_FLOW'
                      ? 'rgba(0, 240, 255, 0.2)'
                      : attentionalState === 'NORMAL_WORK'
                      ? 'rgba(16, 185, 129, 0.2)'
                      : 'rgba(148, 163, 184, 0.2)',
                  color:
                    attentionalState === 'DEEP_FLOW'
                      ? '#00f0ff'
                      : attentionalState === 'NORMAL_WORK'
                      ? '#34d399'
                      : '#cbd5e1',
                  border:
                    attentionalState === 'DEEP_FLOW'
                      ? '1px solid rgba(0, 240, 255, 0.5)'
                      : attentionalState === 'NORMAL_WORK'
                      ? '1px solid rgba(16, 185, 129, 0.4)'
                      : '1px solid rgba(148, 163, 184, 0.4)',
                }}
              >
                {attentionalState}
              </span>
            </div>

            <div style={{ fontSize: 11, color: '#64748b' }}>
              Policy: {attentionalState === 'DEEP_FLOW' ? 'Queue Non-Critical' : 'Direct Dispatch'}
            </div>
          </div>

          {/* Load Gauge */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
              <span>Cognitive Load Index</span>
              <span style={{ fontWeight: 600, color: '#00f0ff' }}>{(loadScore * 100).toFixed(0)}%</span>
            </div>
            <div style={{ height: 10, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 5, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${loadScore * 100}%`,
                  backgroundColor: loadScore >= 0.75 ? '#00f0ff' : loadScore >= 0.35 ? '#10b981' : '#38bdf8',
                  boxShadow: '0 0 12px rgba(0, 240, 255, 0.6)',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>

          {/* Activity Metrics Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 4 }}>
            <div style={{ padding: 8, backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>Interaction Velocity</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', marginTop: 2 }}>{interactionRate} / min</div>
            </div>
            <div style={{ padding: 8, backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>Window Switch Rate</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', marginTop: 2 }}>{windowSwitches} / min</div>
            </div>
            <div style={{ padding: 8, backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>Focus Dwell</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', marginTop: 2 }}>{Math.floor(dwellSeconds / 60)}m {dwellSeconds % 60}s</div>
            </div>
          </div>
        </div>

        {/* State Simulator Controls */}
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => handleSimulateState('flow')}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: 'rgba(0, 240, 255, 0.1)',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              borderRadius: 6,
              color: '#00f0ff',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <FlashRegular style={{ fontSize: 14 }} />
            Simulate Deep Flow (85% Load)
          </button>
          <button
            onClick={() => handleSimulateState('idle')}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: 6,
              color: '#94a3b8',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <ArrowSyncRegular style={{ fontSize: 14 }} />
            Simulate Idle (20% Load)
          </button>
        </div>

        {/* Deferred Notification Queue */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 6 }}>
              <HourglassHalfRegular style={{ fontSize: 14 }} />
              DEFERRED NOTIFICATION QUEUE ({deferredQueue.length})
            </div>
            {deferredQueue.length > 0 && (
              <button
                onClick={handleFlushQueue}
                style={{
                  padding: '4px 10px',
                  backgroundColor: 'rgba(245, 158, 11, 0.15)',
                  border: '1px solid rgba(245, 158, 11, 0.4)',
                  borderRadius: 4,
                  color: '#fbbf24',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Flush Queue Now
              </button>
            )}
          </div>

          {deferredQueue.length === 0 ? (
            <div
              style={{
                padding: '16px',
                textAlign: 'center',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderRadius: 6,
                border: '1px dashed rgba(255, 255, 255, 0.1)',
                color: '#64748b',
                fontSize: 12,
              }}
            >
              No pending deferred notifications in queue.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {deferredQueue.map((item) => (
                <div
                  key={item.notification_id}
                  style={{
                    padding: '10px 14px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(245, 158, 11, 0.2)',
                    borderRadius: 6,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>{item.title}</div>
                    <span
                      style={{
                        fontSize: 9,
                        padding: '1px 6px',
                        borderRadius: 8,
                        backgroundColor: 'rgba(245, 158, 11, 0.15)',
                        color: '#fbbf24',
                        border: '1px solid rgba(245, 158, 11, 0.3)',
                      }}
                    >
                      {item.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#cbd5e1' }}>{item.body}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 18px',
          borderTop: '1px solid rgba(0, 240, 255, 0.2)',
          fontSize: 11,
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 240, 255, 0.02)',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertUrgentRegular style={{ color: '#ef4444' }} />
          Critical Safety Alerts Bypass Pacing (Rule 1 / Rule 3)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <ShieldCheckmarkRegular style={{ color: '#00f0ff' }} />
          Local Ambient Monitoring
        </span>
      </div>
    </div>
  );
};
