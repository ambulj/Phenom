import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BranchForkRegular,
  FlashRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  HourglassHalfRegular,
  TagRegular,
} from '@fluentui/react-icons';

export interface TaskContractUI {
  task_id: string;
  title: string;
  required_skills: Record<string, number>;
  prerequisites: string[];
  status: string; // OPEN, AUCTIONING, AWARDED, COMPLETED
  assigned_agent_id?: string;
  winning_specialization?: string;
  suitability_score?: number;
}

export interface WorkerBidUI {
  agent_id: string;
  specialization: string;
  suitability_score: number;
  estimated_latency_ms: number;
}

interface TaskAuctionProtocolHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const TaskAuctionProtocolHUD: React.FC<TaskAuctionProtocolHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [tasks, setTasks] = useState<TaskContractUI[]>([
    {
      task_id: 'task_001',
      title: 'Consolidate Project Knowledge Context',
      required_skills: { memory_query: 0.8, synthesis: 0.7 },
      prerequisites: [],
      status: 'AWARDED',
      assigned_agent_id: 'agent_knowledgeresearcher',
      winning_specialization: 'KnowledgeResearcher',
      suitability_score: 0.92,
    },
    {
      task_id: 'task_002',
      title: 'Synthesize Core Feature Implementation',
      required_skills: { code_synthesis: 0.85, ast_manipulation: 0.8 },
      prerequisites: ['task_001'],
      status: 'AWARDED',
      assigned_agent_id: 'agent_codearchitect',
      winning_specialization: 'CodeArchitect',
      suitability_score: 0.94,
    },
    {
      task_id: 'task_003',
      title: 'Verify Guardian SLA & Test Coverage',
      required_skills: { testing: 0.9, sla_benchmark: 0.85 },
      prerequisites: ['task_002'],
      status: 'OPEN',
    },
  ]);

  const [selectedTaskId, setSelectedTaskId] = useState<string>('task_003');
  const [bids, setBids] = useState<WorkerBidUI[]>([
    { agent_id: 'agent_testorchestrator', specialization: 'TestOrchestrator', suitability_score: 0.95, estimated_latency_ms: 18.5 },
    { agent_id: 'agent_securityauditor', specialization: 'SecurityAuditor', suitability_score: 0.78, estimated_latency_ms: 28.0 },
    { agent_id: 'agent_codearchitect', specialization: 'CodeArchitect', suitability_score: 0.55, estimated_latency_ms: 36.2 },
    { agent_id: 'agent_knowledgeresearcher', specialization: 'KnowledgeResearcher', suitability_score: 0.48, estimated_latency_ms: 42.0 },
  ]);

  const [objectiveInput, setObjectiveInput] = useState<string>('Build Multi-Modal Vision Anchors');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (externalEvent?.type === 'auction.update' && externalEvent.payload) {
      if (externalEvent.payload.tasks) setTasks(externalEvent.payload.tasks);
      if (externalEvent.payload.bids) setBids(externalEvent.payload.bids);
    }
  }, [externalEvent]);

  const handleConductAuction = (taskId: string) => {
    const updated = tasks.map((t) => {
      if (t.task_id === taskId) {
        return {
          ...t,
          status: 'AWARDED',
          assigned_agent_id: bids[0].agent_id,
          winning_specialization: bids[0].specialization,
          suitability_score: bids[0].suitability_score,
        };
      }
      return t;
    });
    setTasks(updated);

    if (sendMessage) {
      sendMessage({
        type: 'auction.award',
        payload: { task_id: taskId, winning_agent_id: bids[0].agent_id },
      });
    }

    setFeedback(`Awarded ${taskId} to ${bids[0].specialization} (${(bids[0].suitability_score * 100).toFixed(0)}% Match)`);
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleDecomposeObjective = () => {
    const newTasks: TaskContractUI[] = [
      {
        task_id: `task_${Date.now()}_1`,
        title: `Research Architecture: ${objectiveInput}`,
        required_skills: { memory_query: 0.8, security_audit: 0.7 },
        prerequisites: [],
        status: 'OPEN',
      },
      {
        task_id: `task_${Date.now()}_2`,
        title: `Implement Logic: ${objectiveInput}`,
        required_skills: { code_synthesis: 0.9, ast_manipulation: 0.85 },
        prerequisites: [`task_${Date.now()}_1`],
        status: 'OPEN',
      },
    ];
    setTasks([...tasks, ...newTasks]);
    setFeedback(`Decomposed objective into ${newTasks.length} DAG task contracts.`);
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
          <BranchForkRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, letterSpacing: 0.5 }}>
              DECENTRALIZED TASK AUCTION & BIDDING PROTOCOL
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Phase 27-02 • DAG Dependency Ordering • Capability Matching Matrix
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
        {/* Objective Decomposer */}
        <div
          style={{
            padding: 12,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 8,
            display: 'flex',
            gap: 8,
          }}
        >
          <input
            type="text"
            value={objectiveInput}
            onChange={(e) => setObjectiveInput(e.target.value)}
            placeholder="Enter high-level objective to decompose..."
            style={{
              flex: 1,
              padding: '6px 10px',
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: 4,
              color: '#fff',
              fontSize: 12,
            }}
          />
          <button
            onClick={handleDecomposeObjective}
            style={{
              padding: '6px 14px',
              backgroundColor: 'rgba(0, 240, 255, 0.15)',
              border: '1px solid rgba(0, 240, 255, 0.4)',
              borderRadius: 4,
              color: '#00f0ff',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Decompose DAG
          </button>
        </div>

        {/* Task Contract DAG List */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#00f0ff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <TagRegular style={{ fontSize: 14 }} />
            ACTIVE TASK DAG CONTRACTS ({tasks.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tasks.map((task) => (
              <div
                key={task.task_id}
                onClick={() => setSelectedTaskId(task.task_id)}
                style={{
                  padding: '10px 14px',
                  backgroundColor:
                    selectedTaskId === task.task_id ? 'rgba(0, 240, 255, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                  border:
                    selectedTaskId === task.task_id ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 6,
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>
                    <span style={{ color: '#38bdf8' }}>[{task.task_id}]</span> {task.title}
                  </div>
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                    Skills: {Object.entries(task.required_skills).map(([k, v]) => `${k} (≥${(v * 100).toFixed(0)}%)`).join(' • ')}
                    {task.prerequisites.length > 0 && ` • Prereqs: ${task.prerequisites.join(', ')}`}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 10,
                      backgroundColor:
                        task.status === 'AWARDED'
                          ? 'rgba(16, 185, 129, 0.2)'
                          : task.status === 'COMPLETED'
                          ? 'rgba(56, 189, 248, 0.2)'
                          : 'rgba(245, 158, 11, 0.2)',
                      color:
                        task.status === 'AWARDED'
                          ? '#34d399'
                          : task.status === 'COMPLETED'
                          ? '#38bdf8'
                          : '#fbbf24',
                      border:
                        task.status === 'AWARDED'
                          ? '1px solid rgba(16, 185, 129, 0.4)'
                          : '1px solid rgba(245, 158, 11, 0.4)',
                    }}
                  >
                    {task.status}
                    {task.winning_specialization && ` (${task.winning_specialization})`}
                  </span>

                  {task.status === 'OPEN' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleConductAuction(task.task_id);
                      }}
                      style={{
                        padding: '4px 10px',
                        backgroundColor: '#00f0ff',
                        border: 'none',
                        borderRadius: 4,
                        color: '#000',
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <FlashRegular style={{ fontSize: 12 }} />
                      Auction
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Bidding Matrix for Selected Contract */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f59e0b', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <HourglassHalfRegular style={{ fontSize: 14 }} />
            SPECIALIST WORKER BIDDING MATRIX FOR [{selectedTaskId}]
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {bids.map((bid, idx) => (
              <div
                key={bid.agent_id}
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: idx === 0 ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: idx === 0 ? '#34d399' : '#f1f5f9' }}>
                    {bid.specialization} <span style={{ fontSize: 10, color: '#64748b' }}>({bid.agent_id})</span>
                    {idx === 0 && <span style={{ marginLeft: 6, fontSize: 10, color: '#10b981', fontWeight: 700 }}>• TOP BIDDER</span>}
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    Latency Est: {bid.estimated_latency_ms} ms
                  </div>
                </div>

                <div style={{ width: 140, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, height: 6, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 3, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${bid.suitability_score * 100}%`,
                        backgroundColor: idx === 0 ? '#10b981' : '#38bdf8',
                      }}
                    />
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0', width: 35 }}>
                    {(bid.suitability_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
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
          Autonomous Contract Auctioning • Rule 1 Tier 1 Confirmation Enforced
        </span>
        <span>DAG Integrity Checked</span>
      </div>
    </div>
  );
};
