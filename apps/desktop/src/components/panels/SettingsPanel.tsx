import React, { useState } from 'react';
import { Button, Input, Select } from '@fluentui/react-components';
import { DismissRegular, CheckmarkRegular, MicRegular, MicOffRegular } from '@fluentui/react-icons';
import { apiFetch } from '../../utils/api';

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
  const [vaultStatus, setVaultStatus] = useState<any>(null);
  const [vaultRemoteUrl, setVaultRemoteUrl] = useState<string>('');
  const [vaultToken, setVaultToken] = useState<string>('');
  const [vaultMessage, setVaultMessage] = useState<string>('');
  const [vaultTesting, setVaultTesting] = useState<boolean>(false);
  const [vaultSyncing, setVaultSyncing] = useState<boolean>(false);

  // Google Workspace states
  const [workspaceStatus, setWorkspaceStatus] = useState<any>(null);
  const [gmailAddress, setGmailAddress] = useState<string>('');
  const [gmailPassword, setGmailPassword] = useState<string>('');
  const [calendarToken, setCalendarToken] = useState<string>('');
  const [workspaceMessage, setWorkspaceMessage] = useState<string>('');
  const [workspaceTesting, setWorkspaceTesting] = useState<boolean>(false);

  // Telegram Remote states
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [revealedPin, setRevealedPin] = useState<string>('');
  const [pinMessage, setPinMessage] = useState<string>('');

  React.useEffect(() => {
    apiFetch('/api/vault/status')
      .then((res) => res.json())
      .then((data) => {
        setVaultStatus(data);
        if (data.remote_url) setVaultRemoteUrl(data.remote_url);
      })
      .catch((err) => console.error('Error loading vault status:', err));

    apiFetch('/api/workspace/status')
      .then((res) => res.json())
      .then((data) => {
        setWorkspaceStatus(data);
        if (data.gmail_address) setGmailAddress(data.gmail_address);
      })
      .catch((err) => console.error('Error loading workspace status:', err));
    apiFetch('/api/telegram/status')
      .then((res) => res.json())
      .then((data) => setTelegramStatus(data))
      .catch((err) => console.error('Error loading telegram status:', err));
  }, []);

  const handleTestVaultConnection = async () => {
    setVaultTesting(true);
    setVaultMessage('Testing connection to remote...');
    try {
      const res = await apiFetch('/api/vault/test_connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remote_url: vaultRemoteUrl })
      });
      const data = await res.json();
      setVaultMessage(data.message || (data.status === 'success' ? 'Connection successful!' : 'Connection failed.'));
    } catch (e: any) {
      setVaultMessage(`Connection error: ${e.message}`);
    } finally {
      setVaultTesting(false);
    }
  };

  const handleSaveVaultConfig = async () => {
    try {
      const res = await apiFetch('/api/vault/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remote_url: vaultRemoteUrl, token: vaultToken || undefined })
      });
      await res.json();
      setVaultMessage('Vault configuration saved. Token secured in Windows Credential Manager.');
      setVaultToken('');
      const statusRes = await apiFetch('/api/vault/status');
      setVaultStatus(await statusRes.json());
    } catch (e: any) {
      setVaultMessage(`Error saving config: ${e.message}`);
    }
  };

  const handleSyncVaultNow = async () => {
    setVaultSyncing(true);
    setVaultMessage('Syncing vault changes to remote git...');
    try {
      const res = await apiFetch('/api/vault/sync', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setVaultMessage(`Sync complete! Changes committed: ${data.committed}, Pushed: ${data.pushed}`);
      } else {
        setVaultMessage(`Sync response: ${data.output || data.status}`);
      }
    } catch (e: any) {
      setVaultMessage(`Sync failed: ${e.message}`);
    } finally {
      setVaultSyncing(false);
    }
  };

  const handleSaveWorkspaceConfig = async () => {
    try {
      if (gmailAddress && gmailPassword) {
        await apiFetch('/api/workspace/gmail/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address: gmailAddress, password: gmailPassword })
        });
        setGmailPassword('');
      }
      if (calendarToken) {
        await apiFetch('/api/workspace/calendar/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: calendarToken })
        });
        setCalendarToken('');
      }
      setWorkspaceMessage('Google Workspace credentials saved to Windows Credential Manager.');
      const res = await apiFetch('/api/workspace/status');
      setWorkspaceStatus(await res.json());
    } catch (e: any) {
      setWorkspaceMessage(`Error saving workspace config: ${e.message}`);
    }
  };

  const handleTestWorkspaceConnection = async () => {
    setWorkspaceTesting(true);
    setWorkspaceMessage('Testing Gmail IMAP & Calendar API connections...');
    try {
      const res = await apiFetch('/api/workspace/test_connection', { method: 'POST' });
      const data = await res.json();
      const parts = [];
      if (data.gmail) {
        parts.push(`Gmail: ${data.gmail.ok ? 'Connected' : data.gmail.message}`);
      }
      if (data.calendar) {
        parts.push(`Calendar: ${data.calendar.ok ? 'Connected' : data.calendar.message}`);
      }
      setWorkspaceMessage(parts.join(' | '));
    } catch (e: any) {
      setWorkspaceMessage(`Connection test error: ${e.message}`);
    } finally {
      setWorkspaceTesting(false);
    }
  };

  const handleDisconnectWorkspace = async () => {
    try {
      await apiFetch('/api/workspace/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'all' })
      });
      setWorkspaceMessage('Workspace disconnected. Credentials removed from Windows Credential Manager.');
      setGmailAddress('');
      setGmailPassword('');
      setCalendarToken('');
      const res = await apiFetch('/api/workspace/status');
      setWorkspaceStatus(await res.json());
    } catch (e: any) {
      setWorkspaceMessage(`Disconnect error: ${e.message}`);
    }
  };

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

        {/* Telegram Remote Control (Phase 6) */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#38bdf8', margin: 0 }}>Telegram Remote Control (Phase 6)</h3>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8' }}>
              Credential Manager
            </span>
          </div>
          <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 10px 0' }}>
            Remotely chat, approve Tier 1/2 actions, check status, and trigger kill switch. Messages from non-whitelisted user IDs are silently ignored.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Owner Telegram User ID
              </label>
              <Input
                placeholder="e.g. 123456789"
                defaultValue=""
                id="tg-owner-input"
                style={{ width: '100%' }}
                size="small"
              />
            </div>
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Bot Token (Stored in Credential Manager)
              </label>
              <Input
                type="password"
                placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                defaultValue=""
                id="tg-token-input"
                style={{ width: '100%' }}
                size="small"
              />
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Button
                appearance="primary"
                size="small"
                onClick={async () => {
                  const tokenEl = document.getElementById('tg-token-input') as HTMLInputElement;
                  const ownerEl = document.getElementById('tg-owner-input') as HTMLInputElement;
                  if (tokenEl && ownerEl) {
                    await apiFetch('/api/telegram/config', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ token: tokenEl.value, owner_id: ownerEl.value })
                    });
                    const res = await apiFetch('/api/telegram/status');
                    setTelegramStatus(await res.json());
                    alert('Telegram configuration saved to Windows Credential Manager.');
                  }
                }}
              >
                Save Credentials
              </Button>
              <Button
                appearance="secondary"
                size="small"
                onClick={async () => {
                  await apiFetch('/api/telegram/unlock', { method: 'POST' });
                  const res = await apiFetch('/api/telegram/status');
                  setTelegramStatus(await res.json());
                  alert('Remote control unlocked at physical desktop. Failed PIN counters reset.');
                }}
              >
                Unlock Remote (Reset Lockout)
              </Button>
            </div>

            {/* Remote PIN Security & Unattended Controls (Task 7g) */}
            <div style={{ marginTop: 12, padding: 10, background: 'rgba(15, 23, 42, 0.6)', borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>Remote 6-Digit PIN Security</span>
                <span style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 10,
                  background: telegramStatus?.locked ? '#ef4444' : '#10b981',
                  color: '#ffffff',
                  fontWeight: 600
                }}>
                  {telegramStatus?.locked ? 'REMOTE LOCKED' : 'REMOTE READY'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 8 }}>
                Required for Tier 2 commands (/do &lt;task&gt;). Locks after 3 failed strikes. Messages auto-deleted in 15 seconds.
              </div>

              {telegramStatus?.failed_attempts > 0 && (
                <div style={{ fontSize: 11, color: '#f87171', marginBottom: 6 }}>
                  ⚠️ Failed PIN attempts: {telegramStatus.failed_attempts} / 3 strikes
                </div>
              )}

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Button
                  appearance="secondary"
                  size="small"
                  onClick={async () => {
                    const res = await apiFetch('/api/telegram/pin/reveal');
                    const data = await res.json();
                    setRevealedPin(data.pin);
                    setPinMessage('PIN displayed securely on physical desktop only.');
                  }}
                >
                  Reveal Active PIN
                </Button>
                <Button
                  appearance="secondary"
                  size="small"
                  onClick={async () => {
                    const res = await apiFetch('/api/telegram/pin/rotate', { method: 'POST' });
                    const data = await res.json();
                    setRevealedPin(data.new_pin);
                    setPinMessage('New 6-digit PIN generated and stored securely.');
                    const statusRes = await apiFetch('/api/telegram/status');
                    setTelegramStatus(await statusRes.json());
                  }}
                >
                  Rotate PIN
                </Button>
                {revealedPin && (
                  <span style={{ fontSize: 14, fontFamily: 'monospace', fontWeight: 700, color: '#38bdf8', letterSpacing: 2 }}>
                    {revealedPin}
                  </span>
                )}
              </div>
              {pinMessage && (
                <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 4 }}>
                  {pinMessage}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Obsidian Vault & Private Git Backup (Hardening Task 6) */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#38bdf8', marginBottom: 8 }}>Obsidian Vault & Private Git Backup</h3>
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 10 }}>
            Stored outside the code repository. Versioned with git and backed up nightly to your private repo.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 2 }}>
                Vault Path (Fixed Location)
              </label>
              <div style={{ fontSize: 12, color: '#f1f5f9', background: 'rgba(15, 23, 42, 0.5)', padding: '6px 10px', borderRadius: 4, fontFamily: 'monospace' }}>
                {vaultStatus ? vaultStatus.vault_path : 'Loading...'}
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Private Git Remote URL
              </label>
              <Input
                placeholder="https://github.com/your-username/private-vault.git"
                value={vaultRemoteUrl}
                onChange={(e) => setVaultRemoteUrl(e.target.value)}
                style={{ width: '100%' }}
                size="small"
              />
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Must be a private repo. Code repository URL is strictly refused.
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Fine-Grained Git Token {vaultStatus?.has_token ? '(Configured in Credential Manager)' : ''}
              </label>
              <Input
                type="password"
                placeholder={vaultStatus?.has_token ? '••••••••••••••••••••' : 'github_pat_... (contents-write only)'}
                value={vaultToken}
                onChange={(e) => setVaultToken(e.target.value)}
                style={{ width: '100%' }}
                size="small"
              />
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Stored securely in Windows Credential Manager under Phenom/vault-git-token. Never logged.
              </div>
            </div>

            {vaultMessage && (
              <div style={{ fontSize: 12, color: vaultMessage.includes('fail') || vaultMessage.includes('error') ? '#f87171' : '#34d399', marginTop: 4 }}>
                {vaultMessage}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Button
                appearance="primary"
                size="small"
                onClick={handleSaveVaultConfig}
              >
                Save Vault Config
              </Button>
              <Button
                appearance="secondary"
                size="small"
                disabled={vaultTesting || !vaultRemoteUrl}
                onClick={handleTestVaultConnection}
              >
                {vaultTesting ? 'Testing...' : 'Test Connection'}
              </Button>
              <Button
                appearance="subtle"
                size="small"
                disabled={vaultSyncing}
                onClick={handleSyncVaultNow}
              >
                {vaultSyncing ? 'Syncing...' : 'Sync Now'}
              </Button>
            </div>
          </div>
        </div>

        {/* Google Workspace (Gmail & Calendar) */}
        <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 14, borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#38bdf8', margin: 0 }}>
              Google Workspace (Gmail & Calendar)
            </h3>
            <span style={{ fontSize: 11, color: workspaceStatus?.gmail_configured || workspaceStatus?.calendar_configured ? '#34d399' : '#94a3b8' }}>
              {workspaceStatus?.gmail_configured || workspaceStatus?.calendar_configured ? '● Connected' : '○ Not Configured'}
            </span>
          </div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
            Real IMAP over SSL for Gmail (read-only search and draft creation; sending is impossible). Google Calendar API for viewing and creating events.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Gmail Address {workspaceStatus?.gmail_address ? `(${workspaceStatus.gmail_address})` : ''}
              </label>
              <Input
                placeholder="your.email@gmail.com"
                value={gmailAddress}
                onChange={(e) => setGmailAddress(e.target.value)}
                style={{ width: '100%' }}
                size="small"
              />
            </div>

            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Gmail App Password {workspaceStatus?.gmail_configured ? '(Configured in Credential Manager)' : ''}
              </label>
              <Input
                type="password"
                placeholder={workspaceStatus?.gmail_configured ? '••••••••••••••••' : '16-character Google App Password'}
                value={gmailPassword}
                onChange={(e) => setGmailPassword(e.target.value)}
                style={{ width: '100%' }}
                size="small"
              />
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Requires 2FA enabled on Google Account -&gt; Security -&gt; App passwords. Stored in Windows Credential Manager under Phenom/gmail-app-password.
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Google Calendar OAuth Token {workspaceStatus?.calendar_configured ? '(Configured in Credential Manager)' : ''}
              </label>
              <Input
                type="password"
                placeholder={workspaceStatus?.calendar_configured ? '••••••••••••••••' : 'ya29.a0... OAuth Bearer Token'}
                value={calendarToken}
                onChange={(e) => setCalendarToken(e.target.value)}
                style={{ width: '100%' }}
                size="small"
              />
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                Stored securely under Phenom/google-calendar-token. Scopes: calendar.events.readonly and calendar.events.
              </div>
            </div>

            {workspaceMessage && (
              <div style={{ fontSize: 12, color: workspaceMessage.includes('fail') || workspaceMessage.includes('error') ? '#f87171' : '#34d399', marginTop: 4 }}>
                {workspaceMessage}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Button
                appearance="primary"
                size="small"
                onClick={handleSaveWorkspaceConfig}
              >
                Save Workspace Config
              </Button>
              <Button
                appearance="secondary"
                size="small"
                disabled={workspaceTesting || (!workspaceStatus?.gmail_configured && !workspaceStatus?.calendar_configured && !gmailAddress)}
                onClick={handleTestWorkspaceConnection}
              >
                {workspaceTesting ? 'Testing...' : 'Test Connection'}
              </Button>
              <Button
                appearance="subtle"
                size="small"
                onClick={handleDisconnectWorkspace}
              >
                Disconnect
              </Button>
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
