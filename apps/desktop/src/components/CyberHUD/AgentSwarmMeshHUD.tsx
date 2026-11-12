import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PeopleTeamRegular,
  CodeRegular,
  ShieldCheckmarkRegular,
  BeakerRegular,
  BrainCircuitRegular,
  SendRegular,
  CheckmarkCircleRegular,
  PlayRegular,
  StopRegular,
} from '@fluentui/react-icons';

export interface SpecialistAgentUI {
  agent_id: string;
  specialization: string;
  status: string; // IDLE, BUSY, HALTED
  mailbox_size: number;
  sent_count: number;
  received_count: number;
  skill_vector: Record<string, number>;
}

interface AgentSwarmMeshHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const AgentSwarmMeshHUD: React.FC<AgentSwarmMeshHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [agents, setAgents] = useState<SpecialistAgentUI[]>([
    {
      agent_id: 'agent_codearchitect',
      specialization: 'CodeArchitect',
      status: 'IDLE',
      mailbox_size: 1,
      sent_count: 8,
      received_count: 5,
      skill_vector: { code_synthesis: 0.95, ast_manipulation: 0.90, security_audit: 0.40 },
    },
    {
      agent_id: 'agent_securityauditor',
      specialization: 'SecurityAuditor',
      status: 'IDLE',
      mailbox_size: 2,
      sent_count: 4,
      received_count: 6,
      skill_vector: { security_audit: 0.98, rule_8_shield: 1.0, testing: 0.80 },
    },
    {
      agent_id: 'agent_testorchestrator',
      specialization: 'TestOrchestrator',
      status: 'IDLE',
      mailbox_size: 0,
      sent_count: 3,
      received_count: 4,
      skill_vector: { testing: 0.95, chaos_battery: 0.90, sla_benchmark: 0.92 },
    },
    {
      agent_id: 'agent_knowledgeresearcher',
      specialization: 'KnowledgeResearcher',
      status: 'IDLE',
      mailbox_size: 0,
      sent_count: 5,
      received_count: 3,
      skill_vector: { memory_query: 0.92, epistemic_beliefs: 0.88, synthesis: 0.85 },
    },
  ]);

  const [senderId, setSenderId] = useState<string>('agent_codearchitect');
  const [recipientId, setRecipientId] = useState<string>('agent_securityauditor');
  const [messageType, setMessageType] = useState<string>('QUERY');
  const [messagePayload, setMessagePayload] = useState<string>('Validate AST security visitor rules');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'mesh.update' && externalEvent.payload) {
      if (externalEvent.payload.agents) setAgents(externalEvent.payload.agents);
    }
  }, [externalEvent]);

  const getSpecialistIcon = (spec: string) => {
    switch (spec) {
      case 'CodeArchitect':
        return <CodeRegular style={{ color: '#00f0ff', fontSize: 18 }} />;
      case 'SecurityAuditor':
        return <ShieldCheckmarkRegular style={{ color: '#10b981', fontSize: 18 }} />;
      case 'TestOrchestrator':
        return <BeakerRegular style={{ color: '#f59e0b', fontSize: 18 }} />;
      case 'KnowledgeResearcher':
        return <BrainCircuitRegular style={{ color: '#a78bfa', fontSize: 18 }} />;
      default:
        return <PeopleTeamRegular style={{ color: '#38bdf8', fontSize: 18 }} />;
    }
  };

  const handleSendMessage = () => {
    const updatedAgents = agents.map((a) => {
      if (a.agent_id === recipientId || recipientId === 'BROADCAST') {
        return { ...a, mailbox_size: a.mailbox_size + 1, received_count: a.received_count + 1 };
      }
      if (a.agent_id === senderId) {
        return { ...a, sent_count: a.sent_count + 1 };
      }
      return a;
    });
    setAgents(updatedAgents);

    if (sendMessage) {
      sendMessage({
        type: 'mesh.send_message',
        payload: {
          sender_id: senderId,
          recipient_id: recipientId,
          message_type: messageType,
          payload: { text: messagePayload },
        },
      });
    }

    setFeedback(`Routed ${messageType} from ${senderId} to ${recipientId}`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleToggleHalt = (agentId: string) => {
    const updatedAgents = agents.map((a) => {
      if (a.agent_id === agentId) {
        const nextStatus = a.status === 'HALTED' ? 'IDLE' : 'HALTED';
        return { ...a, status: nextStatus };
      }
      return a;
    });
    setAgents(updatedAgents);
    setFeedback(`Agent ${agentId} status updated.`);
    setTimeout(() => setFeedback(null), 3000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 40,
        right: 40,
        width: 680,
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
          <PeopleTeamRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              LOCAL AGENT SWARM MESH & SPECIALIST REGISTRY
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 27-01 • In-Memory P2P Mailbox Queues • Zero Cloud Telemetry (Rule 4)
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
        {/* Swarm Node Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
          {agents.map((agent) => (
            <div
              key={agent.agent_id}
              style={{
                padding: '12px 14px',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border:
                  agent.status === 'HALTED'
                    ? '1px solid rgba(239, 68, 68, 0.4)'
                    : '1px solid rgba(0, 240, 255, 0.2)',
                borderRadius: 8,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {getSpecialistIcon(agent.specialization)}
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>{agent.specialization}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>{agent.agent_id}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 10,
                      backgroundColor:
                        agent.status === 'HALTED'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : 'rgba(16, 185, 129, 0.2)',
                      color: agent.status === 'HALTED' ? '#f87171' : '#34d399',
                      border:
                        agent.status === 'HALTED'
                          ? '1px solid rgba(239, 68, 68, 0.4)'
                          : '1px solid rgba(16, 185, 129, 0.4)',
                    }}
                  >
                    {agent.status}
                  </span>
                  <button
                    onClick={() => handleToggleHalt(agent.agent_id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: agent.status === 'HALTED' ? '#10b981' : '#ef4444',
                      cursor: 'pointer',
                      padding: 2,
                      display: 'flex',
                    }}
                    title={agent.status === 'HALTED' ? 'Resume Agent' : 'Halt Agent'}
                  >
                    {agent.status === 'HALTED' ? <PlayRegular style={{ fontSize: 14 }} /> : <StopRegular style={{ fontSize: 14 }} />}
                  </button>
                </div>
              </div>

              {/* Skills summary */}
              <div style={{ fontSize: 10, color: '#94a3b8' }}>
                Skills:{' '}
                {Object.entries(agent.skill_vector)
                  .map(([k, v]) => `${k} (${(v * 100).toFixed(0)}%)`)
                  .join(' • ')}
              </div>

              {/* Mailbox & Traffic */}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#cbd5e1', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: 6 }}>
                <span>Mailbox: <strong style={{ color: '#00f0ff' }}>{agent.mailbox_size}</strong></span>
                <span>Sent: <strong style={{ color: '#38bdf8' }}>{agent.sent_count}</strong></span>
                <span>Recv: <strong style={{ color: '#10b981' }}>{agent.received_count}</strong></span>
              </div>
            </div>
          ))}
        </div>

        {/* Inter-Agent Message Dispatcher */}
        <div
          style={{
            padding: 14,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(0, 240, 255, 0.15)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', display: 'flex', alignItems: 'center', gap: 6 }}>
            <SendRegular style={{ fontSize: 14 }} />
            PEER-TO-PEER ASYNCHRONOUS MESSAGE ROUTER
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Sender Node</label>
              <select
                value={senderId}
                onChange={(e) => setSenderId(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              >
                {agents.map((a) => (
                  <option key={a.agent_id} value={a.agent_id} style={{ background: '#0f172a' }}>
                    {a.specialization} ({a.agent_id})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Recipient Node</label>
              <select
                value={recipientId}
                onChange={(e) => setRecipientId(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              >
                <option value="BROADCAST" style={{ background: '#0f172a' }}>[BROADCAST TO ALL]</option>
                {agents.map((a) => (
                  <option key={a.agent_id} value={a.agent_id} style={{ background: '#0f172a' }}>
                    {a.specialization} ({a.agent_id})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: 10, color: '#94a3b8' }}>Message Type</label>
              <select
                value={messageType}
                onChange={(e) => setMessageType(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: 2,
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 4,
                  color: '#fff',
                  fontSize: 12,
                }}
              >
                <option value="QUERY" style={{ background: '#0f172a' }}>QUERY</option>
                <option value="DIRECTIVE" style={{ background: '#0f172a' }}>DIRECTIVE</option>
                <option value="STATE_UPDATE" style={{ background: '#0f172a' }}>STATE_UPDATE</option>
                <option value="BID" style={{ background: '#0f172a' }}>BID</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ fontSize: 10, color: '#94a3b8' }}>Payload Text</label>
            <input
              type="text"
              value={messagePayload}
              onChange={(e) => setMessagePayload(e.target.value)}
              style={{
                width: '100%',
                marginTop: 2,
                padding: '6px 8px',
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: 4,
                color: '#fff',
                fontSize: 12,
              }}
            />
          </div>

          <button
            onClick={handleSendMessage}
            style={{
              padding: '8px 14px',
              backgroundColor: '#00f0ff',
              border: 'none',
              borderRadius: 4,
              color: '#000',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              marginTop: 4,
            }}
          >
            <SendRegular style={{ fontSize: 14 }} />
            Transmit In-Memory P2P Message
          </button>
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
          <ShieldCheckmarkRegular style={{ color: '#00f0ff' }} />
          Local In-Memory Queues • Zero Cloud Telemetry (Rule 4)
        </span>
        <span>Guardian SLA &lt; 25ms Active</span>
      </div>
    </div>
  );
};
