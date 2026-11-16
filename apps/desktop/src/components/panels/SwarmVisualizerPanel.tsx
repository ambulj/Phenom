import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import {
  DismissRegular,
  PlayRegular,
  PauseRegular,
  StopRegular,
  BotRegular,
} from '@fluentui/react-icons';

export interface SwarmAgentNode {
  role: 'architect' | 'coder' | 'security_auditor' | 'web_scout';
  displayName: string;
  status: 'idle' | 'bidding' | 'executing' | 'reviewing' | 'vetoed';
  activeTask?: string;
  bidFitness?: number;
}

export interface SwarmVisualizerPanelProps {
  onClose: () => void;
  onHalt?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  isPaused?: boolean;
  agents?: SwarmAgentNode[];
  quorumApproved?: boolean;
  coderSigned?: boolean;
  securitySigned?: boolean;
  vramUsedMb?: number;
  maxVramMb?: number;
  missionGoal?: string;
  elapsedSeconds?: number;
}

export const SwarmVisualizerPanel: React.FC<SwarmVisualizerPanelProps> = ({
  onClose,
  onHalt,
  onPause,
  onResume,
  isPaused = false,
  agents = [
    { role: 'architect', displayName: 'Architect', status: 'reviewing', activeTask: 'DAG Wave Decomposition', bidFitness: 0.95 },
    { role: 'coder', displayName: 'Coder', status: 'executing', activeTask: 'AST Syntax Validation', bidFitness: 0.88 },
    { role: 'security_auditor', displayName: 'Security Auditor', status: 'reviewing', activeTask: 'Path Guard Audit', bidFitness: 0.92 },
    { role: 'web_scout', displayName: 'Web Scout', status: 'idle', activeTask: 'Standby for Research', bidFitness: 0.65 },
  ],
  quorumApproved = true,
  coderSigned = true,
  securitySigned = true,
  vramUsedMb = 4850,
  maxVramMb = 5632,
  missionGoal = 'Multi-Agent Autonomous Task Orchestration',
  elapsedSeconds = 120,
}) => {
  const vramPercent = Math.min(100, Math.round((vramUsedMb / maxVramMb) * 100));
  const vramIsWarning = vramUsedMb > 5200;

  const mins = Math.floor(elapsedSeconds / 60);
  const secs = elapsedSeconds % 60;
  const timerStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        borderRadius: '8px',
        padding: '16px',
        fontFamily: 'Segoe UI, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          paddingBottom: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BotRegular style={{ fontSize: '20px', color: '#38bdf8' }} />
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>SWARM VISUALIZER</h2>
          <Badge
            appearance="filled"
            color={quorumApproved ? 'success' : 'warning'}
            style={{ fontSize: '11px', textTransform: 'uppercase' }}
          >
            {quorumApproved ? 'Quorum: Approved' : 'Quorum: Pending'}
          </Badge>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isPaused ? (
            <Button
              size="small"
              icon={<PlayRegular />}
              appearance="secondary"
              onClick={onResume}
            >
              Resume
            </Button>
          ) : (
            <Button
              size="small"
              icon={<PauseRegular />}
              appearance="secondary"
              onClick={onPause}
            >
              Pause
            </Button>
          )}

          <Button
            size="small"
            icon={<StopRegular />}
            appearance="primary"
            style={{ backgroundColor: '#ef4444', color: '#ffffff' }}
            onClick={onHalt}
          >
            HALT
          </Button>

          <Button
            size="small"
            appearance="subtle"
            icon={<DismissRegular />}
            onClick={onClose}
          />
        </div>
      </div>

      {/* Goal & Metrics Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr',
          gap: '12px',
          marginBottom: '16px',
          padding: '10px 14px',
          backgroundColor: 'rgba(30, 41, 59, 0.6)',
          borderRadius: '6px',
          fontSize: '12px',
        }}
      >
        <div>
          <span style={{ color: '#94a3b8' }}>Active Goal: </span>
          <span style={{ fontWeight: 500, color: '#e2e8f0' }}>{missionGoal}</span>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>RTX 3050 VRAM: </span>
          <span style={{ color: vramIsWarning ? '#f59e0b' : '#10b981', fontWeight: 600 }}>
            {(vramUsedMb / 1024).toFixed(1)} / {(maxVramMb / 1024).toFixed(1)} GB ({vramPercent}%)
          </span>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Mission Timer: </span>
          <span style={{ color: '#38bdf8', fontWeight: 600 }}>{timerStr}</span>
        </div>
      </div>

      {/* Active Agent Chips */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {agents.map((ag) => (
          <div
            key={ag.role}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              backgroundColor: 'rgba(30, 41, 59, 0.5)',
              fontSize: '11px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ fontWeight: 600, color: '#f8fafc' }}>{ag.displayName}:</span>
            <span style={{ color: '#94a3b8' }}>{ag.status}</span>
          </div>
        ))}
      </div>

      {/* SVG Interactive Multi-Agent Graph Canvas */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          backgroundColor: 'rgba(15, 23, 42, 0.7)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <svg
          viewBox="0 0 600 400"
          style={{ width: '100%', height: '100%', maxHeight: '380px' }}
        >
          {/* Connecting Links */}
          <line x1="300" y1="70" x2="130" y2="240" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="300" y1="70" x2="470" y2="240" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="130" y1="240" x2="470" y2="240" stroke="rgba(16, 185, 129, 0.4)" strokeWidth="2" />
          <line x1="130" y1="240" x2="300" y2="340" stroke="rgba(168, 85, 247, 0.3)" strokeWidth="2" strokeDasharray="4 4" />
          <line x1="470" y1="240" x2="300" y2="340" stroke="rgba(168, 85, 247, 0.3)" strokeWidth="2" strokeDasharray="4 4" />

          {/* Center Hub Indicator */}
          <circle cx="300" cy="220" r="30" fill="rgba(30, 41, 59, 0.8)" stroke="#38bdf8" strokeWidth="1.5" />
          <text x="300" y="224" textAnchor="middle" fill="#38bdf8" fontSize="10" fontWeight="bold">SWARM</text>

          {/* Node 1: Architect (Top Center) */}
          <g transform="translate(300, 70)">
            <circle r="36" fill="rgba(6, 182, 212, 0.15)" stroke="#06b6d4" strokeWidth="2.5" />
            <text x="0" y="-4" textAnchor="middle" fill="#f8fafc" fontSize="12" fontWeight="bold">Architect</text>
            <text x="0" y="14" textAnchor="middle" fill="#94a3b8" fontSize="9">Arbitrator</text>
          </g>

          {/* Node 2: Coder (Left) */}
          <g transform="translate(130, 240)">
            <circle r="36" fill="rgba(16, 185, 129, 0.15)" stroke="#10b981" strokeWidth="2.5" />
            <text x="0" y="-4" textAnchor="middle" fill="#f8fafc" fontSize="12" fontWeight="bold">Coder</text>
            <text x="0" y="14" textAnchor="middle" fill="#94a3b8" fontSize="9">Workspace</text>
          </g>

          {/* Node 3: Security Auditor (Right) */}
          <g transform="translate(470, 240)">
            <circle r="36" fill="rgba(245, 158, 11, 0.15)" stroke="#f59e0b" strokeWidth="2.5" />
            <text x="0" y="-4" textAnchor="middle" fill="#f8fafc" fontSize="12" fontWeight="bold">Security</text>
            <text x="0" y="14" textAnchor="middle" fill="#94a3b8" fontSize="9">Veto Power</text>
          </g>

          {/* Node 4: Web Scout (Bottom Center) */}
          <g transform="translate(300, 340)">
            <circle r="32" fill="rgba(168, 85, 247, 0.15)" stroke="#a855f7" strokeWidth="2.5" />
            <text x="0" y="-3" textAnchor="middle" fill="#f8fafc" fontSize="11" fontWeight="bold">Web Scout</text>
            <text x="0" y="13" textAnchor="middle" fill="#94a3b8" fontSize="9">Research</text>
          </g>
        </svg>
      </div>

      {/* Two-Tier Quorum Sign-Off Footer */}
      <div
        style={{
          marginTop: '16px',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '12px',
        }}
      >
        <div
          style={{
            padding: '10px',
            backgroundColor: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '6px',
            borderLeft: `4px solid ${coderSigned ? '#10b981' : '#f59e0b'}`,
          }}
        >
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Coder Sign-Off</div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: coderSigned ? '#10b981' : '#f59e0b' }}>
            {coderSigned ? '✓ Verified (AST + Tests)' : '⏳ Awaiting Tests'}
          </div>
        </div>

        <div
          style={{
            padding: '10px',
            backgroundColor: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '6px',
            borderLeft: `4px solid ${securitySigned ? '#10b981' : '#f59e0b'}`,
          }}
        >
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Security Auditor Sign-Off</div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: securitySigned ? '#10b981' : '#f59e0b' }}>
            {securitySigned ? '✓ Verified (0 Alerts)' : '⏳ Precondition Audit'}
          </div>
        </div>

        <div
          style={{
            padding: '10px',
            backgroundColor: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '6px',
            borderLeft: `4px solid ${quorumApproved ? '#10b981' : '#f59e0b'}`,
          }}
        >
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Consensus State</div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: quorumApproved ? '#10b981' : '#f59e0b' }}>
            {quorumApproved ? '✓ TWO-TIER PASS' : '⏳ PENDING REVIEW'}
          </div>
        </div>
      </div>
    </div>
  );
};
