#!/usr/bin/env python3
"""Azure TTS REST 합성. 문장 하나당 wav 하나."""
import os
import subprocess
import sys
import urllib.request
import xml.sax.saxutils as sx


def load_env(path=None):
    path = path or os.path.join(os.path.dirname(__file__), "..", ".env")
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def synth(text: str, out_path: str, env=None, rate: str = "0%"):
    env = env or load_env()
    region = env["AZURE_SPEECH_REGION"]
    voice = env.get("AZURE_TTS_VOICE", "ko-KR-SunHiNeural")
    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="ko-KR"><voice name="{voice}">'
        f'<prosody rate="{rate}">{sx.escape(text)}</prosody>'
        f"</voice></speak>"
    )
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": env["AZURE_SPEECH_KEY"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "aivideo",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        audio = r.read()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(audio)
    return duration(out_path)


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


if __name__ == "__main__":
    print(synth(sys.argv[1], sys.argv[2]))
