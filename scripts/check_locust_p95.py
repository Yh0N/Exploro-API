"""
Lee el CSV de estadísticas de Locust (--csv prefijo) y falla si el percentil 95
supera el umbral (por defecto 200 ms).

Locust escribe columnas como \"95%\" con tiempos en milisegundos.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Valida p95 de Locust vs umbral en ms")
    p.add_argument(
        "stats_csv",
        type=Path,
        help="Ruta al archivo *_stats.csv generado por locust --csv",
    )
    p.add_argument(
        "--max-p95-ms",
        type=float,
        default=200.0,
        help="Máximo permitido para el peor p95 entre filas agregadas (ms)",
    )
    args = p.parse_args()

    if not args.stats_csv.is_file():
        print(f"No existe el archivo: {args.stats_csv}", file=sys.stderr)
        return 2

    worst = 0.0
    worst_name = ""
    with args.stats_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        key = None
        if reader.fieldnames:
            for cand in ("95%", "95pct", "95th percentile"):
                if cand in reader.fieldnames:
                    key = cand
                    break
        if not key:
            print(f"No se encontró columna de p95 en: {reader.fieldnames}", file=sys.stderr)
            return 2

        for row in reader:
            name = row.get("Name") or row.get("name") or ""
            raw = row.get(key, "").strip()
            if not raw or raw == "N/A":
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            if val > worst:
                worst = val
                worst_name = name

    if worst <= 0:
        print("No se pudo calcular p95 a partir del CSV.", file=sys.stderr)
        return 2

    print(f"Peor p95 observado: {worst:.1f} ms ({worst_name or 'sin nombre'})")
    if worst > args.max_p95_ms:
        print(
            f"Fallo SLA: p95 {worst:.1f} ms > {args.max_p95_ms} ms",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
