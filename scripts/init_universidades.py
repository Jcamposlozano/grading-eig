"""Inicializa el prefijo de cada universidad habilitada en el bucket.

Para cada universidad de la allowlist (config `universidades.permitidas`, o
`--universidades` CSV) que aún NO tenga objetos, crea un marcador
`{env}/{universidad}/.keep` (objeto vacío) para que la "carpeta" exista.

- Idempotente: salta las universidades que ya tienen objetos (p. ej. eig tras la
  migración).
- COPY-ONLY: nunca borra nada.
- Seguro por defecto: dry-run; usar --apply para escribir.

Uso:
  python scripts/init_universidades.py                      # dry-run (env=prod)
  python scripts/init_universidades.py --apply
  python scripts/init_universidades.py --env dev --universidades westfield,esic --apply
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable


def has_objects(s3, bucket: str, prefix: str) -> bool:
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
    return response.get("KeyCount", 0) > 0


def init_universidades(
    s3,
    *,
    bucket: str,
    env: str,
    universidades: list[str],
    apply: bool = False,
    log: Callable[[str], None] = print,
) -> dict[str, list[str]]:
    created: list[str] = []
    skipped: list[str] = []
    for universidad in universidades:
        prefix = f"{env}/{universidad}/"
        if has_objects(s3, bucket, prefix):
            skipped.append(universidad)
            log(f"SKIP    {universidad} (ya tiene objetos en {prefix})")
            continue
        key = f"{prefix}.keep"
        if apply:
            s3.put_object(Bucket=bucket, Key=key, Body=b"")
            log(f"CREADO  {key}")
        else:
            log(f"DRY-RUN crearía {key}")
        created.append(universidad)
    return {"created": created, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa prefijos de universidades.")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET", "prisma-calificacion-canvas"))
    parser.add_argument("--env", default="prod")
    parser.add_argument(
        "--universidades", default=None, help="CSV; por defecto la allowlist de config"
    )
    parser.add_argument("--region", default=os.getenv("AWS_REGION"))
    parser.add_argument("--apply", action="store_true", help="escribe (por defecto: dry-run)")
    args = parser.parse_args()

    import boto3
    from dotenv import load_dotenv

    load_dotenv()

    if args.universidades:
        universidades = [u.strip().lower() for u in args.universidades.split(",") if u.strip()]
    else:
        from grading.shared.config import load_config

        universidades = load_config()["universidades"]["permitidas"]

    s3 = boto3.client("s3", region_name=args.region)
    result = init_universidades(
        s3,
        bucket=args.bucket,
        env=args.env,
        universidades=universidades,
        apply=args.apply,
    )
    mode = "APLICADO" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] creadas={result['created']} omitidas={result['skipped']}")


if __name__ == "__main__":
    main()
