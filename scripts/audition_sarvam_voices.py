"""
Phenom Voice Audition Utility: Full Sarvam AI Bulbul v3 Catalog
Auditions all 23 studio-recorded neural voices across male and female styles.

Usage:
  python scripts/audition_sarvam_voices.py --list
  python scripts/audition_sarvam_voices.py --gender male
  python scripts/audition_sarvam_voices.py --gender female
  python scripts/audition_sarvam_voices.py --speaker kabir
  python scripts/audition_sarvam_voices.py --speaker kabir --text "Hello Abhi, this is a custom test."
"""

import sys
import os
import io
import time
import argparse

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backend.voice.cloud_tts import sarvam_tts

MALE_SPEAKERS = [
    ("shubh", "Natural, versatile & clear [DEFAULT MALE]"),
    ("aditya", "Warm, professional & trustworthy"),
    ("kabir", "Deep, authoritative & confident [JARVIS STYLE]"),
    ("rahul", "Youthful, energetic & conversational"),
    ("rohan", "Friendly, casual & relaxed"),
    ("amit", "Crisp, news-anchor style"),
    ("dev", "Calm, tech-companion style"),
    ("ratan", "Mature, experienced tone"),
    ("varun", "Expressive & dynamic"),
    ("manan", "Gentle & modern"),
    ("sumit", "Upbeat & articulate"),
    ("aayan", "Soft-spoken & clear"),
    ("ashutosh", "Formal & dignified"),
    ("advait", "Storyteller & character tone")
]

FEMALE_SPEAKERS = [
    ("priya", "Articulate, expressive & balanced [DEFAULT FEMALE]"),
    ("pooja", "Warm, friendly companion [WARM SIDEKICK]"),
    ("simran", "Bright, youthful & conversational"),
    ("kavya", "Poised, elegant & clear"),
    ("ishita", "Engaging, lively & friendly"),
    ("shreya", "Melodic, calm & soft"),
    ("roopa", "Mature, reassuring & steady"),
    ("ritu", "Direct, professional & concise"),
    ("neha", "Energetic & cheerful")
]

ALL_SPEAKERS = MALE_SPEAKERS + FEMALE_SPEAKERS

SAMPLE_UTTERANCES = [
    ("Hindi Greeting", "Namaste Abhi, main Phenom hoon. Yeh meri aawaz ka namoona hai.", "नमस्ते अभि, मैं फिनोम हूँ। यह मेरी आवाज़ का नमूना है।"),
    ("Hinglish Casual", "Sab smooth chal raha hai Abhi, batao aaj kismein haath lagana hai?", "Sab smooth chal raha hai Abhi, batao aaj kismein haath lagana hai?")
]

def play_in_memory_wav(wav_bytes: bytes):
    try:
        import soundfile as sf
        import sounddevice as sd
        data, samplerate = sf.read(io.BytesIO(wav_bytes))
        sd.play(data, samplerate=samplerate, blocking=True)
    except Exception as e:
        print(f"  [AUDIO PLAYBACK NOTICE]: {e}")

def list_speakers():
    print("=" * 75)
    print("SARVAM AI BULBUL v3: FULL SPEAKER CATALOG (23 VOICES)")
    print("=" * 75)
    print("\n[MALE VOICES (14)]:")
    for name, desc in MALE_SPEAKERS:
        print(f"  - {name:<12} : {desc}")
    print("\n[FEMALE VOICES (9)]:")
    for name, desc in FEMALE_SPEAKERS:
        print(f"  - {name:<12} : {desc}")
    print("\n" + "=" * 75)
    print("To audition: python scripts/audition_sarvam_voices.py --speaker <name>")
    print("=" * 75)

def audition_voices(target_speaker: str = None, gender: str = None, custom_text: str = None):
    print("=" * 75)
    print("PHENOM VOICE AUDITION: SARVAM AI BULBUL v3")
    print("Owner Nickname: Abhi | Model: bulbul:v3")
    print("=" * 75)

    key = sarvam_tts.get_api_key()
    if not key:
        print("\n[NOTICE] Sarvam API key not found in Credential Manager or $env:SARVAM_API_KEY.")
        print("To listen to live Sarvam neural voices:")
        print("  1. Get a free API key at https://www.sarvam.ai")
        print("  2. Run: $env:SARVAM_API_KEY = 'your_api_key_here'")
        print("  3. Or save in Credential Manager: target 'Phenom/sarvam-api-key'")
        print("\nDemonstrating voice dispatch logic in dry-run mode...\n")

    if target_speaker:
        speakers_to_test = [s for s in ALL_SPEAKERS if s[0].lower() == target_speaker.lower()]
        if not speakers_to_test:
            print(f"[ERROR] Speaker '{target_speaker}' not recognized. Run with --list to see all options.")
            return
    elif gender == "male":
        speakers_to_test = MALE_SPEAKERS
    elif gender == "female":
        speakers_to_test = FEMALE_SPEAKERS
    else:
        # Highlight top recommended subset by default to avoid auditioning 23 voices all at once
        speakers_to_test = [
            ("shubh", "Natural, versatile & clear [DEFAULT MALE]"),
            ("aditya", "Warm & professional"),
            ("kabir", "Deep & confident [JARVIS STYLE]"),
            ("rahul", "Youthful & energetic"),
            ("dev", "Calm & tech companion"),
            ("priya", "Articulate & balanced [DEFAULT FEMALE]"),
            ("pooja", "Warm & friendly companion"),
            ("simran", "Bright & conversational")
        ]

    for speaker_name, description in speakers_to_test:
        print(f"\n--- Auditioning: [{speaker_name.upper()}] ({description}) ---")
        if custom_text:
            utterances = [("Custom Utterance", custom_text, custom_text)]
        else:
            utterances = SAMPLE_UTTERANCES

        for label, display_text, synth_text in utterances:
            print(f"  > Speaking ({label}): \"{display_text}\"")
            if key:
                wav = sarvam_tts.synthesize(synth_text, is_shareable=True, speaker=speaker_name, model="bulbul:v3")
                if wav:
                    print(f"    Synthesized {len(wav)} bytes in RAM. Playing audio...")
                    play_in_memory_wav(wav)
                    time.sleep(0.4)
                else:
                    print("    [Fallback] Failed to synthesize via Sarvam API; falling back to local SAPI voice.")
            else:
                print("    [Dry-run] Synthesize request prepared for speaker:", speaker_name)
                time.sleep(0.2)

    print("\n" + "=" * 75)
    print("Audition completed! Set your chosen speaker in config.toml under [assistant] sarvam_speaker.")
    print("=" * 75)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audition Sarvam AI voices for Phenom")
    parser.add_argument("--list", action="store_true", help="List all 23 available Sarvam Bulbul v3 speakers")
    parser.add_argument("--speaker", default=None, help="Select a specific speaker to audition (e.g. kabir, aditya, priya)")
    parser.add_argument("--gender", choices=["male", "female"], default=None, help="Audition all speakers of a specific gender")
    parser.add_argument("--text", default=None, help="Custom sentence to synthesize and audition")
    args = parser.parse_args()

    if args.list:
        list_speakers()
    else:
        audition_voices(args.speaker, args.gender, args.text)
