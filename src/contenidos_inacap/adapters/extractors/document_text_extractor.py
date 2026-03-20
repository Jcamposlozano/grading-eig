from __future__ import annotations

from pathlib import Path

from docx import Document
from pypdf import PdfReader

from contenidos_inacap.ports.document_extractor_port import DocumentExtractorPort


class DocumentTextExtractor(DocumentExtractorPort):
    def extract(self, *, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".txt":
            return self._extract_txt(path)

        if suffix == ".pdf":
            return self._extract_pdf(path)

        if suffix == ".docx":
            return self._extract_docx(path)

        raise ValueError(f"Formato de documento no soportado: {suffix}")

    def _extract_txt(self, path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()

    def _extract_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        parts: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())

        return "\n\n".join(parts).strip()

    def _extract_docx(self, path: Path) -> str:
        doc = Document(str(path))
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(parts).strip()