import React, { useState } from 'react';
import {
  AppsRegular,
  CursorHoverRegular,
  PlayRegular,
} from '@fluentui/react-icons';
import { UIElementNodePayload, UIAWorkflowResultPayload } from '../../types/protocol';

interface DeepUIAutomationHUDProps {
  rootNode: UIElementNodePayload | null;
  lastResult?: UIAWorkflowResultPayload | null;
  onExecuteSampleWorkflow?: () => void;
  onInvokeElement?: (elementId: string) => void;
}

export const DeepUIAutomationHUD: React.FC<DeepUIAutomationHUDProps> = ({
  rootNode,
  lastResult,
  onExecuteSampleWorkflow,
  onInvokeElement,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!rootNode) {
    return null;
  }

  return (
    <div
      style={{
        background: 'rgba(9, 14, 28, 0.94)',
        border: '1px solid #a855f755',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(168, 85, 247, 0.12)',
        maxWidth: 440,
        width: '100%',
        marginBottom: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AppsRegular style={{ color: '#a855f7' }} />
          <span style={{ fontWeight: 'bold', letterSpacing: 1, color: '#c084fc' }}>
            DEEP UIAUTOMATION & SELF-HEALING
          </span>
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          {isMinimized ? '[+ EXPAND]' : '[- MINIMIZE]'}
        </button>
      </div>

      {!isMinimized && (
        <>
          {/* Target Window & Inspection Banner */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 11,
              marginBottom: 10,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ color: '#94a3b8' }}>Target Window:</span>
              <span style={{ color: '#c084fc', fontWeight: 'bold' }}>{rootNode.name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Mode:</span>
              <span style={{ color: '#10b981' }}>Non-Intrusive (Focus Preserved)</span>
            </div>
          </div>

          {/* Accessibility Tree Child Elements */}
          <div style={{ marginBottom: 12 }}>
            <span style={{ color: '#94a3b8', fontSize: 11, display: 'block', marginBottom: 6 }}>
              ACCESSIBLE ELEMENTS ({rootNode.children.length})
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {rootNode.children.map((child) => (
                <div
                  key={child.element_id}
                  style={{
                    background: 'rgba(15, 23, 42, 0.5)',
                    border: '1px solid rgba(168, 85, 247, 0.15)',
                    borderRadius: 4,
                    padding: '6px 8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <CursorHoverRegular style={{ color: '#38bdf8' }} />
                    <span style={{ color: '#e2e8f0' }}>{child.name}</span>
                    <span style={{ color: '#64748b', fontSize: 10 }}>[{child.control_type}]</span>
                  </div>
                  {onInvokeElement && (
                    <button
                      onClick={() => onInvokeElement(child.element_id)}
                      style={{
                        background: '#a855f722',
                        border: '1px solid #a855f7',
                        borderRadius: 3,
                        color: '#c084fc',
                        fontSize: 10,
                        padding: '2px 6px',
                        cursor: 'pointer',
                      }}
                    >
                      INVOKE
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Workflow Execution & Healing Summary */}
          {lastResult && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${lastResult.is_success ? '#10b98144' : '#f43f5e44'}`,
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: 11,
                marginBottom: 10,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 'bold', color: lastResult.is_success ? '#10b981' : '#f43f5e' }}>
                  Workflow: {lastResult.workflow_id}
                </span>
                <span style={{ color: '#94a3b8', fontSize: 10 }}>{lastResult.elapsed_ms.toFixed(1)} ms</span>
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#cbd5e1' }}>
                <span>Steps: {lastResult.successful_steps}/{lastResult.total_steps}</span>
                {lastResult.healed_steps > 0 && (
                  <span style={{ color: '#f59e0b' }}>Healed Steps: {lastResult.healed_steps}</span>
                )}
              </div>
            </div>
          )}

          {/* Quick Action */}
          {onExecuteSampleWorkflow && (
            <button
              onClick={onExecuteSampleWorkflow}
              style={{
                width: '100%',
                background: '#a855f722',
                border: '1px solid #a855f7',
                borderRadius: 4,
                color: '#c084fc',
                fontSize: 11,
                padding: '6px 10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <PlayRegular /> RUN SELF-HEALING WORKFLOW
            </button>
          )}
        </>
      )}
    </div>
  );
};
