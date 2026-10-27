# PHASE 3: Screen, UI, and browser automation

## Objective
Phenom can operate the browser and the desktop, with the user always able to see and stop it.

## Read first
AGENTS.md, SAFETY.md (especially tier 2, tier 3 and the prohibitions), ARCHITECTURE.md, HANDOFF.md.

## Build

1. **Browser.** Playwright with a persistent profile. A live view panel shows what Phenom is doing. The user logs in themselves; Phenom never types or stores passwords.
2. **Desktop control.** Screenshot understanding, mouse and keyboard actions, window focus. Prefer UI Automation or accessibility APIs; fall back to coordinates only when needed. Every action is Tier 2 and previewed as a step plan the first time.
3. **Live feedback.** Both together: an on-screen highlight of the current target, and a step list in the overlay showing done, current and upcoming steps.
4. **Human takeover.** If the user moves the mouse or presses a key during automation, pause at once and ask: continue or stop. Never resume without an answer. Distinguish the user's input from Phenom's own synthetic input.
5. **Fill-the-cart.** Amazon.in, Flipkart, Swiggy and Zomato. Search, choose, add to cart, and stop at the cart. Show the cart summary to the user. Payment, checkout completion, card data and OTP entry are Tier 3 and blocked in code (no code path can click final pay or place-order).
6. **YouTube summaries.** Use captions when present. Otherwise download audio with yt-dlp, transcribe locally with Whisper, and summarize with the local model. Delete the temporary audio afterwards.
7. **Limits.** Step limit, timeout, and a "stuck" detector on every run. Clear message when a limit is hit.
8. **Screen privacy.** Screenshots are analysed locally and never sent to the cloud. They are not saved unless the user asks.

## Tests
- A scripted browser task with a live view.
- Pause-on-input within 1 second, and no resume without an answer.
- A dry-run cart fill on each site that stops before payment.
- A test proving the pay and place-order actions are blocked at the tool level.
- A YouTube video without captions summarized and the temp audio deleted.

## Done criteria
- [ ] All eight items work
- [ ] Takeover pauses within 1 second
- [ ] Payment is impossible by construction
- [ ] SAFETY.md audit passes for the new tools

## Out of scope
RAG, integrations, Telegram.

## Finish
Follow the finish protocol in AGENTS.md section 7 and stop.
