"""
Phenom Privacy Classifier
Enforces SAFETY.md Section 7:
- Inputs and files are 'private' by default.
- Specific paths (Documents, Desktop, Photos, Mail, Obsidian vault, credentials) are strictly 'private'.
- Folders explicitly marked shareable by the user, or public web content, are 'shareable'.
- Manual UI override takes highest precedence.
"""

import os
from typing import Optional, List, Literal

PrivacyLabel = Literal["private", "shareable"]

PRIVATE_PATH_KEYWORDS = [
    "documents", "desktop", "photos", "pictures", "mail", "vault",
    "password", "secret", "credential", "id_rsa", "financial", "medical", "tax"
]

PRIVATE_CONTENT_KEYWORDS = [
    "password", "credit card", "ssn", "secret_key", "bearer ", "private key",
    "confidential", "api_key"
]

class PrivacyClassifier:
    def __init__(self):
        self._shareable_folders: set[str] = set()

    def add_shareable_folder(self, folder_path: str):
        self._shareable_folders.add(os.path.abspath(folder_path))

    def remove_shareable_folder(self, folder_path: str):
        self._shareable_folders.discard(os.path.abspath(folder_path))

    def list_shareable_folders(self) -> List[str]:
        return list(self._shareable_folders)

    def classify(
        self,
        text: str,
        file_paths: Optional[List[str]] = None,
        manual_override: Optional[PrivacyLabel] = None
    ) -> tuple[PrivacyLabel, str]:
        """
        Classifies input as 'private' or 'shareable'.
        Returns (label, reason).
        """
        # Rule 1: Manual UI override
        if manual_override:
            return manual_override, f"Manual user override: {manual_override}"

        # Rule 2: Explicitly shareable folder check
        if file_paths:
            for fp in file_paths:
                norm_fp = os.path.abspath(fp)
                # Check if in a designated shareable folder
                in_shareable = any(norm_fp == sf or norm_fp.startswith(sf + os.sep) for sf in self._shareable_folders)
                if not in_shareable:
                    # Check private keywords in path
                    lower_fp = norm_fp.lower()
                    for kw in PRIVATE_PATH_KEYWORDS:
                        if kw in lower_fp:
                            return "private", f"Path '{fp}' contains private keyword '{kw}'"
                    # Default files to private unless shareable folder
                    return "private", f"File '{fp}' is not inside an authorized shareable folder"

        # Rule 3: Content inspection
        lower_text = text.lower()
        for kw in PRIVATE_CONTENT_KEYWORDS:
            if kw in lower_text:
                return "private", f"Content contains sensitive keyword '{kw}'"

        # Rule 4: Default is private per Permanent Rule 4
        return "private", "Default privacy policy (private by default)"

privacy_classifier = PrivacyClassifier()
