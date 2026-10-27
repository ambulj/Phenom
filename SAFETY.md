# SAFETY.md: risk tiers and safety rules

This file is the contract for the Safety layer. The code enforces it; this document must always match the code. Update it whenever a tool is added or changed.

## 1. Risk tiers
| Tier | Name | Behaviour | Examples |
| --- | --- | --- | --- |
| 0 | Read-only | Runs automatically, logged | list files, read a file, search memory, check weather, read calendar, system status |
| 1 | Reversible change | One confirmation; user may choose "remember for this folder" | create or move or copy a file, open or close an app, organize Downloads, save an email draft, write a vault note |
| 2 | Destructive or external | Explicit confirmation with a preview of exactly what will happen; never remembered | recycle-bin delete, create a calendar event, send content to a cloud model, drive the browser or screen, fill a web cart, remote approvals |
| 3 | Blocked or system-level | Blocked by default; allowed only if listed in section 6; needs a typed confirmation on the desktop; cannot be approved remotely | payments, permanent delete, changing system settings, sending email, touching credentials, installing software, editing other people's calendar events |

Unknown tools or unclassified calls are Tier 3.

## 2. Tool declaration
Every tool declares: `name`, `tier`, `description`, a Pydantic argument schema, `preview(args)` (a human-readable description of the effect), and `undo(args, result)` when reversible. A tool without a tier cannot be registered.

## 3. Confirmation dialog
- Shows: what Phenom wants to do, the tool, the exact arguments, the tier, and a preview (for example the list of files to be moved with old and new paths).
- Buttons: Approve, Deny, and (Tier 1 only) "Approve and remember for this folder".
- Timeouts: no answer within 2 minutes counts as Deny.
- Remembered choices are listed in Settings with a revoke button. They never apply to Tier 2 or 3, and never outside the chosen folder.

## 4. Action log
SQLite table `action_log`, one row per attempted action:
`id, timestamp, source (desktop|voice|telegram|scheduler), tool, tier, arguments_redacted, decision (auto|approved|denied|blocked|timeout), result_status, error, undo_token`
- Arguments are redacted: no file contents, email bodies, passwords, keys.
- The UI log panel supports filter, search, export, and "Undo" where an undo token exists.

## 5. Guardian kill switch
- UI button and a global hotkey (default Ctrl+Alt+Pause, editable).
- On trigger: cancel the running model stream, abort every running tool, close automation sessions, stop speech and listening, set state to "halted", log the event.
- Works even if the model or a tool is hung (runs in its own thread or process and force-terminates child processes).
- After a halt Phenom does nothing until the user clicks Resume.

## 6. Tier 3 allowlist
Empty by default. Anything added needs the user's written approval and a line here: tool, reason, date.

## 7. Privacy labels and cloud escalation
- Labels: `private` (default) or `shareable`.
- Automatic rules: anything in Documents, Desktop, Photos, Mail, Obsidian vault, financial, medical, ID or credential-looking content is `private`. Files in a folder the user marks shareable, and public web content, are `shareable`. The user can override any label in the UI.
- Local first: all requests start on the local model.
- Cloud escalation only when ALL are true: the input is `shareable`, it is too long or too hard for the local model, and the user approved after seeing a preview.
- Preview shows: which model, the exact text or the file excerpts that will be sent, the size, and the reason for escalation.
- "Remember for this folder" is allowed for shareable folders only.
- Every escalation is logged with what was sent (redacted) and the reason.

## 8. Hard prohibitions (enforced in code)
- No trades, no buy or sell suggestions, no financial advice phrasing.
- No photo move, rename, edit or delete.
- No permanent delete.
- No payment, checkout completion, or entering card data.
- No sending email.
- No typing or storing passwords.
- No audio stored by default; no audio sent to the cloud.

## 9. Audit checklist (run at the end of Phases 1, 3, 5, 6, 7)
- [ ] Every registered tool has a tier, preview and tests
- [ ] No code path calls a tool without the Safety layer
- [ ] Kill switch works from UI, hotkey, voice, and Telegram (when present)
- [ ] Nothing private reaches the cloud without a previewed approval
- [ ] Log contains no secrets or private content
- [ ] Every prohibition in section 8 has a test
