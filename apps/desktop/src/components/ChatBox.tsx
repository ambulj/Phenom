import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@fluentui/react-components';
import {
  SendRegular,
  StopRegular,
  EyeRegular,
  NewsRegular,
  MoneyRegular,
  FolderOpenRegular,
  DeleteRegular,
  MicRegular,
  PlayRegular,
  DocumentPdfRegular
} from '@fluentui/react-icons';
import { OrbState } from '../types/protocol';

interface ChatMessage {
  id: string;
  role: string;
  content: string;
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

export const ChatBox: React.FC<ChatBoxProps> = ({
  orbState,
  onSendMessage,
  onCancelMessage,
  onClearHistory,
  onTriggerVoice,
  streamingText,
  isStreaming,
  isShrunk,
  messages = []
}) => {
  const [inputText, setInputText] = useState('');
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

  const handleQuickPrompt = (promptText: string) => {
    if (isStreaming || orbState === 'halted') return;
    onSendMessage(promptText);
  };

  const renderContentFormatted = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('[Phenom Safety Gate:') || line.startsWith('[Action Blocked:')) {
        return (
          <div
            key={idx}
            style={{
              display: 'inline-block',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#fca5a5',
              padding: '2px 8px',
              borderRadius: 6,
              fontSize: 12,
              fontFamily: 'monospace',
              margin: '4px 0'
            }}
          >
            🛡️ {line}
          </div>
        );
      }
      if (line.startsWith('[Tool ') && line.includes('Result:')) {
        return (
          <div
            key={idx}
            style={{
              display: 'inline-block',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#6ee7b7',
              padding: '2px 8px',
              borderRadius: 6,
              fontSize: 12,
              fontFamily: 'monospace',
              margin: '4px 0'
            }}
          >
            ✓ {line}
          </div>
        );
      }
      return <div key={idx}>{line}</div>;
    });
  };

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
        gap: 12,
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
    >
      {/* Scrollable Conversation Stream HUD */}
      {hasHistory ? (
        <div
          style={{
            maxHeight: '45vh',
            minHeight: 120,
            overflowY: 'auto',
            background: 'rgba(9, 14, 26, 0.85)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            backdropFilter: 'blur(20px)',
            borderRadius: 20,
            padding: '20px 24px',
            boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: 14
          }}
        >
          {messages.map((m) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  gap: 4
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px',
                    fontWeight: 600,
                    color: isUser ? '#60a5fa' : '#38bdf8',
                    paddingLeft: isUser ? 0 : 4,
                    paddingRight: isUser ? 4 : 0
                  }}
                >
                  {isUser ? 'You' : '⚡ Phenom'}
                </div>
                <div
                  style={{
                    maxWidth: '85%',
                    background: isUser
                      ? 'linear-gradient(135deg, rgba(37, 99, 235, 0.35), rgba(30, 64, 175, 0.45))'
                      : 'rgba(15, 23, 42, 0.75)',
                    border: isUser
                      ? '1px solid rgba(96, 165, 250, 0.4)'
                      : '1px solid rgba(56, 189, 248, 0.25)',
                    borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    padding: '12px 18px',
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: '#f1f5f9',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
                  }}
                >
                  {renderContentFormatted(m.content)}
                </div>
              </div>
            );
          })}

          {/* Active Live Token Streaming Bubble */}
          {isStreaming && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: 4
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  textTransform: 'uppercase',
                  letterSpacing: '0.6px',
                  fontWeight: 600,
                  color: '#38bdf8',
                  paddingLeft: 4,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <span
                  style={{
                    display: 'inline-block',
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: '#38bdf8',
                    boxShadow: '0 0 8px #38bdf8'
                  }}
                />
                ⚡ Phenom Replying...
              </div>
              <div
                style={{
                  maxWidth: '85%',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  borderRadius: '16px 16px 16px 4px',
                  padding: '12px 18px',
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: '#f8fafc',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  boxShadow: '0 0 20px rgba(56, 189, 248, 0.15)'
                }}
              >
                {streamingText ? (
                  renderContentFormatted(streamingText)
                ) : (
                  <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>
                    Formulating response...
                  </span>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      ) : null}

      {/* Quick Action Chips */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          overflowX: 'auto',
          paddingBottom: 2
        }}
      >
        <button
          onClick={() => handleQuickPrompt("What's on my screen right now? Inspect active window and report any errors.")}
          style={{
            background: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            color: '#7dd3fc',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(56, 189, 248, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(56, 189, 248, 0.12)')}
        >
          <EyeRegular fontSize={14} /> ⚡ Inspect Screen
        </button>

        <button
          onClick={() => handleQuickPrompt("Give me a brief summary of today's tech news")}
          style={{
            background: 'rgba(168, 85, 247, 0.12)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            color: '#d8b4fe',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(168, 85, 247, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(168, 85, 247, 0.12)')}
        >
          <NewsRegular fontSize={14} /> 📰 Tech News
        </button>

        <button
          onClick={() => handleQuickPrompt("What are the current stock market quotes for my watchlist?")}
          style={{
            background: 'rgba(34, 197, 94, 0.12)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            color: '#86efac',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(34, 197, 94, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(34, 197, 94, 0.12)')}
        >
          <MoneyRegular fontSize={14} /> 📊 Markets
        </button>

        <button
          onClick={() => handleQuickPrompt("Organize my Downloads folder and preview files to tidy")}
          style={{
            background: 'rgba(234, 179, 8, 0.12)',
            border: '1px solid rgba(234, 179, 8, 0.3)',
            color: '#fde047',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(234, 179, 8, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(234, 179, 8, 0.12)')}
        >
          <FolderOpenRegular fontSize={14} /> 🧹 Tidy Downloads
        </button>

        <button
          onClick={() => handleQuickPrompt("Toggle media play/pause on Spotify")}
          style={{
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#6ee7b7',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(16, 185, 129, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(16, 185, 129, 0.12)')}
        >
          <PlayRegular fontSize={14} /> 🎵 Play/Pause
        </button>

        <button
          onClick={() => handleQuickPrompt("Split pages from a PDF document")}
          style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(239, 68, 68, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)')}
        >
          <DocumentPdfRegular fontSize={14} /> 📄 Split PDF
        </button>

        <button
          onClick={() => handleQuickPrompt("Calculate math formula: sqrt(144) + 15 * 8")}
          style={{
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#fda4af',
            padding: '6px 12px',
            borderRadius: 9999,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(244, 63, 94, 0.22)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(244, 63, 94, 0.12)')}
        >
          🧮 Math Calc
        </button>

        {hasHistory && onClearHistory && (
          <button
            onClick={onClearHistory}
            title="Clear Chat Stream"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              color: '#f87171',
              padding: '6px 10px',
              borderRadius: 9999,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              marginLeft: 'auto'
            }}
          >
            <DeleteRegular fontSize={13} /> Clear
          </button>
        )}
      </div>

      {/* Cyberpunk Glass Input Bar */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'rgba(10, 15, 30, 0.92)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          borderRadius: 9999,
          padding: '8px 18px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.12)',
          transition: 'border 0.2s ease, box-shadow 0.2s ease'
        }}
      >
        <span style={{ color: '#38bdf8', fontSize: 16 }}>⚡</span>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={
            orbState === 'halted'
              ? 'Phenom is halted. Click Resume in the top bar to continue.'
              : orbState === 'listening'
              ? '🎙️ Listening to your voice... Speak your command now!'
              : 'Ask Phenom anything (or say "Hey Jarvis")...'
          }
          disabled={isStreaming || orbState === 'halted'}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#f8fafc',
            fontSize: 14,
            padding: '8px 4px'
          }}
        />

        {onTriggerVoice && (
          <Button
            appearance="subtle"
            icon={<MicRegular style={{ color: orbState === 'listening' ? '#38bdf8' : '#94a3b8' }} />}
            onClick={onTriggerVoice}
            title="Click to speak (or say 'Hey Jarvis')"
            style={{
              background: orbState === 'listening' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
              borderRadius: '50%',
              minWidth: 36,
              width: 36,
              height: 36,
              padding: 0,
              boxShadow: orbState === 'listening' ? '0 0 12px #38bdf8' : 'none'
            }}
          />
        )}

        {isStreaming ? (
          <Button
            appearance="subtle"
            icon={<StopRegular />}
            onClick={onCancelMessage}
            style={{ color: '#ef4444' }}
          >
            Stop
          </Button>
        ) : (
          <Button
            appearance="primary"
            icon={<SendRegular />}
            onClick={() => handleSubmit()}
            disabled={!inputText.trim() || orbState === 'halted'}
            style={{
              background: 'linear-gradient(135deg, #0284c7, #2563eb)',
              border: 'none',
              borderRadius: 9999,
              padding: '6px 16px'
            }}
          >
            Send
          </Button>
        )}
      </form>
    </div>
  );
};
