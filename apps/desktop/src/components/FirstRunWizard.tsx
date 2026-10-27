import React, { useState } from 'react';
import { Button, Input, Badge, Checkbox } from '@fluentui/react-components';
import {
  CheckmarkCircleFilled,
  KeyRegular,
  KeyboardRegular,
  FolderRegular,
  Speaker2Regular,
  ArrowRightRegular,
  ArrowLeftRegular
} from '@fluentui/react-icons';

interface FirstRunWizardProps {
  onComplete: () => void;
}

export const FirstRunWizard: React.FC<FirstRunWizardProps> = ({ onComplete }) => {
  const [step, setStep] = useState<number>(1);

  // Form states
  const [nvidiaKey, setNvidiaKey] = useState<string>('');
  const [telegramToken, setTelegramToken] = useState<string>('');
  const [telegramOwnerId, setTelegramOwnerId] = useState<string>('');

  const [indexDocuments, setIndexDocuments] = useState<boolean>(true);
  const [indexDownloads, setIndexDownloads] = useState<boolean>(true);
  const [indexPhotos, setIndexPhotos] = useState<boolean>(true);

  const handleFinish = async () => {
    // Save credentials to backend
    try {
      if (telegramToken && telegramOwnerId) {
        await fetch('http://localhost:8000/api/telegram/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: telegramToken, owner_id: telegramOwnerId })
        });
      }
    } catch (e) {
      console.error('Failed to save wizard config:', e);
    }
    localStorage.setItem('phenom_first_run_done', 'true');
    onComplete();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        background: 'rgba(11, 15, 25, 0.95)',
        backdropFilter: 'blur(24px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#f8fafc',
        fontFamily: 'Segoe UI, system-ui, sans-serif'
      }}
    >
      <div
        style={{
          width: 580,
          background: 'rgba(15, 23, 42, 0.96)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 16,
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.6)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '24px 28px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>✨</span>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: '#60a5fa' }}>
                Welcome to Phenom
              </h1>
              <span style={{ fontSize: 12, color: '#94a3b8' }}>
                Personal Windows 11 Desktop Assistant Setup
              </span>
            </div>
          </div>
          <Badge appearance="tint" color="brand">Step {step} of 4</Badge>
        </div>

        {/* Body Content */}
        <div style={{ padding: '24px 28px', minHeight: 280, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* STEP 1: Language & Voice */}
          {step === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8' }}>
                <Speaker2Regular style={{ fontSize: 18 }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>English Voice & Audio Architecture</h2>
              </div>
              <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: '20px', margin: 0 }}>
                Phenom operates exclusively in English with a witty, Jarvis-style male voice. Speech processing is completely private and local:
              </p>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.06)', fontSize: 12, lineHeight: '22px' }}>
                • <strong>Voice Synthesis:</strong> Windows SAPI5 Male Voice (Microsoft David)<br />
                • <strong>Speech Recognition:</strong> Faster-Whisper (CUDA accelerated on NVIDIA GPU)<br />
                • <strong>Wake Word:</strong> openWakeWord (Hey Jarvis / Alexa)<br />
                • <strong>Privacy Guarantee:</strong> Audio is processed strictly in RAM and never written to disk.
              </div>
            </div>
          )}

          {/* STEP 2: API Keys & Credentials */}
          {step === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#a855f7' }}>
                <KeyRegular style={{ fontSize: 18 }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>API Credentials (Optional)</h2>
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0 }}>
                Keys are stored securely in Windows Credential Manager. Local Llama 3 8B works without any keys.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    NVIDIA API Key (for cloud Nemotron escalation on long non-private text)
                  </label>
                  <Input
                    type="password"
                    placeholder="nvapi-..."
                    value={nvidiaKey}
                    onChange={(_, d) => setNvidiaKey(d.value)}
                    size="small"
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    Telegram Bot Token (for remote control)
                  </label>
                  <Input
                    type="password"
                    placeholder="123456:ABC-..."
                    value={telegramToken}
                    onChange={(_, d) => setTelegramToken(d.value)}
                    size="small"
                    style={{ width: '100%' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
                    Telegram Owner User ID (only this user can message Phenom)
                  </label>
                  <Input
                    placeholder="e.g. 123456789"
                    value={telegramOwnerId}
                    onChange={(_, d) => setTelegramOwnerId(d.value)}
                    size="small"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Safe Default Hotkeys */}
          {step === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b' }}>
                <KeyboardRegular style={{ fontSize: 18 }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Safe Default System Hotkeys</h2>
              </div>
              <p style={{ fontSize: 12, color: '#cbd5e1', margin: 0 }}>
                System-level global hotkeys configured with conflict detection:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 8 }}>
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#fca5a5' }}>Guardian Kill Switch</span>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Immediately halts all models and tools</div>
                  </div>
                  <Badge appearance="filled" color="danger">Ctrl + Alt + Pause</Badge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 8, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Push-to-Talk</span>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Hold to speak directly to Phenom</div>
                  </div>
                  <Badge appearance="tint" color="informative">Alt + Space</Badge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 8, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Toggle Mini Overlay</span>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>Show / hide compact desktop bar</div>
                  </div>
                  <Badge appearance="tint" color="informative">Ctrl + Alt + P</Badge>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Privacy & Indexing Boundaries */}
          {step === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981' }}>
                <FolderRegular style={{ fontSize: 18 }} />
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Privacy & Indexing Boundaries</h2>
              </div>
              <p style={{ fontSize: 12, color: '#cbd5e1', margin: 0 }}>
                Choose which folders Phenom may read for long-term memory and search:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <Checkbox
                  checked={indexDocuments}
                  onChange={(_, d) => setIndexDocuments(!!d.checked)}
                  label="Documents (PDFs, Word docs, spreadsheets, slides)"
                />
                <Checkbox
                  checked={indexDownloads}
                  onChange={(_, d) => setIndexDownloads(!!d.checked)}
                  label="Downloads (For reversible automatic categorization and cleanup)"
                />
                <Checkbox
                  checked={indexPhotos}
                  onChange={(_, d) => setIndexPhotos(!!d.checked)}
                  label="Photos (Search & EXIF indexing ONLY - never moved, renamed, or edited)"
                />
              </div>
              <div style={{ padding: '10px 14px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 8, fontSize: 11, color: '#6ee7b7', lineHeight: '18px' }}>
                🛡️ <strong>Safety Guarantee:</strong> Private files never leave your NVIDIA GPU. Permanent delete and photo modification are blocked at the code level.
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: '16px 28px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          {step > 1 ? (
            <Button appearance="subtle" icon={<ArrowLeftRegular />} onClick={() => setStep(step - 1)}>
              Back
            </Button>
          ) : <div />}

          {step < 4 ? (
            <Button appearance="primary" icon={<ArrowRightRegular />} iconPosition="after" onClick={() => setStep(step + 1)}>
              Continue
            </Button>
          ) : (
            <Button appearance="primary" icon={<CheckmarkCircleFilled />} style={{ background: '#10b981' }} onClick={handleFinish}>
              Finish Setup & Launch
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
