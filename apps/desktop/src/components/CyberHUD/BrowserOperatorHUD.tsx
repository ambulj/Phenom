import React, { useState, useEffect } from 'react';
import {
  GlobeRegular,
  PauseRegular,
  PlayRegular,
  HandRightRegular,
  DismissRegular,
  AddRegular,
  DocumentBulletListRegular,
  ShieldCheckmarkRegular,
  NavigationRegular
} from '@fluentui/react-icons';

export interface BrowserOperatorHUDProps {
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export interface TabItemDTO {
  tab_id: string;
  title: string;
  url: string;
  is_active: boolean;
}

export const BrowserOperatorHUD: React.FC<BrowserOperatorHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [currentUrl, setCurrentUrl] = useState<string>('https://news.ycombinator.com');
  const [activeTitle, setActiveTitle] = useState<string>('Hacker News');
  const [frameBase64, setFrameBase64] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [isTakeover, setIsTakeover] = useState<boolean>(false);
  const [showScrapedData, setShowScrapedData] = useState<boolean>(false);
  const [scrapedContent, setScrapedContent] = useState<any | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('Autonomous Operator Standing By');

  const [tabs, setTabs] = useState<TabItemDTO[]>([
    {
      tab_id: 'tab-main',
      title: 'Hacker News',
      url: 'https://news.ycombinator.com',
      is_active: true
    }
  ]);

  useEffect(() => {
    if (!externalEvent) return;
    const { type, payload } = externalEvent;

    if (type === 'browser.frame' && payload?.frame) {
      setFrameBase64(payload.frame);
    } else if (type === 'browser.navigated' && payload) {
      if (payload.url) setCurrentUrl(payload.url);
      if (payload.title) setActiveTitle(payload.title);
      setStatusMessage(`Navigated to ${payload.title || payload.url}`);
    } else if (type === 'browser.tabs' && Array.isArray(payload.tabs)) {
      setTabs(payload.tabs);
    } else if (type === 'browser.scraped' && payload) {
      setScrapedContent(payload);
      setShowScrapedData(true);
      setStatusMessage(`Extracted ${payload.headings?.length || 0} headings & ${payload.tables?.length || 0} tables`);
    } else if (type === 'browser.takeover') {
      setIsPaused(!!payload.is_paused);
      setIsTakeover(!!payload.is_takeover);
      setStatusMessage(payload.is_takeover ? 'Human Takeover Active' : payload.is_paused ? 'Paused' : 'Operating');
    }
  }, [externalEvent]);

  const handleNavigate = () => {
    if (!currentUrl.trim()) return;
    setStatusMessage(`Navigating to ${currentUrl}...`);
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_navigate',
          args: { url: currentUrl }
        }
      });
    }
  };

  const handlePause = () => {
    setIsPaused(true);
    setStatusMessage('Operator paused by user');
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_takeover_control',
          args: { action: 'pause' }
        }
      });
    }
  };

  const handleResume = () => {
    setIsPaused(false);
    setIsTakeover(false);
    setStatusMessage('Autonomous operator resumed');
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_takeover_control',
          args: { action: 'resume' }
        }
      });
    }
  };

  const handleTakeover = () => {
    setIsTakeover(true);
    setStatusMessage('Manual takeover triggered (Rule 8 guarded)');
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_takeover_control',
          args: { action: 'takeover' }
        }
      });
    }
  };

  const handleNewTab = () => {
    const url = 'about:blank';
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_manage_tabs',
          args: { action: 'new', url: url }
        }
      });
    }
    const newId = `tab-${Date.now().toString().slice(-4)}`;
    setTabs(prev => [
      ...prev.map(t => ({ ...t, is_active: false })),
      { tab_id: newId, title: 'New Tab', url: url, is_active: true }
    ]);
  };

  const handleSwitchTab = (tabId: string) => {
    setTabs(prev => prev.map(t => ({ ...t, is_active: t.tab_id === tabId })));
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_manage_tabs',
          args: { action: 'switch', tab_id: tabId }
        }
      });
    }
  };

  const handleCloseTab = (tabId: string) => {
    if (tabs.length <= 1) return;
    setTabs(prev => prev.filter(t => t.tab_id !== tabId));
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_manage_tabs',
          args: { action: 'close', tab_id: tabId }
        }
      });
    }
  };

  const handleExtractContent = () => {
    setStatusMessage('Extracting verified DOM tables & headings...');
    if (sendMessage) {
      sendMessage({
        type: 'execute_tool',
        payload: {
          tool: 'browser_extract_content',
          args: {}
        }
      });
    }
  };

  return (
    <div
      style={{
        width: '640px',
        maxHeight: '740px',
        background: 'rgba(10, 15, 24, 0.95)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(0, 240, 255, 0.28)',
        borderRadius: '16px',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 240, 255, 0.15)',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 1000
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(0, 240, 255, 0.04)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.25), rgba(0, 122, 255, 0.35))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#00f0ff',
              boxShadow: '0 0 14px rgba(0, 240, 255, 0.35)'
            }}
          >
            <GlobeRegular fontSize={18} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#f8fafc', letterSpacing: '0.4px' }}>
              Autonomous Browser Operator
            </h3>
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>
              {activeTitle ? `${activeTitle} • ` : ''}Persistent Playwright Engine • Sovereign Web Navigator
            </span>
          </div>
        </div>

        {/* Rule 8 Payment Protection Shield Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              padding: '3px 8px',
              borderRadius: '6px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34d399',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.5px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Rule 8 Permanent Payment Blocker is strictly active"
          >
            <ShieldCheckmarkRegular fontSize={12} />
            RULE 8 PROTECTED
          </div>

          {onClose && (
            <button
              onClick={onClose}
              title="Close Browser Operator"
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

      {/* Tabs Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '6px 14px',
          background: 'rgba(0, 0, 0, 0.4)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          overflowX: 'auto'
        }}
      >
        {tabs.map((tab) => (
          <div
            key={tab.tab_id}
            onClick={() => handleSwitchTab(tab.tab_id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '6px',
              background: tab.is_active ? 'rgba(0, 240, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
              border: tab.is_active ? '1px solid rgba(0, 240, 255, 0.35)' : '1px solid transparent',
              color: tab.is_active ? '#00f0ff' : '#94a3b8',
              fontSize: '11px',
              cursor: 'pointer',
              maxWidth: '140px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tab.title || 'Tab'}</span>
            {tabs.length > 1 && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  handleCloseTab(tab.tab_id);
                }}
                style={{ cursor: 'pointer', opacity: 0.7 }}
              >
                ×
              </span>
            )}
          </div>
        ))}

        <button
          onClick={handleNewTab}
          title="Open new tab"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            padding: '4px 6px',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <AddRegular fontSize={14} />
        </button>
      </div>

      {/* Navigation URL Bar & Action Ribbon */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
          padding: '10px 18px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
        }}
      >
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="text"
            value={currentUrl}
            onChange={(e) => setCurrentUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
            placeholder="Enter web destination or search URL..."
            style={{
              flex: 1,
              background: 'rgba(0, 0, 0, 0.5)',
              border: '1px solid rgba(0, 240, 255, 0.25)',
              borderRadius: '8px',
              padding: '6px 12px',
              color: '#f8fafc',
              fontSize: '12px',
              outline: 'none'
            }}
          />
          <button
            onClick={handleNavigate}
            title="Navigate to destination"
            style={{
              background: 'rgba(0, 240, 255, 0.15)',
              border: '1px solid rgba(0, 240, 255, 0.4)',
              color: '#00f0ff',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <NavigationRegular fontSize={13} /> Go
          </button>
        </div>

        {/* Structured Scrape Button */}
        <button
          onClick={handleExtractContent}
          title="Extract structured tables & headings without fabrication"
          style={{
            background: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            color: '#38bdf8',
            padding: '6px 10px',
            borderRadius: '8px',
            fontSize: '11px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <DocumentBulletListRegular fontSize={14} /> Scrape
        </button>
      </div>

      {/* Control Ribbon (Pause / Step / Takeover) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 18px',
          background: 'rgba(0, 0, 0, 0.25)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)'
        }}
      >
        <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: isTakeover ? '#eab308' : isPaused ? '#ef4444' : '#10b981',
              boxShadow: `0 0 8px ${isTakeover ? '#eab308' : isPaused ? '#ef4444' : '#10b981'}`
            }}
          />
          {statusMessage}
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {!isPaused ? (
            <button
              onClick={handlePause}
              title="Pause automation"
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#f87171',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <PauseRegular fontSize={12} /> Pause
            </button>
          ) : (
            <button
              onClick={handleResume}
              title="Resume automation"
              style={{
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: '#34d399',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <PlayRegular fontSize={12} /> Resume
            </button>
          )}

          <button
            onClick={handleTakeover}
            title="Request manual human takeover"
            style={{
              background: 'rgba(234, 179, 8, 0.15)',
              border: '1px solid rgba(234, 179, 8, 0.35)',
              color: '#fde047',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <HandRightRegular fontSize={12} /> Takeover
          </button>
        </div>
      </div>

      {/* Viewport Live Stream or Scraped Data */}
      <div
        style={{
          height: '420px',
          background: '#040711',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden'
        }}
      >
        {frameBase64 ? (
          <img
            src={`data:image/jpeg;base64,${frameBase64}`}
            alt="Live Browser Viewport"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        ) : (
          <div style={{ textAlign: 'center', color: '#64748b' }}>
            <GlobeRegular fontSize={40} style={{ opacity: 0.3, marginBottom: '8px' }} />
            <div style={{ fontSize: '13px' }}>Live Viewport Stream Idle</div>
            <div style={{ fontSize: '11px', color: '#475569' }}>
              Persistent Chromium context will stream on navigation
            </div>
          </div>
        )}

        {/* Scraped Content Overlay Drawer */}
        {showScrapedData && scrapedContent && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(4, 7, 17, 0.94)',
              backdropFilter: 'blur(10px)',
              padding: '16px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#00f0ff' }}>
                Extracted Structured Provenance
              </div>
              <button
                onClick={() => setShowScrapedData(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>

            {/* Headings */}
            {scrapedContent.headings && scrapedContent.headings.length > 0 && (
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', marginBottom: '4px' }}>
                  Document Headings
                </div>
                {scrapedContent.headings.slice(0, 5).map((h: any, i: number) => (
                  <div key={i} style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '2px' }}>
                    <span style={{ color: '#00f0ff', fontSize: '10px' }}>[{h.tag}]</span> {h.text}
                  </div>
                ))}
              </div>
            )}

            {/* Structured Tables */}
            {scrapedContent.tables && scrapedContent.tables.length > 0 && (
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', marginBottom: '4px' }}>
                  Structured Tables ({scrapedContent.tables.length})
                </div>
                <div
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '6px',
                    padding: '8px',
                    fontSize: '11px',
                    color: '#94a3b8'
                  }}
                >
                  Table 1: {scrapedContent.tables[0].length} rows detected
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
