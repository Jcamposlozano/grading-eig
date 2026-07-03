"""Migración curada: eig-chatbot-logs-prod -> prisma-calificacion-canvas.

Principios (ver docs/PLAN_ESCALABILIDAD.md §8):
  - COPY-ONLY: nunca borra ni modifica el bucket origen.
  - Idempotente: omite los destinos que ya existen (re-ejecutable).
  - Seguro por defecto: corre en DRY-RUN; hay que pasar --apply para copiar.
  - Sin caps silenciosos: imprime el resumen y qué descarta.

Modo `eig` (depuración + estructura nueva): solo conserva lo útil del bucket viejo
y lo coloca en el layout `{env}/{universidad}/...`:
  - rubricas/rubrica.json  -> {env}/eig/{curso}/actividades/{actividad}/rubrica/rubrica.json
                              (replicada bajo cada actividad con entregas; usable por RubricPort)
  - raw/{curso}_{act}_{user}.json (calificaciones viejas)
                           -> {env}/eig/{curso}/{user|self}/{act}/grading/legacy_calificacion.json
                              (histórico; nombre 'legacy_' para no romper la idempotencia del flujo nuevo)
  - raw/log_*, audit/*, placeholders de carpeta -> DESCARTADOS.

Modo `identity`: copia tal cual (mapeo genérico).

Permisos AWS necesarios:
  origen  (eig-chatbot-logs-prod):     s3:ListBucket, s3:GetObject
  destino (prisma-calificacion-canvas): s3:ListBucket, s3:GetObject, s3:PutObject

Uso:
  python scripts/migrate_bucket.py                 # dry-run, modo eig
  python scripts/migrate_bucket.py --apply         # ejecuta las copias
  python scripts/migrate_bucket.py --mode identity # copia genérica tal cual
"""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

KeyMapper = Callable[[str], "list[str]"]

# raw/{curso}_{actividad}_{user}.json  (user puede venir vacío)
_GRADING_RE = re.compile(r"raw/(\d+)_(\d+)_(\d*)\.json")


@dataclass
class MigrationStats:
    scanned: int = 0
    copied: int = 0
    skipped_existing: int = 0
    filtered_out: int = 0


def default_map_key(src_key: str) -> list[str]:
    """Identidad: copia tal cual (modo genérico)."""
    return [src_key]


def discover_grading(
    s3, source_bucket: str, *, prefix: str = "raw/"
) -> list[tuple[str, str, str, str]]:
    """Calificaciones viejas como (curso, actividad, user, src_key). Excluye logs."""
    out = []
    for key, _size in iter_keys(s3, source_bucket, prefix):
        match = _GRADING_RE.fullmatch(key)
        if match:
            out.append((match.group(1), match.group(2), match.group(3), key))
    return out


def build_eig_map_key(
    curso_actividades: set[tuple[str, str]],
    *,
    env: str = "prod",
    universidad: str = "eig",
) -> KeyMapper:
    """Mapper curado para el bucket de EIG (ver módulo)."""

    def _map(src_key: str) -> list[str]:
        if src_key.endswith("/") or src_key.startswith("audit/") or src_key.startswith("raw/log_"):
            return []  # placeholders, audit y logs: se descartan
        if src_key == "rubricas/rubrica.json":
            return [
                f"{env}/{universidad}/{curso}/actividades/{actividad}/rubrica/rubrica.json"
                for curso, actividad in sorted(curso_actividades)
            ]
        match = _GRADING_RE.fullmatch(src_key)
        if match:
            curso, actividad, user = match.group(1), match.group(2), match.group(3)
            estudiante = user or "self"
            return [
                f"{env}/{universidad}/{curso}/{estudiante}/{actividad}/grading/legacy_calificacion.json"
            ]
        return []  # depuración: cualquier otra cosa se descarta

    return _map


def iter_keys(s3, bucket: str, prefix: str = "") -> Iterator[tuple[str, int]]:
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield obj["Key"], obj["Size"]


def dest_exists(s3, bucket: str, key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def migrate(
    s3,
    *,
    source_bucket: str,
    dest_bucket: str,
    source_prefix: str = "",
    map_key: KeyMapper = default_map_key,
    apply: bool = False,
    log: Callable[[str], None] = print,
) -> MigrationStats:
    stats = MigrationStats()
    for src_key, _size in iter_keys(s3, source_bucket, source_prefix):
        stats.scanned += 1
        dst_keys = map_key(src_key)
        if not dst_keys:
            stats.filtered_out += 1
            log(f"DESCARTA {src_key}")
            continue
        for dst_key in dst_keys:
            if dest_exists(s3, dest_bucket, dst_key):
                stats.skipped_existing += 1
                continue
            if apply:
                s3.copy_object(
                    Bucket=dest_bucket,
                    Key=dst_key,
                    CopySource={"Bucket": source_bucket, "Key": src_key},
                )
                log(f"COPIADO  {src_key} -> {dst_key}")
            else:
                log(f"DRY-RUN  {src_key} -> {dst_key}")
            stats.copied += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Migración curada de bucket (copy-only).")
    parser.add_argument("--source-bucket", default="eig-chatbot-logs-prod")
    parser.add_argument(
        "--dest-bucket", default=os.getenv("S3_BUCKET", "prisma-calificacion-canvas")
    )
    parser.add_argument("--mode", choices=["eig", "identity"], default="eig")
    parser.add_argument("--env", default="prod")
    parser.add_argument("--universidad", default="eig")
    parser.add_argument("--region", default=os.getenv("AWS_REGION"))
    parser.add_argument(
        "--apply", action="store_true", help="ejecuta las copias (por defecto: dry-run)"
    )
    args = parser.parse_args()

    import boto3
    from dotenv import load_dotenv

    load_dotenv()
    s3 = boto3.client("s3", region_name=args.region)

    if args.mode == "eig":
        grading = discover_grading(s3, args.source_bucket)
        curso_actividades = {(curso, actividad) for curso, actividad, _user, _key in grading}
        print(
            f"calificaciones viejas: {len(grading)} | (curso, actividad): {sorted(curso_actividades)}"
        )
        mapper = build_eig_map_key(curso_actividades, env=args.env, universidad=args.universidad)
    else:
        mapper = default_map_key

    stats = migrate(
        s3,
        source_bucket=args.source_bucket,
        dest_bucket=args.dest_bucket,
        map_key=mapper,
        apply=args.apply,
    )
    mode = "APLICADO" if args.apply else "DRY-RUN"
    print(
        f"\n[{mode}] escaneados={stats.scanned} copiados={stats.copied} "
        f"omitidos_existentes={stats.skipped_existing} descartados={stats.filtered_out}"
    )


if __name__ == "__main__":
    main()
