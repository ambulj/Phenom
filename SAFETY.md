# SAFETY.md: risk tiers and safety rules

This file is the contract for the Safety layer. The code enforces it; this document must always match the code. Update it whenever a tool is added or changed.

## 1. Risk tiers
| Tier | Name | Behaviour | Examples |
| --- | --- | --- | --- |
| 0 | Read-only | Runs automatically, logged | list files, read a file, search memory & vector store, search photos, inspect UI elements, take screenshot (RAM), summarize YouTube, organize Downloads dry run, get mode, list scheduled jobs, get weather, get tech news, get market quote, get financial watchlist, get mutual fund quote, get sports score, search research papers, lookup DOI citation, search/read Gmail, list calendar events |
| 1 | Reversible change | One confirmation; user may choose "remember for this folder" | create or move or copy a file, open or close an app, organize Downloads apply (reversible with undo), write Obsidian vault note, append daily log, set mode, schedule reminder, cancel scheduled job, add/remove financial watchlist, create Gmail draft, generate document (.docx, .xlsx, .pptx, .pdf) |
| 2 | Destructive or external | Explicit confirmation with a preview of exactly what will happen; never remembered | recycle-bin delete, create a calendar event, send content to a cloud model, drive the browser or screen, fill a web cart, desktop action plans, remote approvals |
| 3 | Blocked or system-level | Blocked by default; allowed only if listed in section 6; needs a typed confirmation on the desktop; cannot be approved remotely | modify/delete photos, payments, checkout completion, OTP entry, permanent delete, changing system settings, sending email, editing or deleting calendar events, financial trading/orders, financial advice/recommendations, touching credentials, installing software |

Unknown tools or unclassified calls are Tier 3.

## 2. Tool declaration
Every tool declares: `name`, `tier`, `description`, a Pydantic argument schema, `preview(args)` (a human-readable description of the effect), and `undo(args, result)` when reversible. A tool without a tier cannot be registered.

## 3. Confirmation dialog
- Shows: what Phenom wants to do, the tool, the exact arguments, the tier, and a preview (for example the list of files to be moved with old and new paths, or the ordered steps in an automation plan).
- Buttons: Approve, Deny, and (Tier 1 only) "Approve and remember for this folder".
- Timeouts: no answer within 2 minutes counts as Deny.
- Remembered choices are listed in Settings with a revoke button. They never apply to Tier 2 or 3, and never outside the chosen folder.
- **Voice Safety Guarantee**: Voice requests are marked `source="voice"`. Destructive (Tier 2) and reversible (Tier 1) actions strictly require an on-screen visual confirmation dialog; spoken "yes" or voice affirmations are categorically refused by safety code.
- **Automation Takeover**: Physical user mouse or keyboard input during automated desktop/browser tasks triggers an instant pause (< 1 second). Automation will never resume without an explicit user answer (`continue` or `stop`).
- **Telegram Remote Approvals**: Tier 1 and Tier 2 actions may be approved over Telegram by the whitelisted owner ID, presenting the exact same preview as on the desktop. Tier 3 actions are permanently prohibited from remote approval and require physical typed desktop confirmation.
- **Telegram Whitelist & Lock Guarantee**: Messages or callbacks from non-whitelisted user IDs are silently ignored and logged. The `/lock` command disables remote control until physically re-enabled at the desktop application.

## 4. Action log
SQLite table `action_log`, one row per attempted action:
`id, timestamp, source (desktop|voice|telegram|scheduler), tool, tier, arguments_redacted, decision (auto|approved|denied|blocked|timeout), result_status, error, undo_token`
- Arguments are redacted: no file contents, email bodies, passwords, keys, or payment details.
- The UI log panel supports filter, search, export, and "Undo" where an undo token exists.

## 5. Guardian kill switch
- UI button and a global hotkey (default Ctrl+Alt+Pause, editable).
- On trigger: cancel the running model stream, abort every running tool, close automation sessions, stop speech and listening, set state to "halted", log the event.
- Works even if the model or a tool is hung (runs in its own thread or process and force-terminates child processes).
- After a halt Phenom does nothing until the user clicks Resume.

## 6. Tier 3 allowlist
Empty by default. Anything added needs the user's written approval and a line here: tool, reason, date.
Permanently blocked without allowlist entries: `modify_photo`, `delete_photo`, `checkout_pay`, `enter_payment_info`, `send_email`, `calendar_delete_event`, `calendar_edit_event`, `place_trade`, `suggest_trade`.

## 7. Privacy labels and cloud escalation
- Labels: `private` (default) or `shareable`.
- Automatic rules: anything in Documents, Desktop, Photos, Mail, Obsidian vault (`vault/`), financial, medical, ID or credential-looking content is `private`. Files in a folder the user marks shareable, and public web content, are `shareable`. The user can override any label in the UI.
- Local first: all requests start on the local model.
- Cloud escalation only when ALL are true: the input is `shareable`, it is too long or too hard for the local model, and the user approved after seeing a preview.
- Preview shows: which model, the exact text or the file excerpts that will be sent, the size, and the reason for escalation.
- "Remember for this folder" is allowed for shareable folders only.
- Every escalation is logged with what was sent (redacted) and the reason.

## 8. Hard prohibitions (enforced in code)
- No trades, no buy or sell suggestions, no financial advice phrasing. Informational market quotes and single-trigger price alerts only.
- No sending email. Phenom may only save email drafts for user review.
- No calendar deletion or editing of existing events. Creating new events is permitted under Tier 2.
- No photo move, rename, edit or delete. Photos are indexed and searched only.
- No permanent delete. Delete means Recycle Bin (`send2trash`).
- No payment, checkout completion, entering card data, or OTP submission. Fill-the-cart stops unconditionally before checkout.
- No typing or storing passwords.
- No audio stored on disk; no audio sent to the cloud. Audio is processed strictly in-memory (RAM) and discarded immediately. Temporary YouTube audio scratch files are guaranteed deleted after transcription.
- Screenshots are processed in RAM only, analyzed locally, and never sent to the cloud or saved without explicit user instruction.
- Spoken "yes" never approves Tier 1 or Tier 2 actions.
- No remote approval for Tier 3 actions; Tier 3 must be confirmed with typed confirmation on the desktop.
- Telegram bot messages from non-whitelisted user IDs are silently ignored and logged; zero replies sent to unauthorized users.
- Remote control can be locked at any time via /lock and cannot be unlocked from Telegram.

## 9. Audit checklist (run at the end of Phases 1, 2, 3, 4, 5, 6, 7)
- [x] Every registered tool has a tier, preview and tests
- [x] No code path calls a tool without the Safety layer
- [x] Kill switch works from UI, hotkey, voice, and Telegram (when present)
- [x] Spoken confirmation cannot approve destructive or reversible actions (on-screen confirmation enforced)
- [x] Zero audio files written to disk (in-memory RAM processing verified)
- [x] Payment and checkout completion are impossible by construction (Tier 3 blocked)
- [x] Screenshots processed in RAM only (zero saved without instruction)
- [x] Photos are untouched by construction; modify and delete are Tier 3 blocked
- [x] Downloads cleanup is 100% reversible via undo token
- [x] Vector embeddings and memory stored encrypted at rest in SQLCipher
- [x] Human takeover pauses automation within 1 second and never resumes without explicit answer
- [x] Sending email is blocked in code and classified Tier 3
- [x] Calendar event deletion and editing are blocked in code and classified Tier 3
- [x] Placing trades and offering buy/sell suggestions are blocked in code and classified Tier 3
- [x] Financial watchlist alerts trigger once without spamming
- [x] Live data pipeline falls back to scraping when API fails and is explicitly labelled
- [x] Generated documents (.docx, .xlsx, .pptx, .pdf) open and parse correctly
- [x] Telegram bot strictly accepts owner user ID only; non-whitelisted senders silently ignored and logged
- [x] Telegram remote approvals work for Tier 1 and Tier 2 with preview
- [x] Tier 3 actions are categorically refused remotely
- [x] Telegram /halt command halts running tasks immediately
- [x] Telegram /lock command disables remote control until re-enabled at the desktop
- [x] Nothing private reaches the cloud or Telegram without a previewed approval
- [x] Log contains no secrets, credentials, or private content
- [x] Every prohibition in section 8 has a test
