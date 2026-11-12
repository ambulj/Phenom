import React, { useState } from 'react';
import {
  DismissRegular,
  ShieldCheckmarkRegular,
  FlashRegular,
  CheckmarkCircleRegular,
  LockClosedRegular,
  WarningRegular,
  FilterRegular,
  SearchRegular,
} from '@fluentui/react-icons';

interface ToolPolicyUI {
  tool_name: string;
  tier: number;
  auto_executable: boolean;
  requires_confirmation: boolean;
  is_blocked: boolean;
  category: string;
  description: string;
}

interface SafetyTierMatrixHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SafetyTierMatrixHUD: React.FC<SafetyTierMatrixHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [filterTier, setFilterTier] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [autoExecuteTier1, setAutoExecuteTier1] = useState<boolean>(true);

  const initialTools: ToolPolicyUI[] = [
    { tool_name: 'open_app', tier: 0, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'DESKTOP', description: 'Launch installed Windows applications directly' },
    { tool_name: 'close_app', tier: 1, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'DESKTOP', description: 'Gracefully terminate or close running application' },
    { tool_name: 'recycle_delete', tier: 1, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'FILESYSTEM', description: 'Safely move file or folder to Windows Recycle Bin' },
    { tool_name: 'create_file', tier: 1, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'FILESYSTEM', description: 'Create a new local file with specified content' },
    { tool_name: 'move_file', tier: 1, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'FILESYSTEM', description: 'Relocate local file or directory' },
    { tool_name: 'read_file', tier: 0, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'FILESYSTEM', description: 'Read local file text content' },
    { tool_name: 'list_directory', tier: 0, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'FILESYSTEM', description: 'Inspect directory entries and subfolders' },
    { tool_name: 'set_volume', tier: 0, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'DESKTOP', description: 'Adjust master or application audio volume' },
    { tool_name: 'tile_windows', tier: 0, auto_executable: true, requires_confirmation: false, is_blocked: false, category: 'DESKTOP', description: 'Arrange active windows on desktop monitors' },
    { tool_name: 'send_email', tier: 2, auto_executable: false, requires_confirmation: true, is_blocked: false, category: 'COMMUNICATION', description: 'High-risk: Outbound email dispatch' },
    { tool_name: 'telegram_broadcast', tier: 2, auto_executable: false, requires_confirmation: true, is_blocked: false, category: 'COMMUNICATION', description: 'High-risk: Broadcast remote Telegram notification' },
    { tool_name: 'modify_registry_key', tier: 2, auto_executable: false, requires_confirmation: true, is_blocked: false, category: 'SECURITY', description: 'High-risk: Windows registry hive alteration' },
    { tool_name: 'execute_checkout_payment', tier: 3, auto_executable: false, requires_confirmation: false, is_blocked: true, category: 'FINANCE', description: 'Blocked: Rule 8 anti-checkout violation' },
  ];

  const [toolsList, setToolsList] = useState<ToolPolicyUI[]>(initialTools);

  const filteredTools = toolsList.filter((tool) => {
    if (filterTier !== 'ALL' && tool.tier.toString() !== filterTier) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return tool.tool_name.toLowerCase().includes(q) || tool.category.toLowerCase().includes(q) || tool.description.toLowerCase().includes(q);
    }
    return true;
  });

  const tierCounts = {
    0: toolsList.filter((t) => t.tier === 0).length,
    1: toolsList.filter((t) => t.tier === 1).length,
    2: toolsList.filter((t) => t.tier === 2).length,
    3: toolsList.filter((t) => t.tier === 3).length,
  };

  const handleToggleTier1Auto = () => {
    const nextVal = !autoExecuteTier1;
    setAutoExecuteTier1(nextVal);
    setToolsList((prev) =>
      prev.map((t) => {
        if (t.tier === 1) {
          return {
            ...t,
            auto_executable: nextVal,
            requires_confirmation: !nextVal,
          };
        }
        return t;
      })
    );
  };

  const handleReclassifyQuick = (toolName: string, targetTier: number) => {
    setToolsList((prev) =>
      prev.map((t) => {
        if (t.tool_name === toolName) {
          return {
            ...t,
            tier: targetTier,
            auto_executable: targetTier === 0 || (targetTier === 1 && autoExecuteTier1),
            requires_confirmation: targetTier === 2 || (targetTier === 1 && !autoExecuteTier1),
            is_blocked: targetTier === 3,
          };
        }
        return t;
      })
    );
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(3, 7, 18, 0.9)',
        backdropFilter: 'blur(16px)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        fontFamily: "'Segoe UI Variable Text', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(14, 165, 233, 0.08) 0%, rgba(2, 6, 23, 0.7) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ShieldCheckmarkRegular style={{ fontSize: '24px', color: '#38bdf8' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, letterSpacing: '0.5px' }}>
              Safety Tier Matrix & Pragmatic Auto-Execution
            </h2>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Milestone 29 Phase 2 • Zero-Prompt Execution for Tier 0 & 1 • High-Risk Boundary Gating
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleToggleTier1Auto}
            style={{
              background: autoExecuteTier1 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              border: `1px solid ${autoExecuteTier1 ? '#22c55e' : '#ef4444'}`,
              borderRadius: '8px',
              padding: '6px 14px',
              color: autoExecuteTier1 ? '#4ade80' : '#f87171',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            <FlashRegular />
            Tier 1 Auto-Run: {autoExecuteTier1 ? 'ENABLED (Zero-Prompt)' : 'DISABLED (Prompting)'}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: 'none',
                borderRadius: '8px',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f0f6fc',
                cursor: 'pointer',
              }}
            >
              <DismissRegular style={{ fontSize: '18px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Tier Stats Summary */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div
            onClick={() => setFilterTier('0')}
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${filterTier === '0' ? '#38bdf8' : 'rgba(56, 189, 248, 0.2)'}`,
              borderRadius: '12px',
              padding: '16px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', marginBottom: '8px' }}>
              <CheckmarkCircleRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>TIER 0 • READ-ONLY</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{tierCounts[0]}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Instant silent auto-run (e.g. open_app)</div>
          </div>

          <div
            onClick={() => setFilterTier('1')}
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${filterTier === '1' ? '#4ade80' : 'rgba(34, 197, 94, 0.2)'}`,
              borderRadius: '12px',
              padding: '16px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#4ade80', marginBottom: '8px' }}>
              <FlashRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>TIER 1 • REVERSIBLE FAST-PATH</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{tierCounts[1]}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Zero-prompt auto-run (recycle_delete, close_app)</div>
          </div>

          <div
            onClick={() => setFilterTier('2')}
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${filterTier === '2' ? '#fbbf24' : 'rgba(245, 158, 11, 0.2)'}`,
              borderRadius: '12px',
              padding: '16px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', marginBottom: '8px' }}>
              <WarningRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>TIER 2 • HIGH-RISK PROMPTED</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{tierCounts[2]}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Outbound communications & registry gates</div>
          </div>

          <div
            onClick={() => setFilterTier('3')}
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${filterTier === '3' ? '#f87171' : 'rgba(239, 68, 68, 0.2)'}`,
              borderRadius: '12px',
              padding: '16px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', marginBottom: '8px' }}>
              <LockClosedRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>TIER 3 • BLOCKED</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{tierCounts[3]}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Rule 8 payments & dangerous commands</div>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, maxWidth: '400px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '8px 12px',
                width: '100%',
              }}
            >
              <SearchRegular style={{ color: '#94a3b8' }} />
              <input
                type="text"
                placeholder="Search tools, categories, or descriptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#f8fafc',
                  fontSize: '13px',
                  width: '100%',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <FilterRegular /> Tier:
            </span>
            {['ALL', '0', '1', '2', '3'].map((tierVal) => (
              <button
                key={tierVal}
                onClick={() => setFilterTier(tierVal)}
                style={{
                  background: filterTier === tierVal ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1px solid ${filterTier === tierVal ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '6px',
                  padding: '4px 10px',
                  color: filterTier === tierVal ? '#38bdf8' : '#94a3b8',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                {tierVal === 'ALL' ? 'All Tiers' : `Tier ${tierVal}`}
              </button>
            ))}
          </div>
        </div>

        {/* Tools Table */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: 'rgba(2, 6, 23, 0.7)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8' }}>
                <th style={{ padding: '12px 16px' }}>TOOL NAME</th>
                <th style={{ padding: '12px 16px' }}>TIER</th>
                <th style={{ padding: '12px 16px' }}>CATEGORY</th>
                <th style={{ padding: '12px 16px' }}>EXECUTION POLICY</th>
                <th style={{ padding: '12px 16px' }}>DESCRIPTION</th>
                <th style={{ padding: '12px 16px' }}>QUICK OVERRIDE</th>
              </tr>
            </thead>
            <tbody>
              {filteredTools.map((tool) => {
                const tierColor =
                  tool.tier === 0 ? '#38bdf8' : tool.tier === 1 ? '#4ade80' : tool.tier === 2 ? '#fbbf24' : '#f87171';
                return (
                  <tr
                    key={tool.tool_name}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      background: 'rgba(15, 23, 42, 0.2)',
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc', fontFamily: 'monospace' }}>
                      {tool.tool_name}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          background: `${tierColor}22`,
                          border: `1px solid ${tierColor}55`,
                          color: tierColor,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          fontSize: '11px',
                        }}
                      >
                        Tier {tool.tier}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '12px' }}>{tool.category}</td>
                    <td style={{ padding: '12px 16px' }}>
                      {tool.auto_executable ? (
                        <span style={{ color: '#4ade80', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FlashRegular style={{ fontSize: '14px' }} /> Auto-Run (Zero-Prompt)
                        </span>
                      ) : tool.requires_confirmation ? (
                        <span style={{ color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <WarningRegular style={{ fontSize: '14px' }} /> User Confirmation Required
                        </span>
                      ) : (
                        <span style={{ color: '#f87171', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <LockClosedRegular style={{ fontSize: '14px' }} /> Blocked By Safety Rule
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#cbd5e1', fontSize: '12px', maxWidth: '300px' }}>
                      {tool.description}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {tool.tier !== 3 && (
                        <div style={{ display: 'flex', gap: '6px' }}>
                          {[0, 1, 2].map((tVal) => (
                            <button
                              key={tVal}
                              onClick={() => handleReclassifyQuick(tool.tool_name, tVal)}
                              style={{
                                background: tool.tier === tVal ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                                border: '1px solid rgba(255, 255, 255, 0.1)',
                                borderRadius: '4px',
                                padding: '2px 6px',
                                fontSize: '10px',
                                color: tool.tier === tVal ? '#38bdf8' : '#94a3b8',
                                cursor: 'pointer',
                              }}
                            >
                              T{tVal}
                            </button>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default SafetyTierMatrixHUD;
