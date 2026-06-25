"""Migración idempotente: eig-chatbot-logs-prod -> prisma-calificacion-canvas.

Principios (ver docs/PLAN_ESCALABILIDAD.md §8):
  - COPY-ONLY: nunca borra nada del bucket origen.
  - Idempotente: omite los objetos que ya existen en destino (re-ejecutable).
  - Seguro por defecto: corre en DRY-RUN; hay que pasar --apply para copiar.
  - Sin caps silenciosos: imprime el resumen (escaneados/copiados/omitidos/filtrados).

El QUÉ migrar vive en `default_map_key`: por ahora es identidad (copia tal cual).
Cuando se conozca la estructura real de eig-chatbot-logs-prod, ahí se filtran los
logs de chatbot (devolviendo None) y se transforman las claves de rúbricas/
artefactos al layout nuevo `{env}/{universidad}/{curso}/...`.

Permisos AWS necesarios para ejecutarlo (la credencial `raw_bucket` del .env NO los tiene):
  origen  (eig-chatbot-logs-prod):     s3:ListBucket, s3:GetObject
  destino (prisma-calificacion-canvas): s3:ListBucket, s3:GetObject, s3:PutObject

Uso:
  python scripts/migrate_bucket.py                 # dry-run (no copia)
  python scripts/migrate_bucket.py --apply         # ejecuta las copias
  python scripts/migrate_bucket.py --source-prefix rubricas/ --apply
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass

KeyMapper = Callable[[str], "str | None"]


@dataclass
class MigrationStats:
    scanned: int = 0
    copied: int = 0
    skipped_existing: int = 0
    filtered_out: int = 0


def default_map_key(src_key: str) -> str | None:
    """Clave de destino para ``src_key``, o ``None`` para NO migrarla.

    Identidad por ahora. Punto de extensión para filtrar/transformar cuando se
    conozca el layout de origen.
    """
    return src_key


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
        dst_key = map_key(src_key)
        if dst_key is None:
            stats.filtered_out += 1
            continue
        if dest_exists(s3, dest_bucket, dst_key):
            stats.skipped_existing += 1
            continue
        if apply:
            # copy_object = copia server-side (sin descargar). Para objetos > 5 GB
            # se necesitaría multipart copy; los artefactos aquí son pequeños.
            s3.copy_object(
                Bucket=dest_bucket,
                Key=dst_key,
                CopySource={"Bucket": source_bucket, "Key": src_key},
            )
            log(f"COPIADO  {src_key} -> {dst_key}")
        else:
            log(f"DRY-RUN  copiaría {src_key} -> {dst_key}")
        stats.copied += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Migración idempotente de bucket (copy-only).")
    parser.add_argument("--source-bucket", default="eig-chatbot-logs-prod")
    parser.add_argument(
        "--dest-bucket", default=os.getenv("S3_BUCKET", "prisma-calificacion-canvas")
    )
    parser.add_argument("--source-prefix", default="")
    parser.add_argument("--region", default=os.getenv("AWS_REGION"))
    parser.add_argument(
        "--apply", action="store_true", help="ejecuta las copias (por defecto: dry-run)"
    )
    args = parser.parse_args()

    import boto3
    from dotenv import load_dotenv

    load_dotenv()
    s3 = boto3.client("s3", region_name=args.region)

    stats = migrate(
        s3,
        source_bucket=args.source_bucket,
        dest_bucket=args.dest_bucket,
        source_prefix=args.source_prefix,
        apply=args.apply,
    )
    mode = "APLICADO" if args.apply else "DRY-RUN"
    print(
        f"\n[{mode}] escaneados={stats.scanned} copiados={stats.copied} "
        f"omitidos_existentes={stats.skipped_existing} filtrados={stats.filtered_out}"
    )


if __name__ == "__main__":
    main()
