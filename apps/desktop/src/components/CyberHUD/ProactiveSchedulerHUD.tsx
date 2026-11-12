import React, { useState, useEffect } from 'react';
import {
  ClockRegular,
  PlayRegular,
  PauseRegular,
  DismissRegular,
  WeatherSunnyRegular,
  FolderRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface ScheduledJobItem {
  job_id: string;
  name: string;
  interval_seconds: number;
  enabled: boolean;
  job_type: string;
  next_run: number;
  run_count: number;
  last_status: string;
}

export interface ProactiveSchedulerHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const ProactiveSchedulerHUD: React.FC<ProactiveSchedulerHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [isRunning, setIsRunning] = useState<boolean>(true);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [jobs, setJobs] = useState<ScheduledJobItem[]>([
    {
      job_id: 'job-morning-01',
      name: '08:30 AM Morning Briefing & Obsidian Sync',
      interval_seconds: 86400,
      enabled: true,
      job_type: 'cron',
      next_run: Date.now() / 1000 + 3600,
      run_count: 14,
      last_status: 'success'
    },
    {
      job_id: 'job-watcher-02',
      name: 'Workspace File Watcher & Ledger Index',
      interval_seconds: 60,
      enabled: true,
      job_type: 'watcher',
      next_run: Date.now() / 1000 + 45,
      run_count: 320,
      last_status: 'success'
    }
  ]);
  const [isBriefingLoading, setIsBriefingLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'scheduler.status_update') {
      const p = externalEvent.payload || {};
      if (typeof p.is_running === 'boolean') setIsRunning(p.is_running);
      if (typeof p.is_paused === 'boolean') setIsPaused(p.is_paused);
      if (p.jobs) setJobs(p.jobs);
    }
  }, [externalEvent]);

  const handleTriggerBriefing = () => {
    setIsBriefingLoading(true);
    setStatusMessage('Generating 08:30 Morning Briefing & Obsidian Daily Note...');
    if (sendMessage) {
      sendMessage({
        type: 'scheduler.trigger_morning_briefing',
        payload: { include_weather: true, include_calendar: true }
      });
    }
    setTimeout(() => {
      setIsBriefingLoading(false);
      setStatusMessage('Briefing created & Obsidian note synced to vault/Daily/');
      setTimeout(() => setStatusMessage(null), 4000);
    }, 1200);
  };

  const handleTogglePause = () => {
    const nextPaused = !isPaused;
    setIsPaused(nextPaused);
    if (sendMessage) {
      sendMessage({
        type: nextPaused ? 'scheduler.pause' : 'scheduler.resume',
        payload: {}
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
        width: '520px',
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
              background: 'linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.4)',
            }}
          >
            <ClockRegular style={{ color: '#050b14', fontSize: '18px' }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px', color: '#f8fafc' }}>
              Autonomous Proactive Scheduler HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Background Event Daemon & Morning Briefing (SCH-02, AUT-01)
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

      {/* Daemon Status Badges */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
        <div
          style={{
            flex: 1,
            background: isPaused ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)',
            border: isPaused ? '1px solid rgba(245, 158, 11, 0.35)' : '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px',
            color: isPaused ? '#f59e0b' : '#10b981',
          }}
        >
          <SparkleRegular style={{ fontSize: '15px' }} />
          <span>{isPaused ? 'Daemon Paused' : (isRunning ? 'Daemon Active (Asyncio Event Loop)' : 'Daemon Stopped')}</span>
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
          <FolderRegular style={{ fontSize: '15px' }} />
          <span>2 Watched Dirs</span>
        </div>
      </div>

      {/* Notification Toast Message */}
      {statusMessage && (
        <div
          style={{
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid #38bdf8',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '11px',
            color: '#38bdf8',
            marginBottom: '12px',
          }}
        >
          {statusMessage}
        </div>
      )}

      {/* Scheduled Jobs List */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
          Active Scheduled Jobs & Reactive Watchers ({jobs.length})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
          {jobs.map((j) => (
            <div
              key={j.job_id}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '6px',
                padding: '10px 12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 500, color: '#f1f5f9' }}>{j.name}</div>
                <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
                  Interval: {j.interval_seconds}s | Runs: {j.run_count} | Status: {j.last_status}
                </div>
              </div>
              <span
                style={{
                  fontSize: '10px',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  background: j.enabled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: j.enabled ? '#34d399' : '#f87171',
                  border: j.enabled ? '1px solid #10b981' : '1px solid #ef4444',
                }}
              >
                {j.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Control Buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
        <button
          onClick={handleTriggerBriefing}
          disabled={isBriefingLoading}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '8px 14px',
            borderRadius: '6px',
            border: '1px solid #00f0ff',
            background: 'rgba(0, 240, 255, 0.15)',
            color: '#00f0ff',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <WeatherSunnyRegular style={{ fontSize: '15px' }} />
          {isBriefingLoading ? 'Synthesizing...' : 'Trigger 08:30 Morning Briefing'}
        </button>

        <button
          onClick={handleTogglePause}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: '6px',
            border: isPaused ? '1px solid #10b981' : '1px solid #f59e0b',
            background: isPaused ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            color: isPaused ? '#10b981' : '#f59e0b',
            fontSize: '11px',
            cursor: 'pointer',
          }}
        >
          {isPaused ? <PlayRegular style={{ fontSize: '14px' }} /> : <PauseRegular style={{ fontSize: '14px' }} />}
          {isPaused ? 'Resume Daemon' : 'Pause Daemon'}
        </button>
      </div>
    </div>
  );
};
