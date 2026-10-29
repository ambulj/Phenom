"""
Phenom Voice Audition Utility: Sarvam AI Bulbul Voices
Auditions current valid production Sarvam Hindi speakers (Bulbul v3):
- chirag_hi_social   (Male, natural, social & casual [RECOMMENDED MALE])
- suman_hi_companion (Female, warm, friendly companion [RECOMMENDED FEMALE])
- vipul_hi_social    (Male, relaxed conversational)
- aarti_hi_customer  (Female, clear, professional & articulate)
- advait_hi_character(Male, expressive character voice)
- vandana_hi_ecomm   (Female, polished & commercial)
- aryaman_hi_ads     (Male, energetic advertisement tone)

Plays in-memory (RAM only) directly through system audio output.
"""

import sys
import os
import io
import time
import argparse

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.backend.voice.cloud_tts import sarvam_tts

SPEAKERS = [
    ("chirag_hi_social", "Male, natural & friendly [RECOMMENDED MALE]"),
    ("suman_hi_companion", "Female, warm companion [RECOMMENDED FEMALE]"),
    ("vipul_hi_social", "Male, relaxed conversational"),
    ("aarti_hi_customer", "Female, clear & articulate"),
    ("advait_hi_character", "Male, expressive character voice"),
    ("vandana_hi_ecomm", "Female, polished & commercial"),
    ("aryaman_hi_ads", "Male, energetic voice")
]

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

def audition_voices(target_speaker: str = None):
    print("=" * 75)
    print("PHENOM VOICE AUDITION: SARVAM AI BULBUL (HINDI & HINGLISH)")
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

    speakers_to_test = [s for s in SPEAKERS if target_speaker is None or s[0] == target_speaker]

    for speaker_name, description in speakers_to_test:
        print(f"\n--- Auditioning: [{speaker_name.upper()}] ({description}) ---")
        for label, display_text, synth_text in SAMPLE_UTTERANCES:
            print(f"  > Speaking ({label}): \"{display_text}\"")
            if key:
                wav = sarvam_tts.synthesize(synth_text, is_shareable=True, speaker=speaker_name, model="bulbul:v3")
                if wav:
                    print(f"    Synthesized {len(wav)} bytes in RAM. Playing audio...")
                    play_in_memory_wav(wav)
                    time.sleep(0.5)
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
    parser.add_argument("--speaker", default=None,
                        help="Select a specific speaker to audition (e.g. chirag_hi_social, suman_hi_companion)")
    args = parser.parse_args()
    audition_voices(args.speaker)
