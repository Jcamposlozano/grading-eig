
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from contenidos_inacap.ports.audio_extractor_port import AudioExtractorPort


class FFmpegAudioExtractor(AudioExtractorPort):
    def __init__(self, temp_dir: str = "data/temp") -> None:
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_audio(self, *, input_path: str) -> str:
        input_file = Path(input_path)

        if not input_file.exists():
            raise FileNotFoundError(f"No existe el archivo de entrada: {input_path}")

        output_filename = f"{uuid.uuid4().hex}.wav"
        output_path = self.temp_dir / output_filename

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_file),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg falló al extraer audio. stderr={result.stderr.strip()}"
            )

        return str(output_path.resolve())