import React, { useState } from 'react';
import { Button, Input, Select } from '@fluentui/react-components';
import { DismissRegular, CheckmarkRegular, MicRegular, MicOffRegular } from '@fluentui/react-icons';

interface SettingsPanelProps {
  onClose: () => void;
  hotkeys?: Record<string, string>;
  onUpdateHotkey?: (action: string, keyCombo: string) => void;
  hotkeyError?: string | null;
  wakePhrase?: string;
  onSetWakePhrase?: (phrase: string) => void;
  isMuted?: boolean;
  onToggleMute?: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  onClose,
  hotkeys = {
    push_to_talk: 'alt+space',
    toggle_phenom: 'ctrl+alt+p',
    kill_switch: 'ctrl+alt+pause'
  },
  onUpdateHotkey,
  hotkeyError,
  wakePhrase = 'hey_jarvis',
  onSetWakePhrase,
  isMuted = false,
  onToggleMute
}) => {
  const [editedHotkeys, setEditedHotkeys] = useState<Record<string, string>>(hotkeys);
  const [currentWakePhrase, setCurrentWakePhrase] = useState<string>(wakePhrase);

  const handleKeyChange = (action: string, val: string) => {
    setEditedHotkeys((prev) => ({ ...prev, [action]: val }));
  };

  const handleSaveHotkey = (action: string) => {
    if (onUpdateHotkey) {
      onUpdateHotkey(action, editedHotkeys[action] || '');
    }
  };

  const handleWakePhraseChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPhrase = e.target.value;
    setCurrentWakePhrase(newPhrase);
    if (onSetWakePhrase) {
      onSetWakePhrase(newPhrase);
    }
  };

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
        {/* Voice & Wake Word Configuration */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#00e5ff', marginBottom: 8 }}>Voice & Wake Word (Phase 2)</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Wake Phrase (openWakeWord)
              </label>
              <Select
                value={currentWakePhrase}
                onChange={handleWakePhraseChange}
                style={{ width: '100%', background: 'rgba(15, 23, 42, 0.6)', color: '#f8fafc' }}
              >
                <option value="hey_jarvis">Hey Jarvis (Default)</option>
                <option value="alexa">Alexa</option>
              </Select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#e2e8f0' }}>Microphone Privacy</div>
                <div style={{ fontSize: 12, color: '#94a3b8' }}>Processed in RAM only. Never written to disk.</div>
              </div>
              <Button
                appearance={isMuted ? 'primary' : 'subtle'}
                icon={isMuted ? <MicOffRegular /> : <MicRegular />}
                onClick={onToggleMute}
                style={{
                  backgroundColor: isMuted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: isMuted ? '#f87171' : '#34d399',
                  border: isMuted ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)'
                }}
              >
                {isMuted ? 'Muted' : 'Listening'}
              </Button>
            </div>
          </div>
        </div>

        {/* Global Hotkeys & Conflict Detection */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#f59e0b', marginBottom: 8 }}>Global Keyboard Hotkeys</h3>
          
          {hotkeyError && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              color: '#fca5a5',
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 12,
              marginBottom: 10
            }}>
              {hotkeyError}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Push to talk */}
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Push-to-Talk
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  value={editedHotkeys.push_to_talk ?? hotkeys.push_to_talk ?? 'alt+space'}
                  onChange={(_, data) => handleKeyChange('push_to_talk', data.value)}
                  style={{ flex: 1 }}
                />
                <Button icon={<CheckmarkRegular />} onClick={() => handleSaveHotkey('push_to_talk')}>
                  Save
                </Button>
              </div>
            </div>

            {/* Toggle Phenom */}
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Show / Hide Window
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  value={editedHotkeys.toggle_phenom ?? hotkeys.toggle_phenom ?? 'ctrl+alt+p'}
                  onChange={(_, data) => handleKeyChange('toggle_phenom', data.value)}
                  style={{ flex: 1 }}
                />
                <Button icon={<CheckmarkRegular />} onClick={() => handleSaveHotkey('toggle_phenom')}>
                  Save
                </Button>
              </div>
            </div>

            {/* Guardian Kill Switch */}
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Guardian Kill Switch
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  value={editedHotkeys.kill_switch ?? hotkeys.kill_switch ?? 'ctrl+alt+pause'}
                  onChange={(_, data) => handleKeyChange('kill_switch', data.value)}
                  style={{ flex: 1 }}
                />
                <Button icon={<CheckmarkRegular />} onClick={() => handleSaveHotkey('kill_switch')}>
                  Save
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Model Architecture */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#60a5fa', marginBottom: 6 }}>Model Architecture</h3>
          <div style={{ fontSize: 13, color: '#cbd5e1' }}>Default Model: <strong>Llama 3 8B (4-bit Q4_0 on Ollama)</strong></div>
          <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 4 }}>Cloud Model: <strong>Nemotron 70B (build.nvidia.com)</strong></div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
            Private data is strictly prohibited from leaving the local machine. Cloud escalation requires explicit confirmation preview.
          </div>
        </div>

        {/* Security Tiers */}
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
