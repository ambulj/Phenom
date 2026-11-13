"""
Phenom DARK-WEBINT Tool Registry
Registers:
1. crawl_onion_service (Tier 1) - Crawls Tor v3 .onion hidden services with HTML/script sanitization
2. correlate_threat_intelligence (Tier 0) - Correlates target ports against CVEs and exploit signatures
3. profile_threat_actor (Tier 0) - Retrieves MITRE ATT&CK adversary profiles and TTP mappings
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from services.backend.safety.registry import registry
from services.backend.cyber.dark_webint import dark_webint


# 1. Crawl Onion Service
class CrawlOnionArgs(BaseModel):
    onion_url: str = Field(..., description="v3 .onion URL or domain (56 characters)")
    socks_port: Optional[int] = Field(default=9050, description="Local Tor SOCKS5 proxy port")


def crawl_preview(args: Dict[str, Any]) -> str:
    onion = args.get("onion_url", "unknown.onion")
    return f"Crawl Tor onion service '{onion}' with OPSEC content sanitization"


@registry.register(
    name="crawl_onion_service",
    tier=1,
    description="Crawls a Tor v3 .onion hidden service through a local SOCKS5 proxy, stripping all scripts, iframes, and trackers for OPSEC protection.",
    args_schema=CrawlOnionArgs,
    preview_fn=crawl_preview,
    can_remember_per_folder=False
)
def crawl_onion_service(onion_url: str, socks_port: int = 9050) -> Dict[str, Any]:
    return dark_webint.crawl_onion_service(onion_url=onion_url, socks_port=socks_port)


# 2. Correlate Threat Intelligence
class CorrelateIntelArgs(BaseModel):
    ip_or_domain: str = Field(..., description="Target IP or domain name")
    open_ports: Optional[List[int]] = Field(default=None, description="List of discovered open TCP ports")


@registry.register(
    name="correlate_threat_intelligence",
    tier=0,
    description="Correlates discovered open ports and IP banners against public CVE advisories, CVSS scores, and exploitation kits.",
    args_schema=CorrelateIntelArgs,
    preview_fn=lambda a: f"Correlate threat intelligence for '{a.get('ip_or_domain')}'",
    can_remember_per_folder=False
)
def correlate_threat_intelligence(ip_or_domain: str, open_ports: Optional[List[int]] = None) -> Dict[str, Any]:
    return dark_webint.correlate_threat_intelligence(ip_or_domain=ip_or_domain, open_ports=open_ports)


# 3. Profile Threat Actor
class ProfileActorArgs(BaseModel):
    actor_name: str = Field(..., description="Name or alias of threat actor (e.g. 'Cozy Bear', 'LockBit')")


@registry.register(
    name="profile_threat_actor",
    tier=0,
    description="Retrieves threat actor attribution, known MITRE ATT&CK technique IDs, malware arsenal, and C2 infrastructure.",
    args_schema=ProfileActorArgs,
    preview_fn=lambda a: f"Profile threat actor '{a.get('actor_name')}'",
    can_remember_per_folder=False
)
def profile_threat_actor(actor_name: str) -> Dict[str, Any]:
    return dark_webint.profile_threat_actor(actor_name=actor_name)
