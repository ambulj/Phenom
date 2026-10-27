import React from 'react';
import { Button, Badge } from '@fluentui/react-components';
import { DismissRegular } from '@fluentui/react-icons';

interface SettingsPanelProps {
  onClose: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ onClose }) => {
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
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Phenom Settings</h2>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#60a5fa', marginBottom: 6 }}>Model Architecture</h3>
          <div style={{ fontSize: 13, color: '#cbd5e1' }}>Default Model: <strong>Llama 3 8B (4-bit Q4_0 on Ollama)</strong></div>
          <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 4 }}>Cloud Model: <strong>Nemotron 70B (build.nvidia.com)</strong></div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
            Private data is strictly prohibited from leaving the local machine. Cloud escalation requires explicit confirmation preview.
          </div>
        </div>

        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#ef4444', marginBottom: 6 }}>Guardian Kill Switch</h3>
          <div style={{ fontSize: 13, color: '#cbd5e1' }}>Global Hotkey: <Badge appearance="filled" color="danger">Ctrl + Alt + Pause</Badge></div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
            Immediately force-terminates child processes, cancels generation streams, and freezes Phenom.
          </div>
        </div>

        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#10b981', marginBottom: 6 }}>Security Tiers (SAFETY.md)</h3>
          <div style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.6 }}>
            • Tier 0: Read-only (Auto-run)<br />
            • Tier 1: Reversible change (Confirmation / Remember for folder)<br />
            • Tier 2: Destructive / External (Explicit preview confirmation, never remembered)<br />
            • Tier 3: Blocked / System-level (Strictly blocked by default)
          </div>
        </div>
      </div>
    </div>
  );
};
