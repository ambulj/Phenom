import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  BranchForkRegular,
  FlashRegular,
  CheckmarkCircleRegular,
  ShieldCheckmarkRegular,
  HourglassHalfRegular,
  TagRegular,
  PlayRegular,
  AddRegular,
} from '@fluentui/react-icons';

export interface PlanNodeUI {
  node_id: string;
  title: string;
  node_type: string; // ROOT_GOAL, SUBTASK, LEAF_ACTION
  status: string;    // PENDING, IN_PROGRESS, BLOCKED, COMPLETED, FAILED
  depth: number;
  parent_id?: string;
  prerequisites: string[];
  action_type?: string;
  estimated_duration_ms: number;
}

interface GoalDecompositionTreeHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const GoalDecompositionTreeHUD: React.FC<GoalDecompositionTreeHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [treeId, setTreeId] = useState<string>('tree_init_001');
  const [rootGoal, setRootGoal] = useState<string>('Autonomous System Health & Safety Verification');
  const [inputGoal, setInputGoal] = useState<string>('');
  const [nodes, setNodes] = useState<PlanNodeUI[]>([
    {
      node_id: 'root_001',
      title: 'Autonomous System Health & Safety Verification',
      node_type: 'ROOT_GOAL',
      status: 'IN_PROGRESS',
      depth: 0,
      prerequisites: [],
      estimated_duration_ms: 220.0,
    },
    {
      node_id: 'sub_001',
      title: 'Analyze Prerequisites & System State',
      node_type: 'SUBTASK',
      status: 'COMPLETED',
      depth: 1,
      parent_id: 'root_001',
      prerequisites: [],
      action_type: 'INSPECT',
      estimated_duration_ms: 45.0,
    },
    {
      node_id: 'leaf_001',
      title: 'Inspect System State & Active Processes',
      node_type: 'LEAF_ACTION',
      status: 'COMPLETED',
      depth: 2,
      parent_id: 'sub_001',
      prerequisites: [],
      action_type: 'INSPECT_STATE',
      estimated_duration_ms: 20.0,
    },
    {
      node_id: 'sub_002',
      title: 'Execute Core Workflow Synthesis',
      node_type: 'SUBTASK',
      status: 'IN_PROGRESS',
      depth: 1,
      parent_id: 'root_001',
      prerequisites: ['sub_001'],
      action_type: 'EXECUTE',
      estimated_duration_ms: 120.0,
    },
    {
      node_id: 'leaf_002',
      title: 'Synthesize Solution & State Deltas',
      node_type: 'LEAF_ACTION',
      status: 'IN_PROGRESS',
      depth: 2,
      parent_id: 'sub_002',
      prerequisites: ['leaf_001'],
      action_type: 'SYNTHESIZE',
      estimated_duration_ms: 80.0,
    },
    {
      node_id: 'sub_003',
      title: 'Verify Safety Invariants & Acceptance',
      node_type: 'SUBTASK',
      status: 'PENDING',
      depth: 1,
      parent_id: 'root_001',
      prerequisites: ['sub_002'],
      action_type: 'VERIFY',
      estimated_duration_ms: 50.0,
    },
    {
      node_id: 'leaf_003',
      title: 'Execute Guardian SLA & Invariant Assertion',
      node_type: 'LEAF_ACTION',
      status: 'PENDING',
      depth: 2,
      parent_id: 'sub_003',
      prerequisites: ['leaf_002'],
      action_type: 'VERIFY_SLA',
      estimated_duration_ms: 30.0,
    },
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'GOAL_TREE_UPDATED' && externalEvent.payload) {
      if (externalEvent.payload.tree_id) setTreeId(externalEvent.payload.tree_id);
      if (externalEvent.payload.root_goal) setRootGoal(externalEvent.payload.root_goal);
      if (externalEvent.payload.nodes) setNodes(externalEvent.payload.nodes);
    }
  }, [externalEvent]);

  const handleDecompose = () => {
    if (!inputGoal.trim()) return;
    const newTreeId = `tree_${Math.random().toString(16).substring(2, 10)}`;
    const newRootId = `root_${Math.random().toString(16).substring(2, 8)}`;
    const newSub1 = `sub_${Math.random().toString(16).substring(2, 8)}`;
    const newSub2 = `sub_${Math.random().toString(16).substring(2, 8)}`;
    const newSub3 = `sub_${Math.random().toString(16).substring(2, 8)}`;

    const newNodes: PlanNodeUI[] = [
      {
        node_id: newRootId,
        title: inputGoal,
        node_type: 'ROOT_GOAL',
        status: 'IN_PROGRESS',
        depth: 0,
        prerequisites: [],
        estimated_duration_ms: 300.0,
      },
      {
        node_id: newSub1,
        title: `Analyze Prerequisites for '${inputGoal.substring(0, 30)}'`,
        node_type: 'SUBTASK',
        status: 'PENDING',
        depth: 1,
        parent_id: newRootId,
        prerequisites: [],
        action_type: 'INSPECT',
        estimated_duration_ms: 50.0,
      },
      {
        node_id: newSub2,
        title: `Execute Core Action for '${inputGoal.substring(0, 30)}'`,
        node_type: 'SUBTASK',
        status: 'PENDING',
        depth: 1,
        parent_id: newRootId,
        prerequisites: [newSub1],
        action_type: 'EXECUTE',
        estimated_duration_ms: 150.0,
      },
      {
        node_id: newSub3,
        title: `Verify Invariants for '${inputGoal.substring(0, 30)}'`,
        node_type: 'SUBTASK',
        status: 'PENDING',
        depth: 1,
        parent_id: newRootId,
        prerequisites: [newSub2],
        action_type: 'VERIFY',
        estimated_duration_ms: 60.0,
      },
    ];

    setTreeId(newTreeId);
    setRootGoal(inputGoal);
    setNodes(newNodes);
    setInputGoal('');

    sendMessage?.({
      type: 'CALL_TOOL',
      tool: 'decompose_hierarchical_goal',
      args: { goal_description: inputGoal, max_depth: 4 },
    });
  };

  const handleAdvanceNode = (nodeId: string) => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.node_id === nodeId) {
          const nextStatus =
            n.status === 'PENDING'
              ? 'IN_PROGRESS'
              : n.status === 'IN_PROGRESS'
              ? 'COMPLETED'
              : 'COMPLETED';
          return { ...n, status: nextStatus };
        }
        return n;
      })
    );
  };

  const completedCount = nodes.filter((n) => n.status === 'COMPLETED').length;
  const progressPercent = nodes.length > 0 ? Math.round((completedCount / nodes.length) * 100) : 0;

  return (
    <div
      style={{
        position: 'fixed',
        top: '60px',
        right: '20px',
        width: '680px',
        maxHeight: 'calc(100vh - 100px)',
        backgroundColor: 'rgba(11, 19, 32, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: '12px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.65), 0 0 16px rgba(56, 189, 248, 0.2)',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.12), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BranchForkRegular style={{ fontSize: '22px', color: '#38bdf8' }} />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 600, letterSpacing: '0.5px', color: '#38bdf8' }}>
              AUTONOMOUS GOAL DECOMPOSITION TREE
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Tree: <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>{treeId}</span> |{' '}
              {completedCount}/{nodes.length} Nodes Completed ({progressPercent}%)
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <DismissRegular style={{ fontSize: '18px' }} />
        </button>
      </div>

      {/* Progress Bar */}
      <div style={{ height: '4px', width: '100%', background: 'rgba(56, 189, 248, 0.1)' }}>
        <div
          style={{
            height: '100%',
            width: `${progressPercent}%`,
            background: 'linear-gradient(90deg, #38bdf8, #10b981)',
            transition: 'width 0.4s ease',
          }}
        />
      </div>

      {/* Goal Decomposition Input */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}>
          DECOMPOSE NEW NATURAL LANGUAGE GOAL
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={inputGoal}
            onChange={(e) => setInputGoal(e.target.value)}
            placeholder="e.g. Audit security AST and benchmark Guardian SLA"
            style={{
              flex: 1,
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#f1f5f9',
              fontSize: '12px',
              outline: 'none',
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleDecompose()}
          />
          <button
            onClick={handleDecompose}
            style={{
              backgroundColor: '#0284c7',
              border: 'none',
              borderRadius: '6px',
              padding: '8px 16px',
              color: '#ffffff',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AddRegular style={{ fontSize: '14px' }} />
            Decompose
          </button>
        </div>
      </div>

      {/* Active Goal Root Badge */}
      <div
        style={{
          padding: '10px 20px',
          background: 'rgba(15, 23, 42, 0.5)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: '12px',
          color: '#cbd5e1',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span style={{ color: '#38bdf8', fontWeight: 600 }}>Active Objective:</span>
        <span style={{ color: '#f8fafc', fontWeight: 500 }}>{rootGoal}</span>
      </div>

      {/* Tree Nodes List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {nodes.map((node) => {
          const isRoot = node.node_type === 'ROOT_GOAL';
          const isSubtask = node.node_type === 'SUBTASK';
          const indent = node.depth * 20;

          const statusColor =
            node.status === 'COMPLETED'
              ? '#10b981'
              : node.status === 'IN_PROGRESS'
              ? '#38bdf8'
              : node.status === 'FAILED'
              ? '#f43f5e'
              : '#f59e0b';

          return (
            <div
              key={node.node_id}
              style={{
                marginLeft: `${indent}px`,
                backgroundColor: isRoot
                  ? 'rgba(30, 41, 59, 0.7)'
                  : isSubtask
                  ? 'rgba(15, 23, 42, 0.65)'
                  : 'rgba(15, 23, 42, 0.45)',
                border: `1px solid ${
                  node.status === 'COMPLETED'
                    ? 'rgba(16, 185, 129, 0.4)'
                    : node.status === 'IN_PROGRESS'
                    ? 'rgba(56, 189, 248, 0.5)'
                    : 'rgba(255, 255, 255, 0.08)'
                }`,
                borderRadius: '8px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '11px',
                      color: '#94a3b8',
                      backgroundColor: 'rgba(255, 255, 255, 0.06)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}
                  >
                    {node.node_id}
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      color: isRoot ? '#a855f7' : isSubtask ? '#38bdf8' : '#e2e8f0',
                      border: `1px solid ${isRoot ? '#a855f7' : isSubtask ? '#38bdf8' : '#64748b'}`,
                      borderRadius: '4px',
                      padding: '1px 5px',
                    }}
                  >
                    {node.node_type}
                  </span>
                  {node.action_type && (
                    <span
                      style={{
                        fontSize: '10px',
                        color: '#67e8f9',
                        backgroundColor: 'rgba(103, 232, 249, 0.1)',
                        padding: '1px 5px',
                        borderRadius: '4px',
                      }}
                    >
                      {node.action_type}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: statusColor,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {node.status === 'COMPLETED' ? (
                      <CheckmarkCircleRegular style={{ fontSize: '13px' }} />
                    ) : node.status === 'IN_PROGRESS' ? (
                      <HourglassHalfRegular style={{ fontSize: '13px' }} />
                    ) : (
                      <TagRegular style={{ fontSize: '13px' }} />
                    )}
                    {node.status}
                  </span>

                  {node.status !== 'COMPLETED' && (
                    <button
                      onClick={() => handleAdvanceNode(node.node_id)}
                      title="Advance node status"
                      style={{
                        background: 'rgba(56, 189, 248, 0.15)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        borderRadius: '4px',
                        padding: '3px 8px',
                        color: '#38bdf8',
                        fontSize: '11px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <PlayRegular style={{ fontSize: '10px' }} />
                      Step
                    </button>
                  )}
                </div>
              </div>

              <div style={{ fontSize: '13px', fontWeight: 500, color: '#f1f5f9' }}>
                {node.title}
              </div>

              {node.prerequisites && node.prerequisites.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#94a3b8' }}>
                  <span>Prerequisites:</span>
                  {node.prerequisites.map((p) => (
                    <span
                      key={p}
                      style={{
                        fontFamily: 'monospace',
                        color: '#cbd5e1',
                        backgroundColor: 'rgba(255, 255, 255, 0.06)',
                        padding: '1px 5px',
                        borderRadius: '3px',
                      }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '12px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.8)',
          fontSize: '11px',
          color: '#94a3b8',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheckmarkRegular style={{ fontSize: '14px', color: '#10b981' }} />
          <span>Guardian SLA Active: &lt; 25.0ms halt latency</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FlashRegular style={{ fontSize: '14px', color: '#38bdf8' }} />
          <span>Local Sovereign Planning (Rule 4)</span>
        </div>
      </div>
    </div>
  );
};
