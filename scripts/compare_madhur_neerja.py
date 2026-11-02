import asyncio
import os
import tempfile
import time
import edge_tts
import sounddevice as sd
import soundfile as sf

TEXT = "Abhi, I am your desktop assistant. Ready to help you with code, terminal commands, and system tasks. Batao, kismein help chahiye?"

async def play(voice: str, name: str):
    print(f"\n>>> Playing: {name} ({voice})")
    comm = edge_tts.Communicate(TEXT, voice)
    chunks = [c["data"] async for c in comm.stream() if c["type"] == "audio"]
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"".join(chunks))
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
    print(f"Finished playing {name}.")

async def main():
    # 1. Play Madhur
    await play("hi-IN-MadhurNeural", "1. Madhur (Male - Jarvis/Tech-Buddy)")
    time.sleep(1.5)
    # 2. Play Neerja
    await play("en-IN-NeerjaNeural", "2. Neerja (Female - Friday/Executive-Assistant)")

if __name__ == "__main__":
    asyncio.run(main())
