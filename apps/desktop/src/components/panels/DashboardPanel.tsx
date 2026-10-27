import React, { useState, useEffect } from 'react';
import {
  Button,
  Badge,
  Input,
  Tab,
  TabList
} from '@fluentui/react-components';
import {
  ClockRegular,
  AddRegular,
  DeleteRegular,
  DismissRegular,
  ArrowClockwiseRegular,
  NewsRegular
} from '@fluentui/react-icons';

interface DashboardPanelProps {
  onClose: () => void;
  onSendWs: (msg: any) => void;
  scheduledJobs: any[];
  watchlistItems: any[];
}

export const DashboardPanel: React.FC<DashboardPanelProps> = ({
  onClose,
  onSendWs,
  scheduledJobs,
  watchlistItems
}) => {
  const [selectedTab, setSelectedTab] = useState<string>('scheduler');
  const [schedulerLogs, setSchedulerLogs] = useState<any[]>([]);
  const [actionLogs, setActionLogs] = useState<any[]>([]);
  const [techNewsArticles, setTechNewsArticles] = useState<any[]>([]);

  // Form states
  const [newReminderTitle, setNewReminderTitle] = useState<string>('');
  const [newReminderDelay, setNewReminderDelay] = useState<string>('60');

  const [newWatchSymbol, setNewWatchSymbol] = useState<string>('');
  const [newWatchPrice, setNewWatchPrice] = useState<string>('200');
  const [newWatchCondition, setNewWatchCondition] = useState<string>('above');
  const [newWatchType, setNewWatchType] = useState<string>('stock');

  // Fetch data on tab switch
  useEffect(() => {
    fetchLogs();
    fetchTechNews();
  }, [selectedTab]);

  const fetchLogs = async () => {
    try {
      const [resSched, resAction] = await Promise.all([
        fetch('http://localhost:8000/api/scheduler/logs?limit=25'),
        fetch('http://localhost:8000/api/logs?limit=25')
      ]);
      if (resSched.ok) {
        setSchedulerLogs(await resSched.json());
      }
      if (resAction.ok) {
        setActionLogs(await resAction.json());
      }
    } catch (e) {
      console.error('Failed to fetch logs:', e);
    }
  };

  const fetchTechNews = async () => {
    try {
      // In dev environment or live
      const articles = [
        {
          source: 'Hacker News',
          title: 'Show HN: Phenom - Personal Windows 11 Desktop AI Assistant',
          link: 'https://news.ycombinator.com',
          summary: 'Fast local-first agent with 3D Three.js orb, voice, and safety tiers.'
        },
        {
          source: 'TechCrunch',
          title: 'Local LLMs on RTX GPUs: Edge Computing and Privacy First',
          link: 'https://techcrunch.com',
          summary: 'Why personal AI assistants are moving to local-first architecture.'
        },
        {
          source: 'The Verge',
          title: 'Windows 11 Fluid Micro-Interactions & Desktop Integration',
          link: 'https://theverge.com',
          summary: 'Exploring particle cloud animations and Fluent UI designs.'
        }
      ];
      setTechNewsArticles(articles);
    } catch (e) {
      console.error('Failed to fetch news:', e);
    }
  };

  const handleAddReminder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReminderTitle.trim()) return;
    const delaySec = parseInt(newReminderDelay, 10) || 60;
    onSendWs({
      type: 'scheduler.add_reminder',
      payload: {
        title: newReminderTitle.trim(),
        delay_seconds: delaySec
      }
    });
    setNewReminderTitle('');
  };

  const handleCancelJob = (jobId: string) => {
    onSendWs({
      type: 'scheduler.cancel',
      payload: { job_id: jobId }
    });
  };

  const handleAddWatchlist = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchSymbol.trim()) return;
    const target = parseFloat(newWatchPrice) || 0.0;
    onSendWs({
      type: 'watchlist.add',
      payload: {
        symbol: newWatchSymbol.trim().toUpperCase(),
        target_price: target,
        condition: newWatchCondition,
        asset_type: newWatchType
      }
    });
    setNewWatchSymbol('');
  };

  const handleRemoveWatchlist = (symbol: string) => {
    onSendWs({
      type: 'watchlist.remove',
      payload: { symbol }
    });
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 60,
        right: 0,
        width: 520,
        height: 'calc(100vh - 60px)',
        background: 'rgba(15, 23, 42, 0.96)',
        backdropFilter: 'blur(20px)',
        borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-8px 0 32px rgba(0, 0, 0, 0.5)',
        color: '#f8fafc'
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ClockRegular style={{ fontSize: 20, color: '#60a5fa' }} />
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Phenom Dashboard</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Button appearance="subtle" icon={<ArrowClockwiseRegular />} onClick={fetchLogs} size="small" />
          <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} size="small" />
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <TabList
          selectedValue={selectedTab}
          onTabSelect={(_, d) => setSelectedTab(d.value as string)}
          size="small"
        >
          <Tab value="scheduler">Scheduler</Tab>
          <Tab value="finance">Watchlist</Tab>
          <Tab value="logs">Live Logs</Tab>
          <Tab value="news">Tech News</Tab>
        </TabList>
      </div>

      {/* Tab Contents */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* ================= TAB: SCHEDULER ================= */}
        {selectedTab === 'scheduler' && (
          <>
            {/* Quick Add Form */}
            <form onSubmit={handleAddReminder} style={{ display: 'flex', flexDirection: 'column', gap: 10, background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#93c5fd' }}>Quick Schedule Reminder</span>
              <Input
                placeholder="Reminder title (e.g. Check PR review)"
                value={newReminderTitle}
                onChange={(_, d) => setNewReminderTitle(d.value)}
                size="small"
              />
              <div style={{ display: 'flex', gap: 10 }}>
                <Input
                  type="number"
                  placeholder="Delay seconds"
                  value={newReminderDelay}
                  onChange={(_, d) => setNewReminderDelay(d.value)}
                  style={{ flex: 1 }}
                  size="small"
                />
                <Button appearance="primary" type="submit" icon={<AddRegular />} size="small">
                  Add Reminder
                </Button>
              </div>
            </form>

            {/* Active Jobs */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1' }}>Scheduled Items ({scheduledJobs.length})</span>
              </div>
              {scheduledJobs.length === 0 ? (
                <div style={{ fontSize: 12, color: '#64748b', fontStyle: 'italic', padding: 8 }}>No active reminders scheduled.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {scheduledJobs.map((job) => (
                    <div
                      key={job.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 14px',
                        background: 'rgba(255, 255, 255, 0.04)',
                        borderRadius: 8,
                        border: '1px solid rgba(255, 255, 255, 0.06)'
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{job.title}</span>
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <Badge appearance="tint" color="informative" size="small">{job.schedule_type}</Badge>
                          <span style={{ fontSize: 11, color: '#94a3b8' }}>
                            Next: {new Date(job.next_run_at).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                      <Button
                        appearance="subtle"
                        icon={<DeleteRegular style={{ color: '#ef4444' }} />}
                        size="small"
                        onClick={() => handleCancelJob(job.id)}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Run Logs */}
            <div style={{ marginTop: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 8 }}>
                Recent Execution Logs
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {schedulerLogs.slice(0, 8).map((log) => (
                  <div
                    key={log.id}
                    style={{
                      padding: '8px 12px',
                      background: 'rgba(255, 255, 255, 0.02)',
                      borderRadius: 6,
                      fontSize: 12,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 600, color: log.status === 'success' ? '#10b981' : '#ef4444' }}>
                        [{log.status.toUpperCase()}]
                      </span>{' '}
                      <span style={{ color: '#e2e8f0' }}>{log.result_summary}</span>
                    </div>
                    <span style={{ color: '#64748b', fontSize: 11 }}>
                      {log.duration_ms ? `${log.duration_ms.toFixed(0)}ms` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ================= TAB: FINANCE WATCHLIST ================= */}
        {selectedTab === 'finance' && (
          <>
            <div style={{ padding: '10px 14px', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.25)', borderRadius: 8, fontSize: 11, color: '#93c5fd' }}>
              <strong>Informational Watchlist Only:</strong> Phenom strictly enforces code-level prohibitions against trading, order placement, and buy/sell suggestions. Alerts trigger once when target is reached.
            </div>

            {/* Add Watchlist Form */}
            <form onSubmit={handleAddWatchlist} style={{ display: 'flex', flexDirection: 'column', gap: 10, background: 'rgba(255, 255, 255, 0.03)', padding: 14, borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.08)' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#93c5fd' }}>Add Symbol Alert</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input
                  placeholder="Ticker (e.g. AAPL, BTC)"
                  value={newWatchSymbol}
                  onChange={(_, d) => setNewWatchSymbol(d.value)}
                  style={{ flex: 1 }}
                  size="small"
                />
                <Input
                  type="number"
                  placeholder="Target $"
                  value={newWatchPrice}
                  onChange={(_, d) => setNewWatchPrice(d.value)}
                  style={{ width: 100 }}
                  size="small"
                />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <select
                  value={newWatchCondition}
                  onChange={(e) => setNewWatchCondition(e.target.value)}
                  style={{ background: '#1e293b', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '4px 8px', fontSize: 12, flex: 1 }}
                >
                  <option value="above">Alert when Price &gt;= Target</option>
                  <option value="below">Alert when Price &lt;= Target</option>
                </select>
                <select
                  value={newWatchType}
                  onChange={(e) => setNewWatchType(e.target.value)}
                  style={{ background: '#1e293b', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '4px 8px', fontSize: 12, width: 100 }}
                >
                  <option value="stock">Stock</option>
                  <option value="crypto">Crypto</option>
                </select>
                <Button appearance="primary" type="submit" icon={<AddRegular />} size="small">
                  Add
                </Button>
              </div>
            </form>

            {/* Watchlist Table */}
            <div>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 8 }}>
                Active Watchlist ({watchlistItems.length})
              </span>
              {watchlistItems.length === 0 ? (
                <div style={{ fontSize: 12, color: '#64748b', fontStyle: 'italic', padding: 8 }}>No symbols currently watched.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {watchlistItems.map((item) => (
                    <div
                      key={item.symbol}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 14px',
                        background: 'rgba(255, 255, 255, 0.04)',
                        borderRadius: 8,
                        border: '1px solid rgba(255, 255, 255, 0.06)'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 14, fontWeight: 700, color: '#38bdf8' }}>{item.symbol}</span>
                          <Badge appearance="tint" color="informative" size="small">{item.asset_type}</Badge>
                          {item.triggered && (
                            <Badge appearance="filled" color="warning" size="small">TRIGGERED ONCE</Badge>
                          )}
                        </div>
                        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 3 }}>
                          Alert: {item.condition} ${item.target_price.toFixed(2)} | Last: {item.last_price ? `$${item.last_price.toFixed(2)}` : 'Tracking...'}
                        </div>
                      </div>
                      <Button
                        appearance="subtle"
                        icon={<DeleteRegular style={{ color: '#ef4444' }} />}
                        size="small"
                        onClick={() => handleRemoveWatchlist(item.symbol)}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ================= TAB: LIVE LOGS ================= */}
        {selectedTab === 'logs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1' }}>
              Safety Layer Action Log ({actionLogs.length})
            </span>
            {actionLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  padding: '10px 12px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: 8,
                  fontSize: 12,
                  border: '1px solid rgba(255, 255, 255, 0.05)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: '#60a5fa' }}>{log.tool}</span>
                  <Badge appearance="tint" color={log.tier === 0 ? 'success' : log.tier === 1 ? 'informative' : log.tier === 2 ? 'warning' : 'danger'} size="small">
                    Tier {log.tier}
                  </Badge>
                </div>
                <div style={{ color: '#94a3b8', fontSize: 11 }}>
                  Decision: <span style={{ color: '#f8fafc', fontWeight: 600 }}>{log.decision}</span> | Status: <span style={{ color: log.result_status === 'SUCCESS' ? '#10b981' : '#ef4444' }}>{log.result_status}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ================= TAB: TECH NEWS ================= */}
        {selectedTab === 'news' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <NewsRegular style={{ color: '#60a5fa' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1' }}>
                Hacker News, TechCrunch & The Verge
              </span>
            </div>
            {techNewsArticles.map((art, idx) => (
              <div
                key={idx}
                style={{
                  padding: 12,
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: 8,
                  border: '1px solid rgba(255, 255, 255, 0.06)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Badge appearance="tint" color="brand" size="small">{art.source}</Badge>
                </div>
                <a
                  href={art.link}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', textDecoration: 'none', display: 'block', marginBottom: 4 }}
                >
                  {art.title}
                </a>
                <p style={{ fontSize: 11, color: '#94a3b8', margin: 0, lineHeight: '15px' }}>
                  {art.summary}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
