import React, { useState } from 'react';
import {
  ShieldCheckmarkRegular,
  ShieldDismissRegular,
  LockClosedRegular,
  LockOpenRegular,
  KeyRegular,
} from '@fluentui/react-icons';
import { BiometricEnclaveStatePayload } from '../../types/protocol';

interface BiometricEnclaveHUDProps {
  enclaveState: BiometricEnclaveStatePayload | null;
  onUnlockPartition?: (partitionType: 'PERSONAL' | 'PROFESSIONAL', token: string) => void;
  onLockPartition?: (partitionType: 'PERSONAL' | 'PROFESSIONAL') => void;
}

export const BiometricEnclaveHUD: React.FC<BiometricEnclaveHUDProps> = ({
  enclaveState,
  onUnlockPartition,
  onLockPartition,
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [selectedPin] = useState('sample-pin');

  if (!enclaveState) {
    return null;
  }

  const { hardware_tpm_present, partitions, active_leases } = enclaveState;

  return (
    <div
      style={{
        background: 'rgba(9, 14, 28, 0.94)',
        border: '1px solid #10b98155',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: 'monospace',
        fontSize: 12,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(16, 185, 129, 0.12)',
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
          borderBottom: '1px solid rgba(16, 185, 129, 0.2)',
          paddingBottom: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {hardware_tpm_present ? (
            <ShieldCheckmarkRegular style={{ color: '#10b981' }} />
          ) : (
            <ShieldDismissRegular style={{ color: '#f59e0b' }} />
          )}
          <span style={{ fontWeight: 'bold', letterSpacing: 1, color: '#10b981' }}>
            BIOMETRIC ENCLAVE & TPM 2.0
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
          {/* Hardware Security Status */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(16, 185, 129, 0.15)',
              borderRadius: 6,
              padding: '6px 10px',
              fontSize: 11,
              marginBottom: 10,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ color: '#94a3b8' }}>TPM 2.0 Module:</span>
            <span style={{ color: hardware_tpm_present ? '#10b981' : '#f59e0b', fontWeight: 'bold' }}>
              {hardware_tpm_present ? 'ACTIVE (Hardware Sealed)' : 'SOFTWARE EMULATION'}
            </span>
          </div>

          {/* Workspace Partitions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
            {Object.entries(partitions).map(([key, part]) => {
              const isUnlocked = part.status === 'UNLOCKED';
              const isPersonal = part.partition_type === 'PERSONAL';

              return (
                <div
                  key={key}
                  style={{
                    background: 'rgba(15, 23, 42, 0.7)',
                    border: `1px solid ${isUnlocked ? '#10b98144' : '#64748b44'}`,
                    borderRadius: 6,
                    padding: '8px 10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {isUnlocked ? (
                        <LockOpenRegular style={{ color: '#10b981' }} />
                      ) : (
                        <LockClosedRegular style={{ color: '#94a3b8' }} />
                      )}
                      <span style={{ fontWeight: 'bold', color: isPersonal ? '#38bdf8' : '#a855f7' }}>
                        {part.name}
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '2px 6px',
                        borderRadius: 4,
                        background: isUnlocked ? '#10b98122' : '#64748b22',
                        color: isUnlocked ? '#10b981' : '#94a3b8',
                      }}
                    >
                      {part.status}
                    </span>
                  </div>

                  <div style={{ fontSize: 10, color: '#94a3b8' }}>
                    Cipher: {part.encryption_cipher}
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    {isUnlocked ? (
                      <button
                        onClick={() => onLockPartition && onLockPartition(part.partition_type as any)}
                        style={{
                          background: '#f43f5e22',
                          border: '1px solid #f43f5e',
                          borderRadius: 4,
                          color: '#f43f5e',
                          fontSize: 10,
                          padding: '4px 8px',
                          cursor: 'pointer',
                        }}
                      >
                        LOCK & ZERO KEY
                      </button>
                    ) : (
                      <button
                        onClick={() =>
                          onUnlockPartition &&
                          onUnlockPartition(part.partition_type as any, selectedPin || 'sample-pin')
                        }
                        style={{
                          background: '#10b98122',
                          border: '1px solid #10b981',
                          borderRadius: 4,
                          color: '#10b981',
                          fontSize: 10,
                          padding: '4px 8px',
                          cursor: 'pointer',
                        }}
                      >
                        UNLOCK WITH HELLO
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Ephemeral Credential Leases */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.4)',
              border: '1px solid rgba(16, 185, 129, 0.15)',
              borderRadius: 6,
              padding: '8px 10px',
              fontSize: 11,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <KeyRegular style={{ color: '#10b981' }} />
              <span style={{ fontWeight: 'bold', color: '#cbd5e1' }}>
                Active Ephemeral Leases ({active_leases.length})
              </span>
            </div>
            {active_leases.length === 0 ? (
              <span style={{ color: '#64748b', fontSize: 10 }}>No credentials leased (RAM is clean)</span>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {active_leases.map((lease) => (
                  <div
                    key={lease.lease_id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: 10,
                      color: '#94a3b8',
                    }}
                  >
                    <span>{lease.target_service}</span>
                    <span style={{ color: '#f59e0b' }}>
                      Expires: {new Date(lease.expires_at * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
