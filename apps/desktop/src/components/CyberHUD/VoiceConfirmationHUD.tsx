import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  MicRegular,
  CheckmarkRegular,
  ShieldRegular,
} from '@fluentui/react-icons';

interface VoicePromptUI {
  prompt_id: string;
  tool_name: string;
  spoken_question: string;
  display_summary: string;
  tier: number;
  time_remaining: number;
}

interface VoiceConfirmationHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const VoiceConfirmationHUD: React.FC<VoiceConfirmationHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [activePrompt, setActivePrompt] = useState<VoicePromptUI>({
    prompt_id: 'conf-voice-001',
    tool_name: 'send_email',
    spoken_question: 'Bro, do you want me to send this email to Alex regarding the project update?',
    display_summary: 'Send outbound email to Alex (Project Update Draft)',
    tier: 2,
    time_remaining: 56,
  });

  const [spokenInput, setSpokenInput] = useState<string>('');
  const [resolutionStatus, setResolutionStatus] = useState<string>('PENDING');
  const [assistantReply, setAssistantReply] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(true);

  // Countdown timer simulation
  useEffect(() => {
    if (resolutionStatus !== 'PENDING') return;
    const interval = setInterval(() => {
      setActivePrompt((prev) => {
        if (prev.time_remaining <= 1) {
          setResolutionStatus('TIMED_OUT');
          setAssistantReply('Voice confirmation timed out, bro. Operation cancelled.');
          return { ...prev, time_remaining: 0 };
        }
        return { ...prev, time_remaining: prev.time_remaining - 1 };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [resolutionStatus]);

  const handleResolve = (userInput: string) => {
    const cleaned = userInput.trim().toLowerCase();
    const isAffirmative = /yes|yeah|yep|sure|go ahead|do it|proceed|confirm|haan|kar do/i.test(cleaned);
    const isNegative = /no|nah|nope|cancel|stop|abort|deny|don't|mat kar/i.test(cleaned);

    if (isAffirmative) {
      setResolutionStatus('APPROVED');
      setAssistantReply('Awesome, bro! Proceeding now.');
    } else if (isNegative) {
      setResolutionStatus('DENIED');
      setAssistantReply('No problem, bro! Cancelled.');
    } else {
      setAssistantReply("Sorry bro, didn't catch that. Say 'yes' to proceed or 'no' to cancel.");
    }
  };

  const handleResetPrompt = () => {
    setActivePrompt({
      prompt_id: `conf-voice-${Math.floor(Math.random() * 900) + 100}`,
      tool_name: 'modify_registry_key',
      spoken_question: 'Bro, should I update the Windows graphics hardware acceleration setting?',
      display_summary: 'Modify Windows graphics registry key HKLM\\Software\\Policies',
      tier: 2,
      time_remaining: 60,
    });
    setResolutionStatus('PENDING');
    setAssistantReply('');
    setSpokenInput('');
    setIsListening(true);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 18, 0.92)',
        backdropFilter: 'blur(16px)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        fontFamily: "'Segoe UI Variable Text', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid rgba(56, 189, 248, 0.2)',
          background: 'linear-gradient(90deg, rgba(14, 165, 233, 0.08) 0%, rgba(2, 6, 23, 0.7) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <MicRegular style={{ fontSize: '24px', color: '#38bdf8' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, letterSpacing: '0.5px' }}>
              Conversational Voice Confirmation & Interactive Dispatcher
            </h2>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Milestone 29 Phase 3 • Natural Spoken Prompts & Hands-Free Approval Intent Resolution
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleResetPrompt}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '6px 12px',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            New Sample Prompt
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: 'none',
                borderRadius: '8px',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f0f6fc',
                cursor: 'pointer',
              }}
            >
              <DismissRegular style={{ fontSize: '18px' }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
        {/* Active Spoken Confirmation Card */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(2, 6, 23, 0.95) 100%)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '16px',
            padding: '24px',
            position: 'relative',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  background: 'rgba(245, 158, 11, 0.15)',
                  border: '1px solid #fbbf24',
                  color: '#fbbf24',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontWeight: 700,
                  fontSize: '11px',
                }}
              >
                TIER {activePrompt.tier} CONFIRMATION REQUIRED
              </span>
              <span style={{ fontSize: '12px', color: '#64748b' }}>[{activePrompt.prompt_id}]</span>
            </div>
            <div style={{ fontSize: '12px', color: activePrompt.time_remaining < 15 ? '#ef4444' : '#38bdf8', fontWeight: 600 }}>
              ⏱ {activePrompt.time_remaining}s remaining
            </div>
          </div>

          {/* Large Conversational Speech Bubble */}
          <div
            style={{
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '16px',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', marginBottom: '8px', textTransform: 'uppercase' }}>
              Spoken Voice Prompt
            </div>
            <div style={{ fontSize: '20px', fontWeight: 600, color: '#f8fafc', lineHeight: '1.4' }}>
              "{activePrompt.spoken_question}"
            </div>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '10px' }}>
              <ShieldRegular style={{ verticalAlign: 'middle', marginRight: '6px' }} />
              Action Summary: <strong style={{ color: '#cbd5e1' }}>{activePrompt.display_summary}</strong>
            </div>
          </div>

          {/* Interactive Speech Waveform Animation */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '16px',
              background: 'rgba(2, 6, 23, 0.6)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              marginBottom: '20px',
            }}
          >
            {[18, 32, 48, 24, 60, 36, 52, 28, 44, 20, 36].map((h, i) => (
              <div
                key={i}
                style={{
                  width: '4px',
                  height: isListening && resolutionStatus === 'PENDING' ? `${h}px` : '8px',
                  backgroundColor: resolutionStatus === 'APPROVED' ? '#4ade80' : resolutionStatus === 'DENIED' ? '#ef4444' : '#38bdf8',
                  borderRadius: '2px',
                  transition: 'height 0.2s ease',
                }}
              />
            ))}
            <span style={{ fontSize: '12px', color: '#94a3b8', marginLeft: '12px' }}>
              {resolutionStatus === 'PENDING'
                ? isListening
                  ? 'Listening for voice reply ("Yes" / "No")...'
                  : 'Microphone paused'
                : `Resolved: ${resolutionStatus}`}
            </span>
          </div>

          {/* 1-Click Action Buttons */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <button
              disabled={resolutionStatus !== 'PENDING'}
              onClick={() => handleResolve('yes, go ahead')}
              style={{
                flex: 1,
                padding: '14px',
                borderRadius: '8px',
                background: resolutionStatus === 'PENDING' ? 'linear-gradient(135deg, #16a34a 0%, #15803d 100%)' : 'rgba(255,255,255,0.05)',
                border: 'none',
                color: '#fff',
                fontSize: '15px',
                fontWeight: 600,
                cursor: resolutionStatus === 'PENDING' ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                opacity: resolutionStatus !== 'PENDING' ? 0.5 : 1,
              }}
            >
              <CheckmarkRegular /> Approve & Execute
            </button>

            <button
              disabled={resolutionStatus !== 'PENDING'}
              onClick={() => handleResolve('no, cancel')}
              style={{
                flex: 1,
                padding: '14px',
                borderRadius: '8px',
                background: resolutionStatus === 'PENDING' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontSize: '15px',
                fontWeight: 600,
                cursor: resolutionStatus === 'PENDING' ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                opacity: resolutionStatus !== 'PENDING' ? 0.5 : 1,
              }}
            >
              <DismissRegular /> Deny / Cancel
            </button>
          </div>

          {/* Conversational Spoken Chips & Simulator */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.5)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', marginBottom: '8px', textTransform: 'uppercase' }}>
              Simulate Spoken Audio Reply
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
              {['"Yes, go ahead bro"', '"Do it"', '"Haan kar de"', '"No, cancel that"', '"Don\'t do it"', '"Mat kar"'].map((chip) => (
                <button
                  key={chip}
                  disabled={resolutionStatus !== 'PENDING'}
                  onClick={() => {
                    setSpokenInput(chip.replace(/"/g, ''));
                    handleResolve(chip.replace(/"/g, ''));
                  }}
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    padding: '4px 10px',
                    fontSize: '12px',
                    color: '#cbd5e1',
                    cursor: resolutionStatus === 'PENDING' ? 'pointer' : 'default',
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                placeholder="Type custom spoken reply (e.g. 'sure, proceed')..."
                value={spokenInput}
                onChange={(e) => setSpokenInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleResolve(spokenInput);
                }}
                disabled={resolutionStatus !== 'PENDING'}
                style={{
                  flex: 1,
                  background: 'rgba(2, 6, 23, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: '13px',
                }}
              />
              <button
                disabled={resolutionStatus !== 'PENDING'}
                onClick={() => handleResolve(spokenInput)}
                style={{
                  background: '#38bdf8',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 16px',
                  color: '#020617',
                  fontWeight: 600,
                  fontSize: '12px',
                  cursor: resolutionStatus === 'PENDING' ? 'pointer' : 'default',
                }}
              >
                Send
              </button>
            </div>
          </div>

          {/* Assistant Voice Feedback Output */}
          {assistantReply && (
            <div
              style={{
                marginTop: '16px',
                padding: '12px 16px',
                borderRadius: '8px',
                background: resolutionStatus === 'APPROVED' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${resolutionStatus === 'APPROVED' ? '#22c55e' : '#ef4444'}`,
                color: resolutionStatus === 'APPROVED' ? '#86efac' : '#fca5a5',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              Phenom Voice Response: "{assistantReply}"
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default VoiceConfirmationHUD;
