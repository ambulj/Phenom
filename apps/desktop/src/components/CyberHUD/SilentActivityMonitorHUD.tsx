import React, { useState } from 'react';
import {
  DismissRegular,
  PulseRegular,
  TimerRegular,
  CheckmarkCircleRegular,
  DismissCircleRegular,
  FilterRegular,
  SearchRegular,
  ArrowCounterclockwiseRegular,
  ChevronDownRegular,
  ChevronRightRegular,
} from '@fluentui/react-icons';

interface TelemetryEventUI {
  event_id: string;
  tool_name: string;
  status: string; // COMPLETED, FAILED, STARTED
  duration_ms: number;
  tier: number;
  timestamp: string;
  arguments: Record<string, any>;
  result_summary?: string;
}

interface SilentActivityMonitorHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

export const SilentActivityMonitorHUD: React.FC<SilentActivityMonitorHUDProps> = ({
  externalEvent: _externalEvent,
  sendMessage: _sendMessage,
  onClose,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const initialEvents: TelemetryEventUI[] = [
    {
      event_id: 'evt-91204-a1',
      tool_name: 'open_app',
      status: 'COMPLETED',
      duration_ms: 14.2,
      tier: 0,
      timestamp: '13:30:12',
      arguments: { app_name: 'CompactGUI' },
      result_summary: 'Launched successfully with PID 7176',
    },
    {
      event_id: 'evt-91205-b2',
      tool_name: 'set_volume',
      status: 'COMPLETED',
      duration_ms: 6.8,
      tier: 0,
      timestamp: '13:30:45',
      arguments: { level: '45%' },
      result_summary: 'Master volume adjusted to 45%',
    },
    {
      event_id: 'evt-91206-c3',
      tool_name: 'recycle_delete',
      status: 'COMPLETED',
      duration_ms: 22.5,
      tier: 1,
      timestamp: '13:31:18',
      arguments: { path: 'C:\\Users\\sauja\\Downloads\\stale_dump.tmp' },
      result_summary: 'Sent to Windows Recycle Bin via send2trash',
    },
    {
      event_id: 'evt-91207-d4',
      tool_name: 'list_files',
      status: 'COMPLETED',
      duration_ms: 8.1,
      tier: 0,
      timestamp: '13:31:50',
      arguments: { directory: 'C:\\Phenom\\vault' },
      result_summary: 'Found 42 vault markdown files',
    },
    {
      event_id: 'evt-91208-e5',
      tool_name: 'send_email',
      status: 'COMPLETED',
      duration_ms: 185.0,
      tier: 2,
      timestamp: '13:32:20',
      arguments: { recipient: 'alex@example.com', auth_token: '[REDACTED]' },
      result_summary: 'Outbound email sent after voice confirmation',
    },
    {
      event_id: 'evt-91209-f6',
      tool_name: 'modify_registry_key',
      status: 'FAILED',
      duration_ms: 12.0,
      tier: 2,
      timestamp: '13:33:02',
      arguments: { key: 'HKLM\\Security\\Test' },
      result_summary: 'Access Denied: Missing elevated administrator token',
    },
  ];

  const [eventsList, setEventsList] = useState<TelemetryEventUI[]>(initialEvents);

  const filteredEvents = eventsList.filter((e) => {
    if (filterStatus !== 'ALL' && e.status !== filterStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        e.tool_name.toLowerCase().includes(q) ||
        e.event_id.toLowerCase().includes(q) ||
        (e.result_summary && e.result_summary.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const totalEvents = eventsList.length;
  const completedEvents = eventsList.filter((e) => e.status === 'COMPLETED').length;
  const failedEvents = eventsList.filter((e) => e.status === 'FAILED').length;
  const avgLatency =
    totalEvents > 0 ? (eventsList.reduce((acc, curr) => acc + curr.duration_ms, 0) / totalEvents).toFixed(1) : '0.0';

  const handleSimulateNewEvent = () => {
    const tools = ['open_app', 'tile_windows', 'read_file', 'set_volume', 'close_app'];
    const selected = tools[Math.floor(Math.random() * tools.length)];
    const dur = parseFloat((Math.random() * 25 + 4).toFixed(1));
    const newEvent: TelemetryEventUI = {
      event_id: `evt-${Math.floor(Math.random() * 90000) + 10000}-sim`,
      tool_name: selected,
      status: 'COMPLETED',
      duration_ms: dur,
      tier: selected === 'close_app' ? 1 : 0,
      timestamp: new Date().toLocaleTimeString(),
      arguments: { target: 'Simulated Desktop Action' },
      result_summary: `Executed silently in ${dur}ms`,
    };
    setEventsList((prev) => [newEvent, ...prev]);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(3, 7, 18, 0.92)',
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
          <PulseRegular style={{ fontSize: '24px', color: '#38bdf8' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, letterSpacing: '0.5px' }}>
              Silent Activity Monitor & Background Telemetry
            </h2>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              Milestone 29 Phase 4 • Zero-Noise Background Tool Activity Waterfall & On-Demand Inspector
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleSimulateNewEvent}
            style={{
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid #38bdf8',
              borderRadius: '8px',
              padding: '6px 14px',
              color: '#38bdf8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            <PulseRegular /> Record Sample Event
          </button>
          <button
            onClick={() => setEventsList(initialEvents)}
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
            <ArrowCounterclockwiseRegular /> Reset
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
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* KPI Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', marginBottom: '8px' }}>
              <PulseRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>TOTAL EVENTS</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{totalEvents}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Buffered background tool executions</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(34, 197, 94, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#4ade80', marginBottom: '8px' }}>
              <CheckmarkCircleRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>COMPLETED ACTIONS</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{completedEvents}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Executed with 0 user prompts</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', marginBottom: '8px' }}>
              <DismissCircleRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>FAILED / BLOCKED</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{failedEvents}</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Intercepted errors or security blocks</div>
          </div>

          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(168, 85, 247, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', marginBottom: '8px' }}>
              <TimerRegular style={{ fontSize: '18px' }} />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>AVERAGE LATENCY</span>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#f8fafc' }}>{avgLatency}ms</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Fast-track execution overhead</div>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, maxWidth: '400px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '8px 12px',
                width: '100%',
              }}
            >
              <SearchRegular style={{ color: '#94a3b8' }} />
              <input
                type="text"
                placeholder="Search events, tools, or result synopses..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#f8fafc',
                  fontSize: '13px',
                  width: '100%',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <FilterRegular /> Status:
            </span>
            {['ALL', 'COMPLETED', 'FAILED'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                style={{
                  background: filterStatus === st ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1px solid ${filterStatus === st ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '6px',
                  padding: '4px 10px',
                  color: filterStatus === st ? '#38bdf8' : '#94a3b8',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Telemetry Event Waterfall List */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              padding: '12px 16px',
              background: 'rgba(2, 6, 23, 0.7)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              fontSize: '12px',
              fontWeight: 600,
              color: '#94a3b8',
              display: 'grid',
              gridTemplateColumns: '32px 140px 180px 100px 90px 1fr',
            }}
          >
            <span />
            <span>EVENT ID</span>
            <span>TOOL NAME</span>
            <span>STATUS</span>
            <span>LATENCY</span>
            <span>RESULT SYNOPSIS</span>
          </div>

          {filteredEvents.map((evt) => {
            const isExpanded = expandedEventId === evt.event_id;
            const statusColor = evt.status === 'COMPLETED' ? '#4ade80' : evt.status === 'FAILED' ? '#f87171' : '#fbbf24';
            return (
              <React.Fragment key={evt.event_id}>
                <div
                  onClick={() => setExpandedEventId(isExpanded ? null : evt.event_id)}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    background: isExpanded ? 'rgba(56, 189, 248, 0.06)' : 'rgba(15, 23, 42, 0.2)',
                    display: 'grid',
                    gridTemplateColumns: '32px 140px 180px 100px 90px 1fr',
                    alignItems: 'center',
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease',
                  }}
                >
                  <span style={{ color: '#94a3b8' }}>
                    {isExpanded ? <ChevronDownRegular /> : <ChevronRightRegular />}
                  </span>
                  <span style={{ fontFamily: 'monospace', color: '#94a3b8', fontSize: '12px' }}>{evt.event_id}</span>
                  <span style={{ fontWeight: 600, color: '#f8fafc', fontFamily: 'monospace' }}>
                    {evt.tool_name}{' '}
                    <span style={{ fontSize: '10px', color: '#64748b' }}>[T{evt.tier}]</span>
                  </span>
                  <span>
                    <span
                      style={{
                        background: `${statusColor}22`,
                        border: `1px solid ${statusColor}55`,
                        color: statusColor,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        fontSize: '11px',
                      }}
                    >
                      {evt.status}
                    </span>
                  </span>
                  <span style={{ color: '#c084fc', fontFamily: 'monospace', fontSize: '12px' }}>
                    {evt.duration_ms}ms
                  </span>
                  <span style={{ color: '#cbd5e1', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {evt.result_summary || 'No synopsis'}
                  </span>
                </div>

                {/* Drill-down Arguments Panel */}
                {isExpanded && (
                  <div
                    style={{
                      padding: '16px 24px',
                      background: 'rgba(2, 6, 23, 0.85)',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase' }}>
                      Tool Arguments (Rule 11 Credential Scrubbed)
                    </div>
                    <pre
                      style={{
                        background: 'rgba(15, 23, 42, 0.8)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: '6px',
                        padding: '10px',
                        fontSize: '12px',
                        color: '#94a3b8',
                        margin: 0,
                        fontFamily: 'monospace',
                        overflowX: 'auto',
                      }}
                    >
                      {JSON.stringify(evt.arguments, null, 2)}
                    </pre>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
export default SilentActivityMonitorHUD;
