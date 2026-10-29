"""
Phenom Daily Briefing & Quiet Hours Protocol (Task 7h)
Implements:
1. "Good Morning" spoken trigger (5:00 AM - 12:00 PM).
2. Strict spoken duration constraint: < 60 seconds spoken output (~130 words maximum).
3. Contents: Top 3 tech news headlines + unread email draft summaries.
   (Weather and calendar strictly excluded per owner decision).
4. Quiet Hours Protocol: 11:00 PM - 7:00 AM (23:00 - 07:00).
   Proactive speech silenced; notifications and briefing committed silently to Obsidian vault daily log.
5. Failure Resilience: Gracefully handles network outages or unauthenticated email.
6. Vault Journal Commitment: Appends full markdown to Daily Logs/YYYY-MM-DD.md.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from services.backend.integrations.news_briefing import tech_news
from services.backend.integrations.google_workspace import google_workspace
from services.backend.memory.vault import vault_manager
from services.backend.memory.db import encrypted_db

DEFAULT_QUIET_START = 23 # 11:00 PM
DEFAULT_QUIET_END = 7    # 7:00 AM
BRIEFING_START_HOUR = 5  # 5:00 AM
BRIEFING_END_HOUR = 12   # 12:00 PM (Noon)

class DailyBriefingManager:
    def __init__(self):
        self.quiet_start = DEFAULT_QUIET_START
        self.quiet_end = DEFAULT_QUIET_END

    def is_quiet_hours(self, hour: Optional[int] = None) -> bool:
        """
        Returns True if current local time falls within Quiet Hours (default 11 PM - 7 AM).
        Proactive speech is silenced during quiet hours.
        """
        if hour is None:
            hour = datetime.now().hour

        if self.quiet_start > self.quiet_end:
            # Wraps around midnight (e.g. 23 to 7)
            return hour >= self.quiet_start or hour < self.quiet_end
        else:
            return self.quiet_start <= hour < self.quiet_end

    def is_briefing_time_window(self, hour: Optional[int] = None) -> bool:
        """Returns True if local time is between 5:00 AM and 12:00 PM."""
        if hour is None:
            hour = datetime.now().hour
        return BRIEFING_START_HOUR <= hour < BRIEFING_END_HOUR

    async def generate_briefing(
        self,
        force_hour: Optional[int] = None,
        dry_run_speech: bool = False
    ) -> Dict[str, Any]:
        """
        Generates daily briefing:
        1. Gathers tech news and email summaries.
        2. Formats spoken text under 60-second constraint (~130 words maximum).
        3. Checks Quiet Hours: silences TTS if quiet hours active.
        4. Commits full markdown entry to Obsidian vault daily log.
        """
        hour = force_hour if force_hour is not None else datetime.now().hour
        quiet = self.is_quiet_hours(hour)

        # 1. Fetch Top 3 Tech News Headlines
        news_headlines = []
        try:
            news_res = await tech_news.get_briefing(items_per_source=1)
            articles = news_res.get("articles", [])
            for art in articles[:3]:
                title = art.get("title", "").strip()
                source = art.get("source", "Tech")
                if title:
                    news_headlines.append(f"{source}: {title}")
        except Exception:
            news_headlines = []

        # 2. Fetch Unread Email Summary
        email_summary = ""
        unread_count = 0
        if not google_workspace.is_gmail_configured():
            email_summary = "Gmail is not connected."
        else:
            try:
                unread = google_workspace.search_emails(query="UNSEEN", max_results=3)
                unread_count = len(unread)
                if unread_count > 0:
                    email_summary = f"You have {unread_count} unread email(s)."
                else:
                    email_summary = "Your inbox is clean."
            except Exception:
                email_summary = "Email status unavailable."

        # 3. Construct Spoken Text (< 60s SLA / ~130 words)
        spoken_parts = ["Good morning, sir."]
        if news_headlines:
            spoken_parts.append("Here are today's top tech headlines:")
            for i, h in enumerate(news_headlines[:3], 1):
                clean_h = h.split(" - ")[0]
                spoken_parts.append(f"{i}. {clean_h}.")
        else:
            spoken_parts.append("Tech news feed is currently offline.")

        spoken_parts.append(email_summary)
        spoken_parts.append("Ready for your instructions.")

        spoken_text = " ".join(spoken_parts)
        words = spoken_text.split()
        word_count = len(words)
        
        # Approximate spoken duration at 130 words per minute
        est_spoken_seconds = round((word_count / 130.0) * 60.0, 1)

        # 4. Construct Markdown for Vault & UI
        md_lines = [
            "## 🌅 Daily Morning Briefing",
            f"*Generated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "### 📰 Top Tech News"
        ]
        if news_headlines:
            for h in news_headlines:
                md_lines.append(f"- {h}")
        else:
            md_lines.append("- *Tech news feed offline or unreachable.*")

        md_lines.append("\n### ✉️ Email Status")
        md_lines.append(f"- {email_summary}")

        briefing_markdown = "\n".join(md_lines)

        # 5. Commit to Obsidian Vault Daily Log
        vault_file = None
        try:
            vault_file = vault_manager.append_daily_log(briefing_markdown)
        except Exception as e:
            print(f"[DailyBriefing] Error appending to vault daily log: {e}")

        # 6. Speech Output Handling (Silenced during Quiet Hours)
        speech_played = False
        if quiet:
            speech_action = "silenced_quiet_hours"
        else:
            speech_action = "spoken"
            if not dry_run_speech:
                from services.backend.voice.tts import tts_engine
                tts_engine.speak(spoken_text)
                speech_played = True

        return {
            "ok": True,
            "spoken_text": spoken_text,
            "briefing_markdown": briefing_markdown,
            "word_count": word_count,
            "est_spoken_seconds": est_spoken_seconds,
            "under_60s_sla": est_spoken_seconds < 60.0,
            "quiet_hours_active": quiet,
            "speech_action": speech_action,
            "speech_played": speech_played,
            "vault_file": vault_file,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

daily_briefing_manager = DailyBriefingManager()
