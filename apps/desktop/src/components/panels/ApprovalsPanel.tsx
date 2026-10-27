import React, { useEffect, useState } from 'react';
import { Button } from '@fluentui/react-components';
import { DismissRegular, ArrowSyncRegular } from '@fluentui/react-icons';

interface ApprovalsPanelProps {
  onClose: () => void;
}

export const ApprovalsPanel: React.FC<ApprovalsPanelProps> = ({ onClose }) => {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchApprovals = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/approvals');
      if (res.ok) {
        const data = await res.json();
        setApprovals(data);
      }
    } catch (e) {
      console.error('Failed to fetch approvals:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
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
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Remembered Approvals</h2>
          <Button appearance="subtle" icon={<ArrowSyncRegular />} onClick={fetchApprovals} size="small" disabled={isLoading} />
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {approvals.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 14 }}>
            No remembered approvals. Tier 1 actions will ask for confirmation unless saved for a folder.
          </div>
        ) : (
          approvals.map((app) => (
            <div
              key={app.id}
              style={{
                background: 'rgba(30, 41, 59, 0.5)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 8,
                padding: '12px 14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#60a5fa' }}>{app.tool}</div>
                <div style={{ fontSize: 12, color: '#cbd5e1', marginTop: 2 }}>{app.folder_path}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
