Phase 7: Polish and Packaging
PHASE 7: polish and packaging.

1. A Windows installer with electron-builder that bundles the UI and the Python backend and checks prerequisites on first run.
2. A first-run wizard: English UI and voice, API keys (NVIDIA, Google OAuth, Telegram), safe default hotkeys, and which folders Phenom may index.
3. Auto-start with Windows, a tray icon, and quiet background start.
4. Auto-update with rollback if the new version fails to start.
5. Local-only crash logs with a one-click export that strips private content.
6. A performance pass: idle CPU and RAM, orb frame rate, and wake-word load, with numbers.
7. A final safety audit: walk every tool through the four tiers, confirm the kill switch works from the UI, voice, hotkey, and Telegram, and confirm nothing private reaches the cloud without a previewed approval.

TESTS: clean install and uninstall on a fresh Windows user profile; update and rollback; the safety audit checklist.

DONE CRITERIA: installs cleanly, starts with Windows, updates safely, and passes the safety audit.
FINISH: follow the finish protocol and stop.