"""
Phenom Universal Cross-Platform Abstraction Subsystem
Provides seamless dual-boot parity across Windows 11 and native Kali Linux.
"""

from .os_bridge import Platform, OSBridge, os_bridge

__all__ = ["Platform", "OSBridge", "os_bridge"]
