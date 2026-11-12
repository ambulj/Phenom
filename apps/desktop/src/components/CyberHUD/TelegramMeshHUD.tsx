import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PhoneLaptopRegular,
  CheckmarkRegular,
  DismissCircleRegular,
  ShieldCheckmarkRegular,
  MicRegular,
  StopRegular
} from '@fluentui/react-icons';

export interface TelegramApprovalTicketHUD {
  ticket_id: string;
  action_name: string;
  tier: number;
  preview_text: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  expires_in_sec: number;
}

export interface TelegramMeshHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const TelegramMeshHUD: React.FC<TelegramMeshHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [pairedChatId] = useState<string>('849204918 (Saujan)');
  const [isConnected] = useState<boolean>(true);
  const [guardianHalted, setGuardianHalted] = useState<boolean>(false);

  const [tickets, setTickets] = useState<TelegramApprovalTicketHUD[]>([
    {
      ticket_id: 'appr_7c4d9a1e',
      action_name: 'git_atomic_refactor',
      tier: 1,
      preview_text: 'Rename symbol \'TaxCalculator\' across 3 files in billing service.',
      status: 'pending',
      expires_in_sec: 240
    },
    {
      ticket_id: 'appr_3f2b18aa',
      action_name: 'generate_architectural_decision_record',
      tier: 1,
      preview_text: 'Create ADR-014: SQLite Inverted Index with BM25 Saturation in Obsidian.',
      status: 'approved',
      expires_in_sec: 0
    }
  ]);

  const [voiceNoteLogs, setVoiceNoteLogs] = useState<Array<{
    id: string;
    timestamp: string;
    transcript: string;
    citations: string[];
    answer: string;
  }>>([
    {
      id: 'vn_01',
      timestamp: '03:14:22',
      transcript: 'What are our memory retention policies for Obsidian daily logs?',
      citations: ['[1] vault/00_Meta/ARCH_RULES.md', '[2] vault/90_System/Memory_Policy.md'],
      answer: 'Daily notes are retained indefinitely in local markdown; summaries are automatically compacted weekly.'
    }
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'telegram.mesh_update' && externalEvent.payload) {
      if (externalEvent.payload.tickets) setTickets(externalEvent.payload.tickets);
      if (externalEvent.payload.voice_notes) setVoiceNoteLogs(externalEvent.payload.voice_notes);
      if (externalEvent.payload.guardian_halted !== undefined) {
        setGuardianHalted(externalEvent.payload.guardian_halted);
      }
    }
  }, [externalEvent]);

  const handleDecision = (ticketId: string, decision: 'approved' | 'rejected') => {
    setTickets((prev) =>
      prev.map((t) => (t.ticket_id === ticketId ? { ...t, status: decision } : t))
    );
    if (sendMessage) {
      sendMessage({
        type: 'telegram.approval_decision',
        payload: { ticket_id: ticketId, decision }
      });
    }
  };

  const handleRemoteHalt = () => {
    setGuardianHalted(true);
    if (sendMessage) {
      sendMessage({
        type: 'guardian.trigger',
        payload: { reason: 'Remote Telegram /halt triggered from Cyber HUD' }
      });
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(8, 12, 22, 0.95)',
        border: '1px solid rgba(0, 136, 204, 0.4)',
        borderRadius: 14,
        boxShadow: '0 8px 36px rgba(0, 0, 0, 0.75), 0 0 20px rgba(0, 136, 204, 0.2)',
        backdropFilter: 'blur(28px)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        overflow: 'hidden'
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(0, 0, 0, 0.3)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <PhoneLaptopRegular style={{ fontSize: 20, color: '#0088cc' }} />
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '0.04em', color: '#f8fafc' }}>
            TELEGRAM MOBILE COMMAND MESH
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(0, 136, 204, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(0, 136, 204, 0.3)',
              fontWeight: 600
            }}
          >
            TEL-04
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: isConnected ? '#10b981' : '#ef4444',
              backgroundColor: isConnected ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              padding: '2px 8px',
              borderRadius: 4,
              border: `1px solid ${isConnected ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`
            }}
          >
            <ShieldCheckmarkRegular style={{ fontSize: 13 }} />
            <span>Paired: {pairedChatId}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleRemoteHalt}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: guardianHalted ? 'rgba(239, 68, 68, 0.4)' : 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              color: '#fca5a5',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            <StopRegular style={{ fontSize: 14 }} />
            <span>{guardianHalted ? 'HALTED (SLA <25ms)' : 'Simulate /halt'}</span>
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 4,
              borderRadius: 6
            }}
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left Column: Interactive Approval Queue */}
        <div
          style={{
            flex: 1,
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'rgba(0, 0, 0, 0.2)'
          }}
        >
          <div style={{ padding: '10px 16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
              PENDING TELEGRAM INLINE APPROVALS ({tickets.filter((t) => t.status === 'pending').length})
            </span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 14 }}>
            {tickets.map((t) => (
              <div
                key={t.ticket_id}
                style={{
                  padding: 14,
                  borderRadius: 10,
                  marginBottom: 10,
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${t.status === 'pending' ? 'rgba(0, 136, 204, 0.4)' : 'rgba(255, 255, 255, 0.06)'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#38bdf8' }}>{t.ticket_id}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>{t.action_name}</span>
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, backgroundColor: 'rgba(234, 179, 8, 0.15)', color: '#fbbf24' }}>
                      Tier {t.tier}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: t.status === 'approved' ? '#10b981' : t.status === 'rejected' ? '#ef4444' : '#eab308'
                    }}
                  >
                    {t.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: '#cbd5e1', marginTop: 6, lineHeight: 1.4 }}>
                  {t.preview_text}
                </div>
                {t.status === 'pending' && (
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    <button
                      onClick={() => handleDecision(t.ticket_id, 'approved')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        backgroundColor: '#059669',
                        border: 'none',
                        color: '#ffffff',
                        borderRadius: 6,
                        padding: '4px 12px',
                        fontSize: 11,
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      <CheckmarkRegular style={{ fontSize: 13 }} />
                      <span>Approve ✅</span>
                    </button>
                    <button
                      onClick={() => handleDecision(t.ticket_id, 'rejected')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        backgroundColor: '#dc2626',
                        border: 'none',
                        color: '#ffffff',
                        borderRadius: 6,
                        padding: '4px 12px',
                        fontSize: 11,
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      <DismissCircleRegular style={{ fontSize: 13 }} />
                      <span>Reject ❌</span>
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: In-Memory Voice Notes & Offline Hybrid RAG Feed */}
        <div style={{ width: 380, display: 'flex', flexDirection: 'column', backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <MicRegular style={{ fontSize: 16, color: '#38bdf8' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
              REMOTE VOICE RAG & VAULT QUERIES
            </span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {voiceNoteLogs.map((vn) => (
              <div
                key={vn.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  marginBottom: 8,
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b' }}>
                  <span>Voice Note Transcript</span>
                  <span>{vn.timestamp}</span>
                </div>
                <div style={{ fontSize: 12, fontWeight: 500, color: '#38bdf8', marginTop: 4 }}>
                  "{vn.transcript}"
                </div>
                <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 6, lineHeight: 1.3 }}>
                  {vn.answer}
                </div>
                <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {vn.citations.map((c, i) => (
                    <span key={i} style={{ fontSize: 10, color: '#10b981', fontFamily: 'monospace' }}>
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
