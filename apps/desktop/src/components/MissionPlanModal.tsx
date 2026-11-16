import React, { useState } from 'react';
import {
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogActions,
  DialogContent,
  Button,
  Badge
} from '@fluentui/react-components';
import {
  ShieldRegular,
  PlayRegular,
  DismissRegular,
  WarningRegular,
  ChevronDownRegular,
  ChevronUpRegular,
  CodeRegular,
  SearchRegular,
  DesktopRegular,
  WrenchRegular
} from '@fluentui/react-icons';

export interface DAGNodePayload {
  node_id: string;
  title: string;
  tool_name: string;
  arguments: Record<string, any>;
  tier: number;
  depends_on: string[];
  timeout_seconds?: number;
  status?: string;
}

export interface MissionDAGPayload {
  mission_id: string;
  goal: string;
  nodes: DAGNodePayload[];
  created_at?: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_confirmation: boolean;
  is_approved?: boolean;
}

interface MissionPlanModalProps {
  mission: MissionDAGPayload | null;
  onAuthorize: (missionId: string) => void;
  onCancel: () => void;
  onEdit?: (goal: string) => void;
}

export const MissionPlanModal: React.FC<MissionPlanModalProps> = ({
  mission,
  onAuthorize,
  onCancel,
  onEdit
}) => {
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  if (!mission) return null;

  const toggleExpand = (nodeId: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId]
    }));
  };

  const getTierBadge = (tier: number) => {
    switch (tier) {
      case 0:
        return (
          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
            Tier 0 • Read-Only
          </span>
        );
      case 1:
        return (
          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-blue-950/80 text-blue-400 border border-blue-800/60">
            Tier 1 • Reversible
          </span>
        );
      case 2:
        return (
          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-950/80 text-amber-400 border border-amber-800/60">
            Tier 2 • External / Destructive
          </span>
        );
      case 3:
      default:
        return (
          <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-950/80 text-rose-400 border border-rose-800/60">
            Tier 3 • Physical Auth Required
          </span>
        );
    }
  };

  const getToolIcon = (toolName: string) => {
    if (toolName.includes('code') || toolName.includes('git') || toolName.includes('test')) {
      return <CodeRegular className="text-cyan-400 mr-1.5" />;
    }
    if (toolName.includes('search') || toolName.includes('paper') || toolName.includes('summarize')) {
      return <SearchRegular className="text-violet-400 mr-1.5" />;
    }
    if (toolName.includes('desktop') || toolName.includes('app') || toolName.includes('browser')) {
      return <DesktopRegular className="text-emerald-400 mr-1.5" />;
    }
    return <WrenchRegular className="text-gray-400 mr-1.5" />;
  };

  const hasHighRisk = mission.nodes.some((n) => n.tier >= 2);

  return (
    <Dialog open={true} onOpenChange={(_, data) => !data.open && onCancel()}>
      <DialogSurface
        className="max-w-2xl bg-slate-950/95 border border-cyan-500/30 text-white rounded-xl shadow-2xl backdrop-blur-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mission-plan-title"
      >
        <DialogTitle id="mission-plan-title" className="border-b border-slate-800/80 pb-3 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldRegular className="text-cyan-400 text-xl" />
            <span className="font-bold text-lg tracking-wide text-cyan-300">
              Autonomous Mission Plan
            </span>
          </div>
          <Badge
            appearance="filled"
            color={
              mission.risk_level === 'critical'
                ? 'danger'
                : mission.risk_level === 'high'
                ? 'severe'
                : mission.risk_level === 'medium'
                ? 'important'
                : 'success'
            }
          >
            {mission.risk_level.toUpperCase()} RISK
          </Badge>
        </DialogTitle>

        <DialogBody className="space-y-4 pt-3">
          <DialogContent className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
            {/* Goal card */}
            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Mission Goal
              </span>
              <p className="mt-1 text-sm font-medium text-slate-100 leading-relaxed">
                {mission.goal}
              </p>
            </div>

            {/* Warning banner if high risk steps present */}
            {hasHighRisk && (
              <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-600/50 flex items-start space-x-2 text-amber-200 text-xs">
                <WarningRegular className="text-amber-400 text-base flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Confirmation Boundary Notice:</span> This mission includes Tier 2 or Tier 3 actions. While upfront approval authorizes execution of safe steps, secondary confirmation will be requested before any destructive step runs.
                </div>
              </div>
            )}

            {/* Step list */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Execution DAG ({mission.nodes.length} Steps)
                </span>
                <span className="text-xs text-slate-500">Kahn's Topological Order</span>
              </div>

              <div className="space-y-2">
                {mission.nodes.map((node, index) => {
                  const isExpanded = !!expandedNodes[node.node_id];
                  return (
                    <div
                      key={node.node_id}
                      className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-2.5">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 text-xs font-bold flex items-center justify-center">
                            {index + 1}
                          </span>
                          <div>
                            <div className="text-sm font-semibold text-slate-200 flex items-center">
                              {getToolIcon(node.tool_name)}
                              {node.title}
                            </div>
                            <div className="text-xs text-slate-400 mt-0.5 flex items-center space-x-2">
                              <code>{node.tool_name}</code>
                              {node.depends_on.length > 0 && (
                                <span>• Depends on: {node.depends_on.join(', ')}</span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 flex-shrink-0">
                          {getTierBadge(node.tier)}
                          <button
                            onClick={() => toggleExpand(node.node_id)}
                            className="text-slate-400 hover:text-slate-200 p-1"
                            title="Toggle argument details"
                          >
                            {isExpanded ? <ChevronUpRegular /> : <ChevronDownRegular />}
                          </button>
                        </div>
                      </div>

                      {/* Expandable arguments details */}
                      {isExpanded && (
                        <div className="mt-2.5 pt-2 border-t border-slate-800/80">
                          <span className="text-xs font-semibold text-slate-500 block mb-1">
                            Arguments:
                          </span>
                          <pre className="text-xs bg-slate-950/80 p-2 rounded text-slate-300 overflow-x-auto border border-slate-900 font-mono">
                            {JSON.stringify(node.arguments, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </DialogContent>

          <DialogActions className="border-t border-slate-800/80 pt-3 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Button
                appearance="subtle"
                icon={<DismissRegular />}
                onClick={onCancel}
                className="text-slate-400 hover:text-white"
              >
                Cancel
              </Button>
              {onEdit && (
                <Button
                  appearance="subtle"
                  onClick={() => onEdit(mission.goal)}
                  className="text-slate-400 hover:text-cyan-400"
                >
                  Edit Goal
                </Button>
              )}
            </div>

            <Button
              appearance="primary"
              icon={<PlayRegular />}
              onClick={() => onAuthorize(mission.mission_id)}
              className="bg-cyan-600 hover:bg-cyan-500 text-white font-semibold shadow-lg shadow-cyan-900/40"
            >
              Authorize Mission
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};
