"""
Speaker separation for police interview transcripts.
Uses GPT-4o-mini to split a raw transcript into:
  - DECLARANT: victim / witness / person being interviewed
  - OFITER:    police officer (questions, prompts)

No audio fingerprinting required — works purely from conversation patterns:
  * Officer asks short questions ("Când?", "Unde erați?", "Descrieți...")
  * Declarant gives long narrative answers

Output is used so that ONLY the declarant's text reaches extraction and
the officer's questions are excluded from the final document.
"""

import json
import re
from openai import OpenAI
from config import OPENAI_API_KEY

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY lipseste din .env."
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """Ești un asistent specializat în analiza transcrierilor interviurilor de poliție.
Transcrierea conține vocea unui ofițer de poliție și vocea unei persoane audiate (victimă, martor sau suspect).

SARCINA TA:
Împarte transcrierea în segmente și etichetează fiecare segment cu vorbitorul:
- OFITER: ofițerul de poliție — pune întrebări scurte, solicită clarificări, dă instrucțiuni
- DECLARANT: persoana audiată — oferă răspunsuri narative, descrie evenimentele, dă detalii

REGULI:
1. Dacă nu ești sigur, atribuie textul narativ lung la DECLARANT, întrebările scurte la OFITER.
2. Păstrează textul original exact — nu modifica, nu rezuma.
3. Returnează EXCLUSIV JSON valid, fără text înainte sau după.
4. Structura răspunsului:
{
  "segments": [
    {"speaker": "OFITER",    "text": "..."},
    {"speaker": "DECLARANT", "text": "..."},
    ...
  ],
  "declarant_text": "textul complet al DECLARANT concatenat",
  "ofiter_text":    "textul complet al OFITER concatenat",
  "confidence":     "high | medium | low"
}
5. confidence = "low" dacă transcrierea nu pare a fi un interviu (un singur vorbitor, monolog, etc.)
"""


def separate(transcript: str) -> dict:
    """
    Split a raw interview transcript into officer vs declarant segments.

    Args:
        transcript: raw Whisper transcript (any language, typically RO/RU)

    Returns:
        {
            "segments":       [{"speaker": "OFITER"|"DECLARANT", "text": "..."}],
            "declarant_text": str,   # only declarant — use this for extraction
            "ofiter_text":    str,   # officer questions — excluded from docs
            "confidence":     str,   # "high" | "medium" | "low"
            "error":          str | None
        }
    """
    if not transcript.strip():
        return _empty("Transcrierea este goală.")

    # If transcript is very short (< 60 chars), assume single speaker
    if len(transcript.strip()) < 60:
        return {
            "segments":       [{"speaker": "DECLARANT", "text": transcript.strip()}],
            "declarant_text": transcript.strip(),
            "ofiter_text":    "",
            "confidence":     "low",
            "error":          None,
        }

    user_msg = (
        "Transcrierea interviului de poliție:\n"
        '"""\n'
        + transcript
        + '\n"""'
    )

    try:
        resp = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw    = resp.choices[0].message.content
        result = json.loads(raw)

        # Validate and normalise
        segments = result.get("segments", [])
        if not segments:
            # GPT returned no segments — treat whole thing as declarant
            return {
                "segments":       [{"speaker": "DECLARANT", "text": transcript.strip()}],
                "declarant_text": transcript.strip(),
                "ofiter_text":    "",
                "confidence":     "low",
                "error":          None,
            }

        # Rebuild declarant/ofiter texts from segments in case GPT missed them
        declarant_parts = [s["text"] for s in segments if s.get("speaker") == "DECLARANT"]
        ofiter_parts    = [s["text"] for s in segments if s.get("speaker") == "OFITER"]

        return {
            "segments":       segments,
            "declarant_text": result.get("declarant_text") or " ".join(declarant_parts),
            "ofiter_text":    result.get("ofiter_text")    or " ".join(ofiter_parts),
            "confidence":     result.get("confidence", "medium"),
            "error":          None,
        }

    except Exception as exc:
        # On any error, fall back gracefully — whole transcript goes to declarant
        return {
            "segments":       [{"speaker": "DECLARANT", "text": transcript.strip()}],
            "declarant_text": transcript.strip(),
            "ofiter_text":    "",
            "confidence":     "low",
            "error":          str(exc),
        }


def _empty(msg: str) -> dict:
    return {
        "segments":       [],
        "declarant_text": "",
        "ofiter_text":    "",
        "confidence":     "low",
        "error":          msg,
    }
