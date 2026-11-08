"""Quick connectivity check for the Gnani Prisma STT endpoint.

Usage:  python test_stt.py [path/to/clip.wav]

Without an argument a one-second silent WAV is generated and sent, which is
enough to confirm that the API key and endpoint work.
"""

from __future__ import annotations

import os
import tempfile
import wave

import requests

from awaaz import config


def make_silent_wav(path: str, seconds: int = 1) -> None:
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 16000 * seconds)


def main() -> None:
    key = config.api_key()
    print(f"API key found: {'yes' if key else 'no'} (endpoint: {config.GNANI_API_URL})")
    if not key:
        print("Set GNANI_API_KEY in .env before running this check.")
        return

    import sys

    clip = sys.argv[1] if len(sys.argv) > 1 else ""
    temp_path = ""
    if not clip:
        handle, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(handle)
        make_silent_wav(temp_path)
        clip = temp_path

    try:
        with open(clip, "rb") as audio:
            response = requests.post(
                config.GNANI_API_URL,
                headers={"X-API-Key-ID": key},
                files={"audio_file": (os.path.basename(clip), audio)},
                data={"language_code": "hi-IN", "format": "transcribe", "itn_native_numerals": "false"},
                timeout=30,
            )
        print("Status code:", response.status_code)
        try:
            print("Response JSON:", response.json())
        except ValueError:
            print("Raw response:", response.text[:500])
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    main()
