import React, { useState, useEffect } from 'react';
import {
  Button,
  Badge,
  Tooltip,
} from '@fluentui/react-components';
import {
  Speaker2Regular,
  DismissRegular,
  NavigationRegular,
} from '@fluentui/react-icons';

export interface ReflexBlip {
  id: string;
  eventType: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'CRITICAL';
  source: string;
  title: string;
  timestamp: number;
}

export interface SuggestedProposal {
  proposalId: string;
  title: string;
  toolName: string;
  tier: number;
  explanation: string;
}

export interface ReflexRadarPayload {
  activeApp: string;
  activeFile?: string;
  project?: string;
  voiceText?: string;
  wordCount?: number;
  blips: ReflexBlip[];
  proposals: SuggestedProposal[];
}

export interface ReflexRadarOverlayProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const ReflexRadarOverlay: React.FC<ReflexRadarOverlayProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [radarData, setRadarData] = useState<ReflexRadarPayload | null>(null);
  const [minimized, setMinimized] = useState<boolean>(false);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'REFLEX_RADAR_TELEMETRY' || type === 'REFLEX_EVENT_DETECTED') {
      const blips: ReflexBlip[] = (payload.recent_events || []).map((e: any, idx: number) => ({
        id: e.event_id || `blip_${idx}`,
        eventType: e.event_type || 'UNKNOWN',
        severity: (e.severity as any) || 'INFO',
        source: e.source || 'sentinel',
        title: e.visual_details?.matched_pattern || e.toast_details?.title || e.event_type,
        timestamp: e.timestamp || Date.now(),
      }));

      const proposals: SuggestedProposal[] = (payload.proposals || []).map((p: any) => ({
        proposalId: p.proposal_id,
        title: p.title,
        toolName: p.tool_name,
        tier: p.tier ?? 0,
        explanation: p.explanation || '',
      }));

      setRadarData({
        activeApp: payload.active_app || payload.process_name || 'VS Code',
        activeFile: payload.active_file,
        project: payload.project_name || 'Phenom',
        voiceText: payload.voice_commentary,
        wordCount: payload.word_count,
        blips: blips.length > 0 ? blips : (radarData?.blips || []),
        proposals,
      });
    }
  }, [externalEvent]);

  if (!radarData && !externalEvent) {
    return null;
  }

  const activeApp = radarData?.activeApp || 'Desktop Active';
  const activeFile = radarData?.activeFile;
  const blips = radarData?.blips || [];
  const proposals = radarData?.proposals || [];
  const voiceText = radarData?.voiceText;
  const wordCount = radarData?.wordCount ?? (voiceText ? voiceText.split(' ').length : 0);

  const handleExecuteProposal = (proposal: SuggestedProposal) => {
    if (sendMessage) {
      sendMessage({
        type: 'EXECUTE_REFLEX_ACTION',
        payload: {
          proposal_id: proposal.proposalId,
          tool_name: proposal.toolName,
          tier: proposal.tier,
        },
      });
    }
  };

  const getBlipColor = (sev: string) => {
    switch (sev) {
      case 'CRITICAL': return '#FF3366';
      case 'WARNING': return '#FFB300';
      case 'SUCCESS': return '#00FFCC';
      default: return '#00B4D8';
    }
  };

  if (minimized) {
    return (
      <div
        onClick={() => setMinimized(false)}
        style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: 9999,
          background: 'rgba(10, 16, 26, 0.9)',
          border: '1px solid #00FFCC',
          borderRadius: '20px',
          padding: '6px 14px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#00FFCC',
          boxShadow: '0 0 15px rgba(0, 255, 204, 0.25)',
        }}
      >
        <NavigationRegular />
        <span style={{ fontSize: '11px', fontFamily: 'monospace' }}>RADAR ({blips.length})</span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        width: '320px',
        background: 'rgba(10, 15, 26, 0.95)',
        border: '1px solid rgba(0, 255, 204, 0.4)',
        borderRadius: '12px',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.7), 0 0 20px rgba(0, 255, 204, 0.2)',
        padding: '14px',
        zIndex: 9999,
        color: '#E0E6ED',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: '#00FFCC',
              boxShadow: '0 0 8px #00FFCC',
              animation: 'pulse 2s infinite',
            }}
          />
          <span style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', color: '#00FFCC' }}>
            REFLEX RADAR
          </span>
          <Badge size="small" appearance="outline" color="brand">
            &lt;100ms
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <Button
            size="small"
            appearance="subtle"
            icon={<DismissRegular />}
            onClick={() => {
              setMinimized(true);
              if (onClose) onClose();
            }}
            title="Minimize"
          />
        </div>
      </div>

      {/* Active Context Chip */}
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: '8px',
          padding: '8px 10px',
          marginBottom: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '3px',
          borderLeft: '3px solid #00FFCC',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#8892B0' }}>
          <span>FOCUS ANCHOR</span>
          <span style={{ color: '#00FFCC' }}>{activeApp}</span>
        </div>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#F8F9FA', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {activeFile ? `📄 ${activeFile}` : `📁 ${radarData?.project || 'Phenom Workspace'}`}
        </div>
      </div>

      {/* Radar Scan Visualization */}
      <div
        style={{
          height: '60px',
          background: 'radial-gradient(circle, rgba(0, 255, 204, 0.08) 0%, rgba(10, 15, 26, 0.5) 70%)',
          borderRadius: '8px',
          position: 'relative',
          overflow: 'hidden',
          marginBottom: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(0, 255, 204, 0.15)',
        }}
      >
        {/* Animated Sweep Line */}
        <div
          style={{
            position: 'absolute',
            width: '100%',
            height: '2px',
            background: 'linear-gradient(90deg, transparent, #00FFCC, transparent)',
            boxShadow: '0 0 10px #00FFCC',
            top: '50%',
          }}
        />
        {/* Radar Blips */}
        <div style={{ display: 'flex', gap: '8px', zIndex: 2 }}>
          {blips.slice(-4).map((b) => (
            <Tooltip key={b.id} content={`${b.eventType}: ${b.title}`} relationship="label">
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: getBlipColor(b.severity),
                  boxShadow: `0 0 8px ${getBlipColor(b.severity)}`,
                  cursor: 'pointer',
                }}
              />
            </Tooltip>
          ))}
          {blips.length === 0 && (
            <span style={{ fontSize: '11px', color: '#6C757D' }}>Sentinel Scanning (10Hz)...</span>
          )}
        </div>
      </div>

      {/* Voice Commentary Capsule */}
      {voiceText && (
        <div
          style={{
            background: 'rgba(0, 255, 204, 0.05)',
            border: '1px solid rgba(0, 255, 204, 0.2)',
            borderRadius: '8px',
            padding: '8px 10px',
            marginBottom: '10px',
            fontSize: '11px',
            lineHeight: '1.4',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#00FFCC', fontWeight: 600 }}>
              <Speaker2Regular /> JARVIS
            </span>
            <span style={{ fontSize: '10px', color: '#8892B0' }}>{wordCount}/20w</span>
          </div>
          <div style={{ fontStyle: 'italic', color: '#E2E8F0' }}>"{voiceText}"</div>
        </div>
      )}

      {/* 1-Click Action Proposals */}
      {proposals.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: '10px', fontWeight: 700, color: '#8892B0', letterSpacing: '0.05em' }}>
            SUGGESTED REFLEX ACTIONS
          </div>
          {proposals.slice(0, 2).map((p) => (
            <div
              key={p.proposalId}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '6px',
                padding: '6px 8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                border: '1px solid rgba(255, 255, 255, 0.06)',
              }}
            >
              <div style={{ overflow: 'hidden', paddingRight: '8px' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#FFFFFF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.title}
                </div>
                <div style={{ fontSize: '10px', color: '#A0AEC0' }}>Tier {p.tier} • {p.toolName}</div>
              </div>
              <Button
                size="small"
                appearance="primary"
                onClick={() => handleExecuteProposal(p)}
                style={{
                  background: 'linear-gradient(135deg, #00FFCC 0%, #00B4D8 100%)',
                  color: '#0A0F1A',
                  fontWeight: 700,
                  fontSize: '10px',
                  height: '24px',
                  minWidth: '50px',
                  border: 'none',
                }}
              >
                Run
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
