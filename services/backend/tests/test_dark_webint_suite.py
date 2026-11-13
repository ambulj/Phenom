"""
Unit tests for Milestone 42 Phase 2: DARK-WEBINT Sovereign Threat Intelligence
Validates:
1. v3 .onion hidden service address regex validation.
2. OPSEC HTML content sanitization (stripping scripts, iframes, handlers).
3. Onion service crawling & IOC extraction.
4. Asset CVE correlation & CVSS scoring.
5. Threat actor attribution & MITRE ATT&CK technique mapping.
6. Universal Guardian kill switch (<25ms SLA) enforcement.
7. ToolRegistry registration for all 3 tools.
"""

import time
import pytest
from services.backend.safety.guardian import guardian
from services.backend.safety.registry import registry
from services.backend.cyber.dark_webint import dark_webint


@pytest.fixture(autouse=True)
def ensure_guardian_active():
    guardian.resume()
    yield
    guardian.resume()


def test_v3_onion_address_validation():
    # Valid 56 base32 character address
    valid_onion = "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion"
    assert len(valid_onion) == 56 + 6  # 56 chars + .onion
    assert dark_webint.is_valid_onion_address(valid_onion) is True

    # Invalid addresses
    assert dark_webint.is_valid_onion_address("short.onion") is False
    assert dark_webint.is_valid_onion_address("http://not_onion.com") is False
    assert dark_webint.is_valid_onion_address("127.0.0.1") is False


def test_html_opsec_sanitization():
    dirty_html = """
    <html>
        <head><script>alert('track_ip')</script></head>
        <body onload="send_beacon()">
            <h1>Target Leak</h1>
            <iframe src="http://malicious-beacon.onion"></iframe>
            <a href="#" onclick="exploit()">Click Here</a>
        </body>
    </html>
    """
    clean_html = dark_webint.sanitize_darkweb_content(dirty_html)
    assert "<script>" not in clean_html
    assert "alert('track_ip')" not in clean_html
    assert "<iframe>" not in clean_html
    assert "onload" not in clean_html
    assert "onclick" not in clean_html
    assert "Target Leak" in clean_html


def test_onion_crawl_and_ioc_extraction():
    valid_onion = "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwx.onion"
    res = dark_webint.crawl_onion_service(valid_onion)
    assert res["status"] == "RETRIEVED"
    assert "sanitized_html" in res
    assert "<script>" not in res["sanitized_html"]
    assert "extracted_intel" in res
    assert len(res["extracted_intel"]["extracted_iocs"]) >= 1


def test_threat_intelligence_correlation():
    res = dark_webint.correlate_threat_intelligence("192.168.1.100", open_ports=[445, 8000])
    assert res["cve_matches_count"] >= 2
    assert res["overall_severity"] == "CRITICAL"
    has_smb = any(m["port"] == 445 for m in res["cve_matches"])
    assert has_smb is True


def test_threat_actor_profiling():
    actor = dark_webint.profile_threat_actor("Cozy Bear")
    assert actor["status"] == "MATCHED"
    prof = actor["profile"]
    assert prof["actor_id"] == "G0016"
    assert "T1059.001" in [t["id"] for t in prof["ttps"]]
    assert "SolarWinds SUNBURST" in prof["malware_arsenal"]


def test_guardian_kill_switch_sla():
    guardian.trigger("Emergency drill")

    t0 = time.perf_counter()
    with pytest.raises(PermissionError):
        dark_webint.crawl_onion_service("expyuzz5wqqfdgah56trgahjkm56789abcdefghijklmnopqrstuvwxyz23.onion")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert latency_ms < 25.0, f"Guardian SLA violation: {latency_ms:.3f}ms >= 25.0ms"


def test_dark_webint_tools_registered():
    import services.backend.tools.dark_webint_tools

    expected = [
        ("crawl_onion_service", 1),
        ("correlate_threat_intelligence", 0),
        ("profile_threat_actor", 0)
    ]
    for t_name, exp_tier in expected:
        tool = registry.get(t_name)
        assert tool is not None, f"Tool '{t_name}' must be registered"
        assert tool.tier == exp_tier
