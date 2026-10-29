# Security Policy

## 1. Supported Versions

Phenom is actively maintained on the `main` branch. Only the latest release and branch HEAD receive security patches.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

---

## 2. Reporting a Vulnerability

We take the security and privacy of personal desktop computing seriously.

If you believe you have discovered a vulnerability in Phenom, please report it responsibly:

1. **GitHub Private Vulnerability Reporting**:
   - Navigate to the repository's **Security** tab and click **Report a vulnerability** to submit an advisory privately.
2. **Email Disclosure**:
   - Alternatively, contact the maintainer directly via GitHub user profile (`ambulj`).

### Please Include:
- A descriptive summary of the potential issue.
- Minimal, reproducible steps (or proof of concept script).
- Threat model impact (e.g., local privilege escalation, untrusted input taint bypass, sandbox egress).

We will acknowledge receipt within 48 hours and work with you to triage, test, and release an atomic patch before any public advisory.

---

## 3. Core Safety Architecture

Phenom implements a defense-in-depth safety layer designed to keep system automation and LLM tooling secure:

- **4-Tier Risk Model**: Every tool execution is classified from Tier 0 (read-only) through Tier 3 (blocked by default, strictly physical typed confirmation required on desktop).
- **Guardian Kill Switch**: Inviolable global hardware hotkey (`Ctrl+Alt+Pause`) and UI button that asynchronously and synchronously terminates model streaming, child process trees, and OS automation.
- **Taint Tracking**: Ingestion of untrusted web, email, PDF, or OCR text flags the execution turn chain, forcing explicit user confirmation for all subsequent actions.
- **Privacy Router**: Zero private data (files, emails, credentials, Indian PII like Aadhaar/PAN/UPI) transits to cloud models without explicit user preview and approval.
- **Local-Only Secret Storage**: All credentials reside in Windows Credential Manager; database storage is encrypted at rest using SQLCipher.
