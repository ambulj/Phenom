import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@fluentui/react-components';
import { SendRegular, StopRegular } from '@fluentui/react-icons';
import { OrbState } from '../types/protocol';

interface ChatBoxProps {
  orbState: OrbState;
  onSendMessage: (text: string) => void;
  onCancelMessage: () => void;
  streamingText: string;
  isStreaming: boolean;
  isShrunk: boolean;
}

export const ChatBox: React.FC<ChatBoxProps> = ({
  orbState,
  onSendMessage,
  onCancelMessage,
  streamingText,
  isStreaming,
  isShrunk
}) => {
  const [inputText, setInputText] = useState('');
  const responseEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    responseEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamingText]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming || orbState === 'halted') return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 32,
        left: isShrunk ? '40%' : '50%',
        transform: 'translateX(-50%)',
        width: '90%',
        maxWidth: 720,
        zIndex: 15,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        transition: 'all 0.4s ease'
      }}
    >
      {/* Streaming Response Bubble */}
      {streamingText && (
        <div
          style={{
            maxHeight: 240,
            overflowY: 'auto',
            background: 'rgba(15, 23, 42, 0.88)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(14px)',
            borderRadius: 16,
            padding: '16px 20px',
            fontSize: 14,
            lineHeight: 1.6,
            color: '#e2e8f0',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
          }}
        >
          <div style={{ whiteSpace: 'pre-wrap' }}>{streamingText}</div>
          <div ref={responseEndRef} />
        </div>
      )}

      {/* Input Bar */}
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'rgba(17, 24, 39, 0.9)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 9999,
          padding: '8px 16px',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.5)'
        }}
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={
            orbState === 'halted'
              ? 'Phenom is halted. Click Resume above to proceed.'
              : 'Ask Phenom anything...'
          }
          disabled={isStreaming || orbState === 'halted'}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#f8fafc',
            fontSize: 15,
            padding: '8px 4px'
          }}
        />

        {isStreaming ? (
          <Button
            appearance="subtle"
            icon={<StopRegular />}
            onClick={onCancelMessage}
            style={{ color: '#ef4444' }}
          >
            Cancel
          </Button>
        ) : (
          <Button
            appearance="primary"
            icon={<SendRegular />}
            onClick={() => handleSubmit()}
            disabled={!inputText.trim() || orbState === 'halted'}
          >
            Send
          </Button>
        )}
      </form>
    </div>
  );
};
