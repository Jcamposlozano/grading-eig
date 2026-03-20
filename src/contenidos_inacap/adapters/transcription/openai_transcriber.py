from __future__ import annotations

import os

from openai import OpenAI

from contenidos_inacap.ports.transcription_port import TranscriptionPort


class OpenAITranscriber(TranscriptionPort):
    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en variables de entorno.")

        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")

    def transcribe(self, *, audio_path: str) -> str:
        with open(audio_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
            )

        text = getattr(transcription, "text", None)
        if not text:
            raise RuntimeError("La transcripción no devolvió texto.")

        return text.strip()