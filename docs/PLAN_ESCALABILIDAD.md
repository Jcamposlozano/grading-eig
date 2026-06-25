# Plan de Escalabilidad — Calificador multi-universidad

> **Estado:** propuesta de diseño (Fase 0 cerrada). Aprobado el enfoque; implementación por pasos pendientes.
> **Alcance:** evolucionar `grading-eig` de single-tenant + disco local a **multi-universidad**, **persistencia S3** y **ejecución asíncrona** disparada por un trigger externo.
> **Convenciones y glosario:** ver [`CLAUDE.md`](../CLAUDE.md).

## Decisiones tomadas

| # | Tema | Decisión |
|---|---|---|
| 1 | Rúbrica (`id_rubrica`) | Se resuelve desde **nuestro S3** por jerarquía (no inline, no Canvas). |
| 2 | Gate de publicación | **Flag booleano del LLM** (`publish` + `confidence`); `true` publica, `false` no. |
| 3 | Ejecución del trigger | **Asíncrona**: API valida + encola en **SQS** + responde `202`; **Worker** orquesta. |
| 4 | Credenciales Canvas por universidad | **AWS Secrets Manager** por `id_universidad(+env)`. |
| 5 | Bucket | Único: `prisma-calificacion-canvas` (`us-east-2`), organizado por jerarquía. |
| 6 | Clasificación de actividad | Decide la estrategia de extracción vía **registry** (no `if/elif`). |
| 7 | Paquete | `contenidos_inacap` → `grading` (renombrado mecánico, paso tardío). |

---

## 1. Mapa del estado actual (Fase 0)

El repo **ya es hexagonal** (`src/contenidos_inacap/` → `domain/application/ports/adapters/entrypoints/shared`), Poetry, py311, FastAPI + Worker, Docker, ruff/black `line-length=100`, pre-commit. La migración *estructural* está casi hecha.

| Área | Estado hoy | Archivo(s) |
|---|---|---|
| Entrada | **3 llamadas HTTP separadas**: import-canvas → `material_id` → extract-text → evaluate | `entrypoints/routers/*` |
| Estado | `InMemoryMaterialRepository` (**efímero**, se pierde al reiniciar) | `adapters/repositories/in_memory_material_repository.py` |
| Worker | **Placeholder**: loop por intervalo, `tick()` vacío, **sin cola** | `entrypoints/worker.py` |
| Canvas | **Funciones de módulo** que leen `CANVAS_BASE_URL`/`CANVAS_ACCESS_TOKEN` (env, **un solo Canvas**) | `adapters/canvas/canvas_client.py` |
| Extracción | doc(`.pdf/.docx/.txt`→texto), video(ffmpeg→wav 16k mono→transcribe), audio(transcribe); `if/elif` por `media_type` | `application/use_cases/extract_text.py`, `adapters/{extractors,media,transcription}` |
| LLM | OpenAI **Responses API** `gpt-4.1-mini` (`client.responses.create(...).output_text`, **válido**); score **resuelto server-side** desde la rúbrica | `adapters/llm/openai_evaluator.py`, `application/use_cases/evaluate_student_response.py` |
| Rúbrica | **Inline** (JSON completo en el request). **No existe `id_rubrica`** | `application/dto/evaluation_dto.py` |
| Publicación | Publica si vienen `canvas_course_id+assignment_id+user_id`; **sin gate true/false**; errores tragados por `print` | `evaluate_student_response.py:66-71,188` |
| Storage | **Solo disco** (`data/uploads/{document,audio,video}`, `data/temp/`). **Sin boto3 / sin S3** | `adapters/storage/local_file_storage.py` |
| Config | `configs/base.yaml`+`{ENV}.yaml`+env. **Cero multi-tenant** | `shared/config.py`, `shared/container.py` |
| Dominio | Entidad `Material` (id, media_type, extracted_text, status, …). **Sin universidad/curso/estudiante** | `domain/entities/material.py` |

### Qué datos extraemos hoy (concreto, para no inventar campos)

- **De Canvas:**
  - `GET /api/v1/users/self/profile` → `id` (resolver user id desde el token).
  - `GET /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions?student_ids[]=&include[]=attachments&per_page=100` (paginado, tope 50 páginas) → `submission.attachments[]`.
  - Por cada attachment: `id` (file id), `display_name`/`filename`, `url`/`download_url`.
  - `GET /api/v1/files/{file_id}` → `url`, `display_name`/`filename`.
  - Descarga binaria (con fallback `…/files/{id}/download?download_frd=1` y detección de HTML).
  - `PUT /api/v1/courses/{c}/assignments/{a}/submissions/{u}` → publica `posted_grade` y `comment.text_comment` (en requests separados).
- **Del entregable:** texto plano (documento) o **transcripción** (audio/video, OpenAI `gpt-4o-mini-transcribe`; video pasa por ffmpeg → WAV 16 kHz mono).
- **Metadatos en `Material`:** `id`, `filename`, `original_filename`, `media_type` (`DOCUMENT|AUDIO|VIDEO`), `mime_type`, `file_path`, `file_size`, `extracted_text`, `status` (`UPLOADED|PROCESSING|COMPLETED|FAILED`), `error_message`, `created_at`.

### ⚠️ Seguridad

El `.env` contiene **claves AWS, OpenAI y token de Canvas en texto plano y vivas**, además de `S3_BUCKET=prisma-calificacion-canvas` y `AWS_REGION=us-east-2` que **ningún código usa todavía**. `.env` está en `.gitignore` (bien), pero estas claves deben **rotarse** y moverse a Secrets Manager (Paso 0).

### Gaps hacia el objetivo

1. Multi-tenant inexistente (dominio, config, credenciales).
2. Sin persistencia S3 ni layout por jerarquía.
3. Flujo de 3 llamadas + estado efímero → falta orquestador de un solo disparo.
4. `id_rubrica` y gate `publish` no existen.
5. Worker sin cola; repo en memoria.

---

## 2. Modelo de dominio propuesto

Entidades `@dataclass` (mismo estilo que `Material`), **sin** dependencias de framework/AWS.

```
Universidad ─┬─< Curso ─┬─< Estudiante
             │          └─< Actividad ──(clasificacion, rubrica_id)
             │                  └─< Entregable >── Calificacion
             └ (Canvas propio, resuelto por Secrets Manager)
```

- **Universidad**: `id` (slug `westfield|eig|esic|uide`), `nombre`.
- **Curso**: `id`, `universidad_id`, `nombre`.
- **Estudiante**: `id`, `universidad_id`, `canvas_user_id`.
- **Actividad**: `id`, `curso_id`, **`clasificacion: ClasificacionActividad`**, `rubrica_id`.
- **Entregable**: `id`, `universidad_id`, `curso_id`, `estudiante_id`, `actividad_id`, `clasificacion`, `media_type`, `raw_key`, `extracted_text`, `estado: EstadoEntregable`, `error_message`, `created_at`. *(generaliza a `Material`)*
- **Rubrica**: `id`, `criterios: list[Criterio]`, `max_score`; `Criterio{id, name, levels[{level, points, description}]}` (reutiliza la forma de `RubricDTO` actual).
- **Calificacion**: `entregable_id`, `criteria_results[]`, `total_score`, **`publish: bool`**, **`confidence: float`**, `general_feedback`, `published: bool`.
- **Enums**: `ClasificacionActividad {TEXTO, AUDIO, VIDEO}`, `EstadoEntregable {RECIBIDO, DESCARGADO, EXTRAIDO, CALIFICADO, PUBLICADO, FALLIDO}`.

**Dónde vive la clasificación:** en `Actividad`; se copia al `Entregable` al recibirlo y **selecciona la estrategia de extracción** (ver §9). `Material` → `Entregable`: `Material` se mantiene mientras viven las rutas v1; el orquestador nuevo trabaja con `Entregable`. **No hay BD** en esta fase: el estado se infiere de qué keys existen en S3 + `metadata.json`.

---

## 3. Estructura de carpetas objetivo + plan de migración del código

```
src/grading/                     # hoy `contenidos_inacap` (renombrado en paso tardío)
  domain/entities/               # universidad, curso, estudiante, actividad, entregable, rubrica, calificacion
  domain/enums.py                # ClasificacionActividad, EstadoEntregable
  application/use_cases/         # CalificarEntregable (orquestador) + casos existentes
  application/strategies/        # registry de extracción por clasificación
  ports/                         # CanvasPort, StoragePort, LLMPort, ExtractorPort, RubricPort, CredentialsPort, QueuePort
  adapters/canvas/               # CanvasAdapter (creds por instancia) + CanvasAdapterFactory
  adapters/storage/              # S3Storage (+ LocalFileStorage legado)
  adapters/secrets/              # SecretsManagerCredentials
  adapters/queue/                # SqsQueue
  adapters/llm/, extractors/, media/, transcription/
  entrypoints/api.py, routers/, worker.py   # worker = consumidor SQS
  shared/                        # config (multi-tenant), logger, container, prompt_loader
```

La migración del código es **incremental** (ver checklist §11): cada puerto/adaptador nuevo convive con lo viejo detrás de flags; el renombrado de paquete y la deprecación de rutas v1 van al final.

---

## 4. Contrato de entrada del trigger

`POST /v1/calificaciones` → valida, encola en SQS, responde `202`. (El trigger **no** lo construimos nosotros; solo definimos el contrato que espera.)

```jsonc
{
  "id_universidad": "eig",      // requerido; ∈ {westfield, eig, esic, uide}
  "id_curso": "123",            // requerido
  "id_actividad": "456",        // requerido (porta clasificación + rubrica_id)
  "id_entregable": "789",       // requerido (clave de idempotencia)
  "id_estudiante": "1011",      // requerido
  "id_rubrica": "rubricaA",     // requerido (se resuelve desde S3)
  "env": "prod"                 // requerido; ∈ {dev, staging, prod}
}
```

- **Validación:** campos requeridos no vacíos; `id_universidad` ∈ set permitido (config por env); `env` válido. Respuesta `400` con detalle si falla.
- **Idempotencia (SQS at-least-once):** `idempotency_key = sha256(env|uni|curso|actividad|entregable|estudiante|rubrica)`. El orquestador comprueba en S3 si ya existe `grading/calificacion.json` (estado `PUBLICADO`) antes de reprocesar.
- **Auth:** recomendado `x-api-key` (secreto compartido, rotable) inicialmente; opciones futuras: JWT/mTLS o restringir a red interna/VPC. *(Pregunta abierta §10.)*
- **`key-canvas` del diagrama:** **no** viaja en el payload; se resuelve en Secrets Manager por universidad+env. *(Confirmar con el equipo del trigger.)*
- **Respuesta `202`:** `{ "status": "accepted", "correlation_id": "…", "idempotency_key": "…" }`.

---

## 5. Contrato de endpoints (OpenAPI resumido)

Rutas **responsive por jerarquía** (universidad/curso/estudiante/actividad).

```yaml
openapi: 3.0.3
info: { title: grading-eig, version: "1.0" }
paths:
  /v1/calificaciones:
    post:
      summary: Entrada del trigger; valida y encola
      requestBody:    # ver §4
        required: true
      responses:
        "202": { description: Aceptado; encolado para procesamiento asíncrono }
        "400": { description: Validación }
        "401": { description: Auth }
        "409": { description: Duplicado (opcional, idempotencia) }
  /v1/universidades/{uni}/cursos/{curso}/estudiantes/{est}/entregables/{ent}/calificacion:
    get:
      summary: Lee la calificación (de S3)
      responses:
        "200": { description: Calificacion }
        "404": { description: Aún no calificado / no existe }
  /v1/universidades/{uni}/cursos/{curso}/actividades/{act}/rubrica:
    get:
      summary: Lee la rúbrica (de S3)
      responses: { "200": { description: Rubrica }, "404": { description: No existe } }
  /health:        { get: { summary: Liveness,  responses: { "200": {} } } }
  /health/ready:  { get: { summary: Readiness (S3+SQS+Secrets), responses: { "200": {}, "503": {} } } }
```

**Códigos de error:** `400` validación · `401/403` auth · `404` lectura inexistente · `409` duplicado · `502/503` Canvas/dependencias caídas.
**Observabilidad mínima:** logs JSON estructurados con `correlation_id`, `universidad`, `entregable`, `env`; nunca loguear tokens.

---

## 6. Diseño de ports & adapters (firmas)

```python
class StoragePort(Protocol):
    def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> str: ...
    def get_bytes(self, *, key: str) -> bytes: ...
    def put_text(self, *, key: str, text: str) -> str: ...
    def get_text(self, *, key: str) -> str: ...
    def put_json(self, *, key: str, obj: dict) -> str: ...
    def get_json(self, *, key: str) -> dict: ...
    def exists(self, *, key: str) -> bool: ...

class CredentialsPort(Protocol):
    def get_canvas_credentials(self, *, universidad_id: str, env: str) -> CanvasCredentials: ...
# CanvasCredentials = {base_url: str, token: str}

class CanvasPort(Protocol):
    def fetch_submission_attachment(self, *, course_id, assignment_id, user_id,
                                    attachment_index: int = 0) -> AttachmentRef: ...
    def download_file(self, *, attachment: AttachmentRef) -> tuple[bytes, str]: ...   # (bytes, filename)
    def publish_grade(self, *, course_id, assignment_id, user_id,
                      score: int, comment: str) -> None: ...

class RubricPort(Protocol):
    def load(self, *, universidad_id, curso_id, actividad_id, rubrica_id) -> Rubrica: ...

class LLMPort(Protocol):
    def evaluate(self, *, prompt: str) -> LLMEvaluation: ...
# LLMEvaluation = lo actual + publish: bool, confidence: float

class ExtractorPort(Protocol):       # estrategia por clasificación
    def extract(self, *, source_path: str, clasificacion: ClasificacionActividad) -> str: ...

class QueuePort(Protocol):
    def enqueue(self, *, message: dict) -> str: ...
    def consume(self, *, max_messages: int, wait_seconds: int) -> list[QueueMessage]: ...
    def ack(self, *, receipt_handle: str) -> None: ...
    def extend_visibility(self, *, receipt_handle: str, seconds: int) -> None: ...
```

**Refactor Canvas (clave):** `canvas_client.py` (funciones de módulo + env global) → **`CanvasAdapter(CanvasPort)`** que recibe `base_url`+`token` **por instancia** (de `CredentialsPort`), reutilizando la lógica probada (paginación, `download_frd=1`, detección de HTML, separación nota/comentario) y sustituyendo `print(...)` por logger estructurado. Una `CanvasAdapterFactory(credentials).for_university(uni, env) -> CanvasPort` construye la instancia por petición.

**LLM:** extender prompt y parseo para devolver `publish` + `confidence`. El **scoring sigue server-side** (reutiliza `_normalize_and_score_result` / `_resolve_score_from_rubric`).

---

## 7. Resolución multi-tenant (credenciales por universidad)

- **Fuente:** AWS Secrets Manager. Convención de nombre: **`prisma/grading/{env}/canvas/{universidad}`**.
- **Contenido del secreto:** JSON `{ "base_url": "...", "token": "..." }`.
- **Resolución:** `CredentialsPort.get_canvas_credentials(universidad_id, env)` → `CanvasCredentials`; el `CanvasAdapterFactory` instancia el adapter con esos valores.
- **Cache:** en memoria con TTL (~300 s) para no llamar Secrets Manager en cada request.
- **Fallos:** secreto ausente/ilegible → `503 CanvasNotConfigured`. **Nunca** loguear el token.
- **Agregar universidad nueva = solo config + un secreto** (añadir el slug al set permitido + crear `prisma/grading/{env}/canvas/{slug}`). Cero código nuevo.
- Durante la migración: fallback a `CANVAS_BASE_URL`/`CANVAS_ACCESS_TOKEN` del entorno mientras se crean los secretos.

---

## 8. Layout del bucket + plan de migración

```
prisma-calificacion-canvas/                # us-east-2
  {env}/{universidad}/{curso_id}/
    actividades/{actividad_id}/rubrica/{rubrica_id}.json    # rúbrica a nivel ACTIVIDAD (compartida)
    {estudiante_id}/{entregable_id}/
      raw/<original_filename>                               # entregable crudo descargado de Canvas
      extracted/transcription.txt | text.txt | audio.wav    # contenido extraído
      grading/calificacion.json                             # resultado de la calificación
      grading/metadata.json                                 # trazabilidad
```

- **`metadata.json`:** ids de la jerarquía, `correlation_id`, timestamps y transiciones de estado, modelo LLM + hash del prompt, duraciones, filename origen, `publish`/`confidence`.
- **Refinamiento:** la rúbrica vive a **nivel actividad** (se comparte entre estudiantes), no por entregable. El `grading/rubrica.json` por entregable (del enunciado original) se reserva, si acaso, para un *snapshot* de la rúbrica aplicada.

**Migración desde `eig-chatbot-logs-prod` (idempotente):**
- Script en `scripts/` (paso tardío), **copy-only, nunca borra**.
- Copia solo **rúbricas/artefactos reutilizables** al nuevo layout; **deja los logs de chatbot** donde están.
- Re-ejecutable: salta lo que ya existe en destino (chequeo `exists` por key).
- *Pendiente:* inspeccionar la estructura real del bucket viejo para mapear qué objetos migrar (pregunta abierta §10).

---

## 9. Pipeline de extracción según clasificación de actividad

La **clasificación** (en `Actividad`, copiada al `Entregable`) selecciona la estrategia vía registry (reemplaza el `if/elif` de `extract_text.py`):

```python
EXTRACTION_STRATEGIES: dict[ClasificacionActividad, ExtractionStrategy] = {
    ClasificacionActividad.TEXTO: DocumentExtractionStrategy(document_extractor),
    ClasificacionActividad.AUDIO: AudioExtractionStrategy(transcriber),
    ClasificacionActividad.VIDEO: VideoExtractionStrategy(audio_extractor, transcriber),
}
```

| Clasificación | Pipeline | Salida en `extracted/` |
|---|---|---|
| `TEXTO` | leer documento directo (pypdf / python-docx / texto plano) | `text.txt` |
| `AUDIO` | transcribir (OpenAI `gpt-4o-mini-transcribe`) | `transcription.txt` |
| `VIDEO` | ffmpeg → WAV 16 kHz mono → transcribir | `audio.wav` + `transcription.txt` |

Reutiliza los adaptadores actuales (`DocumentTextExtractor`, `FFmpegAudioExtractor`, `OpenAITranscriber`); solo cambia el *dispatch* (registry) y el destino (S3 en lugar de `data/`).

---

## 10. Riesgos, supuestos y preguntas abiertas

**Riesgos / supuestos**

- **Crítico:** claves AWS/OpenAI/Canvas vivas en `.env` → rotar y mover a Secrets Manager (Paso 0).
- `visibility timeout` de SQS vs transcripción de video larga → mitigar con `extend_visibility` + idempotencia (o trocear).
- Duplicados at-least-once → claves de idempotencia + chequeo en S3.
- Rate limits de Canvas y el tope actual de 50 páginas en la paginación de submissions.
- Coste LLM por entregable (transcripción + calificación) escala con volumen.
- Sin BD: listar por prefijo es scan de S3 (suficiente por ahora).
- Región `us-east-2` confirmada en `.env`.

**Preguntas abiertas (para el usuario)**

1. **Auth del trigger:** ¿`x-api-key` compartida, por-tenant, JWT, o red interna/VPC?
2. **SQS:** ¿`standard` (throughput) o `FIFO` (orden + dedup nativo)?
3. **¿BD?** ¿Los listados/consultas justifican DynamoDB, o S3-by-prefix basta esta fase?
4. ~~**Migración bucket:** ¿qué objetos migramos?~~ **RESUELTO:** inspeccionado y migrado (Paso 8 aplicado) — rúbrica (útil) + calificaciones viejas como histórico `legacy_`; logs/audit descartados.
5. ~~**`confidence`:** ¿hay umbral mínimo además del `publish` del LLM?~~ **RESUELTO:** `publish=true` → publica siempre; **sin umbral** de `confidence` (se guarda solo como metadato).
6. **Renombrar paquete** `contenidos_inacap` → `grading`: ¿OK, o conservar el nombre?
7. **Rotación de secretos:** ¿automática (Secrets Manager) o manual?
8. **Límite de video:** ¿tamaño/duración máximos a soportar (afecta timeouts/costos)?
9. **`key-canvas`:** confirmar que el trigger **no** enviará el token (lo resolvemos nosotros).

---

## 11. Roadmap por fases (checklist incremental, sin big-bang)

Cada paso es **enviable y testeable** por separado; convive con lo viejo detrás de flags hasta el corte final. Cada paso lleva tests (unitarios por puerto/adaptador) + target de Makefile.

- [ ] **Paso 0 — Seguridad.** Rotar claves AWS + token Canvas; moverlas a Secrets Manager / entorno seguro; confirmar `.env` en `.gitignore` (lo está).
- [x] **Paso 1 — S3.** `StoragePort` + `S3Storage` (boto3) + `LocalObjectStorage` (dev/tests); config `storage.backend` (local|s3) + factory `get_object_storage()`; convive con `LocalFileStorage`. Tests verdes.
- [x] **Paso 2 — Secrets + Canvas multi-tenant.** `CredentialsPort` (+ `CanvasCredentials`/`CredentialsResolutionError`) con `EnvCredentials` (fallback) y `SecretsManagerCredentials` (secreto `prisma/grading/{env}/canvas/{uni}`, cache TTL, alias de claves); `CanvasPort` + `CanvasAdapter` (delega en `canvas_client`, creds por instancia) + `CanvasAdapterFactory`; `print`→logger en `canvas_client`; config `credentials.backend` (env|secrets_manager) + factories en el container. 21 tests verdes.
- [x] **Paso 3 — Rúbrica + gate.** `RubricPort` + `S3RubricStore` (lee `rubrica.json` por jerarquía vía `StoragePort`) + `shared/s3_keys.rubrica_key`; `EvaluationResponseDTO` extendido con `publish`/`confidence` (prompt + `OpenAIEvaluator` tolerantes); gate aplicado en `evaluate_student_response` (publica en Canvas **solo si `publish=True`** y hay contexto Canvas). 26 tests verdes. *(Pendiente pregunta abierta #5: ¿umbral de `confidence`?)*
- [x] **Paso 4 — Registry de extracción.** `application/strategies/extraction.py`: `ExtractionStrategy` + `DocumentExtractionStrategy`/`AudioExtractionStrategy`/`VideoExtractionStrategy` + `build_extraction_registry`. `ExtractTextUseCase` ya no usa `if/elif`: mapea `media_type`→`ClasificacionActividad` y resuelve la estrategia. El video limpia su audio temporal dentro de la estrategia.
- [x] **Paso 5 — Dominio.** `domain/enums.py` (`ClasificacionActividad`, `EstadoEntregable`) + entidades `Universidad/Curso/Estudiante/Actividad/Entregable/Rubrica/Calificacion` (dataclasses framework-free). `Entregable` generaliza `Material`; `clasificacion_from_media_type` mapea ambos. Mapeo DTO↔dominio para Rúbrica/Calificación se hará en el Paso 7. 37 tests verdes.
- [x] **Paso 6 — Cola + Worker real.** `QueuePort` + `SqsQueue` (+ `InMemoryQueue` dev) con `extend_visibility`; worker pasó de placeholder a `run_consume_loop` (ack en éxito; sin ack ante error → reintento/DLQ).
- [x] **Paso 7 — Orquestador + endpoint.** `CalificarEntregable` (idempotente por S3: descarga→raw, extrae→extracted, rúbrica, califica, grading+metadata, publica si `publish`) + `POST /v1/calificaciones` (202, valida + encola) + GET calificación/rúbrica + `/health/ready`. Reutiliza `RubricGrader`/`feedback`/`media_type`. 66 tests verdes; boot real de la app verificado. *(Supuesto: id_curso/actividad/estudiante = ids de Canvas.)*
- [x] **Paso 8 — Migración bucket (APLICADA).** `scripts/migrate_bucket.py` modo `eig` (curado, data-driven, idempotente, copy-only). **Ejecutado:** 9 objetos copiados a `prisma-calificacion-canvas` — rúbrica `rubrica.json` replicada bajo las 4 actividades con entregas (`prod/eig/2692/actividades/{30282,30300,30301,30302}/rubrica/`) + 5 calificaciones viejas como `…/grading/legacy_calificacion.json`. Descartados: 4 logs `raw/log_*`, `audit/test.txt`, placeholder. Bucket viejo intacto (12 objetos). Idempotencia verificada (re-`--apply` = 0 copias).
- [ ] **Paso 9 — Multi-uni por config.** Set de universidades permitidas por env, sin hardcode.
- [ ] **Paso 10 — Renombrar paquete.** `contenidos_inacap` → `grading` (mecánico, un solo commit).
- [ ] **Paso 11 — Deprecación v1.** Retirar rutas de materiales una vez el orquestador las cubre.

### Anexo — El orquestador `CalificarEntregable` (Paso 7)

Secuencia en el Worker (cada paso idempotente por existencia de objeto en S3):

1. Construir prefijo S3 desde la jerarquía del mensaje.
2. Si `grading/calificacion.json` existe y `estado=PUBLICADO` → `ack` y salir.
3. Resolver credenciales Canvas (`CredentialsPort` → Secrets Manager).
4. Descargar attachment → `raw/` (saltar si existe).
5. Extraer contenido según `clasificacion` (registry) → `extracted/` (saltar si existe).
6. Cargar `Rubrica` desde S3 (`RubricPort`).
7. Calificar con LLM → resolver scores → `Calificacion` con `publish`/`confidence`.
8. Escribir `grading/calificacion.json` + `metadata.json`.
9. Si `publish == true` → `publish_grade` a Canvas → `estado=PUBLICADO`; si no → `estado=CALIFICADO`.
10. `ack` SQS. Errores de publicación **no se tragan** (no-ack → reintento → DLQ).
