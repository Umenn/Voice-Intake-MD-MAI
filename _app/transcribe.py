"""
Audio transcription via OpenAI Whisper API.
Handles Romanian, Russian, and English automatically.
"""

from openai import OpenAI
from config import OPENAI_API_KEY

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY lipseste din .env. "
                "Adaugati cheia la robo_cop_bot/.env"
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

LANGUAGE_CODES = {
    "ro": "romanian",
    "ru": "russian",
    "en": "english",
}


def transcribe(audio_path: str, language: str = "ro") -> dict:
    """
    Transcribe audio file to text using Whisper.
    Args:
        audio_path: path to audio file (webm, mp3, wav, m4a, ogg)
        language:   'ro' | 'ru' | 'en'  (default Romanian)
    Returns:
        {text: str, language: str, duration_seconds: float}
    """
    with open(audio_path, "rb") as f:
        response = _get_client().audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
            response_format="verbose_json",
        )
    return {
        "text":             response.text,
        "language":         response.language,
        "duration_seconds": response.duration,
    }
