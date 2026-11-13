"""
Phenom ESP8266 Hardware Cyber Bridge
Manages USB Serial (UART) connectivity with connected ESP8266 microcontrollers
(NodeMCU, D1 Mini, ESP8266 Deauther, Wi-Fi Packet Monitors).
Enables reading serial telemetry, streaming 802.11 beacon dumps, sending serial commands,
and auditing device connectivity.
"""

import time
import threading
from typing import Dict, Any, List, Optional

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ESP8266Controller:
    """Controls connected ESP8266 hardware boards over USB UART COM ports."""

    def __init__(self):
        self._serial_connection: Optional[Any] = None
        self._active_port: Optional[str] = None
        self._baud_rate: int = 115200
        self._rx_buffer: List[str] = []
        self._is_monitoring: bool = False
        self._monitor_thread: Optional[threading.Thread] = None

    def list_serial_ports(self) -> List[Dict[str, str]]:
        """Scans and lists all USB serial COM devices (e.g. CH340, CP2102, FTDI)."""
        if not SERIAL_AVAILABLE:
            return [{"port": "COM3", "description": "Mock ESP8266 NodeMCU (CH340 UART)", "hardware_id": "USB\\VID_1A86&PID_7523"}]

        found = []
        ports = serial.tools.list_ports.comports()
        for p in ports:
            found.append({
                "port": p.device,
                "description": p.description,
                "hardware_id": p.hwid
            })
        return found

    def connect(self, port: Optional[str] = None, baud_rate: int = 115200) -> Dict[str, Any]:
        """Connects to the ESP8266 board on the specified or auto-discovered COM port."""
        available_ports = self.list_serial_ports()
        target_port = port

        if not target_port:
            # Auto-detect CH340, CP210x, or first available COM port
            for p in available_ports:
                desc = p["description"].lower()
                hwid = p["hardware_id"].lower()
                if "ch340" in desc or "cp210" in desc or "uart" in desc or "usb-serial" in desc or "1a86" in hwid or "10c4" in hwid:
                    target_port = p["port"]
                    break
            if not target_port and available_ports:
                target_port = available_ports[0]["port"]

        if not target_port:
            return {"connected": False, "error": "No USB serial COM ports detected. Connect ESP8266 via USB."}

        self._active_port = target_port
        self._baud_rate = baud_rate

        if not SERIAL_AVAILABLE:
            self._rx_buffer.append(f"[ESP8266] Connected to {target_port} at {baud_rate} baud (Mock Mode)")
            return {
                "connected": True,
                "port": target_port,
                "baud_rate": baud_rate,
                "device": "ESP8266 (Mock Bridge)",
                "status": "Ready for 802.11 beacon injection / packet monitoring"
            }

        try:
            self._serial_connection = serial.Serial(target_port, baud_rate, timeout=1.0)
            self._is_monitoring = True
            self._monitor_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._monitor_thread.start()
            return {
                "connected": True,
                "port": target_port,
                "baud_rate": baud_rate,
                "device": "ESP8266 USB-UART",
                "status": "Online and streaming telemetry"
            }
        except Exception as exc:
            return {"connected": False, "port": target_port, "error": str(exc)}

    def disconnect(self) -> Dict[str, Any]:
        """Disconnects the active serial connection."""
        self._is_monitoring = False
        if self._serial_connection and hasattr(self._serial_connection, "close"):
            try:
                self._serial_connection.close()
            except Exception:
                pass
        port = self._active_port
        self._serial_connection = None
        self._active_port = None
        return {"disconnected": True, "port": port}

    def send_command(self, cmd: str) -> Dict[str, Any]:
        """Sends a text directive (e.g. 'scan aps', 'attack -d', 'sysinfo') to the board."""
        if not self._active_port:
            return {"success": False, "error": "ESP8266 not connected. Run connect_esp8266 first."}

        clean_cmd = cmd.strip() + "\r\n"
        self._rx_buffer.append(f">>> {cmd}")

        if not SERIAL_AVAILABLE or not self._serial_connection:
            # Simulate high-fidelity ESP8266 Deauther / Monitor responses in test/mock mode
            if "scan" in cmd.lower():
                response = "[ESP8266] Scanning 2.4GHz Wi-Fi channels 1-14...\nFound 8 Access Points, 14 Client Stations."
            elif "sysinfo" in cmd.lower() or "version" in cmd.lower():
                response = "[ESP8266] Core: Xtensa LX106 @ 80MHz | Flash: 4MB | Firmware: ESP8266-Cyber-Link v2.6.1"
            elif "attack" in cmd.lower() or "deauth" in cmd.lower():
                response = "[ESP8266] Attack frame transmission started on target BSSID."
            elif "stop" in cmd.lower():
                response = "[ESP8266] Active packet transmission halted. Returning to listening mode."
            else:
                response = f"[ESP8266] ACK: {cmd} executed."
            self._rx_buffer.append(response)
            return {"success": True, "command": cmd, "response": response}

        try:
            self._serial_connection.write(clean_cmd.encode("utf-8"))
            time.sleep(0.15)
            # Read immediate reply
            lines = []
            while self._serial_connection.in_waiting > 0:
                line = self._serial_connection.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    lines.append(line)
            reply = "\n".join(lines) if lines else "Command dispatched to ESP8266."
            return {"success": True, "command": cmd, "response": reply}
        except Exception as exc:
            return {"success": False, "command": cmd, "error": str(exc)}

    def get_telemetry_stream(self, max_lines: int = 30) -> List[str]:
        """Returns the latest captured serial stream lines."""
        return self._rx_buffer[-max_lines:]

    def _read_loop(self):
        """Background thread reading serial lines from the ESP8266."""
        while self._is_monitoring and self._serial_connection:
            try:
                if self._serial_connection.in_waiting > 0:
                    line = self._serial_connection.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        self._rx_buffer.append(line)
                        if len(self._rx_buffer) > 500:
                            self._rx_buffer = self._rx_buffer[-250:]
                time.sleep(0.05)
            except Exception:
                break


esp8266_controller = ESP8266Controller()
