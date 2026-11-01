"""
Phenom Indian Voice Audition Test
Plays Indian voices directly through host speakers using Edge Neural TTS (100% Free, Zero API Key).
"""

import asyncio
import io
import os
import sys
import tempfile
import time
import edge_tts
import sounddevice as sd
import soundfile as sf

VOICE_SAMPLES = [
    {
        "name": "Prabhat (Male - Indian English)",
        "voice": "en-IN-PrabhatNeural",
        "text": "Namaste Abhi. I am Phenom, speaking in the Prabhat male Indian English voice. All systems are online and running smoothly on your laptop. How do you like this tone?"
    },
    {
        "name": "Madhur (Male - Hindi & Hinglish)",
        "voice": "hi-IN-MadhurNeural",
        "text": "Haan Abhi, sab kuch bilkul sorted hai. Main Madhur hoon, aur main Hindi aur Hinglish dono natural andaaz mein bol sakta hoon. Batao aaj kya phodna hai?"
    },
    {
        "name": "Neerja (Female - Indian English)",
        "voice": "en-IN-NeerjaNeural",
        "text": "Hello Abhi. I am Neerja, your female Indian accent option. I can assist you with your code, morning briefing, and desktop tasks."
    },
    {
        "name": "Swara (Female - Hindi & Hinglish)",
        "voice": "hi-IN-SwaraNeural",
        "text": "Namaste Abhi. Main Swara hoon. Aapka schedule aur daily updates main is aawaaz mein de sakti hoon."
    }
]

async def synthesize_to_bytes(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def play_audio_bytes(audio_bytes: bytes):
    # edge-tts returns mp3 audio; soundfile can read it via tempfile or bytes
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name
    try:
        data, samplerate = sf.read(temp_path)
        sd.play(data, samplerate=samplerate)
        sd.wait()
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

async def test_voice(sample_idx: int):
    sample = VOICE_SAMPLES[sample_idx]
    print(f"\n[AUDITIONING] Voice {sample_idx+1}/{len(VOICE_SAMPLES)}: {sample['name']}")
    print(f"Voice ID: {sample['voice']}")
    print(f"Spoken text: \"{sample['text']}\"")
    print("Synthesizing neural audio...")
    audio_bytes = await synthesize_to_bytes(sample['text'], sample['voice'])
    print("Playing through your speakers now...")
    play_audio_bytes(audio_bytes)
    print("Audio playback complete.")

async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target == "all":
        for i in range(len(VOICE_SAMPLES)):
            await test_voice(i)
            time.sleep(0.8)
    else:
        idx = int(target)
        await test_voice(idx)

if __name__ == "__main__":
    asyncio.run(main())
