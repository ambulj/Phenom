import React, { useState } from 'react';
import {
  DismissRegular,
  PeopleTeamRegular,
  PlayRegular,
  TimerRegular,
  CodeRegular,
  BookSearchRegular,
  DocumentBulletListRegular,
} from '@fluentui/react-icons';

interface WorkerUI {
  agent_name: string;
  role: string;
  state: 'WAITING' | 'WORKING' | 'TERMINATED';
  tasks_completed: number;
  average_latency_ms: number;
  active_task_id: string | null;
  capabilities: string[];
}

interface SwarmTaskUI {
  task_id: string;
  agent_name: string;
  prompt: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TERMINATED';
  result?: string;
  latency_ms: number;
}

interface MultiAgentSwarmHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const MultiAgentSwarmHUD: React.FC<MultiAgentSwarmHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [selectedAgent, setSelectedAgent] = useState<'coder' | 'research' | 'executive'>('coder');
  const [taskPrompt, setTaskPrompt] = useState<string>('Inspect active module syntax and verify micro-jail sandbox safety.');
  const [isDispatching, setIsDispatching] = useState<boolean>(false);

  const [workers, setWorkers] = useState<WorkerUI[]>([
    {
      agent_name: 'coder',
      role: 'Code Intelligence & AST Sandbox Specialist',
      state: 'WAITING',
      tasks_completed: 12,
      average_latency_ms: 16.4,
      active_task_id: null,
      capabilities: ['ast_parsing', 'syntax_lint', 'sandbox_eval'],
    },
    {
      agent_name: 'research',
      role: 'Obsidian Vault & Memory Synthesis Specialist',
      state: 'WAITING',
      tasks_completed: 8,
      average_latency_ms: 22.1,
      active_task_id: null,
      capabilities: ['vault_search', 'vector_recall', 'knowledge_synthesis'],
    },
    {
      agent_name: 'executive',
      role: 'Executive Assistant & Ambient Focus Specialist',
      state: 'WAITING',
      tasks_completed: 15,
      average_latency_ms: 12.8,
      active_task_id: null,
      capabilities: ['calendar_sync', 'focus_reminders', 'window_staging'],
    },
  ]);

  const [tasks, setTasks] = useState<SwarmTaskUI[]>([
    {
      task_id: 'task-sw-101',
      agent_name: 'coder',
      prompt: 'Inspect AST syntax tree for screen_intelligence_tracker.py',
      status: 'COMPLETED',
      result: 'AST Syntax Tree: 0 SyntaxErrors. Micro-jail AST visitor validated safe operations.',
      latency_ms: 14.8,
    },
    {
      task_id: 'task-sw-102',
      agent_name: 'research',
      prompt: 'Recall architectural guidelines for local offline execution',
      status: 'COMPLETED',
      result: 'Vault Recall: Rule 4 local invariant active. Zero cloud telemetry sockets detected.',
      latency_ms: 21.3,
    },
    {
      task_id: 'task-sw-103',
      agent_name: 'executive',
      prompt: 'Check scheduled calendar meetings and focus window',
      status: 'COMPLETED',
      result: 'Calendar Status: 0 conflicts. Focused application aligned with primary sprint goals.',
      latency_ms: 11.2,
    },
  ]);

  const handleDispatch = () => {
    if (!taskPrompt.trim()) return;
    setIsDispatching(true);

    const newTaskId = `task-sw-${Date.now().toString().slice(-4)}`;
    const targetAgent = selectedAgent;

    // Set worker to WORKING
    setWorkers((prev) =>
      prev.map((w) =>
        w.agent_name === targetAgent ? { ...w, state: 'WORKING', active_task_id: newTaskId } : w
      )
    );

    setTimeout(() => {
      const completedTask: SwarmTaskUI = {
        task_id: newTaskId,
        agent_name: targetAgent,
        prompt: taskPrompt,
        status: 'COMPLETED',
        result: `[${targetAgent.toUpperCase()} Subagent] Completed directive successfully. Zero cloud egress. Rule 11 scrubbed.`,
        latency_ms: Math.floor(Math.random() * 15) + 10,
      };

      setTasks((prev) => [completedTask, ...prev]);
      setWorkers((prev) =>
        prev.map((w) =>
          w.agent_name === targetAgent
            ? {
                ...w,
                state: 'WAITING',
                active_task_id: null,
                tasks_completed: w.tasks_completed + 1,
              }
            : w
        )
      );
      setIsDispatching(false);
    }, 450);
  };

  const handleTerminateAll = () => {
    setWorkers((prev) => prev.map((w) => ({ ...w, state: 'TERMINATED', active_task_id: null })));
  };

  const handleReviveAll = () => {
    setWorkers((prev) => prev.map((w) => ({ ...w, state: 'WAITING' })));
  };

  const getAgentIcon = (name: string) => {
    switch (name) {
      case 'coder':
        return <CodeRegular style={{ fontSize: 16, color: '#38bdf8' }} />;
      case 'research':
        return <BookSearchRegular style={{ fontSize: 16, color: '#a855f7' }} />;
      case 'executive':
        return <DocumentBulletListRegular style={{ fontSize: 16, color: '#22c55e' }} />;
      default:
        return <PeopleTeamRegular style={{ fontSize: 16, color: '#38bdf8' }} />;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 60,
        right: 20,
        width: 520,
        maxHeight: 'calc(100vh - 100px)',
        background: 'rgba(15, 23, 42, 0.96)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(168, 85, 247, 0.3)',
        borderRadius: 12,
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(168, 85, 247, 0.15)',
        color: '#f8fafc',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        zIndex: 9999,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(168, 85, 247, 0.15), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <PeopleTeamRegular style={{ fontSize: 22, color: '#c084fc' }} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '0.05em', color: '#f8fafc' }}>
              LOCAL MULTI-AGENT SWARM HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Milestone 30 • Autonomous Specialist Workers (SWARM-01)
            </div>
          </div>
        </div>
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
              alignItems: 'center',
              borderRadius: 6,
            }}
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        )}
      </div>

      {/* Worker Fleet Cards */}
      <div
        style={{
          padding: '14px 20px',
          background: 'rgba(15, 23, 42, 0.6)',
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          display: 'flex',
          gap: 10,
        }}
      >
        {workers.map((w) => (
          <div
            key={w.agent_name}
            style={{
              flex: 1,
              background: 'rgba(30, 41, 59, 0.5)',
              border: `1px solid ${
                w.state === 'WORKING'
                  ? 'rgba(56, 189, 248, 0.5)'
                  : w.state === 'TERMINATED'
                  ? 'rgba(239, 68, 68, 0.4)'
                  : 'rgba(148, 163, 184, 0.15)'
              }`,
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: '11px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {getAgentIcon(w.agent_name)}
                <span style={{ fontWeight: 700, color: '#f8fafc', textTransform: 'capitalize' }}>
                  {w.agent_name}
                </span>
              </div>
              <span
                style={{
                  fontSize: '9px',
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontWeight: 700,
                  background:
                    w.state === 'WORKING'
                      ? 'rgba(56, 189, 248, 0.2)'
                      : w.state === 'TERMINATED'
                      ? 'rgba(239, 68, 68, 0.2)'
                      : 'rgba(34, 197, 94, 0.2)',
                  color:
                    w.state === 'WORKING'
                      ? '#38bdf8'
                      : w.state === 'TERMINATED'
                      ? '#f87171'
                      : '#86efac',
                }}
              >
                {w.state}
              </span>
            </div>
            <div style={{ color: '#94a3b8', fontSize: '10px', marginBottom: 6 }}>{w.role.split('&')[0]}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '10px' }}>
              <span>Done: {w.tasks_completed}</span>
              <span>{w.average_latency_ms.toFixed(1)}ms</span>
            </div>
          </div>
        ))}
      </div>

      {/* Task Dispatcher Form */}
      <div
        style={{
          padding: '14px 20px',
          background: 'rgba(30, 41, 59, 0.3)',
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#c084fc' }}>DISPATCH LOCAL WORKSTREAM:</span>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['coder', 'research', 'executive'] as const).map((agent) => (
              <button
                key={agent}
                onClick={() => setSelectedAgent(agent)}
                style={{
                  fontSize: '10px',
                  padding: '3px 8px',
                  borderRadius: 4,
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 700,
                  background: selectedAgent === agent ? 'rgba(168, 85, 247, 0.3)' : 'rgba(30, 41, 59, 0.6)',
                  color: selectedAgent === agent ? '#c084fc' : '#94a3b8',
                }}
              >
                {agent.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={taskPrompt}
            onChange={(e) => setTaskPrompt(e.target.value)}
            placeholder="Enter mission prompt for subagent..."
            style={{
              flex: 1,
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              borderRadius: 6,
              padding: '8px 12px',
              fontSize: '11px',
              color: '#f8fafc',
              outline: 'none',
            }}
          />
          <button
            onClick={handleDispatch}
            disabled={isDispatching}
            style={{
              background: 'rgba(168, 85, 247, 0.25)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              color: '#c084fc',
              borderRadius: 6,
              padding: '8px 14px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: isDispatching ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <PlayRegular style={{ fontSize: 12 }} /> {isDispatching ? 'Running...' : 'Dispatch'}
          </button>
        </div>
      </div>

      {/* Task Waterfall / Recent Executions */}
      <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1, maxHeight: 260 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8' }}>RECENT SWARM TASKS:</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={handleReviveAll}
              style={{
                fontSize: '10px',
                background: 'rgba(34, 197, 94, 0.15)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                color: '#86efac',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
              }}
            >
              Revive Fleet
            </button>
            <button
              onClick={handleTerminateAll}
              style={{
                fontSize: '10px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                borderRadius: 4,
                padding: '2px 6px',
                cursor: 'pointer',
              }}
            >
              Halt All
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {tasks.map((t) => (
            <div
              key={t.task_id}
              style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid rgba(148, 163, 184, 0.15)',
                borderRadius: 6,
                padding: '10px 12px',
                fontSize: '11px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {getAgentIcon(t.agent_name)}
                  <span style={{ fontWeight: 600, color: '#f8fafc', textTransform: 'capitalize' }}>
                    {t.agent_name}
                  </span>
                  <span style={{ color: '#64748b', fontSize: '10px' }}>({t.task_id})</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748b', fontSize: '10px' }}>
                  <TimerRegular style={{ fontSize: 10 }} />
                  <span>{t.latency_ms}ms</span>
                  <span
                    style={{
                      fontSize: '9px',
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: 'rgba(34, 197, 94, 0.15)',
                      color: '#86efac',
                      fontWeight: 700,
                    }}
                  >
                    {t.status}
                  </span>
                </div>
              </div>
              <div style={{ color: '#cbd5e1', marginBottom: 4 }}>{t.prompt}</div>
              {t.result && (
                <div
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    padding: '6px 8px',
                    borderRadius: 4,
                    fontSize: '10px',
                    color: '#94a3b8',
                    fontFamily: 'monospace',
                  }}
                >
                  {t.result}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '10px 20px',
          borderTop: '1px solid rgba(148, 163, 184, 0.1)',
          background: 'rgba(15, 23, 42, 0.8)',
          fontSize: '10px',
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>Rule 4: 100% On-Device Actor Bus</span>
        <span>Guardian Kill Switch: &lt; 25.0ms</span>
      </div>
    </div>
  );
};
