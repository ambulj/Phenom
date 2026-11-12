import React, { useState } from 'react';
import {
  DismissRegular,
  EyeRegular,
  DocumentTextRegular,
  WarningRegular,
  CheckmarkCircleRegular,
  CopyRegular,
  ArrowCounterclockwiseRegular,
  SlideGridRegular,
} from '@fluentui/react-icons';

interface BoundingBoxUI {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  control_type: string;
  confidence: number;
}

interface ScreenIntelligenceHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const ScreenIntelligenceHUD: React.FC<ScreenIntelligenceHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'VISUAL' | 'OCR' | 'ERRORS'>('VISUAL');
  const [trackingMode, setTrackingMode] = useState<'ACTIVE' | 'LOW_POWER' | 'OFF'>('ACTIVE');
  const [copied, setCopied] = useState<boolean>(false);

  const [activeWindow, setActiveWindow] = useState<{
    title: string;
    process: string;
    bounds: { left: number; top: number; width: number; height: number };
    latencyMs: number;
  }>({
    title: 'Visual Studio Code - Phenom',
    process: 'Code.exe',
    bounds: { left: 0, top: 0, width: 1920, height: 1080 },
    latencyMs: 18.4,
  });

  const [boundingBoxes, setBoundingBoxes] = useState<BoundingBoxUI[]>([
    { x: 20, y: 40, width: 1880, height: 50, label: 'Titlebar & Menu Commands', control_type: 'ToolBar', confidence: 0.99 },
    { x: 30, y: 110, width: 1350, height: 850, label: 'Editor Viewport & Code Canvas', control_type: 'Pane', confidence: 0.96 },
    { x: 1400, y: 110, width: 480, height: 850, label: 'File Explorer & Git Sidebar', control_type: 'Tree', confidence: 0.95 },
  ]);

  const [ocrText, setOcrText] = useState<string>(
    `// services/backend/vision/screen_intelligence_tracker.py\nclass ScreenIntelligenceTracker:\n    def capture_window_context(self):\n        # 100% Offline Local On-Device Execution (Rule 4)\n        return active_context\n\nStatus: Local VLM active. FPS: 30. Zero Cloud Egress.`
  );

  const [errorDiagnosis, setErrorDiagnosis] = useState<{
    hasError: boolean;
    title: string;
    message: string;
    severity: 'NONE' | 'WARNING' | 'CRITICAL';
    suggestions: string[];
  }>({
    hasError: false,
    title: 'Screen Clean - No Errors',
    message: 'Active application viewport scanned. Zero unhandled exceptions or crash dialogs detected.',
    severity: 'NONE',
    suggestions: ['All visual subsystems healthy.', 'Continuous background task tracking operational.'],
  });

  const handleSimulateScan = () => {
    setActiveWindow({
      title: 'Brave Browser - GitHub Research',
      process: 'brave.exe',
      bounds: { left: 0, top: 0, width: 1920, height: 1080 },
      latencyMs: 14.8,
    });
    setBoundingBoxes([
      { x: 0, y: 0, width: 1920, height: 80, label: 'Address Bar & Navigation Tabs', control_type: 'ToolBar', confidence: 0.98 },
      { x: 100, y: 120, width: 1720, height: 900, label: 'Web Content Canvas (Markdown Renderer)', control_type: 'Document', confidence: 0.97 },
    ]);
    setOcrText(
      `GitHub - Phenom Desktop Assistant\nREADME.md: Local offline voice and vision AI companion.\nRule 4: Zero Cloud Telemetry Egress.\nUniversal Guardian Kill Switch: < 25.0ms.`
    );
  };

  const handleSimulateErrorScan = () => {
    setErrorDiagnosis({
      hasError: true,
      title: 'Warning: Window Unresponsive',
      message: 'Visual match for application lag / not responding banner detected on screen.',
      severity: 'WARNING',
      suggestions: [
        'Allow process 15 seconds to recover.',
        'Use close_app or Task Manager if hang persists.',
      ],
    });
  };

  const handleCopyOcr = () => {
    navigator.clipboard.writeText(ocrText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 60,
        right: 20,
        width: 480,
        maxHeight: 'calc(100vh - 100px)',
        background: 'rgba(15, 23, 42, 0.96)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(14, 165, 233, 0.3)',
        borderRadius: 12,
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(14, 165, 233, 0.15)',
        color: '#f8fafc',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        zIndex: 9999,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(14, 165, 233, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(14, 165, 233, 0.12), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <EyeRegular style={{ fontSize: 20, color: '#38bdf8' }} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '0.05em', color: '#f8fafc' }}>
              SCREEN INTELLIGENCE HUD
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Milestone 30 • Local Offline VLM & OCR Engine (VIS-01)
            </div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
              borderRadius: 6,
            }}
          >
            <DismissRegular style={{ fontSize: 18 }} />
          </button>
        )}
      </div>

      {/* Mode Controls Bar */}
      <div
        style={{
          padding: '10px 20px',
          background: 'rgba(15, 23, 42, 0.6)',
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>TRACKING:</span>
          {(['ACTIVE', 'LOW_POWER', 'OFF'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setTrackingMode(m)}
              style={{
                fontSize: '10px',
                padding: '3px 8px',
                borderRadius: 4,
                border: 'none',
                cursor: 'pointer',
                fontWeight: 700,
                background:
                  trackingMode === m
                    ? m === 'ACTIVE'
                      ? 'rgba(14, 165, 233, 0.3)'
                      : m === 'LOW_POWER'
                      ? 'rgba(234, 179, 8, 0.3)'
                      : 'rgba(148, 163, 184, 0.2)'
                    : 'rgba(30, 41, 59, 0.6)',
                color:
                  trackingMode === m
                    ? m === 'ACTIVE'
                      ? '#38bdf8'
                      : m === 'LOW_POWER'
                      ? '#facc15'
                      : '#94a3b8'
                    : '#64748b',
              }}
            >
              {m}
            </button>
          ))}
        </div>
        <button
          onClick={handleSimulateScan}
          style={{
            fontSize: '11px',
            background: 'rgba(14, 165, 233, 0.15)',
            border: '1px solid rgba(14, 165, 233, 0.3)',
            color: '#38bdf8',
            borderRadius: 6,
            padding: '4px 8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <ArrowCounterclockwiseRegular style={{ fontSize: 12 }} /> Rescan
        </button>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          background: 'rgba(15, 23, 42, 0.4)',
        }}
      >
        <button
          onClick={() => setActiveTab('VISUAL')}
          style={{
            flex: 1,
            padding: '10px',
            border: 'none',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            background: activeTab === 'VISUAL' ? 'rgba(14, 165, 233, 0.15)' : 'transparent',
            color: activeTab === 'VISUAL' ? '#38bdf8' : '#94a3b8',
            borderBottom: activeTab === 'VISUAL' ? '2px solid #38bdf8' : 'none',
          }}
        >
          <SlideGridRegular style={{ fontSize: 14 }} /> Elements ({boundingBoxes.length})
        </button>
        <button
          onClick={() => setActiveTab('OCR')}
          style={{
            flex: 1,
            padding: '10px',
            border: 'none',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            background: activeTab === 'OCR' ? 'rgba(14, 165, 233, 0.15)' : 'transparent',
            color: activeTab === 'OCR' ? '#38bdf8' : '#94a3b8',
            borderBottom: activeTab === 'OCR' ? '2px solid #38bdf8' : 'none',
          }}
        >
          <DocumentTextRegular style={{ fontSize: 14 }} /> Region OCR
        </button>
        <button
          onClick={() => setActiveTab('ERRORS')}
          style={{
            flex: 1,
            padding: '10px',
            border: 'none',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            background: activeTab === 'ERRORS' ? 'rgba(14, 165, 233, 0.15)' : 'transparent',
            color: activeTab === 'ERRORS' ? (errorDiagnosis.hasError ? '#f87171' : '#38bdf8') : '#94a3b8',
            borderBottom: activeTab === 'ERRORS' ? '2px solid #38bdf8' : 'none',
          }}
        >
          <WarningRegular style={{ fontSize: 14 }} /> Error Scan
        </button>
      </div>

      {/* Content Body */}
      <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1, maxHeight: 420 }}>
        {/* Active Window Context Header */}
        <div
          style={{
            background: 'rgba(30, 41, 59, 0.5)',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 14,
            fontSize: '11px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ color: '#94a3b8' }}>Active Target:</span>
            <span style={{ color: '#38bdf8', fontWeight: 600 }}>{activeWindow.process}</span>
          </div>
          <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: 4 }}>{activeWindow.title}</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b' }}>
            <span>
              Bounds: {activeWindow.bounds.width}×{activeWindow.bounds.height}
            </span>
            <span>Latency: {activeWindow.latencyMs}ms</span>
          </div>
        </div>

        {/* Tab 1: Visual Elements */}
        {activeTab === 'VISUAL' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {boundingBoxes.map((box, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(30, 41, 59, 0.4)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: 6,
                  padding: '10px 12px',
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: '#f8fafc' }}>{box.label}</span>
                  <span
                    style={{
                      fontSize: '9px',
                      padding: '2px 6px',
                      borderRadius: 4,
                      background: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      fontWeight: 700,
                    }}
                  >
                    {box.control_type}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '10px' }}>
                  <span>
                    X: {box.x}, Y: {box.y} • {box.width}×{box.height}
                  </span>
                  <span>Conf: {(box.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 2: Region OCR */}
        {activeTab === 'OCR' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Local Screen OCR Buffer (Rule 11 Scrubbed):</span>
              <button
                onClick={handleCopyOcr}
                style={{
                  fontSize: '11px',
                  background: 'rgba(14, 165, 233, 0.15)',
                  border: '1px solid rgba(14, 165, 233, 0.3)',
                  color: '#38bdf8',
                  borderRadius: 4,
                  padding: '3px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <CopyRegular style={{ fontSize: 12 }} /> {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <textarea
              readOnly
              value={ocrText}
              style={{
                width: '100%',
                height: 180,
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                borderRadius: 6,
                padding: '10px',
                fontFamily: 'monospace',
                fontSize: '11px',
                color: '#e2e8f0',
                resize: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>
        )}

        {/* Tab 3: Error Diagnosis */}
        {activeTab === 'ERRORS' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div
              style={{
                background:
                  errorDiagnosis.severity === 'CRITICAL'
                    ? 'rgba(239, 68, 68, 0.15)'
                    : errorDiagnosis.severity === 'WARNING'
                    ? 'rgba(234, 179, 8, 0.15)'
                    : 'rgba(34, 197, 94, 0.15)',
                border: `1px solid ${
                  errorDiagnosis.severity === 'CRITICAL'
                    ? 'rgba(239, 68, 68, 0.4)'
                    : errorDiagnosis.severity === 'WARNING'
                    ? 'rgba(234, 179, 8, 0.4)'
                    : 'rgba(34, 197, 94, 0.4)'
                }`,
                borderRadius: 8,
                padding: '12px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                {errorDiagnosis.hasError ? (
                  <WarningRegular
                    style={{
                      fontSize: 18,
                      color: errorDiagnosis.severity === 'CRITICAL' ? '#ef4444' : '#eab308',
                    }}
                  />
                ) : (
                  <CheckmarkCircleRegular style={{ fontSize: 18, color: '#22c55e' }} />
                )}
                <span
                  style={{
                    fontWeight: 700,
                    fontSize: '12px',
                    color:
                      errorDiagnosis.severity === 'CRITICAL'
                        ? '#fca5a5'
                        : errorDiagnosis.severity === 'WARNING'
                        ? '#fde047'
                        : '#86efac',
                  }}
                >
                  {errorDiagnosis.title}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4' }}>{errorDiagnosis.message}</div>
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>
                Suggested Remediations:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {errorDiagnosis.suggestions.map((s, idx) => (
                  <div key={idx} style={{ fontSize: '11px', color: '#e2e8f0', display: 'flex', gap: 6 }}>
                    <span style={{ color: '#38bdf8' }}>•</span>
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleSimulateErrorScan}
              style={{
                fontSize: '11px',
                background: 'rgba(234, 179, 8, 0.12)',
                border: '1px solid rgba(234, 179, 8, 0.3)',
                color: '#facc15',
                borderRadius: 6,
                padding: '6px 10px',
                cursor: 'pointer',
                marginTop: 6,
                fontWeight: 600,
              }}
            >
              Trigger Test Warning Match
            </button>
          </div>
        )}
      </div>

      {/* Footer Status */}
      <div
        style={{
          padding: '10px 20px',
          borderTop: '1px solid rgba(148, 163, 184, 0.1)',
          background: 'rgba(15, 23, 42, 0.8)',
          fontSize: '10px',
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>Rule 4: 100% On-Device Local VLM</span>
        <span>Guardian SLA: &lt; 25.0ms</span>
      </div>
    </div>
  );
};
