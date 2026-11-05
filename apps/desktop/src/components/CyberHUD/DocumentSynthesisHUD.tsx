import React, { useState, useEffect } from 'react';
import {
  DocumentRegular,
  DocumentTableRegular,
  DocumentPdfRegular,
  DataBarVerticalRegular,
  OpenRegular,
  ArrowSyncRegular,
  DismissRegular,
  SparkleRegular
} from '@fluentui/react-icons';

export interface DocumentSynthesisHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export interface DocumentItemDTO {
  filename: string;
  file_path: string;
  format: 'docx' | 'xlsx' | 'pptx' | 'pdf' | 'md' | string;
  size_bytes: number;
  modified_at: string;
}

export interface TemplateDTO {
  id: string;
  name: string;
  description: string;
  formats: string[];
  accent_color: string;
}

const DEFAULT_TEMPLATES: TemplateDTO[] = [
  {
    id: 'executive_brief',
    name: 'Executive Brief',
    description: 'High-impact leadership briefing format with Slate/Navy executive typography and structured KPI tables.',
    formats: ['docx', 'pdf', 'pptx'],
    accent_color: '#1A365D'
  },
  {
    id: 'financial_quarterly',
    name: 'Financial Quarterly Report',
    description: 'Financial balance & budget sheet with automated data aggregation, borders, and bar chart embeds.',
    formats: ['xlsx', 'pdf', 'docx'],
    accent_color: '#1F497D'
  },
  {
    id: 'tech_architecture',
    name: 'Technical Architecture Spec',
    description: 'In-depth engineering document with bullet trees, component tables, and architectural slide decks.',
    formats: ['docx', 'pptx', 'pdf'],
    accent_color: '#2B6CB0'
  },
  {
    id: 'cyber_cyan',
    name: 'Cyber Cyan Futuristic',
    description: 'Phenom signature cybernetic theme with neon cyan headers and high-contrast data matrices.',
    formats: ['pptx', 'pdf', 'docx', 'xlsx'],
    accent_color: '#00F0FF'
  }
];

export const DocumentSynthesisHUD: React.FC<DocumentSynthesisHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activeFormatTab, setActiveFormatTab] = useState<string>('ALL');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('executive_brief');
  const [docTitle, setDocTitle] = useState<string>('Q4 Executive Review');
  const [includeChart, setIncludeChart] = useState<boolean>(true);
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('');

  const [documents, setDocuments] = useState<DocumentItemDTO[]>([
    {
      filename: 'Phenom_Hardcore_Overclock_Report.pdf',
      file_path: 'C:\\Phenom\\vault\\documents\\Phenom_Hardcore_Overclock_Report.pdf',
      format: 'pdf',
      size_bytes: 2582,
      modified_at: new Date().toISOString()
    },
    {
      filename: 'Hardcore_Test_Doc.docx',
      file_path: 'C:\\Phenom\\vault\\documents\\Hardcore_Test_Doc.docx',
      format: 'docx',
      size_bytes: 36798,
      modified_at: new Date().toISOString()
    },
    {
      filename: 'Hardcore_Test_Metrics.xlsx',
      file_path: 'C:\\Phenom\\vault\\documents\\Hardcore_Test_Metrics.xlsx',
      format: 'xlsx',
      size_bytes: 5194,
      modified_at: new Date().toISOString()
    },
    {
      filename: 'Hardcore_Test_Deck.pptx',
      file_path: 'C:\\Phenom\\vault\\documents\\Hardcore_Test_Deck.pptx',
      format: 'pptx',
      size_bytes: 29202,
      modified_at: new Date().toISOString()
    }
  ]);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'documents_list_update' && Array.isArray(payload)) {
      setDocuments(payload);
    } else if (type === 'document_generated' && payload?.details) {
      const details = payload.details;
      setDocuments(prev => [
        {
          filename: details.filename,
          file_path: details.file_path,
          format: details.format,
          size_bytes: details.size_bytes || 0,
          modified_at: details.created_at || new Date().toISOString()
        },
        ...prev.filter(d => d.filename !== details.filename)
      ]);
      setIsSynthesizing(false);
      setStatusMessage(`Generated: ${details.filename}`);
    }
  }, [externalEvent]);

  const handleRefresh = () => {
    setStatusMessage('Scanning vault documents...');
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'list_generated_documents',
          args: {}
        }
      });
    }
    setTimeout(() => setStatusMessage(''), 3000);
  };

  const handleCreateDocument = (targetFormat: string) => {
    setIsSynthesizing(true);
    setStatusMessage(`Synthesizing ${targetFormat.toUpperCase()} with ${selectedTemplate} template...`);

    const cleanTitle = docTitle.trim() || 'Phenom Executive Document';
    const slug = cleanTitle.replace(/[^a-zA-Z0-9_\-]+/g, '_');
    const filename = `${slug}.${targetFormat}`;

    const chartConfig = includeChart ? {
      type: 'bar',
      title: `${cleanTitle} Metrics`,
      categories: ['Core Engine', 'Knowledge Vault', 'Safety Layer', 'Memory'],
      data: [100, 98, 100, 95],
      series_values: [100, 98, 100, 95],
      series_name: 'Performance Score'
    } : undefined;

    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'generate_document',
          args: {
            filename: filename,
            format: targetFormat,
            title: cleanTitle,
            template: selectedTemplate,
            chart_config: chartConfig,
            mode: 'create'
          }
        }
      });
    }

    setTimeout(() => {
      setIsSynthesizing(false);
    }, 2000);
  };

  const handleOpenNative = (filePath: string) => {
    setStatusMessage(`Opening ${filePath} in native app...`);
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'open_app',
          args: {
            app_name: filePath
          }
        }
      });
    }
    setTimeout(() => setStatusMessage(''), 3000);
  };

  const filteredDocs = activeFormatTab === 'ALL'
    ? documents
    : documents.filter(d => d.format.toLowerCase() === activeFormatTab.toLowerCase());

  const getFormatBadge = (fmt: string) => {
    switch (fmt.toLowerCase()) {
      case 'docx':
        return { label: 'DOCX', bg: 'rgba(0, 122, 255, 0.2)', color: '#007aff', icon: <DocumentRegular /> };
      case 'xlsx':
        return { label: 'XLSX', bg: 'rgba(16, 124, 65, 0.2)', color: '#107c41', icon: <DocumentTableRegular /> };
      case 'pptx':
        return { label: 'PPTX', bg: 'rgba(216, 59, 1, 0.2)', color: '#d83b01', icon: <DataBarVerticalRegular /> };
      case 'pdf':
        return { label: 'PDF', bg: 'rgba(232, 17, 35, 0.2)', color: '#e81123', icon: <DocumentPdfRegular /> };
      default:
        return { label: fmt.toUpperCase(), bg: 'rgba(0, 240, 255, 0.2)', color: '#00f0ff', icon: <DocumentRegular /> };
    }
  };

  return (
    <div
      style={{
        width: '560px',
        maxHeight: '680px',
        background: 'rgba(12, 18, 28, 0.94)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 240, 255, 0.25)',
        borderRadius: '16px',
        boxShadow: '0 16px 40px rgba(0, 0, 0, 0.7), 0 0 24px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 1000
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(0, 240, 255, 0.03)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(0, 122, 255, 0.3))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#00f0ff',
              boxShadow: '0 0 12px rgba(0, 240, 255, 0.3)'
            }}
          >
            <DocumentRegular fontSize={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, letterSpacing: '0.5px', color: '#f8fafc' }}>
              Autonomous Document Synthesis
            </h3>
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>
              Multi-Format Engine • Obsidian Knowledge Hub
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleRefresh}
            title="Rescan vault documents"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <ArrowSyncRegular fontSize={16} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              title="Close HUD"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <DismissRegular fontSize={18} />
            </button>
          )}
        </div>
      </div>

      {/* Synthesis Action Panel */}
      <div
        style={{
          padding: '16px 20px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
        }}
      >
        <div style={{ marginBottom: '12px' }}>
          <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.8px', color: '#00f0ff', marginBottom: '6px' }}>
            Document Title & Topic
          </label>
          <input
            type="text"
            value={docTitle}
            onChange={e => setDocTitle(e.target.value)}
            placeholder="e.g., Q4 Strategic Financial Overview"
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid rgba(0, 240, 255, 0.2)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#f8fafc',
              fontSize: '13px',
              outline: 'none'
            }}
          />
        </div>

        {/* Template Selector & Chart Option */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
              Styling Template
            </label>
            <select
              value={selectedTemplate}
              onChange={e => setSelectedTemplate(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                padding: '6px 10px',
                color: '#e2e8f0',
                fontSize: '12px',
                outline: 'none'
              }}
            >
              {DEFAULT_TEMPLATES.map(tmpl => (
                <option key={tmpl.id} value={tmpl.id} style={{ background: '#0f172a', color: '#fff' }}>
                  {tmpl.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '16px' }}>
            <input
              type="checkbox"
              id="include_chart"
              checked={includeChart}
              onChange={e => setIncludeChart(e.target.checked)}
              style={{ accentColor: '#00f0ff', cursor: 'pointer' }}
            />
            <label htmlFor="include_chart" style={{ fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
              Embed Native Charts
            </label>
          </div>
        </div>

        {/* 1-Click Synthesis Buttons for All 4 Formats */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => handleCreateDocument('docx')}
            disabled={isSynthesizing}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              background: 'rgba(0, 122, 255, 0.15)',
              border: '1px solid rgba(0, 122, 255, 0.4)',
              color: '#38bdf8',
              fontSize: '12px',
              fontWeight: 500,
              cursor: isSynthesizing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <DocumentRegular fontSize={14} /> + Word
          </button>

          <button
            onClick={() => handleCreateDocument('xlsx')}
            disabled={isSynthesizing}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              background: 'rgba(16, 124, 65, 0.15)',
              border: '1px solid rgba(16, 124, 65, 0.4)',
              color: '#4ade80',
              fontSize: '12px',
              fontWeight: 500,
              cursor: isSynthesizing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <DocumentTableRegular fontSize={14} /> + Excel
          </button>

          <button
            onClick={() => handleCreateDocument('pptx')}
            disabled={isSynthesizing}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              background: 'rgba(216, 59, 1, 0.15)',
              border: '1px solid rgba(216, 59, 1, 0.4)',
              color: '#fb923c',
              fontSize: '12px',
              fontWeight: 500,
              cursor: isSynthesizing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <DataBarVerticalRegular fontSize={14} /> + Deck
          </button>

          <button
            onClick={() => handleCreateDocument('pdf')}
            disabled={isSynthesizing}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: '6px',
              background: 'rgba(232, 17, 35, 0.15)',
              border: '1px solid rgba(232, 17, 35, 0.4)',
              color: '#f87171',
              fontSize: '12px',
              fontWeight: 500,
              cursor: isSynthesizing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <DocumentPdfRegular fontSize={14} /> + PDF
          </button>
        </div>

        {statusMessage && (
          <div style={{ marginTop: '10px', fontSize: '11px', color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <SparkleRegular fontSize={12} /> {statusMessage}
          </div>
        )}
      </div>

      {/* Format Filter Tabs */}
      <div
        style={{
          display: 'flex',
          padding: '10px 20px',
          gap: '6px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(0, 0, 0, 0.2)'
        }}
      >
        {['ALL', 'DOCX', 'XLSX', 'PPTX', 'PDF'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveFormatTab(tab)}
            style={{
              padding: '4px 12px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: activeFormatTab === tab ? 600 : 400,
              background: activeFormatTab === tab ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
              color: activeFormatTab === tab ? '#00f0ff' : '#94a3b8',
              border: activeFormatTab === tab ? '1px solid rgba(0, 240, 255, 0.4)' : '1px solid transparent',
              cursor: 'pointer'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Recents Document List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        {filteredDocs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px 0', color: '#64748b', fontSize: '13px' }}>
            No documents generated in this format category.
          </div>
        ) : (
          filteredDocs.map((doc, idx) => {
            const badge = getFormatBadge(doc.format);
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  transition: 'background 0.2s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
                  <div
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      background: badge.bg,
                      color: badge.color,
                      fontSize: '11px',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {badge.label}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: 500,
                        color: '#f1f5f9',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '320px'
                      }}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>
                      {(doc.size_bytes / 1024).toFixed(1)} KB • {new Date(doc.modified_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>

                {/* 1-Click Open in Native App */}
                <button
                  onClick={() => handleOpenNative(doc.file_path)}
                  title="Open in Native Application"
                  style={{
                    background: 'rgba(0, 240, 255, 0.08)',
                    border: '1px solid rgba(0, 240, 255, 0.25)',
                    color: '#00f0ff',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 500
                  }}
                >
                  <OpenRegular fontSize={13} /> Open
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
