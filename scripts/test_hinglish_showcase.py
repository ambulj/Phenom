"""
Phenom Hinglish Voice Showcase
Tests all free neural voices on real-world conversational Hinglish code-switching:
Mixing English technical terms with natural Hindi grammar.
"""

import asyncio
import os
import sys
import tempfile
import edge_tts
import sounddevice as sd
import soundfile as sf

HINGLISH_SHOWCASE = [
    {
        "id": "madhur",
        "name": "Madhur (Male - Urban Hinglish)",
        "voice": "hi-IN-MadhurNeural",
        "sample": "Abhi, sab kuch bilkul sorted hai! Saare 261 unit tests pass ho chuke hain, aur git repo completely clean hai. Batao, ab kismein haath lagana hai?"
    },
    {
        "id": "swara",
        "name": "Swara (Female - Urban Hinglish)",
        "voice": "hi-IN-SwaraNeural",
        "sample": "Namaste Abhi. Maine aapka calendar aur emails check kar liye hain. Agli meeting shaam ko 4 baje hai, aur koi pending blockers nahi hain."
    },
    {
        "id": "prabhat",
        "name": "Prabhat (Male - Metro Tech Hinglish)",
        "voice": "en-IN-PrabhatNeural",
        "sample": "Hey Abhi! Backend service port 8000 pe online hai, and desktop app smoothly chal rahi hai. Let me know when you want to run the next task."
    },
    {
        "id": "neerja",
        "name": "Neerja (Female - Metro Tech Hinglish)",
        "voice": "en-IN-NeerjaNeural",
        "sample": "Hello Abhi. Security scan complete ho gaya hai. Zero secrets found, and all systems are completely protected."
    }
]

async def synthesize(text: str, voice: str) -> bytes:
    comm = edge_tts.Communicate(text, voice)
    chunks = [c["data"] async for c in comm.stream() if c["type"] == "audio"]
    return b"".join(chunks)

def play(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        p = f.name
    try:
        data, sr = sf.read(p)
        sd.play(data, samplerate=sr)
        sd.wait()
    finally:
        try:
            os.remove(p)
        except Exception:
            pass

async def test_single(idx: int):
    item = HINGLISH_SHOWCASE[idx]
    print(f"\n[HINGLISH AUDITION {idx+1}/{len(HINGLISH_SHOWCASE)}] {item['name']}")
    print(f"Voice ID: {item['voice']}")
    print(f"Sample: \"{item['sample']}\"")
    print("Synthesizing Hinglish speech...")
    b = await synthesize(item['sample'], item['voice'])
    print("Playing through your laptop speakers now...")
    play(b)
    print("Done.")

async def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "all":
        for i in range(len(HINGLISH_SHOWCASE)):
            await test_single(i)
    else:
        await test_single(int(arg))

if __name__ == "__main__":
    asyncio.run(main())
