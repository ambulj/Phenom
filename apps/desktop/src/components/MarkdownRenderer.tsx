import React, { useState } from 'react';
import { CopyRegular, CheckmarkRegular } from '@fluentui/react-icons';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  if (!content) return null;

  // Split by fenced code blocks: ```lang ... ```
  const parts: React.ReactNode[] = [];
  const regex = /```([a-zA-Z0-9_\-\.]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  let blockIdx = 0;
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      const textChunk = content.slice(lastIndex, match.index);
      parts.push(<TextSection key={`text-${blockIdx}-${lastIndex}`} text={textChunk} />);
    }

    const language = match[1]?.trim() || 'code';
    const codeBody = match[2] || '';
    parts.push(
      <CodeBlock key={`code-${blockIdx}`} language={language} code={codeBody} />
    );

    lastIndex = regex.lastIndex;
    blockIdx++;
  }

  if (lastIndex < content.length) {
    parts.push(<TextSection key={`text-end-${lastIndex}`} text={content.slice(lastIndex)} />);
  }

  return <div style={{ lineHeight: 1.6 }}>{parts}</div>;
};

const CodeBlock: React.FC<{ language: string; code: string }> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        margin: '10px 0',
        borderRadius: 8,
        overflow: 'hidden',
        border: '1px solid rgba(0, 229, 255, 0.25)',
        background: '#04070d',
        boxShadow: '0 4px 14px rgba(0, 0, 0, 0.6)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '4px 12px',
          background: 'rgba(13, 20, 36, 0.95)',
          borderBottom: '1px solid rgba(0, 229, 255, 0.15)',
          fontSize: 11,
          fontFamily: 'Consolas, monospace',
          color: '#94a3b8',
        }}
      >
        <span style={{ textTransform: 'uppercase', color: '#00e5ff', fontWeight: 600 }}>
          {language}
        </span>
        <button
          onClick={handleCopy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            background: 'transparent',
            border: 'none',
            color: copied ? '#ccff00' : '#94a3b8',
            cursor: 'pointer',
            fontSize: 11,
            padding: '2px 6px',
            borderRadius: 4,
            transition: 'color 0.2s',
          }}
          title="Copy code to clipboard"
        >
          {copied ? <CheckmarkRegular style={{ fontSize: 13 }} /> : <CopyRegular style={{ fontSize: 13 }} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '12px 14px',
          overflowX: 'auto',
          fontSize: 12,
          fontFamily: 'Consolas, "Fira Code", monospace',
          color: '#e2e8f0',
          lineHeight: 1.5,
        }}
      >
        <code>{code.trim()}</code>
      </pre>
    </div>
  );
};

const TextSection: React.FC<{ text: string }> = ({ text }) => {
  const paragraphs = text.split('\n\n');

  return (
    <>
      {paragraphs.map((p, pIdx) => {
        const trimmed = p.trim();
        if (!trimmed) return null;

        // Render bullet list
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const items = trimmed.split('\n').filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));
          return (
            <ul key={pIdx} style={{ margin: '6px 0', paddingLeft: 20 }}>
              {items.map((it, iIdx) => (
                <li key={iIdx} style={{ margin: '3px 0' }}>
                  <InlineMarkdown text={it.replace(/^[\-\*]\s+/, '')} />
                </li>
              ))}
            </ul>
          );
        }

        return (
          <p key={pIdx} style={{ margin: '6px 0' }}>
            <InlineMarkdown text={trimmed} />
          </p>
        );
      })}
    </>
  );
};

const InlineMarkdown: React.FC<{ text: string }> = ({ text }) => {
  // Bold **text** and inline `code`
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let partIdx = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={partIdx} style={{ color: '#00e5ff', fontWeight: 600 }}>
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={partIdx}
          style={{
            background: 'rgba(0, 229, 255, 0.12)',
            border: '1px solid rgba(0, 229, 255, 0.25)',
            color: '#ccff00',
            padding: '1px 5px',
            borderRadius: 4,
            fontSize: '0.9em',
            fontFamily: 'Consolas, monospace',
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    lastIndex = regex.lastIndex;
    partIdx++;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
};
