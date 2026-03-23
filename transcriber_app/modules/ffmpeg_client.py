import os
import requests

FFMPEG_API = os.getenv("FFMPEG_API_URL", "http://ffmpeg-api:8080")


def get_audio_info(path: str) -> dict:
    with open(path, "rb") as f:
        r = requests.post(f"{FFMPEG_API}/audio/info", files={"file": f})
    r.raise_for_status()
    return r.json()


def convert_audio(path: str, fmt="wav") -> bytes:
    with open(path, "rb") as f:
        r = requests.post(
            f"{FFMPEG_API}/audio/convert",
            files={"file": f},
            data={"format": fmt}
        )
    r.raise_for_status()
    return r.content


def clean_audio(path: str) -> bytes:
    with open(path, "rb") as f:
        r = requests.post(
            f"{FFMPEG_API}/audio/clean",
            files={"file": f}
        )
    r.raise_for_status()
    return r.content
