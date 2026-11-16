import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Button,
  Input,
  Slider,
  Badge,
  Card,
  Text,
} from '@fluentui/react-components';
import {
  DismissRegular,
  SearchRegular,
  ZoomInRegular,
  ZoomOutRegular,
  ArrowResetRegular,
  ShieldRegular,
  BrainCircuitRegular,
  FilterRegular,
} from '@fluentui/react-icons';

export type EntityType =
  | 'PROJECT'
  | 'CONCEPT'
  | 'TASK'
  | 'TOOL'
  | 'DECISION'
  | 'FAILURE';

export interface MatrixNode {
  id: string;
  name: string;
  type: EntityType;
  validStart: number;
  validEnd?: number;
  txStart: number;
  score: number;
  properties: Record<string, any>;
  x?: number;
  y?: number;
}

export interface MatrixEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface KnowledgeMatrixPanelProps {
  onClose: () => void;
  onEmergencyHalt?: () => void;
  initialNodes?: MatrixNode[];
  initialEdges?: MatrixEdge[];
}

const TYPE_COLORS: Record<EntityType, string> = {
  PROJECT: '#3b82f6',
  CONCEPT: '#00e5ff',
  TASK: '#eab308',
  TOOL: '#10b981',
  DECISION: '#a855f7',
  FAILURE: '#ef4444',
};

const SAMPLE_NODES: MatrixNode[] = [
  {
    id: 'node-choreographer',
    name: 'Cognitive Choreographer',
    type: 'PROJECT',
    validStart: 1731750000,
    txStart: 1731750010,
    score: 0.99,
    properties: { milestone: 49, phase: 'All', author: 'Phenom' },
  },
  {
    id: 'node-bitemporal',
    name: 'Bi-Temporal Engine',
    type: 'CONCEPT',
    validStart: 1731752000,
    txStart: 1731752005,
    score: 0.96,
    properties: { dimensions: 'Tv x Tt', storage: 'SQLCipher SQLite' },
  },
  {
    id: 'node-associative',
    name: 'Associative Retriever',
    type: 'TOOL',
    validStart: 1731753000,
    txStart: 1731753010,
    score: 0.92,
    properties: { formula: 'BM25 + Dense + Decay + DegreeCentrality' },
  },
  {
    id: 'node-postmortem',
    name: 'PostMortem Classifier',
    type: 'TOOL',
    validStart: 1731755000,
    txStart: 1731755015,
    score: 0.91,
    properties: { hash: 'sig_{tool}_{cat}_{hash}' },
  },
  {
    id: 'node-anticheckout',
    name: 'Anti-Checkout Shield',
    type: 'DECISION',
    validStart: 1731757000,
    txStart: 1731757002,
    score: 0.98,
    properties: { enforced_rule: 'Rule 8 (No payments/checkouts)' },
  },
  {
    id: 'node-bezier',
    name: 'Bezier Motor Model',
    type: 'TOOL',
    validStart: 1731759000,
    txStart: 1731759012,
    score: 0.89,
    properties: { profile: 'Sinusoidal ease-in-out + Tremor jitter' },
  },
  {
    id: 'node-takeover',
    name: 'Operator Mouse Takeover',
    type: 'DECISION',
    validStart: 1731758000,
    txStart: 1731758005,
    score: 0.95,
    properties: { threshold: '15px displacement', sla: '< 10ms (0.1ms measured)' },
  },
  {
    id: 'node-recovery-fail',
    name: 'Transient DOM Detach',
    type: 'FAILURE',
    validStart: 1731756000,
    txStart: 1731756010,
    score: 0.84,
    properties: { root_cause: 'Node detached during reactive render' },
  },
];

const SAMPLE_EDGES: MatrixEdge[] = [
  { id: 'e1', source: 'node-choreographer', target: 'node-bitemporal', relation: 'ARCHITECTED_BY', weight: 1.0 },
  { id: 'e2', source: 'node-bitemporal', target: 'node-associative', relation: 'QUERIED_BY', weight: 0.95 },
  { id: 'e3', source: 'node-choreographer', target: 'node-bezier', relation: 'DISPATCHES', weight: 0.9 },
  { id: 'e4', source: 'node-bezier', target: 'node-takeover', relation: 'MONITORED_BY', weight: 0.88 },
  { id: 'e5', source: 'node-choreographer', target: 'node-anticheckout', relation: 'RESTRICTED_BY', weight: 1.0 },
  { id: 'e6', source: 'node-postmortem', target: 'node-recovery-fail', relation: 'ANALYZES', weight: 0.85 },
];

export const KnowledgeMatrixPanel: React.FC<KnowledgeMatrixPanelProps> = ({
  onClose,
  onEmergencyHalt,
  initialNodes = SAMPLE_NODES,
  initialEdges = SAMPLE_EDGES,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Search & Type Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  // Zoom and Pan
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Bi-Temporal Time Scrubbers (Unix seconds)
  const minTime = 1731749000;
  const maxTime = 1731760000;
  const [validTimeCutoff, setValidTimeCutoff] = useState<number>(maxTime);

  // Inspector
  const [selectedNode, setSelectedNode] = useState<MatrixNode | null>(null);

  // Filter nodes based on search, type, and Valid Time cutoff
  const filteredNodes = useMemo(() => {
    return initialNodes.filter((node) => {
      if (selectedType !== 'ALL' && node.type !== selectedType) return false;
      if (searchQuery.trim() && !node.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (node.validStart > validTimeCutoff) return false;
      return true;
    });
  }, [initialNodes, selectedType, searchQuery, validTimeCutoff]);

  const activeNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return initialEdges.filter(
      (edge) => activeNodeIds.has(edge.source) && activeNodeIds.has(edge.target)
    );
  }, [initialEdges, activeNodeIds]);

  // Position nodes radially
  const layoutNodes = useMemo(() => {
    const total = filteredNodes.length;
    return filteredNodes.map((node, index) => {
      const angle = (index / (total || 1)) * 2 * Math.PI;
      const radius = 180 + (index % 2) * 50;
      return {
        ...node,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      };
    });
  }, [filteredNodes]);

  // Canvas render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    ctx.save();
    // Center origin + pan + zoom
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);

    // Draw background concentric orbit grids
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
    ctx.lineWidth = 1;
    [100, 180, 230, 290].forEach((r) => {
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.stroke();
    });

    // Draw Edges
    const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]));
    filteredEdges.forEach((edge) => {
      const src = nodeMap.get(edge.source);
      const tgt = nodeMap.get(edge.target);
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x || 0, src.y || 0);
      ctx.lineTo(tgt.x || 0, tgt.y || 0);
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.25)';
      ctx.lineWidth = edge.weight * 1.5;
      ctx.stroke();

      // Draw relation label
      const midX = ((src.x || 0) + (tgt.x || 0)) / 2;
      const midY = ((src.y || 0) + (tgt.y || 0)) / 2;
      ctx.font = '9px Segoe UI, sans-serif';
      ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
      ctx.fillText(edge.relation, midX + 3, midY - 3);
    });

    // Draw Nodes
    layoutNodes.forEach((node) => {
      const color = TYPE_COLORS[node.type] || '#00e5ff';
      const isSelected = selectedNode?.id === node.id;

      // Glow halo if selected
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x || 0, node.y || 0, 16, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0, 229, 255, 0.2)';
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x || 0, node.y || 0, 10, 0, Math.PI * 2);
      ctx.fillStyle = '#0a0e17';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isSelected ? 3 : 2;
      ctx.stroke();

      // Center dot
      ctx.beginPath();
      ctx.arc(node.x || 0, node.y || 0, 3, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Text label
      ctx.font = '11px Segoe UI, sans-serif';
      ctx.fillStyle = isSelected ? '#ffffff' : '#cbd5e1';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, node.x || 0, (node.y || 0) + 22);
    });

    ctx.restore();
  }, [layoutNodes, filteredEdges, zoom, pan, selectedNode]);

  // Handle canvas interactions
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left - canvas.width / 2 - pan.x;
    const clickY = e.clientY - rect.top - canvas.height / 2 - pan.y;

    // Check hit test against scaled nodes
    const clicked = layoutNodes.find((node) => {
      const dx = (node.x || 0) * zoom - clickX;
      const dy = (node.y || 0) * zoom - clickY;
      return Math.sqrt(dx * dx + dy * dy) <= 15 * zoom;
    });

    setSelectedNode(clicked || null);
  };

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, sans-serif',
        position: 'relative',
        backgroundColor: 'rgba(10, 14, 23, 0.98)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          borderBottom: '1px solid rgba(0, 229, 255, 0.2)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BrainCircuitRegular style={{ fontSize: 20, color: '#00e5ff' }} />
          <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
            CyberHUD Knowledge Matrix
          </h2>
          <Badge appearance="tint" color="brand" size="small">
            Bi-Temporal
          </Badge>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {onEmergencyHalt && (
            <Button
              size="small"
              appearance="primary"
              style={{ backgroundColor: '#ef4444', color: '#fff' }}
              icon={<ShieldRegular />}
              onClick={onEmergencyHalt}
            >
              HALT GUARDIAN
            </Button>
          )}
          <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
        </div>
      </div>

      {/* Control bar: Search, Filter chips, Timeline scrubber */}
      <div
        style={{
          padding: '10px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
        }}
      >
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <Input
              placeholder="Search concepts, tools, decisions..."
              value={searchQuery}
              onChange={(_, d) => setSearchQuery(d.value)}
              contentBefore={<SearchRegular />}
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <Button
              size="small"
              appearance="subtle"
              icon={<ZoomInRegular />}
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
            />
            <Button
              size="small"
              appearance="subtle"
              icon={<ZoomOutRegular />}
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
            />
            <Button
              size="small"
              appearance="subtle"
              icon={<ArrowResetRegular />}
              onClick={() => {
                setZoom(1.0);
                setPan({ x: 0, y: 0 });
              }}
            />
          </div>
        </div>

        {/* Filter chips */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <FilterRegular style={{ fontSize: 13, color: '#94a3b8' }} />
          {['ALL', 'PROJECT', 'CONCEPT', 'TASK', 'TOOL', 'DECISION', 'FAILURE'].map((t) => (
            <span
              key={t}
              onClick={() => setSelectedType(t)}
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '12px',
                cursor: 'pointer',
                backgroundColor:
                  selectedType === t
                    ? t === 'ALL'
                      ? '#00e5ff'
                      : TYPE_COLORS[t as EntityType]
                    : 'rgba(255, 255, 255, 0.08)',
                color: selectedType === t ? '#000000' : '#cbd5e1',
                fontWeight: selectedType === t ? 600 : 400,
                transition: 'all 0.15s ease',
              }}
            >
              {t}
            </span>
          ))}
        </div>

        {/* Bi-Temporal Scrubber Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Text size={200} style={{ color: '#94a3b8', whiteSpace: 'nowrap' }}>
            Valid Time (Tv): {new Date(validTimeCutoff * 1000).toLocaleTimeString()}
          </Text>
          <Slider
            min={minTime}
            max={maxTime}
            step={60}
            value={validTimeCutoff}
            onChange={(_, d) => setValidTimeCutoff(d.value)}
            style={{ flex: 1 }}
          />
        </div>
      </div>

      {/* Main Canvas viewport */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <canvas
          ref={canvasRef}
          width={720}
          height={520}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onClick={handleCanvasClick}
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            cursor: isDragging ? 'grabbing' : 'grab',
          }}
        />

        {/* Node Inspector Drawer */}
        {selectedNode && (
          <Card
            style={{
              position: 'absolute',
              right: 16,
              top: 16,
              width: 260,
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              border: `1px solid ${TYPE_COLORS[selectedNode.type] || '#00e5ff'}`,
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
              padding: 12,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 8,
              }}
            >
              <Badge
                appearance="filled"
                style={{
                  backgroundColor: TYPE_COLORS[selectedNode.type],
                  color: '#000',
                  fontWeight: 600,
                }}
              >
                {selectedNode.type}
              </Badge>
              <Button
                size="small"
                appearance="subtle"
                icon={<DismissRegular />}
                onClick={() => setSelectedNode(null)}
              />
            </div>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
              {selectedNode.name}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>
              ID: {selectedNode.id}
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>
              Salience Score: {(selectedNode.score * 100).toFixed(1)}%
            </div>
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 6 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#38bdf8', marginBottom: 4 }}>
                Properties:
              </div>
              {Object.entries(selectedNode.properties).map(([k, v]) => (
                <div key={k} style={{ fontSize: 10, color: '#e2e8f0', marginBottom: 2 }}>
                  <span style={{ color: '#94a3b8' }}>{k}:</span> {String(v)}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};
