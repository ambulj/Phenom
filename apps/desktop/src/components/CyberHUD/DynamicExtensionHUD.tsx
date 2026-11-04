import React, { useState } from 'react';
import {
  CodeRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  ArrowSyncRegular,
  DeleteRegular,
} from '@fluentui/react-icons';
import { DynamicExtensionStatePayload } from '../../types/protocol';

interface DynamicExtensionHUDProps {
  extensionState: DynamicExtensionStatePayload | null;
  onHotReloadExtension?: (extensionId: string) => void;
  onUnloadExtension?: (extensionId: string) => void;
}

export const DynamicExtensionHUD: React.FC<DynamicExtensionHUDProps> = ({
  extensionState,
  onHotReloadExtension,
  onUnloadExtension,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);

  if (!extensionState) {
    return null;
  }

  const { loaded_extensions_count, extensions, is_active } = extensionState;
  const extList = Object.values(extensions);

  return (
    <div
      style={{
        background: 'rgba(9, 14, 28, 0.94)',
        border: '1px solid #06b6d455',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(6, 182, 212, 0.12)',
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
          borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CodeRegular style={{ color: '#06b6d4' }} />
          <span style={{ fontWeight: 'bold', letterSpacing: 1, color: '#22d3ee' }}>
            SELF-SYNTHESIZING EXTENSION FABRIC
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
          {/* Status Metric Banner */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(6, 182, 212, 0.2)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 11,
              marginBottom: 10,
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <span style={{ color: '#94a3b8' }}>Dynamic Synthesis: </span>
              <span style={{ color: is_active ? '#10b981' : '#f43f5e', fontWeight: 'bold' }}>
                {is_active ? 'ACTIVE' : 'HALTED'}
              </span>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Loaded Tools: </span>
              <span style={{ color: '#22d3ee', fontWeight: 'bold' }}>{loaded_extensions_count}</span>
            </div>
          </div>

          {/* Extension List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {extList.length === 0 ? (
              <span style={{ color: '#64748b', fontSize: 11, textAlign: 'center', padding: '8px 0' }}>
                No synthesized micro-tools loaded
              </span>
            ) : (
              extList.map((ext) => {
                const isLoaded = ext.status === 'LOADED';

                return (
                  <div
                    key={ext.extension_id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.7)',
                      border: `1px solid ${isLoaded ? '#06b6d444' : '#64748b44'}`,
                      borderRadius: 6,
                      padding: '8px 10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {ext.ast_verified ? (
                          <CheckmarkCircleRegular style={{ color: '#10b981' }} />
                        ) : (
                          <DismissCircleRegular style={{ color: '#f43f5e' }} />
                        )}
                        <span style={{ fontWeight: 'bold', color: '#e2e8f0' }}>{ext.name}</span>
                        <span style={{ color: '#f59e0b', fontSize: 10 }}>[Tier {ext.risk_tier}]</span>
                      </div>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 3,
                          background: isLoaded ? '#10b98122' : '#64748b22',
                          color: isLoaded ? '#10b981' : '#94a3b8',
                        }}
                      >
                        {ext.status}
                      </span>
                    </div>

                    <div style={{ fontSize: 10, color: '#94a3b8' }}>
                      {ext.description}
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      {isLoaded && onHotReloadExtension && (
                        <button
                          onClick={() => onHotReloadExtension(ext.extension_id)}
                          style={{
                            background: '#06b6d422',
                            border: '1px solid #06b6d4',
                            borderRadius: 3,
                            color: '#22d3ee',
                            fontSize: 10,
                            padding: '3px 8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <ArrowSyncRegular /> RELOAD
                        </button>
                      )}
                      {isLoaded && onUnloadExtension && (
                        <button
                          onClick={() => onUnloadExtension(ext.extension_id)}
                          style={{
                            background: '#f43f5e22',
                            border: '1px solid #f43f5e',
                            borderRadius: 3,
                            color: '#f43f5e',
                            fontSize: 10,
                            padding: '3px 8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <DeleteRegular /> UNLOAD
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
};
