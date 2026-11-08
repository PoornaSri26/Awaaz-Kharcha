import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.vachana.ai/stt/v3"
API_KEY = os.environ.get("GNANI_API_KEY", "")

print(f"API Key found: {'Yes (Length: ' + str(len(API_KEY)) + ')' if API_KEY else 'No'}")

# Generate a small silent or dummy wav file for verification if test.wav does not exist
if not os.path.exists("test.wav"):
    import wave
    with wave.open("test.wav", "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b'\x00\x00' * 16000) # 1 sec of audio

print("Testing API endpoint connection...")
try:
    with open("test.wav", "rb") as f:
        r = requests.post(
            API_URL,
            headers={"X-API-Key-ID": API_KEY},
            files={"audio_file": ("test.wav", f)},
            data={"language_code": "hi-IN", "format": "transcribe", "itn_native_numerals": "false"},
            timeout=30,
        )
    print("Status Code:", r.status_code)
    try:
        print("Response JSON:", r.json())
    except Exception:
        print("Raw Response:", r.text)
except Exception as e:
    print("Request exception:", e)

