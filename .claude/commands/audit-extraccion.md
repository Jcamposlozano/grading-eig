---
description: Audita qué se extrae hoy del entregable y de Canvas, y dónde se persiste
allowed-tools: Read, Glob, Grep, Task
---

Audita (solo lectura) el **pipeline de extracción y la integración con Canvas** del
calificador, y produce un reporte preciso. NO modifiques nada.

Cubre y cita `archivo:línea` para cada afirmación:

1. **Entrada/Canvas** — qué IDs/campos recibe el sistema hoy y de dónde; endpoints de
   Canvas que se llaman (path, método, query params); cómo se autentica (dominio/token);
   qué descarga (submissions, attachments, files). Revisa `adapters/canvas/canvas_client.py`
   y los routers/DTOs de entrada.
2. **Extracción por formato** — para documento (`.pdf/.docx/.txt`), audio y video:
   qué extrae exactamente y con qué librería/herramienta (pypdf, python-docx, ffmpeg,
   transcripción OpenAI), y qué devuelve cada extractor. Revisa `application/use_cases/extract_text.py`
   y `adapters/{extractors,media,transcription}`.
3. **Metadatos** — qué campos/metadatos guarda la entidad de dominio (`Material` /
   `Entregable`) y el estado del proceso.
4. **Persistencia** — dónde se escriben los archivos crudos/extraídos (disco local hoy:
   `data/uploads/...`, `data/temp/...`; S3 cuando aplique).
5. **Calificación** — cómo se arma el prompt (rúbrica + texto), qué devuelve el LLM, y
   cómo se decide publicar la nota en Canvas (gate).

Entrega: un mapa conciso de "qué extraemos hoy" + gaps respecto al objetivo multi-tenant
descrito en `docs/PLAN_ESCALABILIDAD.md`. No inventes campos que el código no maneje.
