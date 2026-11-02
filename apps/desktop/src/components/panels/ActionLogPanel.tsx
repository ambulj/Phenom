import React, { useEffect, useState } from 'react';
import { Button, Badge } from '@fluentui/react-components';
import { DismissRegular, ArrowSyncRegular } from '@fluentui/react-icons';
import { LogEntryPayload } from '../../types/protocol';
import { apiFetch } from '../../utils/api';

interface ActionLogPanelProps {
  onClose: () => void;
}

export const ActionLogPanel: React.FC<ActionLogPanelProps> = ({ onClose }) => {
  const [logs, setLogs] = useState<LogEntryPayload[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const res = await apiFetch('/api/logs');
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (e) {
      console.error('Failed to fetch logs:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 16,
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', margin: 0 }}>Security Action Log</h2>
          <Button appearance="subtle" icon={<ArrowSyncRegular />} onClick={fetchLogs} disabled={isLoading} size="small" />
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {logs.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 14 }}>No actions logged yet.</div>
        ) : (
          logs.map((log) => (
            <div
              key={log.log_id}
              style={{
                background: 'rgba(13, 17, 26, 0.85)',
                border: '1px solid rgba(0, 82, 255, 0.22)',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 13,
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 600, color: '#CCFF00', fontFamily: 'Consolas, monospace' }}>{log.tool}</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <Badge
                    appearance="filled"
                    style={{
                      background: log.tier === 0 ? 'rgba(0, 82, 255, 0.25)' : log.tier === 1 ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)',
                      color: log.tier === 0 ? '#337aff' : log.tier === 1 ? '#f59e0b' : '#ef4444',
                      border: `1px solid ${log.tier === 0 ? '#0052FF' : log.tier === 1 ? '#f59e0b' : '#ef4444'}`
                    }}
                  >
                    Tier {log.tier}
                  </Badge>
                  <Badge
                    appearance="tint"
                    style={{
                      background: log.result_status === 'SUCCESS' ? 'rgba(204, 255, 0, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: log.result_status === 'SUCCESS' ? '#CCFF00' : '#ef4444'
                    }}
                  >
                    {log.result_status}
                  </Badge>
                </div>
              </div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>
                Decision: <strong style={{ color: '#e2e8f0' }}>{log.decision}</strong> | Source: {log.source}
              </div>
              <div style={{ color: '#64748b', fontSize: 11, fontFamily: 'Consolas, monospace', overflowX: 'auto' }}>
                {log.arguments_redacted}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
