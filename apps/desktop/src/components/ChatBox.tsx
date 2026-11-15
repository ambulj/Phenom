import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@fluentui/react-components';
import {
  SendRegular,
  StopRegular,
  MicRegular,
  AttachRegular,
  CopyRegular,
  ArrowResetRegular,
  EditRegular,
  PinRegular,
  Speaker2Regular,
  CheckmarkRegular,
  DismissRegular
} from '@fluentui/react-icons';
import { OrbState } from '../types/protocol';
import { MarkdownRenderer } from './MarkdownRenderer';

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  pinned?: boolean;
}

interface ChatBoxProps {
  orbState: OrbState;
  onSendMessage: (text: string) => void;
  onCancelMessage: () => void;
  onClearHistory?: () => void;
  onTriggerVoice?: () => void;
  streamingText: string;
  isStreaming: boolean;
  isShrunk: boolean;
  messages?: ChatMessage[];
}

export function sanitizeChatText(rawText: string): string {
  if (!rawText) return '';
  let cleaned = rawText;
  // 1. Strip Tool header lines
  cleaned = cleaned.replace(/\*{1,2}\s*Tool\s*:\s*\*{1,2}\s*[`'"]?[a-zA-Z0-9_\-\.]+(?:\([^\)]*\))?[`'"]?/gi, '');
  // 2. Strip JSON execution block header lines
  cleaned = cleaned.replace(/\*{1,2}\s*JSON\s+Execution\s+Block\s*:\s*\*{1,2}/gi, '');
  // 3. Strip fenced json code blocks containing "tool"
  cleaned = cleaned.replace(/```(?:json)?\s*\{\s*["']tool["']\s*:[\s\S]*?\}\s*```/gi, '');
  // 4. Strip raw tool JSON objects
  cleaned = cleaned.replace(/\{\s*["']tool["']\s*:\s*["'][a-zA-Z0-9_\-\.]+["']\s*,\s*["']args["']\s*:[\s\S]*?\}/gi, '');
  // 5. Strip launch explanation boilerplates
  cleaned = cleaned.replace(/This command will launch (?:the )?[^\n\.]+\.?/gi, '');
  // 6. Strip [Action Executed: ...] stamps
  cleaned = cleaned.replace(/\[Action\s+Executed\s*:\s*[^\]]+\]/gi, '');
  // 7. Strip [Phenom Safety Gate: Requesting ...] stamps for clean conversational reading
  cleaned = cleaned.replace(/\[Phenom Safety Gate:\s*Requesting\s+[a-zA-Z0-9_]+[^\]]*\]/gi, '');
  // 8. Strip emoji-badge [Tool ... Result] lines (Task 6E.3)
  cleaned = cleaned.replace(/\[Tool\s+[a-zA-Z0-9_]+\s+Result:\s*[^\]]*\]/gi, '');
  // 9. Clean up stray markdown code fences or orphaned "json" labels
  cleaned = cleaned.replace(/^\s*```(?:json)?\s*$/gm, '');
  cleaned = cleaned.replace(/^\s*json\s*$/gm, '');
  // 10. Clean up multiple blank lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  return cleaned;
}

export const ChatBox: React.FC<ChatBoxProps> = ({
  orbState,
  onSendMessage,
  onCancelMessage,
  onTriggerVoice,
  streamingText,
  isStreaming,
  isShrunk,
  messages = []
}) => {
  const [inputText, setInputText] = useState('');
  const [pinnedMessageId, setPinnedMessageId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamingText, messages.length]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming || orbState === 'halted') return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleCopyMessage = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleReplaySpoken = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(sanitizeChatText(text));
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Local-only file attached notice
      const prompt = `[Local Attachment: ${file.name}] Please summarize this document using local-only intelligence.`;
      setInputText(prompt);
    }
  };

  const pinnedMsg = messages.find((m) => m.id === pinnedMessageId);
  const hasHistory = messages.length > 0 || streamingText.length > 0;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 24,
        left: isShrunk ? '42%' : '50%',
        transform: 'translateX(-50%)',
        width: '94%',
        maxWidth: 820,
        zIndex: 15,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      {/* Pinned Message Bar (Task 6E.3) */}
      {pinnedMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(0, 229, 255, 0.15)',
            border: '1px solid rgba(0, 229, 255, 0.4)',
            backdropFilter: 'blur(16px)',
            borderRadius: 12,
            padding: '8px 14px',
            fontSize: 12,
            color: '#00e5ff',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
            <PinRegular style={{ fontSize: 14 }} />
            <span style={{ fontWeight: 600 }}>Pinned:</span>
            <span style={{ color: '#f8fafc', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
              {sanitizeChatText(pinnedMsg.content).slice(0, 80)}...
            </span>
          </div>
          <button
            onClick={() => setPinnedMessageId(null)}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <DismissRegular style={{ fontSize: 13 }} />
          </button>
        </div>
      )}

      {/* Scrollable Conversation Stream HUD */}
      {hasHistory && (
        <div
          style={{
            maxHeight: '45vh',
            minHeight: 120,
            overflowY: 'auto',
            background: 'rgba(8, 15, 28, 0.88)',
            border: '1px solid rgba(0, 229, 255, 0.25)',
            backdropFilter: 'blur(20px)',
            borderRadius: 20,
            padding: '18px 22px',
            boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 229, 255, 0.14)',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
          }}
        >
          {messages.map((m) => {
            const isUser = m.role === 'user';
            const cleaned = sanitizeChatText(m.content);
            if (!cleaned) return null;

            return (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  gap: 4,
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px',
                    fontWeight: 700,
                    color: isUser ? '#00e5ff' : '#ccff00',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span>{isUser ? 'Abhi' : 'Phenom'}</span>
                  {m.id === pinnedMessageId && <PinRegular style={{ fontSize: 11, color: '#00e5ff' }} />}
                </div>

                <div
                  style={{
                    maxWidth: '85%',
                    padding: '10px 16px',
                    borderRadius: 14,
                    fontSize: 13,
                    lineHeight: 1.5,
                    background: isUser
                      ? 'linear-gradient(135deg, rgba(0, 229, 255, 0.18), rgba(0, 82, 255, 0.25))'
                      : 'rgba(4, 7, 13, 0.85)',
                    border: isUser ? '1px solid rgba(0, 229, 255, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#f8fafc',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
                  }}
                >
                  <MarkdownRenderer content={cleaned} />
                </div>

                {/* Message Actions: Copy, Retry, Edit, Pin, Replay (Task 6E.3) */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 11,
                    color: '#64748b',
                    padding: '2px 6px',
                  }}
                >
                  <button
                    onClick={() => handleCopyMessage(cleaned, m.id)}
                    style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                    title="Copy message"
                  >
                    {copiedId === m.id ? <CheckmarkRegular style={{ fontSize: 12, color: '#ccff00' }} /> : <CopyRegular style={{ fontSize: 12 }} />}
                    <span>{copiedId === m.id ? 'Copied' : 'Copy'}</span>
                  </button>

                  {isUser && (
                    <>
                      <button
                        onClick={() => onSendMessage(m.content)}
                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                        title="Retry this prompt"
                      >
                        <ArrowResetRegular style={{ fontSize: 12 }} />
                        <span>Retry</span>
                      </button>
                      <button
                        onClick={() => setInputText(m.content)}
                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                        title="Edit into input"
                      >
                        <EditRegular style={{ fontSize: 12 }} />
                        <span>Edit</span>
                      </button>
                    </>
                  )}

                  {!isUser && (
                    <button
                      onClick={() => handleReplaySpoken(cleaned)}
                      style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                      title="Replay spoken reply"
                    >
                      <Speaker2Regular style={{ fontSize: 12 }} />
                      <span>Speak</span>
                    </button>
                  )}

                  <button
                    onClick={() => setPinnedMessageId(pinnedMessageId === m.id ? null : m.id)}
                    style={{ background: 'transparent', border: 'none', color: pinnedMessageId === m.id ? '#00e5ff' : '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                    title="Pin message"
                  >
                    <PinRegular style={{ fontSize: 12 }} />
                    <span>{pinnedMessageId === m.id ? 'Unpin' : 'Pin'}</span>
                  </button>
                </div>
              </div>
            );
          })}

          {/* Streaming reply token stream */}
          {streamingText && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: 700, color: '#ccff00' }}>
                Phenom (Streaming...)
              </div>
              <div
                style={{
                  maxWidth: '85%',
                  padding: '10px 16px',
                  borderRadius: 14,
                  fontSize: 13,
                  lineHeight: 1.5,
                  background: 'rgba(4, 7, 13, 0.95)',
                  border: '1px solid rgba(204, 255, 0, 0.4)',
                  color: '#f8fafc',
                }}
              >
                <MarkdownRenderer content={sanitizeChatText(streamingText)} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Glass Bar */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'rgba(8, 15, 28, 0.92)',
          border: '1px solid rgba(0, 229, 255, 0.35)',
          backdropFilter: 'blur(24px)',
          borderRadius: 24,
          padding: '6px 12px 6px 16px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.7), 0 0 16px rgba(0, 229, 255, 0.15)',
        }}
      >
        {/* Hidden File Input for Local Attachments (Task 6E.3) */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileAttach}
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94a3b8',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
            alignItems: 'center',
          }}
          title="Attach local file (local-only intelligence)"
        >
          <AttachRegular style={{ fontSize: 18 }} />
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={orbState === 'halted' ? 'Guardian halted. Click Resume to chat...' : 'Ask Phenom or command desktop...'}
          disabled={orbState === 'halted'}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#f8fafc',
            fontSize: 14,
            outline: 'none',
          }}
        />

        {isStreaming ? (
          <Button
            appearance="subtle"
            icon={<StopRegular style={{ color: '#ef4444' }} />}
            onClick={onCancelMessage}
            title="Stop generation"
          />
        ) : (
          <Button
            type="submit"
            appearance="subtle"
            icon={<SendRegular style={{ color: inputText.trim() ? '#00e5ff' : '#64748b' }} />}
            disabled={!inputText.trim() || orbState === 'halted'}
          />
        )}

        {onTriggerVoice && (
          <Button
            type="button"
            appearance="subtle"
            icon={<MicRegular style={{ color: orbState === 'listening' ? '#ccff00' : '#94a3b8' }} />}
            onClick={onTriggerVoice}
            title="Voice push-to-talk"
          />
        )}
      </form>
    </div>
  );
};
