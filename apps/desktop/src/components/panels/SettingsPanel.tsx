import React, { useState, useEffect } from 'react';
import { Button, Input, Select, Switch, Slider, Badge, Spinner } from '@fluentui/react-components';
import {
  DismissRegular, CheckmarkRegular, MicRegular, MicOffRegular,
  LockClosedRegular, LockOpenRegular, KeyRegular, BotRegular,
  SparkleRegular, ShieldRegular, Speaker2Regular, GlobeRegular,
  WrenchRegular, ArrowSyncRegular
} from '@fluentui/react-icons';
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

type SettingsTab = 'telegram' | 'models' | 'voice' | 'safety' | 'workspace' | 'performance' | 'diagnostics';

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
  const [activeTab, setActiveTab] = useState<SettingsTab>('telegram');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Global Settings state loaded from /api/settings
  const [settings, setSettings] = useState<Record<string, string>>({
    local_model: 'qwen2.5-coder:14b',
    cloud_model: 'meta/llama-3.1-70b-instruct',
    routing_preference: 'hybrid_auto',
    temperature: '0.2',
    stream_tokens: 'true',
    max_context_tokens: '16384',
    wake_phrase: wakePhrase,
    voice_persona: 'jarvis_male',
    speech_rate: '1.0',
    speech_volume: '85',
    speech_output_mode: 'full_voice',
    hotkey_push_to_talk: hotkeys.push_to_talk || 'alt+space',
    hotkey_toggle_phenom: hotkeys.toggle_phenom || 'ctrl+alt+p',
    hotkey_kill_switch: hotkeys.kill_switch || 'ctrl+alt+pause',
    safe_mode: 'false',
    gaming_mode_auto: 'true',
    meeting_privacy_mode: 'false',
    orb_lod: 'ultra',
    start_on_boot: 'true',
    start_minimized: 'false',
    auto_recycle_bin: 'true',
    financial_safeguards: 'true',
    unattended_cart_block: 'true',
    vault_auto_sync_interval: '1_hour',
    telegram_unattended_timeout: '30',
    telegram_pin_auto_delete: 'true',
    morning_briefing_time: '08:00',
    morning_briefing_auto: 'true',
    action_log_retention: '30_days',
    biometric_voice_verification: 'false'
  });

  // Hotkey editing state
  const [editedHotkeys, setEditedHotkeys] = useState<Record<string, string>>(hotkeys);

  // Telegram Remote state
  const [telegramStatus, setTelegramStatus] = useState<any>(null);
  const [tgOwnerInput, setTgOwnerInput] = useState<string>('');
  const [tgTokenInput, setTgTokenInput] = useState<string>('');
  const [revealedPin, setRevealedPin] = useState<string>('');
  const [telegramActionMsg, setTelegramActionMsg] = useState<string>('');

  // Vault state
  const [vaultStatus, setVaultStatus] = useState<any>(null);
  const [vaultRemoteUrl, setVaultRemoteUrl] = useState<string>('');
  const [vaultToken, setVaultToken] = useState<string>('');
  const [vaultMessage, setVaultMessage] = useState<string>('');
  const [vaultTesting, setVaultTesting] = useState<boolean>(false);
  const [vaultSyncing, setVaultSyncing] = useState<boolean>(false);

  // Google Workspace state
  const [workspaceStatus, setWorkspaceStatus] = useState<any>(null);
  const [gmailAddress, setGmailAddress] = useState<string>('');
  const [gmailPassword, setGmailPassword] = useState<string>('');
  const [calendarToken, setCalendarToken] = useState<string>('');
  const [workspaceMessage, setWorkspaceMessage] = useState<string>('');
  const [workspaceTesting, setWorkspaceTesting] = useState<boolean>(false);

  // System Diagnostics state
  const [diagnosticsRunning, setDiagnosticsRunning] = useState<boolean>(false);
  const [diagnosticsResult, setDiagnosticsResult] = useState<any>(null);

  // Load initial settings & statuses
  useEffect(() => {
    // 1. Load System Settings
    apiFetch('/api/settings')
      .then((res) => res.json())
      .then((data) => {
        if (data.settings) {
          setSettings((prev) => ({ ...prev, ...data.settings }));
        }
      })
      .catch((err) => console.error('Error loading settings:', err));

    // 2. Load Telegram Status
    apiFetch('/api/telegram/status')
      .then((res) => res.json())
      .then((data) => {
        setTelegramStatus(data);
        if (data.owner_id) setTgOwnerInput(String(data.owner_id));
      })
      .catch((err) => console.error('Error loading telegram status:', err));

    // 3. Load Vault Status
    apiFetch('/api/vault/status')
      .then((res) => res.json())
      .then((data) => {
        setVaultStatus(data);
        if (data.remote_url) setVaultRemoteUrl(data.remote_url);
      })
      .catch((err) => console.error('Error loading vault status:', err));

    // 4. Load Workspace Status
    apiFetch('/api/workspace/status')
      .then((res) => res.json())
      .then((data) => {
        setWorkspaceStatus(data);
        if (data.gmail_address) setGmailAddress(data.gmail_address);
      })
      .catch((err) => console.error('Error loading workspace status:', err));
  }, []);

  // Update a single setting in local state and persist to backend
  const updateSetting = async (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    try {
      setIsSaving(true);
      await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: { [key]: value } })
      });
      setStatusMessage(`Saved: ${key}`);
      setTimeout(() => setStatusMessage(''), 2500);
    } catch (e: any) {
      setStatusMessage(`Save error: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Telegram Unlock action
  const handleUnlockTelegram = async () => {
    try {
      setTelegramActionMsg('Unlocking remote access from desktop...');
      await apiFetch('/api/telegram/unlock', { method: 'POST' });
      setTelegramStatus((prev: any) => ({ ...prev, locked: false, failed_attempts: 0 }));
      setTelegramActionMsg('Remote control unlocked! Access is now active on your Telegram bot.');
    } catch (e: any) {
      setTelegramActionMsg(`Unlock error: ${e.message}`);
    }
  };

  // Telegram Lock action
  const handleLockTelegram = async () => {
    try {
      setTelegramActionMsg('Locking remote access...');
      await apiFetch('/api/telegram/lock', { method: 'POST' });
      setTelegramStatus((prev: any) => ({ ...prev, locked: true }));
      setTelegramActionMsg('Remote control locked. Access is disabled until unlocked on this desktop.');
    } catch (e: any) {
      setTelegramActionMsg(`Lock error: ${e.message}`);
    }
  };

  // Telegram Save Credentials
  const handleSaveTelegramConfig = async () => {
    try {
      setTelegramActionMsg('Saving Telegram credentials to Windows Credential Manager...');
      await apiFetch('/api/telegram/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tgTokenInput || undefined, owner_id: tgOwnerInput || undefined })
      });
      const res = await apiFetch('/api/telegram/status');
      setTelegramStatus(await res.json());
      setTgTokenInput('');
      setTelegramActionMsg('Telegram configuration secured in Windows Credential Manager.');
    } catch (e: any) {
      setTelegramActionMsg(`Config error: ${e.message}`);
    }
  };

  // Reveal PIN
  const handleRevealPin = async () => {
    try {
      const res = await apiFetch('/api/telegram/pin/reveal');
      const data = await res.json();
      setRevealedPin(data.pin);
      setTelegramActionMsg('PIN displayed securely on physical desktop only.');
    } catch (e: any) {
      setTelegramActionMsg(`PIN reveal error: ${e.message}`);
    }
  };

  // Rotate PIN
  const handleRotatePin = async () => {
    try {
      const res = await apiFetch('/api/telegram/pin/rotate', { method: 'POST' });
      const data = await res.json();
      setRevealedPin(data.new_pin);
      setTelegramActionMsg('New 6-digit PIN generated and stored securely.');
      const statusRes = await apiFetch('/api/telegram/status');
      setTelegramStatus(await statusRes.json());
    } catch (e: any) {
      setTelegramActionMsg(`PIN rotate error: ${e.message}`);
    }
  };

  // Vault actions
  const handleTestVaultConnection = async () => {
    setVaultTesting(true);
    setVaultMessage('Testing connection to private git repo...');
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
      await apiFetch('/api/vault/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remote_url: vaultRemoteUrl, token: vaultToken || undefined })
      });
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

  // Workspace actions
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
      if (data.gmail) parts.push(`Gmail: ${data.gmail.ok ? 'Connected' : data.gmail.message}`);
      if (data.calendar) parts.push(`Calendar: ${data.calendar.ok ? 'Connected' : data.calendar.message}`);
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

  // Run Self-Check
  const handleRunDiagnostics = async () => {
    setDiagnosticsRunning(true);
    try {
      const res = await apiFetch('/api/system/self-check');
      const data = await res.json();
      setDiagnosticsResult(data);
    } catch (e: any) {
      setDiagnosticsResult({ status: 'error', message: e.message });
    } finally {
      setDiagnosticsRunning(false);
    }
  };

  const handleSaveHotkey = (action: string) => {
    if (onUpdateHotkey) {
      onUpdateHotkey(action, editedHotkeys[action] || '');
    }
    updateSetting(`hotkey_${action}`, editedHotkeys[action] || '');
  };

  const tabs: { id: SettingsTab; label: string; icon: any }[] = [
    { id: 'telegram', label: 'Telegram & Remote', icon: <BotRegular /> },
    { id: 'models', label: 'AI Models & Router', icon: <SparkleRegular /> },
    { id: 'voice', label: 'Voice & Persona', icon: <Speaker2Regular /> },
    { id: 'safety', label: 'Guardian & Safety', icon: <ShieldRegular /> },
    { id: 'workspace', label: 'Workspace & Vault', icon: <GlobeRegular /> },
    { id: 'performance', label: 'Gaming & Performance', icon: <ArrowSyncRegular /> },
    { id: 'diagnostics', label: 'Diagnostics & Data', icon: <WrenchRegular /> }
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', color: '#f8fafc', background: '#040609' }}>
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 18px',
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)',
          background: 'rgba(10, 15, 26, 0.95)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc', letterSpacing: 0.5 }}>
            Phenom Settings & Preferences
          </h2>
          {isSaving && <Spinner size="extra-tiny" label="Syncing..." />}
          {statusMessage && (
            <span style={{ fontSize: 11, color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 8px', borderRadius: 4 }}>
              {statusMessage}
            </span>
          )}
        </div>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      {/* Tab Navigation Strip */}
      <div
        style={{
          display: 'flex',
          gap: 6,
          padding: '8px 16px',
          background: 'rgba(8, 12, 20, 0.9)',
          borderBottom: '1px solid rgba(0, 82, 255, 0.15)',
          overflowX: 'auto',
          whiteSpace: 'nowrap'
        }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: isActive ? 600 : 500,
                border: isActive ? '1px solid #0052FF' : '1px solid transparent',
                background: isActive ? 'rgba(0, 82, 255, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: isActive ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* TAB 1: TELEGRAM & REMOTE CONTROL */}
        {activeTab === 'telegram' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Remote Lock Status Card */}
            <div
              style={{
                background: telegramStatus?.locked ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                border: telegramStatus?.locked ? '1px solid #ef4444' : '1px solid #10b981',
                borderRadius: 8,
                padding: 14
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {telegramStatus?.locked ? (
                    <LockClosedRegular style={{ fontSize: 20, color: '#f87171' }} />
                  ) : (
                    <LockOpenRegular style={{ fontSize: 20, color: '#34d399' }} />
                  )}
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: telegramStatus?.locked ? '#fca5a5' : '#6ee7b7' }}>
                      {telegramStatus?.locked ? 'Remote Control is Locked: Access Disabled' : 'Remote Control is Active: Ready for Commands'}
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                      {telegramStatus?.locked
                        ? 'Workstation lockdown engaged. Commands via Telegram are currently rejected for your protection.'
                        : 'Secure unattended uplink ready. You can chat, request snapshots, and approve actions remotely.'}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  {telegramStatus?.locked ? (
                    <Button
                      appearance="primary"
                      size="small"
                      icon={<CheckmarkRegular />}
                      onClick={handleUnlockTelegram}
                      style={{ backgroundColor: '#10b981', color: '#ffffff' }}
                    >
                      Unlock Remote Access
                    </Button>
                  ) : (
                    <Button
                      appearance="secondary"
                      size="small"
                      icon={<LockClosedRegular />}
                      onClick={handleLockTelegram}
                      style={{ borderColor: '#ef4444', color: '#f87171' }}
                    >
                      Emergency Lockdown
                    </Button>
                  )}
                </div>
              </div>

              {/* Informational Help Box */}
              <div
                style={{
                  marginTop: 10,
                  padding: '8px 10px',
                  background: 'rgba(0, 0, 0, 0.3)',
                  borderRadius: 6,
                  fontSize: 11,
                  color: '#cbd5e1',
                  lineHeight: 1.5
                }}
              >
                <strong style={{ color: '#38bdf8' }}>Why Remote Access Locks:</strong> Sending <code>/lock</code> from your phone or entering an incorrect 6-digit PIN 3 times triggers an immediate lockdown to protect your workstation. Clicking <strong>Unlock Remote Access</strong> on this physical desktop restores full bot operation.
              </div>
            </div>

            {/* Telegram Credentials Card */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginBottom: 10 }}>
                Telegram Bot Credentials (Windows Credential Manager)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Owner Telegram Numeric User ID
                  </label>
                  <Input
                    placeholder="e.g. 7717161689"
                    value={tgOwnerInput}
                    onChange={(_, d) => setTgOwnerInput(d.value)}
                    style={{ width: '100%' }}
                    size="small"
                  />
                  <span style={{ fontSize: 11, color: '#64748b' }}>
                    Messages and actions from non-whitelisted user IDs are silently dropped.
                  </span>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Telegram Bot Token
                  </label>
                  <Input
                    type="password"
                    placeholder={telegramStatus?.configured ? '••••••••••••••••••••••••••••••••••••••••••••' : '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'}
                    value={tgTokenInput}
                    onChange={(_, d) => setTgTokenInput(d.value)}
                    style={{ width: '100%' }}
                    size="small"
                  />
                  <span style={{ fontSize: 11, color: '#64748b' }}>
                    Stored securely in Windows Credential Manager under <code>Phenom/telegram-bot-token</code>.
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <Button appearance="primary" size="small" onClick={handleSaveTelegramConfig}>
                    Save Telegram Credentials
                  </Button>
                </div>
              </div>
            </div>

            {/* 6-Digit PIN Security Card */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h3 style={{ fontSize: 13, fontWeight: 600, color: '#CCFF00', margin: 0 }}>
                  Remote 6-Digit PIN Security
                </h3>
                {telegramStatus?.failed_attempts > 0 && (
                  <Badge color="danger" appearance="filled">
                    {telegramStatus.failed_attempts} / 3 Strikes
                  </Badge>
                )}
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 10px 0' }}>
                Required for Tier 2 remote actions (<code>/do &lt;command&gt;</code>). Locks after 3 consecutive wrong entries.
              </p>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Button appearance="secondary" size="small" icon={<KeyRegular />} onClick={handleRevealPin}>
                  Reveal Active PIN
                </Button>
                <Button appearance="secondary" size="small" icon={<ArrowSyncRegular />} onClick={handleRotatePin}>
                  Rotate PIN
                </Button>
                {revealedPin && (
                  <span style={{ fontSize: 16, fontFamily: 'monospace', fontWeight: 800, color: '#38bdf8', letterSpacing: 3, padding: '4px 10px', background: '#000', borderRadius: 4 }}>
                    {revealedPin}
                  </span>
                )}
              </div>
            </div>

            {/* Remote Policies Card */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Remote Session Policies
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Unattended Remote Command Timeout</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Auto-expire pending approvals sent to phone</div>
                  </div>
                  <Select
                    value={settings.telegram_unattended_timeout || '30'}
                    onChange={(e) => updateSetting('telegram_unattended_timeout', e.target.value)}
                    size="small"
                  >
                    <option value="15">15 Minutes</option>
                    <option value="30">30 Minutes (Recommended)</option>
                    <option value="60">1 Hour</option>
                    <option value="120">2 Hours</option>
                  </Select>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Auto-Delete Security Messages in Telegram</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Purges PIN prompts & OTP verification messages after 15 seconds</div>
                  </div>
                  <Switch
                    checked={settings.telegram_pin_auto_delete === 'true'}
                    onChange={(_, d) => updateSetting('telegram_pin_auto_delete', d.checked ? 'true' : 'false')}
                  />
                </div>
              </div>
            </div>

            {telegramActionMsg && (
              <div style={{ fontSize: 12, color: '#38bdf8', padding: '8px 12px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: 6 }}>
                {telegramActionMsg}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: AI MODELS & ROUTER */}
        {activeTab === 'models' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Local Model Selector */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#CCFF00', marginBottom: 10 }}>
                Local Offline Model (Ollama / CUDA)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <label style={{ fontSize: 12, color: '#94a3b8' }}>
                  Select Primary Local Neural Engine
                </label>
                <Select
                  value={settings.local_model || 'qwen2.5-coder:14b'}
                  onChange={(e) => updateSetting('local_model', e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="qwen2.5-coder:14b">qwen2.5-coder:14b — High Precision Code & Algorithmic Reasoning</option>
                  <option value="phenom-jarvis:latest">phenom-jarvis:latest — Specialized British Jarvis Personality</option>
                  <option value="llama3:8b">llama3:8b — Fast Conversational Model (4-bit Q4_0)</option>
                  <option value="qwen2.5:7b">qwen2.5:7b — Ultra-Low VRAM Balanced Engine</option>
                </Select>
                <div style={{ fontSize: 11, color: '#64748b' }}>
                  Private files, code, credentials, and screen captures are strictly processed locally without cloud leakage.
                </div>
              </div>
            </div>

            {/* Cloud Provider & Routing */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginBottom: 10 }}>
                Cloud Inference & Intelligent Model Router
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Model Routing Policy
                  </label>
                  <Select
                    value={settings.routing_preference || 'hybrid_auto'}
                    onChange={(e) => updateSetting('routing_preference', e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="hybrid_auto">Hybrid Auto (Local default, cloud escalation for massive code tasks)</option>
                    <option value="local_only">Strictly Local / Airgapped (Never call cloud APIs under any condition)</option>
                    <option value="cloud_preferred">Cloud Preferred (Maximum reasoning via Nemotron/Llama 70B)</option>
                  </Select>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Cloud Model Tier
                  </label>
                  <Select
                    value={settings.cloud_model || 'meta/llama-3.1-70b-instruct'}
                    onChange={(e) => updateSetting('cloud_model', e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="meta/llama-3.1-70b-instruct">Meta Llama 3.1 70B Instruct (build.nvidia.com)</option>
                    <option value="nvidia/nemotron-4-340b-instruct">NVIDIA Nemotron 4 340B Instruct (High Capacity)</option>
                    <option value="meta/llama-3.3-70b-instruct">Meta Llama 3.3 70B Instruct (Latest)</option>
                  </Select>
                </div>
              </div>
            </div>

            {/* Inference Parameters */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Inference Parameters & Memory RAG
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <label style={{ fontSize: 12, color: '#94a3b8' }}>Sampling Temperature: {settings.temperature || '0.2'}</label>
                    <span style={{ fontSize: 11, color: '#64748b' }}>
                      {parseFloat(settings.temperature || '0.2') <= 0.3 ? 'Deterministic & Code Precision' : parseFloat(settings.temperature || '0.2') <= 0.7 ? 'Balanced Conversational' : 'Creative Exploration'}
                    </span>
                  </div>
                  <Slider
                    min={0.0}
                    max={1.0}
                    step={0.05}
                    value={parseFloat(settings.temperature || '0.2')}
                    onChange={(_, d) => updateSetting('temperature', String(d.value))}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Live Token Streaming</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Stream generated tokens word-by-word with typewriter animation</div>
                  </div>
                  <Switch
                    checked={settings.stream_tokens === 'true'}
                    onChange={(_, d) => updateSetting('stream_tokens', d.checked ? 'true' : 'false')}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Max Context Window
                  </label>
                  <Select
                    value={settings.max_context_tokens || '16384'}
                    onChange={(e) => updateSetting('max_context_tokens', e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="4096">4,096 Tokens (Fastest)</option>
                    <option value="8192">8,192 Tokens</option>
                    <option value="16384">16,384 Tokens (Recommended for coding)</option>
                    <option value="32768">32,768 Tokens (Extended context)</option>
                  </Select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: VOICE & PERSONA */}
        {activeTab === 'voice' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Wake Phrase & Mic */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#CCFF00', marginBottom: 10 }}>
                Wake Word Engine (openWakeWord)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Active Wake Phrase
                  </label>
                  <Select
                    value={settings.wake_phrase || wakePhrase}
                    onChange={(e) => {
                      const phrase = e.target.value;
                      updateSetting('wake_phrase', phrase);
                      if (onSetWakePhrase) onSetWakePhrase(phrase);
                    }}
                    style={{ width: '100%' }}
                  >
                    <option value="hey_jarvis">Hey Jarvis (Default, 80ms latency)</option>
                    <option value="alexa">Alexa</option>
                    <option value="phenom">Phenom</option>
                  </Select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 6 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: '#e2e8f0' }}>Microphone Privacy</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Processed in RAM only. Audio is never written to disk.</div>
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

            {/* TTS Voice Persona */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginBottom: 10 }}>
                Text-to-Speech Persona & Prosody
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Personality Style
                  </label>
                  <Select
                    value={settings.voice_persona || 'jarvis_male'}
                    onChange={(e) => updateSetting('voice_persona', e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="jarvis_male">Jarvis Male British — Composed, polished, refined</option>
                    <option value="jarvis_witty">Jarvis Witty & Playful — Quick banter, energetic</option>
                    <option value="hal_neutral">HAL Neutral — Scientific, concise, minimal</option>
                  </Select>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Audio Output Mode
                  </label>
                  <Select
                    value={settings.speech_output_mode || 'full_voice'}
                    onChange={(e) => updateSetting('speech_output_mode', e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="full_voice">Full Voice Synthesis (Speaks responses aloud)</option>
                    <option value="quiet">Quiet / Silent Mode (Chat UI only, zero audio output)</option>
                    <option value="chime_only">Auditory Chimes Only (Plays subtle tone, text response)</option>
                  </Select>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <label style={{ fontSize: 12, color: '#94a3b8' }}>Speech Rate: {settings.speech_rate || '1.0'}x</label>
                  </div>
                  <Slider
                    min={0.8}
                    max={1.4}
                    step={0.05}
                    value={parseFloat(settings.speech_rate || '1.0')}
                    onChange={(_, d) => updateSetting('speech_rate', String(d.value))}
                  />
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <label style={{ fontSize: 12, color: '#94a3b8' }}>Voice Volume: {settings.speech_volume || '85'}%</label>
                  </div>
                  <Slider
                    min={0}
                    max={100}
                    step={5}
                    value={parseInt(settings.speech_volume || '85', 10)}
                    onChange={(_, d) => updateSetting('speech_volume', String(d.value))}
                  />
                </div>
              </div>
            </div>

            {/* Biometrics */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>Biometric Voiceprint Verification</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>Reject wake word from unrecognized voices using speaker embeddings</div>
                </div>
                <Switch
                  checked={settings.biometric_voice_verification === 'true'}
                  onChange={(_, d) => updateSetting('biometric_voice_verification', d.checked ? 'true' : 'false')}
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: GUARDIAN & SAFETY CONTROLS */}
        {activeTab === 'safety' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Global Hotkeys */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f59e0b', marginBottom: 10 }}>
                Global Keyboard Hotkeys
              </h3>

              {hotkeyError && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', padding: '8px 12px', borderRadius: 6, fontSize: 12, marginBottom: 10 }}>
                  {hotkeyError}
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Push-to-Talk</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Input
                      value={editedHotkeys.push_to_talk ?? hotkeys.push_to_talk ?? 'alt+space'}
                      onChange={(_, data) => setEditedHotkeys((prev) => ({ ...prev, push_to_talk: data.value }))}
                      style={{ flex: 1 }}
                      size="small"
                    />
                    <Button icon={<CheckmarkRegular />} size="small" onClick={() => handleSaveHotkey('push_to_talk')}>Save</Button>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Show / Hide Window</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Input
                      value={editedHotkeys.toggle_phenom ?? hotkeys.toggle_phenom ?? 'ctrl+alt+p'}
                      onChange={(_, data) => setEditedHotkeys((prev) => ({ ...prev, toggle_phenom: data.value }))}
                      style={{ flex: 1 }}
                      size="small"
                    />
                    <Button icon={<CheckmarkRegular />} size="small" onClick={() => handleSaveHotkey('toggle_phenom')}>Save</Button>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Guardian Kill Switch</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Input
                      value={editedHotkeys.kill_switch ?? hotkeys.kill_switch ?? 'ctrl+alt+pause'}
                      onChange={(_, data) => setEditedHotkeys((prev) => ({ ...prev, kill_switch: data.value }))}
                      style={{ flex: 1 }}
                      size="small"
                    />
                    <Button icon={<CheckmarkRegular />} size="small" onClick={() => handleSaveHotkey('kill_switch')}>Save</Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Permanent Safety Rules (SAFETY.md) */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#10b981', marginBottom: 10 }}>
                Permanent Safety Enforcement (Non-Negotiable Guarantees)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>System Safe Mode (Tier 0 Lockdown)</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Restrict all tool executions strictly to read-only actions</div>
                  </div>
                  <Switch
                    checked={settings.safe_mode === 'true'}
                    onChange={(_, d) => updateSetting('safe_mode', d.checked ? 'true' : 'false')}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.85 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Recycle Bin Only (Rule 7)</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Permanent file deletion is impossible by construction</div>
                  </div>
                  <Badge color="success" appearance="filled">Enforced</Badge>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.85 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Anti-Financial Trading Safeguard (Rule 5)</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Informational market data only; trade execution is permanently blocked</div>
                  </div>
                  <Badge color="success" appearance="filled">Enforced</Badge>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.85 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Anti-Checkout Payment Blocker (Rule 8)</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Cart fill allowed; credit card typing and password storage prohibited</div>
                  </div>
                  <Badge color="success" appearance="filled">Enforced</Badge>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: 0.85 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Guardian Emergency Kill Switch SLA</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Interrupt latency strictly measured under 25ms</div>
                  </div>
                  <Badge color="informative" appearance="filled">&lt; 8.28 ms SLA</Badge>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: WORKSPACE & VAULT */}
        {activeTab === 'workspace' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Obsidian Vault */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginBottom: 6 }}>
                Obsidian Vault & Private Git Backup
              </h3>
              <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
                Daily logs, research, and memory summaries stored outside code repo with git versioning.
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 2 }}>Vault Path</label>
                  <div style={{ fontSize: 12, color: '#f1f5f9', background: '#040609', border: '1px solid rgba(0, 82, 255, 0.2)', padding: '6px 10px', borderRadius: 4, fontFamily: 'monospace' }}>
                    {vaultStatus ? vaultStatus.vault_path : 'C:\\Phenom\\vault'}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Private Git Remote URL</label>
                  <Input
                    placeholder="https://github.com/your-username/private-vault.git"
                    value={vaultRemoteUrl}
                    onChange={(e) => setVaultRemoteUrl(e.target.value)}
                    style={{ width: '100%' }}
                    size="small"
                  />
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
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: 12, color: '#94a3b8' }}>Auto-Sync Interval</label>
                  <Select
                    value={settings.vault_auto_sync_interval || '1_hour'}
                    onChange={(e) => updateSetting('vault_auto_sync_interval', e.target.value)}
                    size="small"
                  >
                    <option value="manual">Manual Only</option>
                    <option value="15_min">Every 15 Minutes</option>
                    <option value="1_hour">Every 1 Hour (Recommended)</option>
                    <option value="daily">Daily</option>
                  </Select>
                </div>

                {vaultMessage && (
                  <div style={{ fontSize: 12, color: vaultMessage.includes('fail') || vaultMessage.includes('error') ? '#f87171' : '#34d399' }}>
                    {vaultMessage}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <Button appearance="primary" size="small" onClick={handleSaveVaultConfig}>Save Vault Config</Button>
                  <Button appearance="secondary" size="small" disabled={vaultTesting || !vaultRemoteUrl} onClick={handleTestVaultConnection}>
                    {vaultTesting ? 'Testing...' : 'Test Connection'}
                  </Button>
                  <Button appearance="subtle" size="small" disabled={vaultSyncing} onClick={handleSyncVaultNow}>
                    {vaultSyncing ? 'Syncing...' : 'Sync Now'}
                  </Button>
                </div>
              </div>
            </div>

            {/* Google Workspace */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', margin: 0 }}>Google Workspace (Gmail & Calendar)</h3>
                <span style={{ fontSize: 11, color: workspaceStatus?.gmail_configured || workspaceStatus?.calendar_configured ? '#34d399' : '#94a3b8' }}>
                  {workspaceStatus?.gmail_configured || workspaceStatus?.calendar_configured ? '● Connected' : '○ Not Configured'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
                SSL IMAP for Gmail (draft creation only; sending strictly forbidden). Google Calendar API for viewing & creating events.
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Gmail Address</label>
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
                </div>

                <div>
                  <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                    Google Calendar Token {workspaceStatus?.calendar_configured ? '(Configured in Credential Manager)' : ''}
                  </label>
                  <Input
                    type="password"
                    placeholder={workspaceStatus?.calendar_configured ? '••••••••••••••••' : 'OAuth Bearer Token'}
                    value={calendarToken}
                    onChange={(e) => setCalendarToken(e.target.value)}
                    style={{ width: '100%' }}
                    size="small"
                  />
                </div>

                {workspaceMessage && (
                  <div style={{ fontSize: 12, color: workspaceMessage.includes('fail') || workspaceMessage.includes('error') ? '#f87171' : '#34d399' }}>
                    {workspaceMessage}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <Button appearance="primary" size="small" onClick={handleSaveWorkspaceConfig}>Save Workspace</Button>
                  <Button appearance="secondary" size="small" disabled={workspaceTesting || (!workspaceStatus?.gmail_configured && !gmailAddress)} onClick={handleTestWorkspaceConnection}>
                    {workspaceTesting ? 'Testing...' : 'Test Connection'}
                  </Button>
                  <Button appearance="subtle" size="small" onClick={handleDisconnectWorkspace}>Disconnect</Button>
                </div>
              </div>
            </div>

            {/* Morning Briefing Schedule */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Morning Briefing Scheduler
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Auto-Briefing on First Wake Word</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Read calendar agenda, top news, and weather when you first say "Hey Jarvis"</div>
                  </div>
                  <Switch
                    checked={settings.morning_briefing_auto === 'true'}
                    onChange={(_, d) => updateSetting('morning_briefing_auto', d.checked ? 'true' : 'false')}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: 12, color: '#94a3b8' }}>Preferred Briefing Time Window</label>
                  <Select
                    value={settings.morning_briefing_time || '08:00'}
                    onChange={(e) => updateSetting('morning_briefing_time', e.target.value)}
                    size="small"
                  >
                    <option value="07:00">07:00 AM</option>
                    <option value="08:00">08:00 AM</option>
                    <option value="09:00">09:00 AM</option>
                    <option value="10:00">10:00 AM</option>
                  </Select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: GAMING & PERFORMANCE */}
        {activeTab === 'performance' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Gaming Mode */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#CCFF00' }}>Intelligent Gaming Mode (Resource Governor)</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    Auto-detects active fullscreen 3D DirectX/Vulkan games, pauses background LLM processes, and frees GPU VRAM.
                  </div>
                </div>
                <Switch
                  checked={settings.gaming_mode_auto === 'true'}
                  onChange={(_, d) => updateSetting('gaming_mode_auto', d.checked ? 'true' : 'false')}
                />
              </div>
            </div>

            {/* Meeting Mode */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8' }}>Meeting Privacy Mode</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    Automatically mute microphone, suppress Telegram alerts, and blur sensitive desktop areas during calendar meetings.
                  </div>
                </div>
                <Switch
                  checked={settings.meeting_privacy_mode === 'true'}
                  onChange={(_, d) => updateSetting('meeting_privacy_mode', d.checked ? 'true' : 'false')}
                />
              </div>
            </div>

            {/* 3D Orb Visual LOD */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 8 }}>
                Three.js Particle Orb Level-of-Detail (LOD)
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 12, color: '#94a3b8' }}>Rendering Fidelity</label>
                <Select
                  value={settings.orb_lod || 'ultra'}
                  onChange={(e) => updateSetting('orb_lod', e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="ultra">Ultra (60 FPS, 12,000 particle cloud, full bloom & cyber waves)</option>
                  <option value="standard">Standard (45 FPS, 6,000 particles, low GPU load)</option>
                  <option value="eco">Eco Mode (30 FPS, 2,000 particles, battery optimized)</option>
                </Select>
              </div>
            </div>

            {/* Windows Startup & Behavior */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Desktop Launch & System Tray
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Launch with Windows Boot</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Start Phenom automatically in background when Windows starts</div>
                  </div>
                  <Switch
                    checked={settings.start_on_boot === 'true'}
                    onChange={(_, d) => updateSetting('start_on_boot', d.checked ? 'true' : 'false')}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Start Minimized to System Tray</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Keep window hidden until hotkey (Ctrl+Alt+P) or wake word is spoken</div>
                  </div>
                  <Switch
                    checked={settings.start_minimized === 'true'}
                    onChange={(_, d) => updateSetting('start_minimized', d.checked ? 'true' : 'false')}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: DIAGNOSTICS & SYSTEM DATA */}
        {activeTab === 'diagnostics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Self-Check Runner */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', marginBottom: 8 }}>
                Subsystem Integrity Self-Check
              </h3>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 10px 0' }}>
                Runs real-time verification across SQLite memory, Whisper STT, openWakeWord, Ollama, Guardian E-Stop, and Telegram Uplink.
              </p>
              <Button
                appearance="primary"
                size="small"
                icon={<WrenchRegular />}
                disabled={diagnosticsRunning}
                onClick={handleRunDiagnostics}
              >
                {diagnosticsRunning ? 'Running Subsystem Diagnostics...' : 'Execute Comprehensive Diagnostics'}
              </Button>

              {diagnosticsResult && (
                <div style={{ marginTop: 12, padding: 10, background: '#040609', border: '1px solid rgba(0, 82, 255, 0.2)', borderRadius: 6, fontSize: 11, fontFamily: 'monospace' }}>
                  <div style={{ color: '#34d399', fontWeight: 700, marginBottom: 4 }}>
                    ● Self-Check Output ({diagnosticsResult.status || 'OK'})
                  </div>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: '#cbd5e1' }}>
                    {JSON.stringify(diagnosticsResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Action Log Retention */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 10 }}>
                Data Retention & Privacy
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Action Log History Retention</div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Audit trails are encrypted with AES-256</div>
                  </div>
                  <Select
                    value={settings.action_log_retention || '30_days'}
                    onChange={(e) => updateSetting('action_log_retention', e.target.value)}
                    size="small"
                  >
                    <option value="7_days">7 Days</option>
                    <option value="30_days">30 Days (Recommended)</option>
                    <option value="90_days">90 Days</option>
                    <option value="forever">Indefinite (No Auto-Purge)</option>
                  </Select>
                </div>
              </div>
            </div>

            {/* Export & Reset Actions */}
            <div style={{ background: 'rgba(13, 17, 26, 0.85)', border: '1px solid rgba(0, 82, 255, 0.22)', padding: 14, borderRadius: 8 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc', marginBottom: 8 }}>
                System Maintenance
              </h3>
              <div style={{ display: 'flex', gap: 10 }}>
                <Button
                  appearance="secondary"
                  size="small"
                  onClick={async () => {
                    const res = await apiFetch('/api/system/export', { method: 'POST' });
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `phenom_diagnostic_bundle_${Date.now()}.json`;
                    a.click();
                  }}
                >
                  Export Diagnostic Bundle
                </Button>
                <Button
                  appearance="subtle"
                  size="small"
                  style={{ color: '#f87171' }}
                  onClick={async () => {
                    if (confirm('Clear temporary action logs and restart background workers? Encrypted memory facts are preserved.')) {
                      await apiFetch('/api/system/reset', { method: 'POST' });
                      alert('System cache cleared.');
                    }
                  }}
                >
                  Clear Temporary Cache
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
