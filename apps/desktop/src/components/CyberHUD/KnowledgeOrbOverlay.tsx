import React, { useState, useEffect } from 'react';
import { Badge, Button, Tooltip } from '@fluentui/react-components';
import { DismissRegular, ArrowSyncRegular } from '@fluentui/react-icons';

export type KnowledgeEntityType =
  | 'PROJECT'
  | 'CONCEPT'
  | 'TASK'
  | 'TOOL'
  | 'DECISION'
  | 'FAILURE';

export interface KnowledgeOrbNode {
  id: string;
  name: string;
  entityType: KnowledgeEntityType;
  validTime: string;
  transactionTime: string;
  score: number;
  isActive?: boolean;
  connections: string[];
}

export interface KnowledgeOrbOverlayProps {
  nodes?: KnowledgeOrbNode[];
  onNodeSelect?: (node: KnowledgeOrbNode) => void;
  onClose?: () => void;
  width?: number;
  height?: number;
}

const ENTITY_COLORS: Record<KnowledgeEntityType, string> = {
  PROJECT: '#3b82f6',   // Vibrant Blue
  CONCEPT: '#00e5ff',   // Electric Cyan
  TASK: '#eab308',      // Amber
  TOOL: '#10b981',      // Emerald Green
  DECISION: '#a855f7',  // Neon Purple
  FAILURE: '#ef4444',   // Stark Crimson
};

const DEFAULT_NODES: KnowledgeOrbNode[] = [
  {
    id: 'ent-proj-49',
    name: 'CognitiveChoreographer',
    entityType: 'PROJECT',
    validTime: '2026-11-16T12:00:00Z',
    transactionTime: '2026-11-16T12:00:05Z',
    score: 0.99,
    isActive: true,
    connections: ['ent-con-bitemp', 'ent-tool-bezier', 'ent-dec-anti-chk'],
  },
  {
    id: 'ent-con-bitemp',
    name: 'BiTemporalGraphEngine',
    entityType: 'CONCEPT',
    validTime: '2026-11-16T13:00:00Z',
    transactionTime: '2026-11-16T13:00:02Z',
    score: 0.95,
    isActive: true,
    connections: ['ent-dec-anti-chk', 'ent-fail-rec'],
  },
  {
    id: 'ent-tool-bezier',
    name: 'BezierTrajectoryEngine',
    entityType: 'TOOL',
    validTime: '2026-11-16T16:00:00Z',
    transactionTime: '2026-11-16T16:00:10Z',
    score: 0.91,
    isActive: false,
    connections: ['ent-task-halo'],
  },
  {
    id: 'ent-task-halo',
    name: 'TargetHaloProjection',
    entityType: 'TASK',
    validTime: '2026-11-16T16:30:00Z',
    transactionTime: '2026-11-16T16:30:05Z',
    score: 0.88,
    isActive: false,
    connections: ['ent-tool-bezier'],
  },
  {
    id: 'ent-dec-anti-chk',
    name: 'AntiCheckoutShieldRule8',
    entityType: 'DECISION',
    validTime: '2026-11-16T17:00:00Z',
    transactionTime: '2026-11-16T17:00:01Z',
    score: 0.97,
    isActive: true,
    connections: ['ent-proj-49'],
  },
  {
    id: 'ent-fail-rec',
    name: 'HeuristicSignatureRecovery',
    entityType: 'FAILURE',
    validTime: '2026-11-16T15:00:00Z',
    transactionTime: '2026-11-16T15:00:03Z',
    score: 0.85,
    isActive: false,
    connections: ['ent-con-bitemp'],
  },
];

export const KnowledgeOrbOverlay: React.FC<KnowledgeOrbOverlayProps> = ({
  nodes = DEFAULT_NODES,
  onNodeSelect,
  onClose,
  width = 540,
  height = 420,
}) => {
  const [pulsePhase, setPulsePhase] = useState(0);
  const [hoveredNode, setHoveredNode] = useState<KnowledgeOrbNode | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setPulsePhase((prev) => (prev + 1) % 360);
    }, 40);
    return () => clearInterval(timer);
  }, []);

  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.38;

  // Calculate coordinates for radial orbiting nodes
  const nodePositions = nodes.map((node, index) => {
    const angleOffset = (pulsePhase * 0.25 * Math.PI) / 180;
    const angle = (index / nodes.length) * 2 * Math.PI + angleOffset;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { ...node, x, y };
  });

  return (
    <div
      style={{
        position: 'relative',
        width: `${width}px`,
        height: `${height}px`,
        pointerEvents: 'auto',
        userSelect: 'none',
      }}
    >
      {/* Background SVG Canvas for connecting ripples and relationship lines */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      >
        <defs>
          <filter id="orb-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Orbit Ring */}
        <circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke="rgba(0, 229, 255, 0.18)"
          strokeDasharray="4 6"
          strokeWidth="1.5"
        />

        {/* Pulsing Active Ripple */}
        <circle
          cx={centerX}
          cy={centerY}
          r={radius + Math.sin((pulsePhase * Math.PI) / 180) * 12}
          fill="none"
          stroke="rgba(0, 229, 255, 0.08)"
          strokeWidth="1"
        />

        {/* Inter-node relation lines */}
        {nodePositions.map((node) =>
          node.connections.map((targetId) => {
            const target = nodePositions.find((n) => n.id === targetId);
            if (!target) return null;
            const isHighlighted =
              hoveredNode?.id === node.id || hoveredNode?.id === target.id;
            return (
              <line
                key={`${node.id}-${target.id}`}
                x1={node.x}
                y1={node.y}
                x2={target.x}
                y2={target.y}
                stroke={isHighlighted ? '#00e5ff' : 'rgba(255, 255, 255, 0.12)'}
                strokeWidth={isHighlighted ? 2 : 1}
                strokeDasharray={node.isActive || target.isActive ? '2 2' : undefined}
              />
            );
          })
        )}
      </svg>

      {/* Render Radial Interactive Nodes */}
      {nodePositions.map((node) => {
        const color = ENTITY_COLORS[node.entityType] || '#00e5ff';
        const isHovered = hoveredNode?.id === node.id;
        const glowRadius = node.isActive ? 14 : isHovered ? 10 : 4;

        return (
          <Tooltip
            key={node.id}
            content={
              <div style={{ padding: '4px 6px', fontSize: '11px', color: '#f8fafc' }}>
                <div style={{ fontWeight: 600, color }}>{node.name}</div>
                <div>Type: {node.entityType}</div>
                <div>Score: {(node.score * 100).toFixed(1)}%</div>
                <div>Tv: {new Date(node.validTime).toLocaleTimeString()}</div>
                <div>Tt: {new Date(node.transactionTime).toLocaleTimeString()}</div>
              </div>
            }
            relationship="description"
          >
            <div
              onClick={() => onNodeSelect?.(node)}
              onMouseEnter={() => setHoveredNode(node)}
              onMouseLeave={() => setHoveredNode(null)}
              style={{
                position: 'absolute',
                left: `${node.x - 14}px`,
                top: `${node.y - 14}px`,
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: 'rgba(10, 14, 23, 0.92)',
                border: `2px solid ${color}`,
                boxShadow: `0 0 ${glowRadius}px ${color}`,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                transform: isHovered ? 'scale(1.25)' : 'scale(1.0)',
                zIndex: 10,
              }}
            >
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: color,
                }}
              />
            </div>
          </Tooltip>
        );
      })}

      {/* Header controls overlay */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 12,
          right: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pointerEvents: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Badge appearance="filled" color="brand" size="small">
            Bi-Temporal Matrix
          </Badge>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            {nodes.length} Nodes Loaded
          </span>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <Button
            size="small"
            appearance="subtle"
            icon={<ArrowSyncRegular style={{ fontSize: 13 }} />}
            onClick={() => setPulsePhase(0)}
          />
          {onClose && (
            <Button
              size="small"
              appearance="subtle"
              icon={<DismissRegular style={{ fontSize: 13 }} />}
              onClick={onClose}
            />
          )}
        </div>
      </div>
    </div>
  );
};
