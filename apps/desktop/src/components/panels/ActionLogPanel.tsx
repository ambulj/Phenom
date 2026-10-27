import React, { useEffect, useState } from 'react';
import { Button, Badge } from '@fluentui/react-components';
import { DismissRegular, ArrowSyncRegular } from '@fluentui/react-icons';
import { LogEntryPayload } from '../../types/protocol';

interface ActionLogPanelProps {
  onClose: () => void;
}

export const ActionLogPanel: React.FC<ActionLogPanelProps> = ({ onClose }) => {
  const [logs, setLogs] = useState<LogEntryPayload[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/logs');
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
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Security Action Log</h2>
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
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 13
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{log.tool}</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <Badge appearance="filled" color={log.tier === 0 ? 'informative' : log.tier === 1 ? 'warning' : 'danger'}>
                    Tier {log.tier}
                  </Badge>
                  <Badge appearance="tint" color={log.result_status === 'SUCCESS' ? 'success' : 'danger'}>
                    {log.result_status}
                  </Badge>
                </div>
              </div>
              <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 4 }}>
                Decision: <strong style={{ color: '#e2e8f0' }}>{log.decision}</strong> | Source: {log.source}
              </div>
              <div style={{ color: '#64748b', fontSize: 11, fontFamily: 'monospace', overflowX: 'auto' }}>
                {log.arguments_redacted}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
