import React, { useState, useEffect } from 'react';
import {
  MicRegular,
  WindowRegular,
  EyeRegular,
  CodeRegular,
  DismissRegular,
  ArrowSyncRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface MultimodalFusionHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const MultimodalFusionHUD: React.FC<MultimodalFusionHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [query, setQuery] = useState<string>('Explain what this function does');
  const [activeApp, setActiveApp] = useState<string>('Visual Studio Code');
  const [windowTitle, setWindowTitle] = useState<string>('multimodal_fuser.py — Phenom');
  const [resolvedSymbol, setResolvedSymbol] = useState<{
    name: string;
    kind: string;
    file_path: string;
    line: number;
    confidence: number;
  }>({
    name: 'fuse_context',
    kind: 'method',
    file_path: 'services/backend/fusion/multimodal_fuser.py',
    line: 42,
    confidence: 0.94
  });

  const [promptPreview, setPromptPreview] = useState<string>(
    '=== MULTIMODAL CONTEXT FUSION ===\n' +
    'Active Window: Visual Studio Code - multimodal_fuser.py — Phenom\n' +
    'Domain: CODING\n' +
    'Deictic Resolution: Resolved on-screen reference to method \'fuse_context\' in services/backend/fusion/multimodal_fuser.py:42 (Confidence: 0.94)\n' +
    'Signature: def fuse_context(self, query: str, active_app: str = ...) -> FusedContext\n' +
    '================================='
  );

  useEffect(() => {
    if (externalEvent?.type === 'fusion.updated' && externalEvent.payload) {
      if (externalEvent.payload.active_app) setActiveApp(externalEvent.payload.active_app);
      if (externalEvent.payload.window_title) setWindowTitle(externalEvent.payload.window_title);
      if (externalEvent.payload.deictic) {
        setResolvedSymbol({
          name: externalEvent.payload.deictic.symbol_name || 'None',
          kind: externalEvent.payload.deictic.kind || 'unknown',
          file_path: externalEvent.payload.deictic.file_path || '',
          line: externalEvent.payload.deictic.line_number || 1,
          confidence: externalEvent.payload.deictic.confidence || 0.0
        });
      }
      if (externalEvent.payload.formatted_context_prompt) {
        setPromptPreview(externalEvent.payload.formatted_context_prompt);
      }
    }
  }, [externalEvent]);

  const handleSimulateFusion = () => {
    const isClass = query.toLowerCase().includes('class');
    const symName = isClass ? 'MultimodalFuser' : 'fuse_context';
    const symKind = isClass ? 'class' : 'method';
    const symLine = isClass ? 35 : 42;

    setResolvedSymbol({
      name: symName,
      kind: symKind,
      file_path: 'services/backend/fusion/multimodal_fuser.py',
      line: symLine,
      confidence: 0.96
    });

    setPromptPreview(
      '=== MULTIMODAL CONTEXT FUSION ===\n' +
      `Active Window: ${activeApp} - ${windowTitle}\n` +
      'Domain: CODING\n' +
      `Deictic Resolution: Resolved on-screen reference to ${symKind} '${symName}' in services/backend/fusion/multimodal_fuser.py:${symLine} (Confidence: 0.96)\n` +
      `Signature: ${isClass ? 'class MultimodalFuser' : 'def fuse_context(self, query: str, ...)'}\n` +
      '================================='
    );

    sendMessage?.({
      type: 'fusion.simulate',
      payload: { query }
    });
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'rgba(10, 14, 23, 0.96)',
      backdropFilter: 'blur(20px)',
      color: '#e2e8f0',
      fontFamily: 'Segoe UI Variable, -apple-system, sans-serif',
      boxSizing: 'border-box',
      borderLeft: '1px solid rgba(0, 243, 255, 0.2)'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <SparkleRegular style={{ color: '#00f3ff', fontSize: '20px' }} />
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px', letterSpacing: '0.5px' }}>
              MULTIMODAL CONTEXT FUSION & DEICTIC GROUNDING
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Spoken Intent • Foreground Window • OCR Tokens • AST Symbol Linkage (&lt; 15ms)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleSimulateFusion}
            style={{
              background: 'rgba(0, 243, 255, 0.1)',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              color: '#00f3ff',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ArrowSyncRegular style={{ fontSize: '14px' }} />
            Re-Fuse Streams
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <DismissRegular style={{ fontSize: '18px' }} />
            </button>
          )}
        </div>
      </div>

      {/* 4-Channel Matrix */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        padding: '16px 20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        {/* Channel 1: Voice Intent */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: '8px',
          padding: '12px',
          border: '1px solid rgba(0, 243, 255, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#00f3ff', fontSize: '11px', fontWeight: 600 }}>
            <MicRegular style={{ fontSize: '14px' }} />
            1. VOICE STREAM
          </div>
          <div style={{ fontSize: '12px', fontWeight: 500, color: '#f8fafc', marginTop: '6px' }}>
            "{query}"
          </div>
          <div style={{ fontSize: '10px', color: '#30d158', marginTop: '4px' }}>
            ● Whisper In-RAM Latency: 2.1ms
          </div>
        </div>

        {/* Channel 2: Active Window */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: '8px',
          padding: '12px',
          border: '1px solid rgba(56, 189, 248, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
            <WindowRegular style={{ fontSize: '14px' }} />
            2. FOREGROUND APP
          </div>
          <div style={{ fontSize: '12px', fontWeight: 500, color: '#f8fafc', marginTop: '6px' }}>
            {activeApp}
          </div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {windowTitle}
          </div>
        </div>

        {/* Channel 3: Screen OCR */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: '8px',
          padding: '12px',
          border: '1px solid rgba(192, 132, 252, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#c084fc', fontSize: '11px', fontWeight: 600 }}>
            <EyeRegular style={{ fontSize: '14px' }} />
            3. SCREEN VISION OCR
          </div>
          <div style={{ fontSize: '12px', fontWeight: 500, color: '#f8fafc', marginTop: '6px' }}>
            Active Viewport Tokens
          </div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
            Visible: def fuse_context(...)
          </div>
        </div>

        {/* Channel 4: AST Grounding */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: '8px',
          padding: '12px',
          border: '1px solid rgba(48, 209, 88, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#30d158', fontSize: '11px', fontWeight: 600 }}>
            <CodeRegular style={{ fontSize: '14px' }} />
            4. AST CODE SYMBOL
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#30d158', marginTop: '6px' }}>
            {resolvedSymbol.name} ({resolvedSymbol.kind})
          </div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
            Confidence: {(resolvedSymbol.confidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Main Area: Query Tester & Enriched Prompt Block */}
      <div style={{
        flex: 1,
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        minHeight: 0,
        overflowY: 'auto'
      }}>
        {/* Query Input */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            placeholder="Type or simulate spoken voice query e.g. 'Refactor this function' or 'Explain this class'..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSimulateFusion()}
            style={{
              flex: 1,
              padding: '8px 12px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(0, 243, 255, 0.3)',
              borderRadius: '6px',
              color: '#f8fafc',
              fontSize: '13px',
              outline: 'none'
            }}
          />
          <button
            onClick={handleSimulateFusion}
            style={{
              padding: '8px 16px',
              background: 'rgba(0, 243, 255, 0.2)',
              border: '1px solid #00f3ff',
              borderRadius: '6px',
              color: '#00f3ff',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Fuse & Ground
          </button>
        </div>

        {/* Enriched Prompt Block */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '8px' }}>
            SYNTHESIZED MULTIMODAL PROMPT INJECTION CONTEXT:
          </div>
          <pre style={{
            flex: 1,
            margin: 0,
            padding: '14px',
            background: 'rgba(0, 0, 0, 0.4)',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            color: '#a5f3fc',
            fontFamily: 'Consolas, monospace',
            fontSize: '12px',
            lineHeight: 1.6,
            overflowX: 'auto',
            whiteSpace: 'pre-wrap'
          }}>
            {promptPreview}
          </pre>
        </div>
      </div>
    </div>
  );
};
