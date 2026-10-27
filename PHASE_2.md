# PHASE 2: Voice

## Objective
Hands-free voice with a wake word, speech in and out, without changing the Safety layer or router.

## Read first
AGENTS.md, ARCHITECTURE.md, SAFETY.md, PERSONALITY.md, SPIKES.md (Spike F), HANDOFF.md.

## Build

1. **Wake word.** Local detector running in a background thread or process with low CPU use. On/off toggle in the UI, a visible listening indicator, and a custom wake phrase setting.
2. **Speech to text.** Local Whisper (model size chosen from Spike F) with voice activity detection to find the end of speech. Push-to-talk as a fallback.
3. **Text to speech.** Local male voice, streamed sentence by sentence so speech starts before the full reply is ready.
4. **Barge-in.** The wake word or a hotkey stops speech immediately and the orb returns to listening.
5. **Orb.** Listening, thinking, and speaking states with amplitude-driven bursts while speaking.
6. **Hotkeys.** Defaults for push-to-talk, show or hide Phenom, and kill switch; editable in settings; conflict detection.
7. **Safety.** Voice requests use the same router and Safety layer. Tier 1 and above need an on-screen confirmation, never a voice-only one. A spoken "yes" never approves Tier 2.
8. **Mic privacy.** Audio is processed locally, never stored by default, never sent to the cloud. A visible mic-active indicator. A mute toggle.
9. **Spoken style.** Short replies in voice; long answers go to the chat panel with a short spoken summary.

## Tests
- Wake-word false triggers over 10 minutes of normal speech and music (report the count).
- End-of-speech to first-audio latency.
- Barge-in latency.
- A spoken destructive request still shows the confirmation dialog.
- No audio files are written to disk by default.

## Done criteria
- [ ] Hands-free wake word works and can be disabled
- [ ] Spoken replies play in the male voice, with streaming
- [ ] Barge-in works
- [ ] Hotkeys editable with conflict checks
- [ ] Latency and false-positive numbers recorded in HANDOFF.md
- [ ] Safety rules for voice verified by tests

## Out of scope
Screen control, browser automation, RAG.

## Finish
Follow the finish protocol in AGENTS.md section 7 and stop.
