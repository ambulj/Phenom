import React, { useState, useEffect, useRef } from 'react';
import {
  PlayRegular,
  PauseRegular,
  NextRegular,
  Speaker2Regular,
  SpeakerOffRegular,
  ArrowMaximizeRegular,
  ArrowMinimizeRegular,
  DismissRegular,
} from '@fluentui/react-icons';

export interface MediaPlayerHUDProps {
  onClose?: () => void;
  externalEvent?: {
    type: string;
    payload?: any;
  } | null;
}

export const MediaPlayerHUD: React.FC<MediaPlayerHUDProps> = ({
  onClose,
  externalEvent,
}) => {
  const [query, setQuery] = useState<string>('trending music');
  const [platform, setPlatform] = useState<'youtube' | 'spotify'>('youtube');
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(80);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [currentUrl, setCurrentUrl] = useState<string>(
    'https://www.youtube.com/embed?listType=search&list=trending%20music&autoplay=1'
  );

  const webviewRef = useRef<any>(null);

  // Generate target embed URL
  const resolveEmbedUrl = (searchQuery: string, targetPlatform: 'youtube' | 'spotify') => {
    const encoded = encodeURIComponent(searchQuery.trim() || 'trending music');
    if (targetPlatform === 'spotify') {
      return `https://open.spotify.com/embed/search/${encoded}`;
    }
    return `https://www.youtube.com/embed?listType=search&list=${encoded}&autoplay=1`;
  };

  const handlePlayQuery = (newQuery: string, newPlatform: 'youtube' | 'spotify' = platform) => {
    const url = resolveEmbedUrl(newQuery, newPlatform);
    setQuery(newQuery);
    setPlatform(newPlatform);
    setCurrentUrl(url);
    setIsPlaying(true);
    setIsMuted(false);
    if (webviewRef.current) {
      try {
        webviewRef.current.loadURL(url);
      } catch (e) {}
    }
  };

  const handleTogglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      // Mute or pause in webview
      if (webviewRef.current) {
        try {
          webviewRef.current.executeJavaScript(`
            var v = document.querySelector('video');
            if (v) { v.paused ? v.play() : v.pause(); }
            var a = document.querySelector('audio');
            if (a) { a.paused ? a.play() : a.pause(); }
          `);
        } catch (e) {}
      }
    } else {
      setIsPlaying(true);
      if (webviewRef.current) {
        try {
          webviewRef.current.executeJavaScript(`
            var v = document.querySelector('video');
            if (v) { v.play(); }
          `);
        } catch (e) {}
      }
    }
  };

  const handleNext = () => {
    if (webviewRef.current) {
      try {
        webviewRef.current.executeJavaScript(`
          var nextBtn = document.querySelector('.ytp-next-button') || document.querySelector('[data-testid="control-button-skip-forward"]');
          if (nextBtn) nextBtn.click();
        `);
      } catch (e) {}
    }
  };

  const handleVolumeChange = (newVol: number) => {
    setVolume(newVol);
    if (newVol > 0 && isMuted) {
      setIsMuted(false);
    }
    if (webviewRef.current) {
      try {
        const norm = (newVol / 100).toFixed(2);
        webviewRef.current.executeJavaScript(`
          var v = document.querySelector('video');
          if (v) { v.volume = ${norm}; v.muted = false; }
        `);
      } catch (e) {}
    }
  };

  const handleToggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (window.phenom?.muteAllAudio) {
      window.phenom.muteAllAudio(nextMuted);
    }
    if (webviewRef.current) {
      try {
        webviewRef.current.setAudioMuted(nextMuted);
      } catch (e) {}
    }
  };

  // Listen to external WebSocket commands from Backend (MED-01)
  useEffect(() => {
    if (!externalEvent) return;

    if (externalEvent.type === 'MEDIA_PLAY') {
      const p = externalEvent.payload || {};
      const q = p.query || query;
      const plat = (p.platform === 'spotify' ? 'spotify' : 'youtube') as 'youtube' | 'spotify';
      handlePlayQuery(q, plat);
    } else if (externalEvent.type === 'MEDIA_PAUSE') {
      setIsPlaying(false);
      if (webviewRef.current) {
        try {
          webviewRef.current.executeJavaScript(`
            var v = document.querySelector('video');
            if (v) { v.pause(); }
          `);
        } catch (e) {}
      }
    } else if (externalEvent.type === 'MEDIA_RESUME') {
      setIsPlaying(true);
      if (webviewRef.current) {
        try {
          webviewRef.current.executeJavaScript(`
            var v = document.querySelector('video');
            if (v) { v.play(); }
          `);
        } catch (e) {}
      }
    } else if (externalEvent.type === 'MEDIA_NEXT') {
      handleNext();
    } else if (externalEvent.type === 'MEDIA_VOLUME') {
      const vol = Number(externalEvent.payload?.volume ?? 80);
      handleVolumeChange(vol);
    } else if (externalEvent.type === 'MEDIA_MUTE') {
      setIsMuted(true);
      setIsPlaying(false);
      if (webviewRef.current) {
        try {
          webviewRef.current.setAudioMuted(true);
        } catch (e) {}
      }
    }
  }, [externalEvent]);

  // Listen for Guardian Kill Switch Mute (< 10ms SLA) & OS Media Keys
  useEffect(() => {
    if (window.phenom?.onMediaGuardianMute) {
      window.phenom.onMediaGuardianMute(() => {
        setIsMuted(true);
        setIsPlaying(false);
        if (webviewRef.current) {
          try {
            webviewRef.current.setAudioMuted(true);
          } catch (e) {}
        }
      });
    }

    if (window.phenom?.onMediaTransportKey) {
      window.phenom.onMediaTransportKey((action: string) => {
        if (action === 'play_pause') {
          handleTogglePlay();
        } else if (action === 'next') {
          handleNext();
        } else if (action === 'stop') {
          setIsPlaying(false);
        }
      });
    }
  }, []);

  // Block popup windows from webview
  useEffect(() => {
    const wv = webviewRef.current;
    if (!wv) return;
    const handleNewWindow = (e: any) => {
      e.preventDefault();
    };
    wv.addEventListener('new-window', handleNewWindow);
    return () => {
      wv.removeEventListener('new-window', handleNewWindow);
    };
  }, []);

  return (
    <div
      style={{
        background: 'rgba(9, 14, 26, 0.94)',
        border: '1px solid #00E5FF44',
        borderRadius: 8,
        padding: '12px 14px',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', -apple-system, sans-serif",
        boxShadow: '0 8px 32px rgba(0, 229, 255, 0.12)',
        maxWidth: 580,
        margin: '10px 0',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#00E5FF',
            }}
          >
            CYBER HUD MEDIA SUITE
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 4,
              background: platform === 'youtube' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
              color: platform === 'youtube' ? '#ef4444' : '#10b981',
              border: `1px solid ${platform === 'youtube' ? '#ef444455' : '#10b98155'}`,
              fontWeight: 600,
              textTransform: 'uppercase',
            }}
          >
            {platform}
          </span>
          {isMuted && (
            <span
              style={{
                fontSize: 10,
                padding: '2px 6px',
                borderRadius: 4,
                background: 'rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontWeight: 600,
              }}
            >
              MUTED
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
            }}
            title={isExpanded ? 'Collapse Dock' : 'Expand Dock'}
          >
            {isExpanded ? <ArrowMinimizeRegular /> : <ArrowMaximizeRegular />}
          </button>
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
              }}
              title="Close Player"
            >
              <DismissRegular />
            </button>
          )}
        </div>
      </div>

      {/* Track & Search Input */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handlePlayQuery(query);
          }}
          placeholder="Search song or artist..."
          style={{
            flex: 1,
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            borderRadius: 6,
            padding: '6px 10px',
            color: '#f8fafc',
            fontSize: 12,
            outline: 'none',
          }}
        />
        <button
          onClick={() => handlePlayQuery(query, platform === 'youtube' ? 'spotify' : 'youtube')}
          style={{
            background: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid rgba(148, 163, 184, 0.3)',
            borderRadius: 6,
            padding: '6px 10px',
            color: '#94a3b8',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
          }}
          title="Switch platform"
        >
          {platform === 'youtube' ? 'Spotify' : 'YouTube'}
        </button>
      </div>

      {/* Transport Controls Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.6)',
          borderRadius: 6,
          padding: '6px 10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleTogglePlay}
            style={{
              background: '#00E5FF',
              border: 'none',
              borderRadius: '50%',
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: '#080B10',
              fontWeight: 'bold',
            }}
          >
            {isPlaying ? <PauseRegular fontSize={18} /> : <PlayRegular fontSize={18} />}
          </button>
          <button
            onClick={handleNext}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Next Track"
          >
            <NextRegular fontSize={18} />
          </button>
        </div>

        {/* Volume Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleToggleMute}
            style={{
              background: 'transparent',
              border: 'none',
              color: isMuted ? '#ef4444' : '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {isMuted ? <SpeakerOffRegular fontSize={16} /> : <Speaker2Regular fontSize={16} />}
          </button>
          <input
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={(e) => handleVolumeChange(Number(e.target.value))}
            style={{
              width: 90,
              accentColor: '#00E5FF',
              cursor: 'pointer',
            }}
          />
          <span style={{ fontSize: 11, color: '#64748b', minWidth: 26, textAlign: 'right' }}>
            {volume}%
          </span>
        </div>
      </div>

      {/* Docked Electron Webview Frame */}
      {isExpanded && (
        <div style={{ marginTop: 10, borderRadius: 6, overflow: 'hidden', height: 260, background: '#000' }}>
          <webview
            ref={webviewRef}
            src={currentUrl}
            partition="persist:phenom_media"
            allowpopups={false}
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        </div>
      )}
    </div>
  );
};
