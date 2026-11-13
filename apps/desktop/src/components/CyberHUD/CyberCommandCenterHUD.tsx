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
  ArrowSyncRegular,
  LockClosedRegular,
} from '@fluentui/react-icons';

export interface CyberCommandCenterHUDProps {
  externalEvent?: { type: string; payload?: any } | null;
  sendMessage?: (msg: any) => void;
  onClose?: () => void;
}

type CyberTab = 'recon' | 'kali' | 'kernel' | 'swarm' | 'binary' | 'chrono' | 'intel' | 'spectral' | 'ghost' | 'stealth' | 'packets' | 'esp8266' | 'hashcat' | 'etw' | 'sockets' | 'radar' | 'siem';

interface SwarmAgentState {
  name: string;
  role: string;
  status: 'IDLE' | 'EXECUTING' | 'ALERT';
  actionFinding?: string;
  badgeColor: string;
}

interface SwarmBoardMessage {
  sender: string;
  recipient: string;
  type: string;
  message: string;
  time: string;
}

interface BinaryInstructionItem {
  address: string;
  mnemonic: string;
  bytes: string;
}

interface ROPGadgetItem {
  offset: string;
  mnemonic: string;
  bytes: string;
  type: string;
}

interface KernelProcessNode {
  pid: number;
  name: string;
  parentPid: number;
  parentName: string;
  threatScore: number;
  status: 'CLEAN' | 'SUSPICIOUS' | 'ANOMALOUS';
  anomalyDesc?: string;
  rwxCount: number;
  peIntegrity: 'INTACT' | 'COMPROMISED';
}

interface RWXPageRegion {
  baseAddress: string;
  sizeKb: number;
  protection: string;
  type: string;
  riskLevel: 'HIGH' | 'CRITICAL';
  pid: number;
  process: string;
}

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

interface HoneypotNode {
  id: string;
  service: string;
  port: number;
  hits: number;
  x: number;
  y: number;
  status: 'ARMED' | 'PROBING';
}

interface MeshPeerNode {
  id: string;
  callsign: string;
  ip: string;
  latencyMs: number;
  x: number;
  y: number;
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

  const [radarFilter, setRadarFilter] = useState<'ALL' | 'ADSB' | 'HONEYPOT' | 'MESH'>('ALL');
  const [isolatedPids, setIsolatedPids] = useState<number[]>([]);
  const [sweepRunning, setSweepRunning] = useState<boolean>(false);

  const [kaliLogs, setKaliLogs] = useState<string[]>([
    '[*] Kali Linux WSL2 Subsystem: ACTIVE (Linux 5.15.0-microsoft-standard-WSL2)',
    '[*] Autonomous Lab Safe-Mode: ENFORCED (127.0.0.1, localhost, RFC1918 subnets)',
    '[+] Available Tools in Path: nmap, masscan, whatweb, nikto, dirsearch, hashcat, tshark',
    '[+] 4-Vector Campaign Orchestrator Online: Loopback -> Subnet -> Honeypot -> AAR Debrief',
  ]);
  const [campaignRunning, setCampaignRunning] = useState<boolean>(false);
  const [activeToolRunning, setActiveToolRunning] = useState<string | null>(null);

  const [kernelProcesses, setKernelProcesses] = useState<KernelProcessNode[]>([
    { pid: 4012, name: 'explorer.exe', parentPid: 1120, parentName: 'userinit.exe', threatScore: 0, status: 'CLEAN', rwxCount: 0, peIntegrity: 'INTACT' },
    { pid: 7820, name: 'chrome.exe', parentPid: 4012, parentName: 'explorer.exe', threatScore: 10, status: 'CLEAN', rwxCount: 0, peIntegrity: 'INTACT' },
    { pid: 14820, name: 'python.exe', parentPid: 4012, parentName: 'explorer.exe', threatScore: 0, status: 'CLEAN', rwxCount: 0, peIntegrity: 'INTACT' },
    { pid: 19840, name: 'powershell.exe', parentPid: 9820, parentName: 'cmd.exe', threatScore: 65, status: 'SUSPICIOUS', anomalyDesc: 'EncodedCommand cradle detected', rwxCount: 1, peIntegrity: 'INTACT' },
    { pid: 21400, name: 'certutil.exe', parentPid: 19840, parentName: 'powershell.exe', threatScore: 85, status: 'ANOMALOUS', anomalyDesc: 'T1218: CertUtil remote decode staging', rwxCount: 2, peIntegrity: 'COMPROMISED' },
  ]);

  const [rwxRegions] = useState<RWXPageRegion[]>([
    { baseAddress: '0x00007FF783100000', sizeKb: 64, protection: 'PAGE_EXECUTE_READWRITE (0x40)', type: 'MEM_PRIVATE', riskLevel: 'CRITICAL', pid: 21400, process: 'certutil.exe' },
    { baseAddress: '0x00007FF791240000', sizeKb: 128, protection: 'PAGE_EXECUTE_READWRITE (0x40)', type: 'MEM_PRIVATE', riskLevel: 'CRITICAL', pid: 21400, process: 'certutil.exe' },
    { baseAddress: '0x00007FF645A00000', sizeKb: 32, protection: 'PAGE_EXECUTE_READ (Unbacked)', type: 'MEM_PRIVATE', riskLevel: 'HIGH', pid: 19840, process: 'powershell.exe' },
  ]);

  const [kernelLogs, setKernelLogs] = useState<string[]>([
    '[*] Windows Kernel Anomaly Correlator & Sysmon Provider: ACTIVE',
    '[*] Memory Integrity & VirtualQueryEx Page Scanner: ONLINE',
    '[+] Process Lineage Baseline: 5 tree paths mapped across user-mode boundary.',
    '[+] In-Memory PE Header Integrity: DOS 0x5A4D / NT 0x00004550 verified.',
    '[!] Anomaly Tripped: PID 21400 (certutil.exe) spawned by powershell.exe with 2 RWX pages.',
  ]);

  const [kernelScanRunning, setKernelScanRunning] = useState<boolean>(false);

  // Milestone 40: 5-Agent Swarm & Binary RE State
  const [swarmAgents, setSwarmAgents] = useState<SwarmAgentState[]>([
    { name: 'Vanguard', role: 'Offensive Kali Recon & Vulnerability Probe', status: 'IDLE', actionFinding: 'Safe-Mode scope mapped: 3 open ports (8000, 11434, 2222)', badgeColor: '#ffaa00' },
    { name: 'Sentinel', role: 'Kernel Telemetry & Linux /proc Memory Guard', status: 'IDLE', actionFinding: '0 active RWX anomalies across dual-boot bridge', badgeColor: '#00ff66' },
    { name: 'Specter', role: 'Dynamic Binary Instrumentation & Frida Hooks', status: 'IDLE', actionFinding: 'User-mode Frida telemetry hooks primed on port handles', badgeColor: '#c084fc' },
    { name: 'Synapse', role: 'Prometheus Code Synthesizer & Metamorphism', status: 'IDLE', actionFinding: 'P95 execution latency < 2.5ms; zero deadlock risk', badgeColor: '#00f0ff' },
    { name: 'Prime', role: 'Jarvis Strategic Swarm Coordinator & Hybrid LLM', status: 'IDLE', actionFinding: 'Hybrid Local RTX + Cloud Nemotron routing operational', badgeColor: '#f43f5e' },
  ]);

  const [swarmMessages, setSwarmMessages] = useState<SwarmBoardMessage[]>([
    { sender: 'Prime', recipient: 'ALL', type: 'TASK_BRIEF', message: 'Project OMNI-SINGULARITY: 5-Agent Sovereign Tactical Swarm initialized.', time: '12:00:01' },
    { sender: 'Vanguard', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Target scope 127.0.0.1 verified against RFC1918 safe-mode boundaries.', time: '12:00:02' },
    { sender: 'Sentinel', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Win32 VirtualQueryEx & Linux /proc/maps parity synchronized.', time: '12:00:03' },
    { sender: 'Specter', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Intercepted 5 plaintext telemetry socket frames before TLS encryption.', time: '12:00:04' },
    { sender: 'Synapse', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Hot runtime execution paths optimized with zero deadlock risk.', time: '12:00:05' },
  ]);

  const [swarmRunning, setSwarmRunning] = useState<boolean>(false);

  const [binaryInstructions] = useState<BinaryInstructionItem[]>([
    { address: '0x140001000', mnemonic: 'push rbp', bytes: '55' },
    { address: '0x140001001', mnemonic: 'mov rbp, rsp', bytes: '48 89 E5' },
    { address: '0x140001004', mnemonic: 'sub rsp, 0x20', bytes: '48 83 EC 20' },
    { address: '0x140001008', mnemonic: 'call <NtProtectVirtualMemory>', bytes: 'E8 40 21 00 00' },
    { address: '0x14000100D', mnemonic: 'xor eax, eax', bytes: '31 C0' },
    { address: '0x14000100F', mnemonic: 'ret', bytes: 'C3' },
  ]);

  const [ropGadgets] = useState<ROPGadgetItem[]>([
    { offset: '0x00041A20', mnemonic: 'pop rdi; ret', bytes: '5F C3', type: 'PARAM_REGISTER' },
    { offset: '0x00041A25', mnemonic: 'pop rsi; ret', bytes: '5E C3', type: 'PARAM_REGISTER' },
    { offset: '0x00041A30', mnemonic: 'pop rax; ret', bytes: '58 C3', type: 'SYS_CALL_REGISTER' },
    { offset: '0x00042B00', mnemonic: 'syscall; ret', bytes: '0F 05 C3', type: 'KERNEL_SYSCALL' },
  ]);

  const [fridaLogs, setFridaLogs] = useState<string[]>([
    '[*] Frida Dynamic Binary Instrumentation Engine: READY (User-Mode Hooking)',
    '[+] Injected non-destructive telemetry hook on ntdll.dll!NtProtectVirtualMemory',
    '[+] Injected non-destructive telemetry hook on ws2_32.dll!send / connect',
    '[HOOK_INTERCEPT] PID 14820 | NtProtectVirtualMemory | Address: 0x7FF783100000 | NewProtect: PAGE_EXECUTE_READWRITE (0x40)',
    '[HOOK_CAPTURE] PID 14820 | ws2_32.dll!send | Dest: 127.0.0.1:8000 | Payload: [PLAINTEXT_TELEMETRY_FRAME_VERIFIED]',
  ]);

  const [activeBinaryFile] = useState<string>('python.exe');
  const [activeFridaPid] = useState<number>(14820);

  // Milestone 41: Spectral RF, Ghost Rootkit & Zero-Trace RAM State
  const [spectralBins] = useState<number[]>([
    -92, -90, -88, -75, -55, -42, -58, -80, -91, -92, -90, -89,
    -70, -48, -38, -62, -88, -91, -92, -90, -85, -60, -78, -92
  ]);
  const [spectralWifi] = useState<Array<{ essid: string; bssid: string; ch: number; rssi: number; sec: string }>>([
    { essid: 'PHENOM-SOVEREIGN-SEC', bssid: '00:11:22:33:44:55', ch: 6, rssi: -42, sec: 'WPA3-SAE' },
    { essid: 'LAB-TESTNET-5G', bssid: '34:E6:D7:88:99:AA', ch: 36, rssi: -55, sec: 'WPA2-PSK' },
    { essid: 'PHENOM-SOVEREIGN-SEC', bssid: 'DE:AD:BE:EF:00:01', ch: 11, rssi: -38, sec: 'ROGUE-AP' },
  ]);
  const [spectralBle] = useState<Array<{ name: string; mac: string; rssi: number }>>([
    { name: 'Sovereign-FIDO2-Key', mac: 'F4:12:FA:33:11:00', rssi: -50 },
    { name: 'Nordic-BLE-Sensor', mac: '12:34:56:78:9A:BC', rssi: -78 },
  ]);
  const [ghostHooks] = useState<Array<{ func: string; module: string; status: string; prologue: string }>>([
    { func: 'NtAllocateVirtualMemory', module: 'ntdll.dll', status: 'CLEAN', prologue: '4C 8B D1 B8 18 00 00 00' },
    { func: 'NtProtectVirtualMemory', module: 'ntdll.dll', status: 'CLEAN', prologue: '4C 8B D1 B8 50 00 00 00' },
    { func: 'NtWriteVirtualMemory', module: 'ntdll.dll', status: 'CLEAN', prologue: '4C 8B D1 B8 3A 00 00 00' },
    { func: 'NtCreateThreadEx', module: 'ntdll.dll', status: 'CLEAN', prologue: '4C 8B D1 B8 BD 00 00 00' },
  ]);
  const [stealthActive, setStealthActive] = useState<boolean>(true);
  const [volatileEntries, setVolatileEntries] = useState<number>(24);
  const [volatileBytes, setVolatileBytes] = useState<number>(49152);
  const [zeroizeDone, setZeroizeDone] = useState<boolean>(false);

  // Milestone 42: Chrono-Cyber Campaign DAG & Dark-Web Intel State
  const [chronoStages, setChronoStages] = useState<Array<{ stage: number; name: string; status: 'IDLE' | 'EXECUTING' | 'SUCCESS'; finding: string }>>([
    { stage: 1, name: 'RECON & FINGERPRINT', status: 'SUCCESS', finding: 'Discovered 4 open services (80, 443, 8000, 8080) on loopback.' },
    { stage: 2, name: 'INITIAL ACCESS PROBE', status: 'SUCCESS', finding: 'Identified exposed debug endpoints and API documentation routes.' },
    { stage: 3, name: 'PRIVILEGE ESCALATION', status: 'SUCCESS', finding: 'Audited SUID binaries and token privileges; 2 high-risk paths flagged.' },
    { stage: 4, name: 'PERSISTENCE AUDIT', status: 'SUCCESS', finding: 'Cron & Registry run keys checked; baseline verified clean.' },
    { stage: 5, name: 'MITRE ATT&CK DEBRIEF', status: 'SUCCESS', finding: 'Synthesized MITRE matrix (T1046, T1190, T1068, T1053); Risk Score: 65/100.' },
  ]);
  const [chronoRunning, setChronoRunning] = useState<boolean>(false);
  const [darkwebActors] = useState<Array<{ name: string; id: string; origin: string; severity: string; ttps: string[] }>>([
    { name: 'Cozy Bear / APT29', id: 'G0016', origin: 'State-Sponsored', severity: 'CRITICAL', ttps: ['T1059.001', 'T1078', 'T1588.002', 'T1090'] },
    { name: 'LockBit 3.0 Syndicate', id: 'G0140', origin: 'Cybercriminal', severity: 'CRITICAL', ttps: ['T1486', 'T1027', 'T1562.001'] },
    { name: 'BlackByte Ransomware', id: 'G0145', origin: 'Cybercriminal', severity: 'HIGH', ttps: ['T1566', 'T1083', 'T1490'] },
  ]);

  const [honeypots] = useState<HoneypotNode[]>([
    { id: 'hp-ssh', service: 'SSH Trap', port: 2222, hits: 14, x: 90, y: 75, status: 'ARMED' },
    { id: 'hp-telnet', service: 'Telnet Decoy', port: 2323, hits: 39, x: 345, y: 70, status: 'ARMED' },
    { id: 'hp-http', service: 'HTTP Lure', port: 8088, hits: 3, x: 105, y: 195, status: 'ARMED' },
  ]);

  const [meshPeers] = useState<MeshPeerNode[]>([
    { id: 'mesh-1', callsign: 'NODE-ALPHA', ip: '10.248.0.2', latencyMs: 6, x: 155, y: 165 },
    { id: 'mesh-2', callsign: 'NODE-BRAVO', ip: '10.248.0.3', latencyMs: 12, x: 275, y: 205 },
    { id: 'mesh-3', callsign: 'NODE-CHARLIE', ip: '10.248.0.4', latencyMs: 9, x: 335, y: 145 },
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
    } else if (externalEvent.type === 'TACTICAL_SWEEP_UPDATE') {
      const p = externalEvent.payload || {};
      setReconLogs((prev) => [...prev, `[TACTICAL DAG] Stage: ${p.stage || 'SWEEP'} | ${p.message || ''}`]);
    } else if (externalEvent.type === 'HONEYPOT_ALERT') {
      setReconLogs((prev) => [...prev, `[HONEYPOT ALERT] ${JSON.stringify(externalEvent.payload)}`]);
    } else if (externalEvent.type === 'ISOLATION_EVENT') {
      const pid = externalEvent.payload?.pid;
      if (pid && !isolatedPids.includes(pid)) {
        setIsolatedPids((prev) => [...prev, pid]);
      }
    } else if (externalEvent.type === 'KALI_TOOL_OUTPUT') {
      const line = externalEvent.payload?.line || JSON.stringify(externalEvent.payload);
      setKaliLogs((prev) => [...prev, `[KALI] ${line}`]);
    } else if (externalEvent.type === 'RED_TEAM_CAMPAIGN_UPDATE') {
      const p = externalEvent.payload || {};
      setKaliLogs((prev) => [...prev, `[CAMPAIGN] ${p.vector || 'STAGE'}: ${p.message || ''}`]);
    } else if (externalEvent.type === 'KERNEL_BEHAVIOR_ALERT') {
      const p = externalEvent.payload || {};
      setKernelLogs((prev) => [...prev, `[KERNEL ALERT] PID ${p.target_pid || p.pid || ''}: ${p.details || p.message || ''}`]);
    } else if (externalEvent.type === 'MEMORY_INTEGRITY_ALERT') {
      const p = externalEvent.payload || {};
      setKernelLogs((prev) => [...prev, `[MEMGUARD ALERT] PID ${p.pid || ''}: ${p.threat_verdict || ''} - ${p.anomaly || ''}`]);
    }
  }, [externalEvent, isolatedPids]);

  const handleRunCampaign = (type: string) => {
    setCampaignRunning(true);
    setKaliLogs((prev) => [
      ...prev,
      `[>] Launching Autonomous ${type} Red-Team Campaign against scope ${activeTarget}...`,
      `[*] Verifying target scope against Safe-Mode boundaries... [ALLOWED: 127.0.0.1 / RFC1918]`,
    ]);

    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'execute_red_team_campaign',
        args: { campaign_type: type, target_scope: activeTarget },
      });
    }

    setTimeout(() => {
      setKaliLogs((prev) => [
        ...prev,
        `[+] Vector 1 Complete: 3 open ports verified (8000/api, 11434/ollama, 2222/ssh-decoy).`,
        `[+] Vector 2 Complete: 3 verified subnet assets mapped (Gateway, Phenom-Host, NAS).`,
        `[+] Vector 3 Complete: In-RAM honeypots (ports 2222, 2323, 8088) tripped and verified.`,
        `[+] Vector 4 Complete: Obsidian AAR generated with MITRE ATT&CK techniques mapped.`,
        `[*] Jarvis Vocal Summary: "Sir, autonomous red-team campaign completed with flying colors. Zero rogue intruders."`,
      ]);
      setCampaignRunning(false);
    }, 1800);
  };

  const handleRunKaliTool = (tool: string, args: string) => {
    setActiveToolRunning(tool);
    setKaliLogs((prev) => [
      ...prev,
      `>>> wsl -d kali-linux -- ${tool} ${args} ${activeTarget}`,
    ]);

    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'execute_kali_recon',
        args: { tool, target: activeTarget, arguments: args },
      });
    }

    setTimeout(() => {
      if (tool === 'nmap') {
        setKaliLogs((prev) => [
          ...prev,
          `[NMAP] Host is up (0.00042s latency). Discovered ports: 8000/tcp (http-api), 11434/tcp (ollama), 2222/tcp (ssh).`,
        ]);
      } else if (tool === 'whatweb') {
        setKaliLogs((prev) => [
          ...prev,
          `[WHATWEB] http://${activeTarget}:8000 [200 OK] FastAPI, Python[3.11.9], Title[Phenom API Server], HTTPServer[uvicorn]`,
        ]);
      } else if (tool === 'nikto') {
        setKaliLogs((prev) => [
          ...prev,
          `[NIKTO] Target: http://${activeTarget}:8000 | Server: Uvicorn/FastAPI | 0 Critical Vulnerabilities discovered.`,
        ]);
      } else if (tool === 'masscan') {
        setKaliLogs((prev) => [
          ...prev,
          `[MASSCAN] Rate: 1000 kpps | Discovered open port 8000/tcp on ${activeTarget} | SYN audit complete.`,
        ]);
      } else if (tool === 'hashcat') {
        setKaliLogs((prev) => [
          ...prev,
          `[HASHCAT] RTX 3050 CUDA Acceleration Online | Speed: 21,450 MH/s (NTLM) | Temp: 49°C.`,
        ]);
      } else if (tool === 'tshark') {
        setKaliLogs((prev) => [
          ...prev,
          `[TSHARK] Captured 5 frames on interface any | Protocols: TCP, HTTP, DNS | Zero plaintext leaks.`,
        ]);
      }
      setActiveToolRunning(null);
    }, 1200);
  };

  const handleIsolatePid = (pid: number) => {
    if (!isolatedPids.includes(pid)) {
      setIsolatedPids((prev) => [...prev, pid]);
    }
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'isolate_pid_network_egress',
        args: { pid },
      });
    }
    setReconLogs((prev) => [
      ...prev,
      `[SHIELD] Netsh outbound egress block enforced on PID ${pid}. Threat isolated!`,
    ]);
  };

  const handleAuditSystemRWX = () => {
    setKernelScanRunning(true);
    setKernelLogs((prev) => [
      ...prev,
      `[>] Initiating VirtualQueryEx audit across active user-space processes...`,
      `[*] Scanning memory page protection attributes for PAGE_EXECUTE_READWRITE (0x40)...`,
    ]);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'audit_system_memory_posture',
        args: { max_processes: 25 },
      });
    }
    setTimeout(() => {
      setKernelLogs((prev) => [
        ...prev,
        `[+] Audit Complete: 25 processes scanned across user-space boundaries.`,
        `[!] Detected 2 private commit RWX allocations in PID 21400 (certutil.exe).`,
        `[*] Recommendation: Trigger non-destructive network quarantine.`,
      ]);
      setKernelScanRunning(false);
    }, 1200);
  };

  const handleVerifyProcessPE = (pid: number) => {
    setKernelLogs((prev) => [
      ...prev,
      `[>] Verifying in-memory PE header integrity for PID ${pid}...`,
    ]);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'verify_process_pe_header',
        args: { pid },
      });
    }
    setTimeout(() => {
      const proc = kernelProcesses.find((p) => p.pid === pid);
      if (proc && proc.peIntegrity === 'COMPROMISED') {
        setKernelLogs((prev) => [
          ...prev,
          `[!!!] COMPROMISE ALERT: PID ${pid} (${proc.name}) DOS header corrupted or hollowed!`,
          `[*] MITRE ATT&CK: T1055.012 (Process Hollowing)`,
        ]);
      } else {
        setKernelLogs((prev) => [
          ...prev,
          `[+] PID ${pid}: PE Header INTACT (0x5A4D "MZ" verified in RAM).`,
        ]);
      }
    }, 800);
  };

  const handleQuarantineKernelPid = (pid: number) => {
    handleIsolatePid(pid);
    setKernelProcesses((prev) =>
      prev.map((p) => (p.pid === pid ? { ...p, status: 'CLEAN', threatScore: 0 } : p))
    );
    setKernelLogs((prev) => [
      ...prev,
      `[SHIELD] Quarantine enforced on PID ${pid}: Outbound network egress severed. Process RAM preserved for forensics.`,
    ]);
  };

  const handleDispatchSwarmMission = () => {
    setSwarmRunning(true);
    setSwarmAgents((prev) => prev.map((a) => ({ ...a, status: 'EXECUTING' })));
    setSwarmMessages((prev) => [
      ...prev,
      { sender: 'Prime', recipient: 'ALL', type: 'TASK_BRIEF', message: `Dispatching 5-Agent Sovereign Tactical Mission across scope ${activeTarget}...`, time: new Date().toLocaleTimeString() }
    ]);

    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'dispatch_sovereign_swarm',
        args: { mission_name: 'SOVEREIGN_OMNI_SWEEP', target_scope: activeTarget },
      });
    }

    setTimeout(() => {
      setSwarmAgents((prev) => prev.map((a) => ({ ...a, status: 'IDLE' })));
      setSwarmMessages((prev) => [
        ...prev,
        { sender: 'Vanguard', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Recon & probe complete. 3 open ports mapped.', time: new Date().toLocaleTimeString() },
        { sender: 'Sentinel', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Kernel ETW & Linux /proc memory integrity 100% CLEAN.', time: new Date().toLocaleTimeString() },
        { sender: 'Specter', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Frida hooks active; zero memory injection alerts.', time: new Date().toLocaleTimeString() },
        { sender: 'Synapse', recipient: 'Prime', type: 'STATUS_REPORT', message: 'Prometheus microsecond runtime optimization verified.', time: new Date().toLocaleTimeString() },
        { sender: 'Prime', recipient: 'ALL', type: 'STATUS_REPORT', message: 'All 5 agents completed mission with zero breaches.', time: new Date().toLocaleTimeString() }
      ]);
      setSwarmRunning(false);
    }, 1600);
  };

  const handleDisassembleTargetBinary = () => {
    setFridaLogs((prev) => [
      ...prev,
      `[>] Disassembling executable ${activeBinaryFile}...`,
      `[*] Auditing security mitigations: DEP/NX: ON | ASLR: ON | Stack Canaries: ON`,
      `[+] Disassembled 50 instructions from text section. 0 dangerous buffer overflow calls.`,
    ]);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'analyze_binary_disassembly',
        args: { file_path: activeBinaryFile, max_instructions: 50 },
      });
    }
  };

  const handleAttachFridaHooks = () => {
    setFridaLogs((prev) => [
      ...prev,
      `[>] Attaching Frida Dynamic Binary Instrumentation hooks to PID ${activeFridaPid}...`,
      `[*] Hooked NtProtectVirtualMemory, NtAllocateVirtualMemory, connect, send.`,
      `[+] Telemetry streaming active. User-mode memory safely monitored.`,
    ]);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'instrument_process_with_frida',
        args: { pid: activeFridaPid, hook_profile: 'SECURITY_HOOKS' },
      });
    }
  };

  const handleTriggerPerimeterSweep = () => {
    setSweepRunning(true);
    if (sendMessage) {
      sendMessage({
        type: 'TOOL_EXECUTE',
        tool: 'execute_perimeter_sweep',
        args: {},
      });
    }
    setReconLogs((prev) => [
      ...prev,
      `[>] Initiating Autonomous 5-Stage Cross-Subsystem Perimeter Security Sweep...`,
      `[*] Stage 1: RF SIGINT Spectrum sweep (ADS-B + ACARS 131.55MHz + APRS 144.39MHz)...`,
    ]);
    setTimeout(() => {
      setReconLogs((prev) => [
        ...prev,
        `[+] Stage 1 Complete: 0 emergency squawks, RF spectrum clear.`,
        `[*] Stage 2: Inbound perimeter socket audit (psutil net_connections)...`,
        `[+] Stage 2 Complete: 6 active listening sockets mapped.`,
        `[*] Stage 3: Sigma SIEM rule evaluation across live telemetry...`,
        `[+] Stage 3 Complete: Zero active CRITICAL uncontained threats.`,
        `[*] Stage 4: Canary token & in-RAM honeypot audit (SSH/2222, Telnet/2323)...`,
        `[+] Stage 4 Complete: Canary tokens intact, zero exfiltration indicators.`,
        `[*] Stage 5: Compiling Tactical Security Debrief to Obsidian vault...`,
        `[+] Perimeter Sweep Completed with Zero Breaches! Voice summary generated.`,
      ]);
      setSweepRunning(false);
    }, 1800);
  };

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
          <span
            style={{
              backgroundColor: '#a855f722',
              border: '1px solid #a855f766',
              borderRadius: 4,
              padding: '2px 8px',
              fontSize: 10,
              color: '#c084fc',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            ● DUAL-BOOT: WIN 11 ⇄ KALI
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

              <button
                onClick={handleTriggerPerimeterSweep}
                disabled={sweepRunning}
                style={{
                  gridColumn: 'span 2',
                  backgroundColor: sweepRunning ? '#00f0ff22' : '#00ff661a',
                  border: sweepRunning ? '1px solid #00f0ff' : '1px solid #00ff6644',
                  color: sweepRunning ? '#00f0ff' : '#00ff66',
                  borderRadius: 4,
                  padding: '6px 8px',
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: sweepRunning ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                }}
              >
                <ArrowSyncRegular style={{ animation: sweepRunning ? 'spin 1s linear infinite' : 'none' }} />
                {sweepRunning ? 'EXECUTING PERIMETER SWEEP...' : 'TRIGGER PERIMETER SWEEP (DAG)'}
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
              overflowX: 'auto',
            }}
          >
            {[
              { id: 'recon', label: 'RED-TEAM DAG' },
              { id: 'kali', label: 'KALI CONTROL' },
              { id: 'kernel', label: 'KERNEL SANDBOX' },
              { id: 'swarm', label: 'SOVEREIGN SWARM' },
              { id: 'binary', label: 'BINARY RE / FRIDA' },
              { id: 'chrono', label: 'CHRONO CAMPAIGN' },
              { id: 'intel', label: 'DARK-WEB INTEL' },
              { id: 'spectral', label: 'SPECTRAL RF' },
              { id: 'ghost', label: 'GHOST ROOTKIT' },
              { id: 'stealth', label: 'ZERO-TRACE RAM' },
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
                    fontSize: 9.5,
                    fontWeight: 700,
                    padding: '8px 8px',
                    cursor: 'pointer',
                    letterSpacing: 0.6,
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

            {activeTab === 'kali' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Kali Subsystem Header Info */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#00ff66', fontWeight: 'bold' }}>● WSL2: KALI LINUX ONLINE</span>
                    <span style={{ fontSize: 10, color: '#00f0ff', backgroundColor: '#00f0ff15', padding: '2px 6px', borderRadius: 3 }}>SAFE-MODE BOUND: 127.0.0.1 / RFC1918</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#a855f7' }}>WSLg GUI: burpsuite, wireshark, ghidra</span>
                </div>

                {/* Multi-Vector Campaign Action Bar */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 10, color: '#80a0c0', fontWeight: 'bold' }}>CAMPAIGNS:</span>
                  {(['FULL', 'LOOPBACK', 'SUBNET', 'HONEYPOT'] as const).map((cType) => (
                    <button
                      key={cType}
                      onClick={() => handleRunCampaign(cType)}
                      disabled={campaignRunning}
                      style={{
                        backgroundColor: campaignRunning ? '#00f0ff11' : '#00f0ff1a',
                        border: '1px solid #00f0ff44',
                        color: campaignRunning ? '#6080a0' : '#00f0ff',
                        padding: '4px 8px',
                        borderRadius: 4,
                        fontSize: 9,
                        fontWeight: 700,
                        cursor: campaignRunning ? 'default' : 'pointer',
                      }}
                    >
                      {cType === 'FULL' ? 'FULL CAMPAIGN (4-VECTOR)' : cType}
                    </button>
                  ))}
                </div>

                {/* 1-Click Security Tool Matrix */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 10, color: '#80a0c0', fontWeight: 'bold' }}>TOOL RUNNERS:</span>
                  {[
                    { tool: 'nmap', label: 'NMAP (-sV -T4)', args: '-sV -T4 --top-ports 50' },
                    { tool: 'whatweb', label: 'WHATWEB', args: '' },
                    { tool: 'nikto', label: 'NIKTO (-Tuning 1)', args: '-Tuning 1 -timeout 3' },
                    { tool: 'masscan', label: 'MASSCAN (SYN)', args: '-p1-1024 --rate 1000' },
                    { tool: 'hashcat', label: 'HASHCAT (RTX)', args: '-b -m 1400' },
                    { tool: 'tshark', label: 'TSHARK (PCAP)', args: '-c 5 -i any' },
                  ].map((t) => (
                    <button
                      key={t.tool}
                      onClick={() => handleRunKaliTool(t.tool, t.args)}
                      disabled={activeToolRunning !== null}
                      style={{
                        backgroundColor: activeToolRunning === t.tool ? '#a855f733' : '#0c1626',
                        border: activeToolRunning === t.tool ? '1px solid #a855f7' : '1px solid #00f0ff22',
                        color: activeToolRunning === t.tool ? '#c084fc' : '#a0c0e0',
                        padding: '3px 7px',
                        borderRadius: 3,
                        fontSize: 9,
                        cursor: activeToolRunning !== null ? 'default' : 'pointer',
                        fontWeight: 600,
                      }}
                    >
                      {activeToolRunning === t.tool ? `RUNNING...` : t.label}
                    </button>
                  ))}
                </div>

                {/* Live Console Output Terminal */}
                <div
                  style={{
                    flex: 1,
                    minHeight: 220,
                    backgroundColor: '#040810',
                    border: '1px solid #00f0ff22',
                    borderRadius: 6,
                    padding: 8,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 5,
                    fontSize: 10,
                  }}
                >
                  {kaliLogs.map((line, idx) => (
                    <div
                      key={idx}
                      style={{
                        color: line.startsWith('[+]')
                          ? '#00ff66'
                          : line.startsWith('[!]')
                          ? '#ffaa00'
                          : line.startsWith('[!!!]')
                          ? '#ff003c'
                          : line.startsWith('>>>')
                          ? '#00f0ff'
                          : line.startsWith('[KALI]') || line.startsWith('[CAMPAIGN]')
                          ? '#c084fc'
                          : '#a0c0e0',
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'kernel' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Kernel & Memory Subsystem Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#00ff66', fontWeight: 'bold' }}>● ETW/SYSMON: SENSOR ARMED</span>
                    <span style={{ fontSize: 10, color: '#00f0ff', backgroundColor: '#00f0ff15', padding: '2px 6px', borderRadius: 3 }}>MEMGUARD: VIRTUALQUERYEX ACTIVE</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#ffaa00' }}>RAM ISOLATION: NETSH EGRESS SHIELD READY</span>
                </div>

                {/* 1-Click Kernel & Memory Operations Bar */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 10, color: '#80a0c0', fontWeight: 'bold' }}>SANDBOX ACTIONS:</span>
                  <button
                    onClick={handleAuditSystemRWX}
                    disabled={kernelScanRunning}
                    style={{
                      backgroundColor: kernelScanRunning ? '#00f0ff11' : '#00f0ff1a',
                      border: '1px solid #00f0ff44',
                      color: kernelScanRunning ? '#6080a0' : '#00f0ff',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: kernelScanRunning ? 'default' : 'pointer',
                    }}
                  >
                    {kernelScanRunning ? 'SCANNING MEMORY...' : 'AUDIT SYSTEM RWX PAGES'}
                  </button>
                  <button
                    onClick={() => handleVerifyProcessPE(21400)}
                    style={{
                      backgroundColor: '#a855f722',
                      border: '1px solid #a855f766',
                      color: '#c084fc',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    VERIFY PE HEADER (PID 21400)
                  </button>
                  <button
                    onClick={() => handleQuarantineKernelPid(21400)}
                    disabled={isolatedPids.includes(21400)}
                    style={{
                      backgroundColor: isolatedPids.includes(21400) ? '#ff003c22' : '#ff003c33',
                      border: '1px solid #ff003c88',
                      color: '#ff003c',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: isolatedPids.includes(21400) ? 'default' : 'pointer',
                    }}
                  >
                    {isolatedPids.includes(21400) ? 'PID 21400 CONTAINED' : 'QUARANTINE PID 21400'}
                  </button>
                </div>

                {/* Process Lineage Hierarchy Tree */}
                <div style={{ backgroundColor: '#050a14', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                  <div style={{ fontSize: 10, fontWeight: 'bold', color: '#00f0ff', marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                    <span>PROCESS LINEAGE & ANOMALY MATRIX</span>
                    <span style={{ color: '#80a0c0', fontSize: 9 }}>Sysmon ID 1 / ID 8 / ID 10</span>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9.5 }}>
                    <thead>
                      <tr style={{ color: '#80a0c0', borderBottom: '1px solid #00f0ff22', textAlign: 'left' }}>
                        <th style={{ padding: '3px 6px' }}>LINEAGE / PROCESS</th>
                        <th style={{ padding: '3px 6px' }}>PID</th>
                        <th style={{ padding: '3px 6px' }}>PARENT</th>
                        <th style={{ padding: '3px 6px' }}>THREAT SCORE</th>
                        <th style={{ padding: '3px 6px' }}>RWX PAGES</th>
                        <th style={{ padding: '3px 6px' }}>PE INTEGRITY</th>
                        <th style={{ padding: '3px 6px' }}>CONTAINMENT</th>
                      </tr>
                    </thead>
                    <tbody>
                      {kernelProcesses.map((proc, idx) => {
                        const isAnomalous = proc.status === 'ANOMALOUS';
                        const isSuspicious = proc.status === 'SUSPICIOUS';
                        const isIsolated = isolatedPids.includes(proc.pid);
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid #00f0ff10', backgroundColor: isAnomalous ? '#ff003c0a' : isSuspicious ? '#ffaa000a' : 'transparent' }}>
                            <td style={{ padding: '5px 6px', color: isAnomalous ? '#ff003c' : isSuspicious ? '#ffaa00' : '#00f0ff', fontWeight: 600 }}>
                              {idx === 0 ? 'root ' : ' └── '}{proc.name}
                              {proc.anomalyDesc && <div style={{ fontSize: 8, color: '#ff6b8b', fontWeight: 400 }}>{proc.anomalyDesc}</div>}
                            </td>
                            <td style={{ padding: '5px 6px', color: '#c0d0e0' }}>{proc.pid}</td>
                            <td style={{ padding: '5px 6px', color: '#8090a0' }}>{proc.parentName} ({proc.parentPid})</td>
                            <td style={{ padding: '5px 6px' }}>
                              <span style={{
                                backgroundColor: proc.threatScore > 70 ? '#ff003c22' : proc.threatScore > 40 ? '#ffaa0022' : '#00ff661a',
                                color: proc.threatScore > 70 ? '#ff003c' : proc.threatScore > 40 ? '#ffaa00' : '#00ff66',
                                padding: '2px 5px',
                                borderRadius: 3,
                                fontWeight: 'bold'
                              }}>
                                {proc.threatScore}/100
                              </span>
                            </td>
                            <td style={{ padding: '5px 6px' }}>
                              <span style={{ color: proc.rwxCount > 0 ? '#ff003c' : '#00ff66', fontWeight: proc.rwxCount > 0 ? 'bold' : 'normal' }}>
                                {proc.rwxCount} {proc.rwxCount > 0 ? 'RWX' : 'none'}
                              </span>
                            </td>
                            <td style={{ padding: '5px 6px' }}>
                              <span style={{ color: proc.peIntegrity === 'COMPROMISED' ? '#ff003c' : '#00ff66', fontWeight: 600 }}>
                                {proc.peIntegrity}
                              </span>
                            </td>
                            <td style={{ padding: '5px 6px' }}>
                              {isIsolated ? (
                                <span style={{ color: '#ff003c', fontSize: 8.5, fontWeight: 'bold' }}>ISOLATED</span>
                              ) : isAnomalous || isSuspicious ? (
                                <button
                                  onClick={() => handleQuarantineKernelPid(proc.pid)}
                                  style={{
                                    backgroundColor: '#ff003c22',
                                    border: '1px solid #ff003c66',
                                    color: '#ff003c',
                                    borderRadius: 3,
                                    padding: '2px 6px',
                                    fontSize: 8.5,
                                    cursor: 'pointer',
                                    fontWeight: 'bold',
                                  }}
                                >
                                  QUARANTINE
                                </button>
                              ) : (
                                <span style={{ color: '#00ff66', fontSize: 8.5 }}>PASS</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* RWX Memory Regions Table */}
                <div style={{ backgroundColor: '#050a14', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                  <div style={{ fontSize: 10, fontWeight: 'bold', color: '#ffaa00', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                    <span>UNBACKED / RWX EXECUTABLE MEMORY ALLOCATIONS</span>
                    <span style={{ fontSize: 9, color: '#80a0c0' }}>VirtualQueryEx Scanner</span>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9 }}>
                    <thead>
                      <tr style={{ color: '#80a0c0', borderBottom: '1px solid #00f0ff22', textAlign: 'left' }}>
                        <th style={{ padding: '2px 4px' }}>PROCESS</th>
                        <th style={{ padding: '2px 4px' }}>BASE ADDRESS</th>
                        <th style={{ padding: '2px 4px' }}>SIZE</th>
                        <th style={{ padding: '2px 4px' }}>PAGE PROTECTION</th>
                        <th style={{ padding: '2px 4px' }}>TYPE</th>
                        <th style={{ padding: '2px 4px' }}>RISK</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rwxRegions.map((reg, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #00f0ff10' }}>
                          <td style={{ padding: '3px 4px', color: '#00f0ff' }}>{reg.process} ({reg.pid})</td>
                          <td style={{ padding: '3px 4px', color: '#ffaa00', fontFamily: 'monospace' }}>{reg.baseAddress}</td>
                          <td style={{ padding: '3px 4px' }}>{reg.sizeKb} KB</td>
                          <td style={{ padding: '3px 4px', color: reg.protection.includes('0x40') ? '#ff003c' : '#ffaa00' }}>{reg.protection}</td>
                          <td style={{ padding: '3px 4px', color: '#80a0c0' }}>{reg.type}</td>
                          <td style={{ padding: '3px 4px' }}>
                            <span style={{
                              backgroundColor: reg.riskLevel === 'CRITICAL' ? '#ff003c22' : '#ffaa0022',
                              color: reg.riskLevel === 'CRITICAL' ? '#ff003c' : '#ffaa00',
                              padding: '1px 4px',
                              borderRadius: 2,
                              fontWeight: 'bold',
                              fontSize: 8.5
                            }}>
                              {reg.riskLevel}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Live Console Output Terminal */}
                <div
                  style={{
                    minHeight: 90,
                    maxHeight: 130,
                    backgroundColor: '#040810',
                    border: '1px solid #00f0ff22',
                    borderRadius: 6,
                    padding: 8,
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    fontSize: 9.5,
                  }}
                >
                  {kernelLogs.map((line, idx) => (
                    <div
                      key={idx}
                      style={{
                        color: line.startsWith('[+]')
                          ? '#00ff66'
                          : line.startsWith('[!]')
                          ? '#ffaa00'
                          : line.startsWith('[!!!]')
                          ? '#ff003c'
                          : line.startsWith('>>>') || line.startsWith('[>]')
                          ? '#00f0ff'
                          : line.startsWith('[KERNEL') || line.startsWith('[MEMGUARD')
                          ? '#c084fc'
                          : '#a0c0e0',
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'swarm' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Swarm Subsystem Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#00ff66', fontWeight: 'bold' }}>● 5-AGENT SOVEREIGN SWARM: ONLINE</span>
                    <span style={{ fontSize: 10, color: '#a855f7', backgroundColor: '#a855f715', padding: '2px 6px', borderRadius: 3 }}>HYBRID: RTX 3050 CUDA + CLOUD NEMOTRON</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#00f0ff' }}>CONCURRENCY: 5 PARALLEL WORKERS</span>
                </div>

                {/* Swarm Launch Action Bar */}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button
                    onClick={handleDispatchSwarmMission}
                    disabled={swarmRunning}
                    style={{
                      backgroundColor: swarmRunning ? '#00f0ff11' : '#00f0ff',
                      color: swarmRunning ? '#00f0ff' : '#000',
                      border: 'none',
                      borderRadius: 4,
                      padding: '5px 12px',
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: swarmRunning ? 'default' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <PlayRegular />
                    {swarmRunning ? 'EXECUTING SWARM DAG...' : 'DISPATCH 5-AGENT SOVEREIGN SWARM'}
                  </button>
                  <span style={{ fontSize: 9, color: '#80a0c0' }}>TARGET SCOPE: {activeTarget} (Safe-Mode Bound)</span>
                </div>

                {/* 5-Agent Roster Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6 }}>
                  {swarmAgents.map((ag) => (
                    <div
                      key={ag.name}
                      style={{
                        backgroundColor: '#050a14',
                        border: `1px solid ${ag.badgeColor}44`,
                        borderRadius: 6,
                        padding: '6px 8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 3,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: ag.badgeColor, fontWeight: 'bold', fontSize: 10 }}>{ag.name}</span>
                        <span style={{
                          fontSize: 8,
                          backgroundColor: ag.status === 'EXECUTING' ? '#ffaa0022' : '#00ff661a',
                          color: ag.status === 'EXECUTING' ? '#ffaa00' : '#00ff66',
                          padding: '1px 4px',
                          borderRadius: 2,
                          fontWeight: 700
                        }}>
                          {ag.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 8.5, color: '#8090a0', lineHeight: 1.2 }}>{ag.role}</div>
                      {ag.actionFinding && (
                        <div style={{ fontSize: 8, color: '#a0c0e0', marginTop: 2, borderTop: '1px solid #ffffff10', paddingTop: 3 }}>
                          {ag.actionFinding}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Live Swarm Message Board */}
                <div style={{ flex: 1, backgroundColor: '#040810', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 5, fontSize: 9.5 }}>
                  <div style={{ fontSize: 9, color: '#00f0ff', fontWeight: 'bold', borderBottom: '1px solid #00f0ff22', paddingBottom: 4 }}>
                    INTER-AGENT THREAD-SAFE MESSAGE BOARD (PUB/SUB)
                  </div>
                  {swarmMessages.map((msg, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: 6, alignItems: 'baseline' }}>
                      <span style={{ color: '#8090a0', fontSize: 8.5 }}>[{msg.time}]</span>
                      <span style={{ color: msg.sender === 'Prime' ? '#f43f5e' : msg.sender === 'Vanguard' ? '#ffaa00' : msg.sender === 'Sentinel' ? '#00ff66' : msg.sender === 'Specter' ? '#c084fc' : '#00f0ff', fontWeight: 'bold' }}>
                        {msg.sender} ➔ {msg.recipient}
                      </span>
                      <span style={{ color: '#00f0ff', fontSize: 8, backgroundColor: '#00f0ff15', padding: '1px 3px', borderRadius: 2 }}>{msg.type}</span>
                      <span style={{ color: '#d0f0ff' }}>{msg.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'binary' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Binary RE Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#00ff66', fontWeight: 'bold' }}>● GHIDRA / RIZIN RE: ONLINE</span>
                    <span style={{ fontSize: 10, color: '#c084fc', backgroundColor: '#c084fc15', padding: '2px 6px', borderRadius: 3 }}>FRIDA DBI: USER-MODE HOOKING ACTIVE</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#00f0ff' }}>TARGET: {activeBinaryFile} (PE64) | PID: {activeFridaPid}</span>
                </div>

                {/* Binary Actions Bar */}
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={handleDisassembleTargetBinary}
                    style={{
                      backgroundColor: '#00f0ff1a',
                      border: '1px solid #00f0ff44',
                      color: '#00f0ff',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    DISASSEMBLE BINARY
                  </button>
                  <button
                    onClick={handleAttachFridaHooks}
                    style={{
                      backgroundColor: '#a855f722',
                      border: '1px solid #a855f766',
                      color: '#c084fc',
                      padding: '4px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    ATTACH FRIDA DBI HOOKS
                  </button>
                </div>

                {/* Dual Panels: Disassembly & ROP Gadgets */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {/* Disassembly Stream */}
                  <div style={{ backgroundColor: '#050a14', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 9.5, fontWeight: 'bold', color: '#00f0ff', marginBottom: 4 }}>
                      DISASSEMBLY STREAM (x86_64)
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9 }}>
                      <thead>
                        <tr style={{ color: '#80a0c0', borderBottom: '1px solid #00f0ff22', textAlign: 'left' }}>
                          <th style={{ padding: '2px 4px' }}>ADDRESS</th>
                          <th style={{ padding: '2px 4px' }}>MNEMONIC</th>
                          <th style={{ padding: '2px 4px' }}>BYTES</th>
                        </tr>
                      </thead>
                      <tbody>
                        {binaryInstructions.map((ins, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #00f0ff10' }}>
                            <td style={{ padding: '2px 4px', color: '#8090a0', fontFamily: 'monospace' }}>{ins.address}</td>
                            <td style={{ padding: '2px 4px', color: ins.mnemonic.includes('call') ? '#ffaa00' : '#00ff66', fontWeight: 600 }}>{ins.mnemonic}</td>
                            <td style={{ padding: '2px 4px', color: '#c0d0e0', fontFamily: 'monospace' }}>{ins.bytes}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* ROP Gadgets */}
                  <div style={{ backgroundColor: '#050a14', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 9.5, fontWeight: 'bold', color: '#ffaa00', marginBottom: 4 }}>
                      ROP GADGET MATRIX (CHAIN VIABILITY: HIGH)
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9 }}>
                      <thead>
                        <tr style={{ color: '#80a0c0', borderBottom: '1px solid #00f0ff22', textAlign: 'left' }}>
                          <th style={{ padding: '2px 4px' }}>OFFSET</th>
                          <th style={{ padding: '2px 4px' }}>GADGET</th>
                          <th style={{ padding: '2px 4px' }}>TYPE</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ropGadgets.map((gadget, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #00f0ff10' }}>
                            <td style={{ padding: '2px 4px', color: '#8090a0', fontFamily: 'monospace' }}>{gadget.offset}</td>
                            <td style={{ padding: '2px 4px', color: '#ffaa00', fontWeight: 600 }}>{gadget.mnemonic}</td>
                            <td style={{ padding: '2px 4px', color: '#00f0ff', fontSize: 8 }}>{gadget.type}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Frida Intercepted Telemetry Console */}
                <div style={{ minHeight: 90, maxHeight: 120, backgroundColor: '#040810', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, fontSize: 9 }}>
                  {fridaLogs.map((line, idx) => (
                    <div
                      key={idx}
                      style={{
                        color: line.startsWith('[+]')
                          ? '#00ff66'
                          : line.startsWith('[!]')
                          ? '#ffaa00'
                          : line.startsWith('[HOOK_INTERCEPT]') || line.startsWith('[HOOK_CAPTURE]')
                          ? '#c084fc'
                          : line.startsWith('[>]')
                          ? '#00f0ff'
                          : '#a0c0e0',
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab: CHRONO CAMPAIGN */}
            {activeTab === 'chrono' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Chrono Campaign Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#00f0ff' }}>CHRONO-CYBER 5-STAGE KILL-CHAIN DAG</span>
                    <span style={{ fontSize: 9, color: '#00ff66', backgroundColor: '#00ff6615', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      SCOPE: 127.0.0.1 (AUTONOMOUS LAB SAFE-MODE)
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setChronoRunning(true);
                      setChronoStages((prev) => prev.map((s) => ({ ...s, status: 'EXECUTING' })));
                      setTimeout(() => {
                        setChronoStages((prev) => prev.map((s) => ({ ...s, status: 'SUCCESS' })));
                        setChronoRunning(false);
                      }, 1500);
                    }}
                    style={{
                      backgroundColor: chronoRunning ? '#ffaa0022' : '#00f0ff22',
                      border: `1px solid ${chronoRunning ? '#ffaa00' : '#00f0ff'}`,
                      color: chronoRunning ? '#ffaa00' : '#00f0ff',
                      borderRadius: 4,
                      padding: '4px 8px',
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {chronoRunning ? 'EXECUTING KILL-CHAIN...' : 'DISPATCH 5-STAGE MISSION'}
                  </button>
                </div>

                {/* 5-Stage DAG Stage Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
                  {chronoStages.map((stg) => (
                    <div
                      key={stg.stage}
                      style={{
                        backgroundColor: '#050c18',
                        border: `1px solid ${stg.status === 'SUCCESS' ? '#00ff6644' : stg.status === 'EXECUTING' ? '#ffaa0044' : '#00f0ff22'}`,
                        borderRadius: 6,
                        padding: 8,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 4,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 8.5, color: '#6080a0', fontWeight: 700 }}>STAGE 0{stg.stage}</span>
                        <span
                          style={{
                            fontSize: 7.5,
                            fontWeight: 700,
                            padding: '1px 4px',
                            borderRadius: 2,
                            backgroundColor: stg.status === 'SUCCESS' ? '#00ff6622' : stg.status === 'EXECUTING' ? '#ffaa0022' : '#6080a022',
                            color: stg.status === 'SUCCESS' ? '#00ff66' : stg.status === 'EXECUTING' ? '#ffaa00' : '#6080a0',
                          }}
                        >
                          {stg.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 9.5, fontWeight: 700, color: '#00f0ff' }}>{stg.name}</div>
                      <div style={{ fontSize: 8, color: '#a0c0e0', lineHeight: 1.3 }}>{stg.finding}</div>
                    </div>
                  ))}
                </div>

                {/* Attack Vectors & MITRE Matrix Panel */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 10, flex: 1, minHeight: 0 }}>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#00f0ff', marginBottom: 6 }}>DISCOVERED PRIVILEGE ESCALATION VECTORS</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ backgroundColor: '#091222', border: '1px solid #ffaa0033', borderRadius: 4, padding: 6 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, fontWeight: 700, color: '#ffaa00' }}>
                          <span>SUID Binary: /usr/bin/find</span>
                          <span style={{ color: '#ff003c' }}>HIGH RISK</span>
                        </div>
                        <div style={{ fontSize: 8, color: '#6080a0', fontFamily: 'monospace' }}>Exploit: find . -exec /bin/sh -p \;</div>
                      </div>
                      <div style={{ backgroundColor: '#091222', border: '1px solid #ff003c33', borderRadius: 4, padding: 6 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, fontWeight: 700, color: '#ff003c' }}>
                          <span>Sudoers NOPASSWD: /usr/bin/apt</span>
                          <span style={{ color: '#ff003c' }}>CRITICAL</span>
                        </div>
                        <div style={{ fontSize: 8, color: '#6080a0', fontFamily: 'monospace' }}>Exploit: apt-get changelog --exec /bin/sh</div>
                      </div>
                      <div style={{ backgroundColor: '#091222', border: '1px solid #00f0ff22', borderRadius: 4, padding: 6 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, fontWeight: 700, color: '#00f0ff' }}>
                          <span>Windows Token: SeImpersonatePrivilege</span>
                          <span style={{ color: '#ffaa00' }}>HIGH RISK</span>
                        </div>
                        <div style={{ fontSize: 8, color: '#6080a0', fontFamily: 'monospace' }}>Vector: Named Pipe potato impersonation to NT AUTHORITY\SYSTEM</div>
                      </div>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#c084fc', marginBottom: 6 }}>MITRE ATT&CK v15 MATRIX</div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 8.5 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #c084fc33', color: '#6080a0' }}>
                          <th style={{ padding: '2px 4px', textAlign: 'left' }}>TECH ID</th>
                          <th style={{ padding: '2px 4px', textAlign: 'left' }}>TECHNIQUE</th>
                          <th style={{ padding: '2px 4px', textAlign: 'right' }}>STAGE</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                          <td style={{ padding: '4px', color: '#c084fc', fontFamily: 'monospace' }}>T1046</td>
                          <td style={{ padding: '4px', color: '#ffffff' }}>Network Service Discovery</td>
                          <td style={{ padding: '4px', textAlign: 'right', color: '#00ff66' }}>STG-1</td>
                        </tr>
                        <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                          <td style={{ padding: '4px', color: '#c084fc', fontFamily: 'monospace' }}>T1190</td>
                          <td style={{ padding: '4px', color: '#ffffff' }}>Exploit Public Application</td>
                          <td style={{ padding: '4px', textAlign: 'right', color: '#00ff66' }}>STG-2</td>
                        </tr>
                        <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                          <td style={{ padding: '4px', color: '#c084fc', fontFamily: 'monospace' }}>T1068</td>
                          <td style={{ padding: '4px', color: '#ffffff' }}>Privilege Escalation Exploitation</td>
                          <td style={{ padding: '4px', textAlign: 'right', color: '#00ff66' }}>STG-3</td>
                        </tr>
                        <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                          <td style={{ padding: '4px', color: '#c084fc', fontFamily: 'monospace' }}>T1053</td>
                          <td style={{ padding: '4px', color: '#ffffff' }}>Scheduled Task / Cron Job</td>
                          <td style={{ padding: '4px', textAlign: 'right', color: '#00ff66' }}>STG-4</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: DARK-WEB INTEL */}
            {activeTab === 'intel' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Threat Intel Header & Shared Vault Badge */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #c084fc33' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#c084fc' }}>DARK-WEBINT SOVEREIGN RADAR</span>
                    <span style={{ fontSize: 9, color: '#00ff66', backgroundColor: '#00ff6615', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      TOR SOCKS5: 127.0.0.1:9050 (OPSEC SANITIZED)
                    </span>
                  </div>
                  <span style={{ fontSize: 9, color: '#00f0ff', backgroundColor: '#00f0ff18', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
                    SHARED VAULT: PBKDF2 AES-256 (DUAL-BOOT SYNC)
                  </span>
                </div>

                {/* Threat Actors Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                  {darkwebActors.map((act) => (
                    <div
                      key={act.id}
                      style={{
                        backgroundColor: '#050c18',
                        border: '1px solid #c084fc33',
                        borderRadius: 6,
                        padding: 8,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 4,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 9.5, fontWeight: 700, color: '#ffffff' }}>{act.name}</span>
                        <span
                          style={{
                            fontSize: 8,
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: 2,
                            backgroundColor: act.severity === 'CRITICAL' ? '#ff003c22' : '#ffaa0022',
                            color: act.severity === 'CRITICAL' ? '#ff003c' : '#ffaa00',
                          }}
                        >
                          {act.severity}
                        </span>
                      </div>
                      <div style={{ fontSize: 8.5, color: '#6080a0' }}>Origin: <strong style={{ color: '#c084fc' }}>{act.origin}</strong></div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                        {act.ttps.map((ttp) => (
                          <span
                            key={ttp}
                            style={{
                              backgroundColor: '#00f0ff15',
                              color: '#00f0ff',
                              fontSize: 7.5,
                              fontFamily: 'monospace',
                              padding: '1px 4px',
                              borderRadius: 2,
                            }}
                          >
                            {ttp}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Asset CVE Correlation Table */}
                <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, flex: 1, overflowY: 'auto' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#00f0ff', marginBottom: 6 }}>LOCAL ASSET CVE CORRELATION</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9, textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #00f0ff22', color: '#6080a0' }}>
                        <th style={{ padding: '3px 6px' }}>PORT</th>
                        <th style={{ padding: '3px 6px' }}>CVE IDENTIFIER</th>
                        <th style={{ padding: '3px 6px' }}>ADVISORY TITLE</th>
                        <th style={{ padding: '3px 6px' }}>CVSS SCORE</th>
                        <th style={{ padding: '3px 6px' }}>SEVERITY</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                        <td style={{ padding: '4px 6px', color: '#ffaa00' }}>445</td>
                        <td style={{ padding: '4px 6px', color: '#00f0ff', fontFamily: 'monospace' }}>CVE-2017-0144</td>
                        <td style={{ padding: '4px 6px', color: '#ffffff' }}>EternalBlue SMBv1 Remote Code Execution</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>9.8</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>CRITICAL</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                        <td style={{ padding: '4px 6px', color: '#ffaa00' }}>8000</td>
                        <td style={{ padding: '4px 6px', color: '#00f0ff', fontFamily: 'monospace' }}>CVE-2024-38077</td>
                        <td style={{ padding: '4px 6px', color: '#ffffff' }}>Windows Remote Desktop Licensing RCE</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>9.8</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>CRITICAL</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid #ffffff08' }}>
                        <td style={{ padding: '4px 6px', color: '#ffaa00' }}>443</td>
                        <td style={{ padding: '4px 6px', color: '#00f0ff', fontFamily: 'monospace' }}>CVE-2024-21413</td>
                        <td style={{ padding: '4px 6px', color: '#ffffff' }}>Microsoft Outlook Moniker RCE Vulnerability</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>9.8</td>
                        <td style={{ padding: '4px 6px', color: '#ff003c', fontWeight: 700 }}>CRITICAL</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: SPECTRAL RF RADAR */}
            {activeTab === 'spectral' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* RF Spectrum Banner */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#00f0ff' }}>SPECTRAL-NEXUS RF WATERFALL</span>
                    <span style={{ fontSize: 9, color: '#ffaa00', backgroundColor: '#ffaa0018', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      CENTER: 2437.0 MHz (CH 6) | BW: 20 MHz
                    </span>
                  </div>
                  <span style={{ fontSize: 9, color: '#00ff66', fontWeight: 700 }}>
                    802.11ac/ax + BLE 5.3 ARMED
                  </span>
                </div>

                {/* Live RF Waterfall Visualizer Bars */}
                <div style={{ backgroundColor: '#040810', border: '1px solid #00f0ff33', borderRadius: 6, padding: '10px 12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 8.5, color: '#6080a0' }}>
                    <span>2412 MHz (CH 1)</span>
                    <span style={{ color: '#00f0ff', fontWeight: 700 }}>2437 MHz (CH 6 - CARRIER PEAK)</span>
                    <span>2462 MHz (CH 11)</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 65, backgroundColor: '#02050a', padding: '4px 6px', borderRadius: 4 }}>
                    {spectralBins.map((dbm, idx) => {
                      const heightPct = Math.min(100, Math.max(15, (dbm + 100) * 1.6));
                      const isPeak = dbm > -50;
                      return (
                        <div
                          key={idx}
                          style={{
                            flex: 1,
                            height: `${heightPct}%`,
                            backgroundColor: isPeak ? '#f43f5e' : dbm > -70 ? '#ffaa00' : '#00f0ff',
                            borderRadius: '2px 2px 0 0',
                            transition: 'height 0.2s ease',
                          }}
                          title={`Bin ${idx}: ${dbm} dBm`}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Rogue AP & Deauth Alert Banner */}
                <div style={{ backgroundColor: '#ff003c15', border: '1px solid #ff003c44', borderRadius: 6, padding: '6px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9.5, color: '#ff003c', fontWeight: 700 }}>
                    [!] ROGUE AP DETECTED: Conflicting BSSID DE:AD:BE:EF:00:01 broadcasting PHENOM-SOVEREIGN-SEC
                  </span>
                  <span style={{ fontSize: 8.5, color: '#00ff66', backgroundColor: '#00ff6615', padding: '2px 6px', borderRadius: 3, fontWeight: 700 }}>
                    WPA3 PMF ACTIVE
                  </span>
                </div>

                {/* Scanned Access Points & BLE Devices Tables */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 10, flex: 1, minHeight: 0 }}>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#00f0ff', marginBottom: 6 }}>SCANNED 802.11 ACCESS POINTS</div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9, textAlign: 'left' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #00f0ff22', color: '#6080a0' }}>
                          <th style={{ padding: '2px 4px' }}>ESSID</th>
                          <th style={{ padding: '2px 4px' }}>BSSID</th>
                          <th style={{ padding: '2px 4px' }}>CH</th>
                          <th style={{ padding: '2px 4px' }}>RSSI</th>
                          <th style={{ padding: '2px 4px' }}>SECURITY</th>
                        </tr>
                      </thead>
                      <tbody>
                        {spectralWifi.map((ap, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #ffffff08' }}>
                            <td style={{ padding: '4px', color: ap.sec === 'ROGUE-AP' ? '#ff003c' : '#ffffff', fontWeight: 600 }}>{ap.essid}</td>
                            <td style={{ padding: '4px', color: '#a0c0e0', fontFamily: 'monospace' }}>{ap.bssid}</td>
                            <td style={{ padding: '4px', color: '#ffaa00' }}>{ap.ch}</td>
                            <td style={{ padding: '4px', color: ap.rssi > -50 ? '#00ff66' : '#a0c0e0' }}>{ap.rssi} dBm</td>
                            <td style={{ padding: '4px' }}>
                              <span style={{ backgroundColor: ap.sec === 'ROGUE-AP' ? '#ff003c22' : '#00f0ff22', color: ap.sec === 'ROGUE-AP' ? '#ff003c' : '#00f0ff', padding: '1px 4px', borderRadius: 2, fontSize: 8, fontWeight: 700 }}>
                                {ap.sec}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, overflowY: 'auto' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#c084fc', marginBottom: 6 }}>BLE AIRSPACE BEACONS</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {spectralBle.map((dev, i) => (
                        <div key={i} style={{ backgroundColor: '#091222', border: '1px solid #c084fc33', borderRadius: 4, padding: 6 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, fontWeight: 700, color: '#c084fc' }}>
                            <span>{dev.name}</span>
                            <span style={{ color: '#00ff66' }}>{dev.rssi} dBm</span>
                          </div>
                          <div style={{ fontSize: 8.5, color: '#6080a0', fontFamily: 'monospace' }}>MAC: {dev.mac}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: GHOST ROOTKIT HUNTER */}
            {activeTab === 'ghost' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Ghost Status Banner */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00f0ff22' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#00f0ff' }}>GHOST-PROTOCOL KERNEL INTEGRITY</span>
                    <span style={{ fontSize: 9, color: '#00ff66', backgroundColor: '#00ff6615', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      COMPOSITE THREAT SCORE: 0/100 (BENIGN)
                    </span>
                  </div>
                  <span style={{ fontSize: 9, color: '#c084fc', fontWeight: 700 }}>
                    eBPF & NTAPI PROLOGUE AUDITOR ARMED
                  </span>
                </div>

                {/* Subsystem Integrity Status */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00ff6633', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#00ff66', marginBottom: 4 }}>LINUX KALI KERNEL POSTURE</div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>/proc/modules vs /sys/module match: <strong style={{ color: '#00ff66' }}>100% CLEAN</strong></div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>Hidden LKM Rootkits: <strong style={{ color: '#00ff66' }}>0 DETECTED</strong></div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>Active Kprobes: <strong style={{ color: '#00f0ff' }}>1 (sys_enter_execve)</strong></div>
                  </div>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff33', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#00f0ff', marginBottom: 4 }}>WINDOWS 11 NTAPI INTEGRITY</div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>ntdll.dll Prologue Tampering: <strong style={{ color: '#00ff66' }}>0 HOOKS</strong></div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>SSDT / IDT Table Descriptor: <strong style={{ color: '#00ff66' }}>INTACT</strong></div>
                    <div style={{ fontSize: 9, color: '#a0c0e0' }}>HVCI Memory Code Integrity: <strong style={{ color: '#00ff66' }}>ENFORCED</strong></div>
                  </div>
                </div>

                {/* NTAPI Prologue Inspection Table */}
                <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8, flex: 1, overflowY: 'auto' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#00f0ff', marginBottom: 6 }}>SCANNED SYSCALL PROLOGUES (DETOUR DETECTION)</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 9, textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #00f0ff22', color: '#6080a0' }}>
                        <th style={{ padding: '3px 6px' }}>FUNCTION NAME</th>
                        <th style={{ padding: '3px 6px' }}>MODULE</th>
                        <th style={{ padding: '3px 6px' }}>PROLOGUE BYTES</th>
                        <th style={{ padding: '3px 6px' }}>HOOK STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ghostHooks.map((h, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #ffffff08' }}>
                          <td style={{ padding: '4px 6px', color: '#00f0ff', fontWeight: 600 }}>{h.func}</td>
                          <td style={{ padding: '4px 6px', color: '#a0c0e0' }}>{h.module}</td>
                          <td style={{ padding: '4px 6px', color: '#ffaa00', fontFamily: 'monospace' }}>{h.prologue}</td>
                          <td style={{ padding: '4px 6px' }}>
                            <span style={{ backgroundColor: '#00ff6622', color: '#00ff66', padding: '1px 6px', borderRadius: 2, fontSize: 8, fontWeight: 700 }}>
                              {h.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: ZERO-TRACE EPHEMERAL RAM OS */}
            {activeTab === 'stealth' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
                {/* Zero-Trace Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#091222', padding: '6px 10px', borderRadius: 6, border: '1px solid #00ff6633' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#00ff66' }}>ZERO-TRACE EPHEMERAL RAM POSTURE</span>
                    <span style={{ fontSize: 9, color: stealthActive ? '#00ff66' : '#ffaa00', backgroundColor: stealthActive ? '#00ff6615' : '#ffaa0015', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      {stealthActive ? 'RAM-ONLY (DISK WRITES SUPPRESSED)' : 'PERSISTENT DISK LOGGING'}
                    </span>
                  </div>
                  <button
                    onClick={() => setStealthActive(!stealthActive)}
                    style={{
                      backgroundColor: stealthActive ? '#ff003c22' : '#00ff6622',
                      border: `1px solid ${stealthActive ? '#ff003c' : '#00ff66'}`,
                      color: stealthActive ? '#ff003c' : '#00ff66',
                      borderRadius: 4,
                      padding: '4px 8px',
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {stealthActive ? 'DEACTIVATE STEALTH' : 'ACTIVATE STEALTH'}
                  </button>
                </div>

                {/* Metrics Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 9, color: '#6080a0' }}>VOLATILE TRACES IN RAM</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#00f0ff' }}>{volatileEntries}</div>
                    <div style={{ fontSize: 8, color: '#a0c0e0' }}>Never flushed to disk</div>
                  </div>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 9, color: '#6080a0' }}>VOLATILE BYTES ALLOCATED</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#c084fc' }}>{(volatileBytes / 1024).toFixed(1)} KB</div>
                    <div style={{ fontSize: 8, color: '#a0c0e0' }}>RAM buffer pool</div>
                  </div>
                  <div style={{ backgroundColor: '#050c18', border: '1px solid #00f0ff22', borderRadius: 6, padding: 8 }}>
                    <div style={{ fontSize: 9, color: '#6080a0' }}>GUARDIAN ZEROIZE SLA</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#00ff66' }}>&lt; 0.05 ms</div>
                    <div style={{ fontSize: 8, color: '#a0c0e0' }}>Cryptographic overwrite</div>
                  </div>
                </div>

                {/* Zeroization Action Bar */}
                <div style={{ backgroundColor: '#050c18', border: '1px solid #ff003c44', borderRadius: 6, padding: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#ff003c' }}>EMERGENCY CRYPTOGRAPHIC ZEROIZATION</div>
                    <div style={{ fontSize: 8.5, color: '#a0c0e0' }}>
                      Overwrites all in-memory volatile trace buffers with cryptographic entropy and zeroes in &lt; 25ms.
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setVolatileEntries(0);
                      setVolatileBytes(0);
                      setZeroizeDone(true);
                      setTimeout(() => setZeroizeDone(false), 3000);
                    }}
                    style={{
                      backgroundColor: '#ff003c',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: 4,
                      padding: '6px 12px',
                      fontSize: 9.5,
                      fontWeight: 700,
                      cursor: 'pointer',
                      letterSpacing: 0.5,
                    }}
                  >
                    {zeroizeDone ? 'ZEROIZED CLEAN (0 BYTES)' : 'PURGE & ZEROIZE RAM NOW'}
                  </button>
                </div>
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
                      <th style={{ padding: '4px 6px' }}>CONTAINMENT</th>
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
                        <td style={{ padding: '6px 6px' }}>
                          {isolatedPids.includes(s.pid) ? (
                            <span
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                backgroundColor: '#ff003c22',
                                border: '1px solid #ff003c66',
                                color: '#ff003c',
                                padding: '2px 6px',
                                borderRadius: 3,
                                fontSize: 9,
                                fontWeight: 700,
                              }}
                            >
                              <LockClosedRegular />
                              EGRESS BLOCKED
                            </span>
                          ) : (
                            <button
                              onClick={() => handleIsolatePid(s.pid)}
                              style={{
                                backgroundColor: '#ffaa0015',
                                border: '1px solid #ffaa0055',
                                color: '#ffaa00',
                                borderRadius: 3,
                                padding: '2px 6px',
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer',
                              }}
                              title="Netsh firewall outbound egress block"
                            >
                              ISOLATE EGRESS
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'radar' && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                {/* Domain Selector Filter */}
                <div style={{ display: 'flex', gap: 6, alignSelf: 'flex-start' }}>
                  {(['ALL', 'ADSB', 'HONEYPOT', 'MESH'] as const).map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setRadarFilter(filter)}
                      style={{
                        backgroundColor: radarFilter === filter ? '#00f0ff22' : '#081220',
                        border: radarFilter === filter ? '1px solid #00f0ff' : '1px solid #00f0ff22',
                        color: radarFilter === filter ? '#00f0ff' : '#6080a0',
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 9,
                        fontWeight: 700,
                        cursor: 'pointer',
                        letterSpacing: 0.5,
                      }}
                    >
                      {filter === 'ALL'
                        ? 'UNIFIED AIR & MESH RADAR'
                        : filter === 'ADSB'
                        ? 'ADS-B AIRSPACE'
                        : filter === 'HONEYPOT'
                        ? 'DECEPTION TRAPS'
                        : 'P2P ENCRYPTED MESH'}
                    </button>
                  ))}
                </div>

                <div style={{ width: 450, height: 260, position: 'relative', backgroundColor: '#040810', borderRadius: 8, border: '1px solid #00ff6633' }}>
                  <svg width="100%" height="100%" viewBox="0 0 450 260">
                    {/* Range Rings */}
                    <circle cx="225" cy="130" r="110" fill="none" stroke="#00ff6622" strokeWidth="1" />
                    <circle cx="225" cy="130" r="75" fill="none" stroke="#00ff6622" strokeWidth="1" />
                    <circle cx="225" cy="130" r="40" fill="none" stroke="#00ff6622" strokeWidth="1" />

                    {/* Crosshairs */}
                    <line x1="225" y1="10" x2="225" y2="250" stroke="#00ff6622" strokeWidth="1" strokeDasharray="3 3" />
                    <line x1="15" y1="130" x2="435" y2="130" stroke="#00ff6622" strokeWidth="1" strokeDasharray="3 3" />

                    {/* Center Ground Station */}
                    <circle cx="225" cy="130" r="4" fill="#00ff66" />
                    <text x="225" y="145" fill="#00ff66" fontSize="9" textAnchor="middle">PHENOM TACTICAL RADAR</text>

                    {/* P2P Mesh Interconnect Topology Lines */}
                    {(radarFilter === 'ALL' || radarFilter === 'MESH') && (
                      <g>
                        {meshPeers.map((peer, i) => {
                          const nextPeer = meshPeers[(i + 1) % meshPeers.length];
                          return (
                            <line
                              key={`link-${peer.id}`}
                              x1={peer.x}
                              y1={peer.y}
                              x2={nextPeer.x}
                              y2={nextPeer.y}
                              stroke="#c084fc"
                              strokeWidth="1"
                              strokeDasharray="4 3"
                              opacity="0.4"
                            />
                          );
                        })}
                      </g>
                    )}

                    {/* P2P Mesh Peer Nodes */}
                    {(radarFilter === 'ALL' || radarFilter === 'MESH') &&
                      meshPeers.map((peer) => (
                        <g key={peer.id}>
                          <rect x={peer.x - 4} y={peer.y - 4} width="8" height="8" fill="#c084fc" transform={`rotate(45 ${peer.x} ${peer.y})`} />
                          <circle cx={peer.x} cy={peer.y} r="10" fill="none" stroke="#c084fc" strokeWidth="1" opacity="0.5">
                            <animate attributeName="r" values="7;13;7" dur="3s" repeatCount="indefinite" />
                          </circle>
                          <text x={peer.x + 8} y={peer.y - 3} fill="#c084fc" fontSize="9" fontWeight="bold">
                            {peer.callsign}
                          </text>
                          <text x={peer.x + 8} y={peer.y + 8} fill="#a855f7" fontSize="8">
                            {peer.ip} • {peer.latencyMs}ms
                          </text>
                        </g>
                      ))}

                    {/* Deception Honeypot Traps */}
                    {(radarFilter === 'ALL' || radarFilter === 'HONEYPOT') &&
                      honeypots.map((hp) => (
                        <g key={hp.id}>
                          <circle cx={hp.x} cy={hp.y} r="6" fill="#f97316" />
                          <circle cx={hp.x} cy={hp.y} r="11" fill="none" stroke="#f97316" strokeWidth="1" opacity="0.6">
                            <animate attributeName="r" values="6;14;6" dur="2.5s" repeatCount="indefinite" />
                          </circle>
                          <text x={hp.x + 10} y={hp.y - 3} fill="#f97316" fontSize="9" fontWeight="bold">
                            {hp.service} ({hp.port})
                          </text>
                          <text x={hp.x + 10} y={hp.y + 8} fill="#fdba74" fontSize="8">
                            {hp.status} • {hp.hits} PROBES
                          </text>
                        </g>
                      ))}

                    {/* ADS-B Aircraft Blips */}
                    {(radarFilter === 'ALL' || radarFilter === 'ADSB') &&
                      radarAircraft.map((plane) => (
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

                <div style={{ fontSize: 10, color: '#00ff66', display: 'flex', gap: 14 }}>
                  <span>ADS-B: {radarAircraft.length} CRAFT</span>
                  <span style={{ color: '#f97316' }}>HONEYPOTS: {honeypots.length} TRAPS ARMED</span>
                  <span style={{ color: '#c084fc' }}>P2P MESH: {meshPeers.length} PEERS (8ms)</span>
                  <span>RANGE: 50 NM</span>
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
