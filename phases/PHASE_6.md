Phase 6: Telegram Remote Control and Approvals
PHASE 6: Telegram remote control.

1. A Telegram bot that accepts messages only from the owner’s Telegram user ID. Every other sender is ignored silently and logged.
2. Remote commands run through the same router and Safety layer as local ones, with the source recorded in the action log.
3. Approvals over Telegram for Tier 1 and Tier 2 actions, showing the same preview as the desktop dialog. Tier 3 actions cannot be approved remotely.
4. A remote kill switch command that halts everything and confirms it halted.
5. Status, task, and log summaries on request, with private content redacted from messages.
6. The bot token lives in Credential Manager. Add a /lock command that disables remote control until re-enabled at the desktop.

TESTS: a message from a non-whitelisted ID is ignored; an approval round trip works; Tier 3 is refused remotely; the remote kill switch halts a running task.

DONE CRITERIA: all six items pass and nothing sensitive is ever sent to Telegram.
FINISH: follow the finish protocol and stop.