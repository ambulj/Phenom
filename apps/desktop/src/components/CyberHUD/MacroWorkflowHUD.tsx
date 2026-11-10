import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  PlayRegular,
  RecordRegular,
  ShieldCheckmarkRegular,
  CheckmarkCircleRegular,
  WrenchRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface WorkflowRecipeHUDItem {
  recipe_id: string;
  name: string;
  description: string;
  steps_count: number;
  safety_tier: number;
  parameters: string[];
}

export interface MacroWorkflowHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const MacroWorkflowHUD: React.FC<MacroWorkflowHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [recipes, setRecipes] = useState<WorkflowRecipeHUDItem[]>([
    {
      recipe_id: 'generate_weekly_standup_report',
      name: 'Generate Weekly Standup Report',
      description: 'Collects git logs, formats markdown notes in Obsidian, and opens briefing window.',
      steps_count: 5,
      safety_tier: 1,
      parameters: ['branch_name', 'output_folder']
    },
    {
      recipe_id: 'backup_local_databases',
      name: 'Backup SQLite Databases',
      description: 'Halts background sync, creates atomic snapshot in backup directory, and resumes daemon.',
      steps_count: 4,
      safety_tier: 2,
      parameters: ['target_drive']
    }
  ]);

  const [selectedRecipeId, setSelectedRecipeId] = useState<string>('generate_weekly_standup_report');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isDryRun, setIsDryRun] = useState<boolean>(true);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [paramValues, setParamValues] = useState<Record<string, string>>({
    branch_name: 'main',
    output_folder: 'reports/weekly'
  });

  const [activeRecipeYaml, setActiveRecipeYaml] = useState<string>(
    'recipe_id: generate_weekly_standup_report\n' +
    'name: Generate Weekly Standup Report\n' +
    'safety_tier: 1\n' +
    'parameters:\n' +
    '  branch_name: main\n' +
    '  output_folder: reports/weekly\n' +
    'steps:\n' +
    '  - step_id: 1\n' +
    '    action: bash_exec\n' +
    '    command: git log -n 10 --oneline ${branch_name}\n' +
    '  - step_id: 2\n' +
    '    action: click\n' +
    '    target_type: ocr_text\n' +
    '    target_value: Obsidian Notes\n' +
    '    heal_strategy: ocr_fallback\n' +
    '  - step_id: 3\n' +
    '    action: type\n' +
    '    text_input: Weekly Standup for ${branch_name}\n' +
    '  - step_id: 4\n' +
    '    action: hotkey\n' +
    '    key_sequence: ctrl+s\n' +
    '  - step_id: 5\n' +
    '    action: assert_screen\n' +
    '    target_value: Saved'
  );

  const [executionSteps, setExecutionSteps] = useState<Array<{
    id: number;
    action: string;
    target: string;
    status: 'pending' | 'running' | 'success' | 'healed';
    healMsg?: string;
  }>>([
    { id: 1, action: 'bash_exec', target: 'git log -n 10 --oneline main', status: 'success' },
    { id: 2, action: 'click', target: 'Obsidian Notes', status: 'healed', healMsg: 'Relocated from (210, 450) to (215, 480) via OCR matching' },
    { id: 3, action: 'type', target: 'Weekly Standup for main', status: 'success' },
    { id: 4, action: 'hotkey', target: 'ctrl+s', status: 'success' },
    { id: 5, action: 'assert_screen', target: 'Saved', status: 'success' }
  ]);

  useEffect(() => {
    if (externalEvent?.type === 'workflow.list' && Array.isArray(externalEvent.payload)) {
      setRecipes(externalEvent.payload);
    } else if (externalEvent?.type === 'workflow.step_update' && externalEvent.payload) {
      const { step_id, status, heal_event } = externalEvent.payload;
      setExecutionSteps((prev) =>
        prev.map((s) => (s.id === step_id ? { ...s, status, healMsg: heal_event?.message } : s))
      );
    }
  }, [externalEvent]);

  const handleSimulateExecution = () => {
    setIsExecuting(true);
    setActiveStepIndex(0);

    if (sendMessage) {
      sendMessage({
        type: 'workflow.execute',
        payload: {
          recipe_id: selectedRecipeId,
          dry_run: isDryRun,
          parameters: paramValues
        }
      });
    }

    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      setActiveStepIndex(step);
      if (step >= executionSteps.length) {
        clearInterval(interval);
        setIsExecuting(false);
      }
    }, 600);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(8, 12, 22, 0.95)',
        border: '1px solid rgba(0, 243, 255, 0.35)',
        borderRadius: 14,
        boxShadow: '0 8px 36px rgba(0, 0, 0, 0.75), 0 0 20px rgba(0, 243, 255, 0.15)',
        backdropFilter: 'blur(28px)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        overflow: 'hidden'
      }}
    >
      {/* Top Header */}
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
          <SparkleRegular style={{ fontSize: 20, color: '#00f3ff' }} />
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '0.04em', color: '#f8fafc' }}>
            DESKTOP MACRO SYNTHESIS & WORKFLOW ENGINE
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(0, 243, 255, 0.15)',
              color: '#00f3ff',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              fontWeight: 600
            }}
          >
            AUT-02
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              padding: '2px 8px',
              borderRadius: 4,
              border: '1px solid rgba(16, 185, 129, 0.25)'
            }}
          >
            <ShieldCheckmarkRegular style={{ fontSize: 13 }} />
            <span>Rule 8 Anti-Checkout Shield Active</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => setIsRecording((prev) => !prev)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: isRecording ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${isRecording ? '#ef4444' : 'rgba(255, 255, 255, 0.15)'}`,
              color: isRecording ? '#ef4444' : '#94a3b8',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
              fontWeight: 500
            }}
          >
            <RecordRegular style={{ fontSize: 14 }} />
            <span>{isRecording ? 'Recording...' : 'Record Macro'}</span>
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

      {/* Main Body Columns */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left Column: Recipe Catalog */}
        <div
          style={{
            width: 250,
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <div style={{ padding: '10px 14px', fontSize: 11, fontWeight: 600, color: '#64748b', letterSpacing: '0.05em' }}>
            SYNTHESIZED RECIPES ({recipes.length})
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px 8px 8px' }}>
            {recipes.map((r) => (
              <div
                key={r.recipe_id}
                onClick={() => setSelectedRecipeId(r.recipe_id)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 8,
                  marginBottom: 6,
                  cursor: 'pointer',
                  backgroundColor: selectedRecipeId === r.recipe_id ? 'rgba(0, 243, 255, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${selectedRecipeId === r.recipe_id ? 'rgba(0, 243, 255, 0.4)' : 'transparent'}`
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: selectedRecipeId === r.recipe_id ? '#00f3ff' : '#f1f5f9' }}>
                  {r.name}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, lineHeight: 1.3 }}>
                  {r.description}
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  <span style={{ fontSize: 10, color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', padding: '1px 6px', borderRadius: 4 }}>
                    {r.steps_count} steps
                  </span>
                  <span style={{ fontSize: 10, color: '#fbbf24', backgroundColor: 'rgba(251, 191, 36, 0.1)', padding: '1px 6px', borderRadius: 4 }}>
                    Tier {r.safety_tier}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center Column: YAML Recipe Viewer & Parameter Bindings */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ padding: '10px 16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>RECIPE YAML SPECIFICATION</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={isDryRun}
                  onChange={(e) => setIsDryRun(e.target.checked)}
                />
                Dry Run (Safe Simulation)
              </label>
              <button
                onClick={handleSimulateExecution}
                disabled={isExecuting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#ffffff',
                  borderRadius: 6,
                  padding: '5px 12px',
                  fontSize: 12,
                  cursor: isExecuting ? 'not-allowed' : 'pointer',
                  fontWeight: 600
                }}
              >
                <PlayRegular style={{ fontSize: 14 }} />
                <span>{isExecuting ? 'Running...' : 'Execute Recipe'}</span>
              </button>
            </div>
          </div>
          <div style={{ padding: '8px 16px', backgroundColor: 'rgba(0, 0, 0, 0.3)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#64748b' }}>Parameter Bindings:</span>
            {Object.keys(paramValues).map((k) => (
              <div key={k} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: '#38bdf8' }}>{k}:</span>
                <input
                  type="text"
                  value={paramValues[k]}
                  onChange={(e) => setParamValues((prev) => ({ ...prev, [k]: e.target.value }))}
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: 4,
                    color: '#e2e8f0',
                    fontSize: 11,
                    padding: '2px 6px',
                    width: 100
                  }}
                />
              </div>
            ))}
          </div>
          <div style={{ flex: 1, padding: 14, overflowY: 'auto' }}>
            <textarea
              value={activeRecipeYaml}
              onChange={(e) => setActiveRecipeYaml(e.target.value)}
              style={{
                width: '100%',
                height: '100%',
                margin: 0,
                fontFamily: "'Consolas', monospace",
                fontSize: 12,
                color: '#38bdf8',
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
                padding: 12,
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.05)',
                lineHeight: 1.5,
                resize: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
        </div>

        {/* Right Column: Execution Stepper & Self-Healing Log */}
        <div style={{ width: 300, display: 'flex', flexDirection: 'column', backgroundColor: 'rgba(0, 0, 0, 0.25)' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
            EXECUTION STEPPER & SELF-HEALING
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
            {executionSteps.map((s, idx) => (
              <div
                key={s.id}
                style={{
                  padding: 10,
                  borderRadius: 8,
                  marginBottom: 8,
                  backgroundColor: idx === activeStepIndex ? 'rgba(0, 243, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${s.status === 'healed' ? 'rgba(234, 179, 8, 0.4)' : idx === activeStepIndex ? '#00f3ff' : 'rgba(255, 255, 255, 0.06)'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9' }}>
                    Step {s.id}: {s.action.toUpperCase()}
                  </span>
                  {s.status === 'healed' ? (
                    <span style={{ fontSize: 10, color: '#eab308', display: 'flex', alignItems: 'center', gap: 3 }}>
                      <WrenchRegular style={{ fontSize: 12 }} />
                      Healed
                    </span>
                  ) : s.status === 'success' ? (
                    <CheckmarkCircleRegular style={{ fontSize: 14, color: '#10b981' }} />
                  ) : (
                    <span style={{ fontSize: 10, color: '#64748b' }}>Pending</span>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, fontFamily: 'monospace' }}>
                  {s.target}
                </div>
                {s.healMsg && (
                  <div style={{ fontSize: 10, color: '#fbbf24', marginTop: 4, backgroundColor: 'rgba(234, 179, 8, 0.1)', padding: '3px 6px', borderRadius: 4 }}>
                    ⚡ {s.healMsg}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
