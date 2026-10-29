"""
Phenom Typosquatting Protection Engine (Task 7i)
Detects malicious, deceptive, and typosquatted package names attempting to mimic
popular packages on PyPI or npm.

Features:
- Curated database of top popular packages (requests, colorama, torch, cryptography, etc.)
- Multi-tier similarity detection:
  1. Levenshtein edit distance check (distance 1-2)
  2. Punctuation/hyphen evasion (e.g. fast-api -> fastapi, async-io -> asyncio)
  3. Suffix/prefix deception (e.g. cryptography-v2, numpy-tools, py-torch)
  4. Token permutation/inversion (e.g. docx-python vs python-docx)
  5. Truncation / legacy stripping (e.g. beautifulsoup -> beautifulsoup4, scikit -> scikit-learn)
- Prominent red warning banner generation and risk classification.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

class PackageSecurityReport(BaseModel):
    package_name: str
    target_popular_package: Optional[str] = None
    is_suspicious: bool = False
    edit_distance: Optional[int] = None
    similarity_reason: Optional[str] = None
    warning_banner: Optional[str] = None
    version: Optional[str] = "1.0.0"
    author: Optional[str] = "Unknown"
    downloads_count: int = 0
    homepage: Optional[str] = None

class TyposquatGuard:
    # Curated corpus of top packages widely used in Python / Node.js ecosystems
    POPULAR_PACKAGES: Set[str] = {
        "requests", "colorama", "torch", "cryptography", "fastapi", "pydantic",
        "pydantic-core", "python-dateutil", "urllib3", "beautifulsoup4", "numpy",
        "pandas", "scikit-learn", "flask", "asyncio", "websockets", "psutil",
        "pillow", "opencv-python", "opencv", "reportlab", "python-docx",
        "pytest", "httpx", "uvicorn", "click", "rich", "black", "flake8", "mypy",
        "scipy", "matplotlib", "seaborn", "tensorflow", "keras", "django", "sqlalchemy",
        "celery", "redis", "wheel", "setuptools", "pip", "twine", "boto3", "jinja2",
        "pyyaml", "certifi", "six", "idna", "charset-normalizer", "typing-extensions",
        "packaging", "attrs", "virtualenv", "setuptools-scm", "coverage", "tqdm",
        "greenlet", "aiohttp", "starlette", "anyio", "sniffio", "exceptiongroup"
    }

    SUSPICIOUS_AFFIXES: List[str] = [
        "-v2", "-v3", "-lib", "-tools", "-data", "-fast", "-imaging",
        "-client", "-core", "-dev", "-official", "-python", "-py",
        "py-", "python-", "lib-"
    ]

    def __init__(self, custom_popular_packages: Optional[Set[str]] = None):
        self.popular_packages = set(self.POPULAR_PACKAGES)
        if custom_popular_packages:
            self.popular_packages.update(custom_popular_packages)

    def evaluate_package(
        self,
        package_name: str,
        version: str = "latest",
        author: str = "Unknown",
        downloads_count: int = 150,
        homepage: Optional[str] = None
    ) -> PackageSecurityReport:
        """
        Analyzes a candidate package against the popular package corpus.
        Returns a PackageSecurityReport detailing typosquat risk.
        """
        raw_name = package_name.strip().lower()
        if not raw_name:
            return PackageSecurityReport(
                package_name=package_name,
                is_suspicious=True,
                warning_banner="Empty package name is invalid."
            )

        # 1. Exact match with popular package -> SAFE
        if raw_name in self.popular_packages:
            return PackageSecurityReport(
                package_name=package_name,
                target_popular_package=raw_name,
                is_suspicious=False,
                version=version,
                author=author,
                downloads_count=downloads_count,
                homepage=homepage or f"https://pypi.org/project/{raw_name}/"
            )

        # 2. Check token swap / inversion (e.g. docx-python vs python-docx)
        for popular in self.popular_packages:
            cand_tokens = set(raw_name.replace("_", "-").split("-"))
            pop_tokens = set(popular.replace("_", "-").split("-"))
            if len(cand_tokens) > 1 and cand_tokens == pop_tokens:
                return self._create_suspicious_report(
                    package_name=package_name,
                    target=popular,
                    dist=levenshtein_distance(raw_name, popular),
                    reason=f"Token order inversion of popular package '{popular}'",
                    version=version, author=author, downloads=downloads_count, homepage=homepage
                )

        # 3. Check de-hyphenation / punctuation evasion (e.g. fast-api -> fastapi, async-io -> asyncio)
        clean_cand = raw_name.replace("-", "").replace("_", "")
        for popular in self.popular_packages:
            clean_pop = popular.replace("-", "").replace("_", "")
            if clean_cand == clean_pop and raw_name != popular:
                return self._create_suspicious_report(
                    package_name=package_name,
                    target=popular,
                    dist=levenshtein_distance(raw_name, popular),
                    reason=f"Punctuation/hyphen variant of popular package '{popular}'",
                    version=version, author=author, downloads=downloads_count, homepage=homepage
                )

        # 4. Check affix spoofing (e.g. cryptography-v2, numpy-tools, py-torch)
        for popular in self.popular_packages:
            # Check prefix
            for pfx in ["py-", "python-", "lib-"]:
                if raw_name == f"{pfx}{popular}" or raw_name == f"{pfx}{popular.replace('python-', '')}":
                    return self._create_suspicious_report(
                        package_name=package_name,
                        target=popular,
                        dist=len(pfx),
                        reason=f"Prefix '{pfx}' added to popular package '{popular}'",
                        version=version, author=author, downloads=downloads_count, homepage=homepage
                    )
            # Check suffix
            for sfx in self.SUSPICIOUS_AFFIXES:
                if sfx.startswith("-") and raw_name == f"{popular}{sfx}":
                    return self._create_suspicious_report(
                        package_name=package_name,
                        target=popular,
                        dist=len(sfx),
                        reason=f"Suffix '{sfx}' added to popular package '{popular}'",
                        version=version, author=author, downloads=downloads_count, homepage=homepage
                    )

        # 5. Check truncated / prefix matching (e.g. scikit -> scikit-learn, beautifulsoup -> beautifulsoup4)
        for popular in self.popular_packages:
            if popular.startswith(raw_name) and len(raw_name) >= 5 and abs(len(popular) - len(raw_name)) <= 6:
                return self._create_suspicious_report(
                    package_name=package_name,
                    target=popular,
                    dist=levenshtein_distance(raw_name, popular),
                    reason=f"Truncated variant of popular package '{popular}'",
                    version=version, author=author, downloads=downloads_count, homepage=homepage
                )

        # 6. Check Levenshtein distance (distance 1 or 2)
        best_match: Optional[str] = None
        min_dist: int = 999
        for popular in self.popular_packages:
            d = levenshtein_distance(raw_name, popular)
            if d < min_dist:
                min_dist = d
                best_match = popular

        if min_dist <= 2 and best_match:
            return self._create_suspicious_report(
                package_name=package_name,
                target=best_match,
                dist=min_dist,
                reason=f"Within edit distance {min_dist} of popular package '{best_match}'",
                version=version, author=author, downloads=downloads_count, homepage=homepage
            )

        # Clean / unrecognized package without close typo
        return PackageSecurityReport(
            package_name=package_name,
            is_suspicious=False,
            version=version,
            author=author,
            downloads_count=downloads_count,
            homepage=homepage
        )

    def _create_suspicious_report(
        self,
        package_name: str,
        target: str,
        dist: int,
        reason: str,
        version: str,
        author: str,
        downloads: int,
        homepage: Optional[str]
    ) -> PackageSecurityReport:
        banner = f"Warning: '{package_name}' is within edit distance of popular package '{target}'. Proceed with caution."
        return PackageSecurityReport(
            package_name=package_name,
            target_popular_package=target,
            is_suspicious=True,
            edit_distance=dist,
            similarity_reason=reason,
            warning_banner=banner,
            version=version,
            author=author,
            downloads_count=downloads,
            homepage=homepage
        )

# Global typosquat guard instance
typosquat_guard = TyposquatGuard()
