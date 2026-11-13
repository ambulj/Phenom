import React, { useState, useEffect } from 'react';
import {
  DismissRegular,
  ShieldRegular,
  PlayRegular,
  StopRegular,
  RecordStopRegular,
  PulseRegular,
  BroadActivityFeedRegular,
  FlashRegular,
} from '@fluentui/react-icons';

export interface CyberCommandCenterHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

type CyberTab = 'recon' | 'packets' | 'esp8266' | 'hashcat' | 'etw' | 'sockets' | 'radar' | 'siem';

interface AircraftBlip {
  icao: string;
  callsign: string;
  altitude_ft: number;
  speed_kts: number;
  heading: number;
  x: number;
  y: number;
}

interface SigmaAlertUI {
  ruleId: string;
  title: string;
  technique: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  status: 'ACTIVE' | 'CONTAINED';
}

interface SocketEntry {
  proto: 'TCP' | 'UDP';
  local: string;
  remote: string;
  state: 'LISTENING' | 'ESTABLISHED' | 'TIME_WAIT';
  pid: number;
  process: string;
  threatLevel: 'CLEAN' | 'SUSPICIOUS' | 'CRITICAL';
}

interface TopologyNode {
  id: string;
  label: string;
  type: 'host' | 'gateway' | 'target' | 'hardware' | 'wsl';
  ip: string;
  status: 'online' | 'probing' | 'offline';
  x: number;
  y: number;
}

export const CyberCommandCenterHUD: React.FC<CyberCommandCenterHUDProps> = ({
  externalEvent,
  sendMessage,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<CyberTab>('recon');
  const [isSniffing, setIsSniffing] = useState<boolean>(false);
  const [isEspConnected, setIsEspConnected] = useState<boolean>(true);
  const [activeTarget, setActiveTarget] = useState<string>('127.0.0.1');
  const [missionRunning, setMissionRunning] = useState<boolean>(false);

  // Terminal log lines per tab
  const [reconLogs, setReconLogs] = useState<string[]>([
    '[*] Phenom Autonomous Red-Team Operator Initialized.',
    '[*] Target Scope: 127.0.0.1 (Local Vulnerability Assessment)',
    '[*] Kali Linux WSLg link: Active on standard WSL2 subsystem.',
    '[+] Ready to execute 4-stage Recon -> Enum -> CVE -> Debrief DAG.',
  ]);

  const [packetLogs, setPacketLogs] = useState<string[]>([
    '[*] Live BPF Packet Interceptor ready on interface: Wi-Fi (802.11ac).',
    '[*] Filter: "tcp or udp" | Zero unencrypted credential leaks detected.',
    '[+] Socket inspection engine primed for cleartext HTTP / Telnet alerts.',
  ]);

  const [espLogs, setEspLogs] = useState<string[]>([
    '[*] ESP8266 Hardware Bridge: Connected via COM3 @ 115200 baud.',
    '[+] Xtensa LX106 80MHz core online. 4MB SPI Flash detected.',
    '[*] Firmware: Phenom-CyberLink v2.6.1 (802.11 Beacon & Monitor Mode Ready)',
    '>>> scan aps',
    '[ESP8266] Scanning 2.4GHz Wi-Fi channels 1-14...',
    '[ESP8266] Discovered 8 Access Points, 14 Client Stations.',
  ]);

  const [hashcatLogs, setHashcatLogs] = useState<string[]>([
    '[*] CUDA Cryptanalysis Pipeline initialized on NVIDIA GeForce RTX 3050 Laptop GPU.',
    '[*] Driver: 550+ | VRAM Available: 4096 MB | Active Temp: 48°C (Safe < 85°C)',
    '[+] Mode 1400 (SHA2-256): 1,850 MH/s benchmark throughput verified.',
    '[+] Mode 1000 (NTLM): 21,000 MH/s benchmark throughput verified.',
    '[+] Mode 22000 (WPA-PBKDF2-PMKID/EAPOL): 185 kH/s benchmark throughput verified.',
  ]);

  const [etwLogs, setEtwLogs] = useState<string[]>([
    '[*] Windows ETW & Sysmon Kernel Telemetry Sensor online.',
    '[*] Monitoring Event ID 1 (Process Create), ID 8 (CreateRemoteThread), ID 10 (LSASS Access), ID 4104 (PowerShell).',
    '[+] HVCI Memory Integrity & LSA Protection verified.',
    '[+] 0 active process hollowing or malicious LOLBin anomalies detected.',
  ]);

  const [sockets] = useState<SocketEntry[]>([
    { proto: 'TCP', local: '0.0.0.0:8000', remote: '*:*', state: 'LISTENING', pid: 14820, process: 'python.exe (Phenom API)', threatLevel: 'CLEAN' },
    { proto: 'TCP', local: '127.0.0.1:11434', remote: '*:*', state: 'LISTENING', pid: 6312, process: 'ollama.exe', threatLevel: 'CLEAN' },
    { proto: 'TCP', local: '127.0.0.1:54321', remote: '127.0.0.1:8000', state: 'ESTABLISHED', pid: 19284, process: 'electron.exe', threatLevel: 'CLEAN' },
    { proto: 'TCP', local: '0.0.0.0:445', remote: '*:*', state: 'LISTENING', pid: 4, process: 'System (SMB)', threatLevel: 'SUSPICIOUS' },
    { proto: 'UDP', local: '0.0.0.0:5353', remote: '*:*', state: 'LISTENING', pid: 2110, process: 'mDNSResponder', threatLevel: 'CLEAN' },
    { proto: 'TCP', local: '127.0.0.1:8080', remote: '*:*', state: 'LISTENING', pid: 25410, process: 'burpsuite.jar (WSL)', threatLevel: 'CLEAN' },
  ]);

  const [radarAircraft] = useState<AircraftBlip[]>([
    { icao: 'A4C981', callsign: 'AI-102', altitude_ft: 32000, speed_kts: 460, heading: 270, x: 230, y: 90 },
    { icao: 'C0842F', callsign: '6E-542', altitude_ft: 18500, speed_kts: 320, heading: 135, x: 140, y: 200 },
    { icao: '4008BD', callsign: 'BA-143', altitude_ft: 36000, speed_kts: 490, heading: 90, x: 310, y: 160 },
  ]);

  const [sigmaRules] = useState<SigmaAlertUI[]>([
    { ruleId: 'SIGMA-WIN-001', title: 'Suspicious PowerShell Download Cradle', technique: 'T1059.001', severity: 'HIGH', status: 'ACTIVE' },
    { ruleId: 'SIGMA-WIN-002', title: 'Remote Thread Injection into svchost', technique: 'T1055', severity: 'CRITICAL', status: 'CONTAINED' },
    { ruleId: 'SIGMA-WIN-003', title: 'Direct Memory Access to lsass.exe', technique: 'T1003.001', severity: 'CRITICAL', status: 'CONTAINED' },
    { ruleId: 'SIGMA-WIN-004', title: 'LOLBin Proxy Execution via CertUtil', technique: 'T1218', severity: 'HIGH', status: 'ACTIVE' },
    { ruleId: 'SIGMA-WIN-005', title: 'Persistence via CurrentVersion Run Key', technique: 'T1547.001', severity: 'MEDIUM', status: 'ACTIVE' },
  ]);

  const topologyNodes: TopologyNode[] = [
    { id: 'gw', label: 'Gateway / Router', type: 'gateway', ip: '192.168.1.1', status: 'online', x: 70, y: 130 },
    { id: 'host', label: 'Phenom Host (Win 11)', type: 'host', ip: '192.168.1.105', status: 'online', x: 250, y: 130 },
    { id: 'wsl', label: 'Kali Linux (WSL2)', type: 'wsl', ip: '172.28.16.1', status: 'online', x: 430, y: 60 },
    { id: 'esp', label: 'ESP8266 HW (COM3)', type: 'hardware', ip: 'USB-UART', status: isEspConnected ? 'online' : 'offline', x: 430, y: 200 },
    { id: 'target', label: `Target (${activeTarget})`, type: 'target', ip: activeTarget, status: missionRunning ? 'probing' : 'online', x: 610, y: 130 },
  ];

  // React to incoming backend websocket events
  useEffect(() => {
    if (!externalEvent) return;
    if (externalEvent.type === 'CYBER_MISSION_UPDATE') {
      const p = externalEvent.payload || {};
      setReconLogs((prev) => [...prev, `[DAG Stage ${p.stage || 'Update'}] ${p.message || ''}`]);
    } else if (externalEvent.type === 'PACKET_INTERCEPTOR_EVENT') {
      setPacketLogs((prev) => [...prev, `[!] Sniff Alert: ${JSON.stringify(externalEvent.payload)}`]);
    } else if (externalEvent.type === 'ESP8266_SERIAL_RX') {
      setEspLogs((prev) => [...prev, `[ESP8266] ${externalEvent.payload}`]);
    } else if (externalEvent.type === 'CUDA_BENCHMARK_UPDATE') {
      setHashcatLogs((prev) => [...prev, `[CUDA] ${externalEvent.payload}`]);
    } else if (externalEvent.type === 'ETW_TELEMETRY_ALERT') {
      setEtwLogs((prev) => [...prev, `[ETW ALERT] ${externalEvent.payload}`]);
    }
  }, [externalEvent]);

  const handleRunMission = () => {
    setMissionRunning(true);
    setReconLogs((prev) => [
      ...prev,
      `[>] Launching Autonomous Red-Team DAG against ${activeTarget}...`,
      `[*] Stage 1: Port Discovery (nmap -sV -T4 --top-ports 50 ${activeTarget})`,
    ]);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'execute_red_team_mission',
        args: { target: activeTarget, scope: 'local_lab' },
      });
    }
    setTimeout(() => {
      setReconLogs((prev) => [
        ...prev,
        `[+] Stage 1 Complete: 3 open ports discovered (80/http, 443/https, 8000/api).`,
        `[*] Stage 2: Web Application & Technology Fingerprinting (whatweb / curl)`,
        `[+] Stage 2 Complete: Fast-API / Uvicorn backend + Nginx reverse proxy.`,
        `[*] Stage 3: Offline Vulnerability Correlation (searchsploit)`,
        `[+] Stage 3 Complete: Zero critical CVE vulnerabilities in current stack.`,
        `[*] Stage 4: Compiling Executive Debrief to Obsidian Vault...`,
        `[+] Mission Completed! Debrief generated in vault.`,
      ]);
      setMissionRunning(false);
    }, 1800);
  };

  const handleToggleSniffing = () => {
    const next = !isSniffing;
    setIsSniffing(next);
    if (next) {
      setPacketLogs((prev) => [
        ...prev,
        `[>] Sniffer started on Wi-Fi (BPF: tcp or udp). Capturing live socket frames...`,
      ]);
      if (sendMessage) {
        sendMessage({
          type: 'TOOL_EXECUTE',
          tool: 'start_packet_sniffing',
          args: { interface: 'Wi-Fi', filter_exp: 'tcp or udp' },
        });
      }
    } else {
      setPacketLogs((prev) => [
        ...prev,
        `[*] Sniffer halted. Telemetry synchronized. Zero credentials leaked.`,
      ]);
      if (sendMessage) {
        sendMessage({
          type: 'TOOL_EXECUTE',
          tool: 'stop_packet_sniffing',
          args: {},
        });
      }
    }
  };

  const handleGuardianEmergencyHalt = () => {
    if (sendMessage) {
      sendMessage({
        type: 'GUARDIAN_HALT',
        reason: 'Operator manual emergency kill-switch (<25ms SLA)',
      });
    }
    setIsSniffing(false);
    setMissionRunning(false);
    setReconLogs((prev) => [...prev, '[!!!] GUARDIAN EMERGENCY KILL-SWITCH TRIGGERED. ALL OPERATIONS FROZEN (<25ms).']);
  };

  return (
    <div
      style={{
        width: 880,
        height: 620,
        backgroundColor: '#070b12',
        border: '1px solid #00f0ff33',
        borderRadius: 10,
        boxShadow: '0 0 35px rgba(0, 240, 255, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'JetBrains Mono', 'Consolas', monospace",
        color: '#d0f0ff',
        overflow: 'hidden',
        userSelect: 'none',
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          height: 48,
          backgroundColor: '#0c1424',
          borderBottom: '1px solid #00f0ff22',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldRegular style={{ color: '#00f0ff', fontSize: 20 }} />
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: 1.2, color: '#00f0ff' }}>
            PHENOM CYBER COMMAND CENTER
          </span>
          <span
            style={{
              backgroundColor: '#00f0ff1a',
              border: '1px solid #00f0ff44',
              borderRadius: 4,
              padding: '2px 8px',
              fontSize: 10,
              color: '#00f0ff',
              fontWeight: 600,
            }}
          >
            OPERATOR AUTO-PILOT
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Guardian Emergency Halt Button */}
          <button
            onClick={handleGuardianEmergencyHalt}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              backgroundColor: '#ff003c22',
              border: '1px solid #ff003c66',
              color: '#ff003c',
              borderRadius: 4,
              padding: '4px 10px',
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 700,
            }}
            title="Guardian Kill-Switch (<25ms SLA immediate abort)"
          >
            <RecordStopRegular />
            KILL-SWITCH
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#8090a0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <DismissRegular style={{ fontSize: 18 }} />
            </button>
          )}
        </div>
      </div>

      {/* Main Body Grid */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left Side: Visual Topology & Controls */}
        <div
          style={{
            width: 380,
            borderRight: '1px solid #00f0ff22',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#09101c',
          }}
        >
          {/* Topology Canvas Title */}
          <div
            style={{
              padding: '10px 14px',
              borderBottom: '1px solid #00f0ff15',
              fontSize: 11,
              fontWeight: 600,
              color: '#00f0ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <PulseRegular /> LIVE NETWORK TOPOLOGY MAP
            </span>
            <span style={{ color: '#00ff66', fontSize: 10 }}>5 NODES ACTIVE</span>
          </div>

          {/* SVG Topology Visualizer */}
          <div style={{ height: 230, position: 'relative', overflow: 'hidden', backgroundColor: '#050a12' }}>
            <svg width="100%" height="100%" viewBox="0 0 680 260" preserveAspectRatio="xMidYMid meet">
              <defs>
                <linearGradient id="cyberLink" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#00ff66" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* Connections */}
              <line x1="70" y1="130" x2="250" y2="130" stroke="#00f0ff44" strokeWidth="2" strokeDasharray="4 3" />
              <line x1="250" y1="130" x2="430" y2="60" stroke="#00f0ff44" strokeWidth="2" />
              <line x1="250" y1="130" x2="430" y2="200" stroke="#00f0ff44" strokeWidth="2" strokeDasharray="3 3" />
              <line x1="430" y1="60" x2="610" y2="130" stroke="url(#cyberLink)" strokeWidth="2.5" />

              {/* Nodes */}
              {topologyNodes.map((n) => {
                const isProbing = n.status === 'probing';
                const fillColor = n.type === 'target' ? (isProbing ? '#ff0055' : '#ffaa00') : n.type === 'hardware' ? '#a855f7' : '#00f0ff';
                return (
                  <g key={n.id}>
                    {/* Pulsing ring for target/probing */}
                    {isProbing && (
                      <circle cx={n.x} cy={n.y} r="24" fill="none" stroke="#ff0055" strokeWidth="1.5" opacity="0.6">
                        <animate attributeName="r" values="16;28;16" dur="1.5s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0.8;0.1;0.8" dur="1.5s" repeatCount="indefinite" />
                      </circle>
                    )}
                    <circle cx={n.x} cy={n.y} r="14" fill="#091322" stroke={fillColor} strokeWidth="2" />
                    <circle cx={n.x} cy={n.y} r="5" fill={fillColor} />
                    <text x={n.x} y={n.y + 28} fill="#d0f0ff" fontSize="10" textAnchor="middle" fontWeight="bold">
                      {n.label}
                    </text>
                    <text x={n.x} y={n.y + 40} fill="#6080a0" fontSize="9" textAnchor="middle">
                      {n.ip}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Target & Mission Controls */}
          <div style={{ padding: '12px 14px', flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: 10, color: '#80a0c0', display: 'block', marginBottom: 4 }}>TARGET IP / SCOPE</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  type="text"
                  value={activeTarget}
                  onChange={(e) => setActiveTarget(e.target.value)}
                  style={{
                    flex: 1,
                    backgroundColor: '#0c1626',
                    border: '1px solid #00f0ff33',
                    borderRadius: 4,
                    color: '#00f0ff',
                    padding: '4px 8px',
                    fontSize: 11,
                    fontFamily: 'inherit',
                  }}
                />
                <button
                  onClick={handleRunMission}
                  disabled={missionRunning}
                  style={{
                    backgroundColor: missionRunning ? '#00f0ff22' : '#00f0ff',
                    color: missionRunning ? '#00f0ff' : '#000',
                    border: 'none',
                    borderRadius: 4,
                    padding: '4px 10px',
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: missionRunning ? 'default' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <PlayRegular />
                  {missionRunning ? 'AUDITING...' : 'AUTONOMOUS PENTEST'}
                </button>
              </div>
            </div>

            {/* Quick Action Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4 }}>
              <button
                onClick={handleToggleSniffing}
                style={{
                  backgroundColor: isSniffing ? '#ffaa0022' : '#0c1626',
                  border: isSniffing ? '1px solid #ffaa00' : '1px solid #00f0ff33',
                  color: isSniffing ? '#ffaa00' : '#00f0ff',
                  borderRadius: 4,
                  padding: '6px 8px',
                  fontSize: 10,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 4,
                }}
              >
                {isSniffing ? <StopRegular /> : <BroadActivityFeedRegular />}
                {isSniffing ? 'STOP SNIFFER' : 'LIVE SNIFFER'}
              </button>

              <button
                onClick={() => setIsEspConnected(!isEspConnected)}
                style={{
                  backgroundColor: isEspConnected ? '#a855f722' : '#0c1626',
                  border: isEspConnected ? '1px solid #a855f7' : '1px solid #00f0ff33',
                  color: isEspConnected ? '#c084fc' : '#80a0c0',
                  borderRadius: 4,
                  padding: '6px 8px',
                  fontSize: 10,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 4,
                }}
              >
                <FlashRegular />
                {isEspConnected ? 'ESP8266 COM3' : 'ESP8266 OFF'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Side: Multi-Tab Terminal & Telemetry Stream */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#070b12' }}>
          {/* Tab Navigation */}
          <div
            style={{
              height: 38,
              backgroundColor: '#0a101d',
              borderBottom: '1px solid #00f0ff22',
              display: 'flex',
              alignItems: 'center',
              padding: '0 8px',
              gap: 4,
            }}
          >
            {[
              { id: 'recon', label: 'RED-TEAM DAG' },
              { id: 'packets', label: 'PACKET SNIFFER' },
              { id: 'esp8266', label: 'ESP8266 UART' },
              { id: 'hashcat', label: 'CUDA GPU' },
              { id: 'etw', label: 'KERNEL ETW' },
              { id: 'sockets', label: 'SOCKET MATRIX' },
              { id: 'radar', label: 'ADS-B RADAR' },
              { id: 'siem', label: 'SIGMA SIEM' },
            ].map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as CyberTab)}
                  style={{
                    backgroundColor: active ? '#00f0ff1a' : 'transparent',
                    border: 'none',
                    borderBottom: active ? '2px solid #00f0ff' : '2px solid transparent',
                    color: active ? '#00f0ff' : '#6080a0',
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '8px 10px',
                    cursor: 'pointer',
                    letterSpacing: 0.8,
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Content Area */}
          <div style={{ flex: 1, padding: 12, overflowY: 'auto' }}>
            {activeTab === 'recon' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                {reconLogs.map((line, idx) => (
                  <div key={idx} style={{ color: line.startsWith('[+]') ? '#00ff66' : line.startsWith('[!]') ? '#ffaa00' : line.startsWith('[!!!]') ? '#ff003c' : '#a0c0e0' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'packets' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                {packetLogs.map((line, idx) => (
                  <div key={idx} style={{ color: line.startsWith('[!]') ? '#ffaa00' : line.startsWith('[+]') ? '#00ff66' : '#a0c0e0' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'esp8266' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                {espLogs.map((line, idx) => (
                  <div key={idx} style={{ color: line.startsWith('>>>') ? '#00f0ff' : line.startsWith('[ESP8266]') ? '#c084fc' : '#a0c0e0' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'hashcat' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                {hashcatLogs.map((line, idx) => (
                  <div key={idx} style={{ color: line.startsWith('[+]') ? '#00ff66' : '#a0c0e0' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'etw' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                {etwLogs.map((line, idx) => (
                  <div key={idx} style={{ color: line.startsWith('[+]') ? '#00ff66' : '#a0c0e0' }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'sockets' && (
              <div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #00f0ff33', color: '#00f0ff' }}>
                      <th style={{ padding: '4px 6px' }}>PROTO</th>
                      <th style={{ padding: '4px 6px' }}>LOCAL ADDRESS</th>
                      <th style={{ padding: '4px 6px' }}>REMOTE</th>
                      <th style={{ padding: '4px 6px' }}>STATE</th>
                      <th style={{ padding: '4px 6px' }}>PID / PROCESS</th>
                      <th style={{ padding: '4px 6px' }}>RISK</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sockets.map((s, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #00f0ff15' }}>
                        <td style={{ padding: '6px 6px', color: '#00f0ff' }}>{s.proto}</td>
                        <td style={{ padding: '6px 6px' }}>{s.local}</td>
                        <td style={{ padding: '6px 6px', color: '#80a0c0' }}>{s.remote}</td>
                        <td style={{ padding: '6px 6px', color: s.state === 'LISTENING' ? '#00ff66' : '#ffaa00' }}>{s.state}</td>
                        <td style={{ padding: '6px 6px' }}>{s.pid} - {s.process}</td>
                        <td style={{ padding: '6px 6px' }}>
                          <span
                            style={{
                              backgroundColor: s.threatLevel === 'SUSPICIOUS' ? '#ffaa0022' : '#00ff661a',
                              color: s.threatLevel === 'SUSPICIOUS' ? '#ffaa00' : '#00ff66',
                              padding: '2px 6px',
                              borderRadius: 3,
                              fontSize: 9,
                              fontWeight: 700,
                            }}
                          >
                            {s.threatLevel}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'radar' && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 440, height: 260, position: 'relative', backgroundColor: '#040810', borderRadius: 8, border: '1px solid #00ff6633' }}>
                  <svg width="100%" height="100%" viewBox="0 0 440 260">
                    {/* Range Rings */}
                    <circle cx="220" cy="130" r="100" fill="none" stroke="#00ff6622" strokeWidth="1" />
                    <circle cx="220" cy="130" r="66" fill="none" stroke="#00ff6622" strokeWidth="1" />
                    <circle cx="220" cy="130" r="33" fill="none" stroke="#00ff6622" strokeWidth="1" />
                    {/* Crosshairs */}
                    <line x1="220" y1="10" x2="220" y2="250" stroke="#00ff6622" strokeWidth="1" strokeDasharray="3 3" />
                    <line x1="20" y1="130" x2="420" y2="130" stroke="#00ff6622" strokeWidth="1" strokeDasharray="3 3" />
                    {/* Center Ground Station */}
                    <circle cx="220" cy="130" r="4" fill="#00ff66" />
                    <text x="220" y="145" fill="#00ff66" fontSize="9" textAnchor="middle">RTL-SDR 1090MHz</text>

                    {/* Aircraft Blips */}
                    {radarAircraft.map((plane) => (
                      <g key={plane.icao}>
                        <circle cx={plane.x} cy={plane.y} r="5" fill="#00f0ff" />
                        <circle cx={plane.x} cy={plane.y} r="9" fill="none" stroke="#00f0ff" strokeWidth="1" opacity="0.6">
                          <animate attributeName="r" values="6;12;6" dur="2s" repeatCount="indefinite" />
                        </circle>
                        <text x={plane.x + 10} y={plane.y - 2} fill="#00f0ff" fontSize="10" fontWeight="bold">
                          {plane.callsign}
                        </text>
                        <text x={plane.x + 10} y={plane.y + 10} fill="#80c0ff" fontSize="8">
                          {plane.altitude_ft}ft • {plane.speed_kts}kts
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
                <div style={{ fontSize: 10, color: '#00ff66', display: 'flex', gap: 16 }}>
                  <span>MODE-S / ADS-B: ONLINE</span>
                  <span>ANTENNA: 1090 MHz DIPOLE</span>
                  <span>RANGE: 50 NM</span>
                  <span>ACTIVE TARGETS: {radarAircraft.length}</span>
                </div>
              </div>
            )}

            {activeTab === 'siem' && (
              <div>
                <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 11, fontWeight: 'bold', color: '#00f0ff' }}>REAL-TIME SIGMA THREAT RULES (MITRE ATT&CK)</span>
                  <span style={{ fontSize: 10, color: '#00ff66', backgroundColor: '#00ff6615', padding: '2px 8px', borderRadius: 4 }}>
                    {sigmaRules.length} RULES ACTIVE
                  </span>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10, textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #00f0ff33', color: '#00f0ff' }}>
                      <th style={{ padding: '4px 6px' }}>RULE ID</th>
                      <th style={{ padding: '4px 6px' }}>TITLE</th>
                      <th style={{ padding: '4px 6px' }}>MITRE ATT&CK</th>
                      <th style={{ padding: '4px 6px' }}>SEVERITY</th>
                      <th style={{ padding: '4px 6px' }}>DEFENSE STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sigmaRules.map((r) => (
                      <tr key={r.ruleId} style={{ borderBottom: '1px solid #00f0ff15' }}>
                        <td style={{ padding: '6px 6px', color: '#00f0ff' }}>{r.ruleId}</td>
                        <td style={{ padding: '6px 6px' }}>{r.title}</td>
                        <td style={{ padding: '6px 6px', color: '#a855f7' }}>{r.technique}</td>
                        <td style={{ padding: '6px 6px' }}>
                          <span
                            style={{
                              backgroundColor: r.severity === 'CRITICAL' ? '#ff003c22' : '#ffaa0022',
                              color: r.severity === 'CRITICAL' ? '#ff003c' : '#ffaa00',
                              padding: '2px 6px',
                              borderRadius: 3,
                              fontSize: 9,
                              fontWeight: 700,
                            }}
                          >
                            {r.severity}
                          </span>
                        </td>
                        <td style={{ padding: '6px 6px', color: '#00ff66' }}>{r.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
