# CLAUDE.md — grading-eig

Memoria de proyecto para sesiones de Claude Code. Léela antes de tocar el repo.

## Qué es este sistema

Servicio de **calificación automática de entregables** académicos. Un trigger externo
indica un entregable (universidad, curso, estudiante, actividad, rúbrica); el sistema
descarga el entregable desde Canvas, extrae su contenido (texto / transcripción de
audio o video), lo califica con un LLM contra una rúbrica, y **opcionalmente publica
la nota de vuelta en Canvas**.

Estado actual: funciona para **una sola** universidad (EIG), Canvas configurado por
variable de entorno global, y persistencia en **disco local**. Estamos evolucionándolo
a **multi-universidad / multi-tenant** con persistencia en **S3** y ejecución
**asíncrona** (ver `docs/PLAN_ESCALABILIDAD.md`).

> El plan vivo y el roadmap están en **`docs/PLAN_ESCALABILIDAD.md`**. Ese documento manda.

## Arquitectura objetivo: hexagonal (ports & adapters)

El repo **ya es hexagonal**. Mantener la separación de capas y la regla de dependencias
(el dominio no importa frameworks ni AWS; las dependencias apuntan hacia adentro):

- `domain/` — entidades y reglas puras (Universidad, Curso, Estudiante, Actividad,
  Entregable, Rúbrica, Calificación). Sin FastAPI, sin boto3, sin OpenAI.
- `application/` — casos de uso (p.ej. `CalificarEntregable`, `ExtraerContenido`,
  `PublicarNotaEnCanvas`).
- `ports/` — interfaces (`CanvasPort`, `StoragePort`, `LLMPort`, `ExtractorPort`,
  `RubricPort`, `CredentialsPort`, `QueuePort`).
- `adapters/` — implementaciones concretas (CanvasAdapter por universidad, S3Storage,
  adapter del LLM, extractores audio/video/texto, SecretsManager, SQS).
- `entrypoints/` — API (FastAPI) y Worker.
- `shared/` — config, logger, container (DI), shutdown, prompt_loader.

### Estructura de carpetas objetivo

```
src/grading/                     # paquete renombrado desde `contenidos_inacap`
  domain/entities/               # universidad, curso, estudiante, actividad, entregable, rubrica, calificacion
  domain/enums.py                # ClasificacionActividad, EstadoEntregable
  application/use_cases/         # CalificarEntregable (orquestador) + casos existentes
  application/strategies/        # registry de extracción por clasificación de actividad
  ports/                         # CanvasPort, StoragePort, LLMPort, ExtractorPort, RubricPort, CredentialsPort, QueuePort
  adapters/canvas/               # CanvasAdapter (creds por instancia) + CanvasAdapterFactory
  adapters/storage/              # S3Storage (+ LocalFileStorage legado)
  adapters/secrets/              # SecretsManagerCredentials
  adapters/queue/                # SqsQueue
  adapters/llm/, extractors/, media/, transcription/
  entrypoints/api.py, routers/, worker.py   # worker = consumidor SQS
  shared/                        # config (multi-tenant), logger, container, prompt_loader
```

## Glosario de dominio

- **Universidad** — tenant raíz (`westfield | eig | esic | uide`). Cada una tiene su
  propio Canvas (dominio + token), resuelto desde Secrets Manager. Nada hardcodeado.
- **Curso** — pertenece a una universidad.
- **Estudiante** — pertenece a una universidad; mapea a un `canvas_user_id`.
- **Actividad** — tarea evaluable de un curso. Porta la **clasificación** y el `rubrica_id`.
- **Clasificación (de la actividad)** — `TEXTO | AUDIO | VIDEO`. **Decide la estrategia
  de extracción** (video → extraer audio → transcribir; texto → leer directo).
- **Entregable** — lo que sube un estudiante para una actividad (generaliza la entidad
  `Material` actual).
- **Rúbrica** — criterios + niveles + puntos. Se resuelve **desde nuestro S3** por id.
- **Calificación** — resultado del LLM normalizado: score por criterio, total, feedback,
  y el flag **`publish`** (`true` → sube nota a Canvas; `false` → no).

## Convenciones de código (del template)

- **Python 3.11**, **Poetry** (`pyproject.toml`). Paquete bajo `src/`.
- **ruff** + **black**, `line-length = 100`, `target-version = py311`.
  - ruff lint: `select = ["E","F","I","B","UP","SIM","RUF"]`, `ignore = ["E501"]`.
  - formato: comillas dobles, indent con espacios.
- **pre-commit** con ruff (`ruff` + `ruff-format`). Correr antes de commitear.
- Logs **estructurados** (no `print`); incluir `correlation_id` / universidad / entregable.
- Tipos explícitos en firmas de puertos (args keyword-only, retornos anotados).

### Comandos

```
make install        # poetry install
make run-api        # API FastAPI (uvicorn)
make run-worker     # Worker
make format         # ruff format + ruff check --fix
make lint           # ruff check
make precommit      # instala hooks
make docker-up/down/logs
poetry run pytest   # tests
```

## Reglas de trabajo

- **Multi-tenant desde el diseño:** nada hardcodeado a una universidad. Agregar una
  universidad nueva debe ser **solo configuración + un secreto**, nunca código nuevo.
- **No inventar campos** que el código no maneja. Verificar en el código qué se extrae
  hoy antes de proponer estructuras nuevas.
- **Incremental, no big-bang:** cambios por pasos pequeños, enviables y testeables;
  convivir con lo viejo detrás de flags hasta el corte final (ver roadmap).
- **Secretos:** nunca loguear tokens/keys; `.env` es solo local y está en `.gitignore`.
  Producción usa AWS Secrets Manager.

## No-objetivos (en esta etapa)

- **No** construimos los triggers externos (sí diseñamos el contrato de entrada que esperan).
- **No** reescribimos el LLM ni cambiamos de proveedor salvo justificación explícita.
- **No** inventamos campos/metadatos que el código actual no extrae.
- **No** introducimos base de datos en esta fase (estado en S3 por prefijo); revisar más adelante.
- **No** hacemos migraciones big-bang; nada de borrar el bucket viejo (`eig-chatbot-logs-prod`).
