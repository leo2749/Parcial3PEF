"""
Compara el resultado de pytest-benchmark contra la línea base y decide si hay regresión.

Criterio (ver docs/calidad/controles.md):

* Cada benchmark se **normaliza** dividiendo su mediana por la mediana de
  ``test_calibracion`` (carga fija de Python puro). Así el valor depende poco
  del hardware y la línea base sirve aunque el CI corra en otra máquina.
* Hay **regresión** si el valor normalizado supera al de la línea base en más
  de la tolerancia (``--tolerancia``, 50 % por defecto: los runners
  compartidos del CI tienen bastante ruido).
* Además se exige que la versión optimizada sea al menos ``--speedup-minimo``
  veces más rápida que el baseline **en la misma corrida** (no depende de la
  línea base ni de la máquina).

Uso:
    python scripts/comparar_benchmark.py                      # comparar
    python scripts/comparar_benchmark.py --actualizar         # regrabar la línea base

Sale con código 1 si hay regresión, 0 si no.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CALIBRACION = "test_calibracion"
BASELINE = "test_recomendar_baseline"
OPTIMIZADO = "test_recomendar_optimizado_sin_cache"


def leer_medianas(ruta: Path) -> dict[str, float]:
    """Devuelve ``{nombre_benchmark: mediana_en_segundos}`` de un JSON de pytest-benchmark."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {b["name"]: b["stats"]["median"] for b in datos["benchmarks"]}


def normalizar(medianas: dict[str, float]) -> dict[str, float]:
    """Divide cada mediana por la de la calibración."""
    referencia = medianas[CALIBRACION]
    return {nombre: valor / referencia for nombre, valor in medianas.items()
            if nombre != CALIBRACION}


def comparar(actual: dict[str, float], base: dict[str, float],
             tolerancia: float) -> list[dict[str, object]]:
    """Arma una fila por benchmark con la variación respecto de la línea base."""
    filas: list[dict[str, object]] = []
    for nombre, valor in sorted(actual.items()):
        referencia = base.get(nombre)
        if referencia is None:
            filas.append({"benchmark": nombre, "actual": valor, "base": None,
                          "variacion": None, "estado": "NUEVO"})
            continue
        variacion = valor / referencia - 1
        estado = "REGRESION" if variacion > tolerancia else "OK"
        filas.append({"benchmark": nombre, "actual": valor, "base": referencia,
                      "variacion": variacion, "estado": estado})
    return filas


def escribir_reporte(destino: Path, filas: list[dict[str, object]], speedup: float,
                     speedup_minimo: float, tolerancia: float) -> None:
    """Escribe el reporte legible (Markdown) y el de máquina (JSON)."""
    lineas = [
        "# Comparación de benchmarks contra la línea base",
        "",
        f"Tolerancia de regresión: {tolerancia:.0%} · valores normalizados por `{CALIBRACION}`",
        "",
        "| Benchmark | Actual | Línea base | Variación | Estado |",
        "|---|---:|---:|---:|---|",
    ]
    for fila in filas:
        base = f"{fila['base']:.3f}" if fila["base"] is not None else "—"
        variacion = f"{fila['variacion']:+.1%}" if fila["variacion"] is not None else "—"
        lineas.append(f"| {fila['benchmark']} | {fila['actual']:.3f} | {base} | "
                      f"{variacion} | {fila['estado']} |")
    estado_speedup = "OK" if speedup >= speedup_minimo else "INSUFICIENTE"
    lineas += ["", f"Speedup optimizado vs. baseline (misma corrida): **{speedup:.1f}x** "
               f"(mínimo exigido {speedup_minimo:.1f}x) → {estado_speedup}", ""]
    destino.with_suffix(".md").write_text("\n".join(lineas), encoding="utf-8")
    destino.with_suffix(".json").write_text(json.dumps(
        {"tolerancia": tolerancia, "speedup": speedup, "speedup_minimo": speedup_minimo,
         "filas": filas}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lineas))


def main() -> int:
    """Punto de entrada; devuelve el código de salida."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--resultado", type=Path, default=RAIZ / "reportes" / "benchmark.json")
    parser.add_argument("--linea-base", type=Path,
                        default=RAIZ / "benchmarks" / "linea_base.json")
    parser.add_argument("--tolerancia", type=float, default=0.50)
    parser.add_argument("--speedup-minimo", type=float, default=3.0)
    parser.add_argument("--actualizar", action="store_true",
                        help="guarda el resultado actual como nueva línea base")
    args = parser.parse_args()

    medianas = leer_medianas(args.resultado)
    actual = normalizar(medianas)
    if args.actualizar:
        args.linea_base.write_text(json.dumps(
            {"descripcion": f"Medianas normalizadas por {CALIBRACION}. "
                            "Regenerar con: python scripts/comparar_benchmark.py --actualizar",
             "valores": actual}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Línea base actualizada en {args.linea_base}")
        return 0

    base = json.loads(args.linea_base.read_text(encoding="utf-8"))["valores"]
    filas = comparar(actual, base, args.tolerancia)
    speedup = medianas[BASELINE] / medianas[OPTIMIZADO]
    escribir_reporte(args.resultado.with_name("benchmark_comparacion"), filas, speedup,
                     args.speedup_minimo, args.tolerancia)

    regresiones = [f["benchmark"] for f in filas if f["estado"] == "REGRESION"]
    if regresiones or speedup < args.speedup_minimo:
        print(f"\nRECHAZADO: regresiones={regresiones} speedup={speedup:.1f}x", file=sys.stderr)
        return 1
    print("\nAPROBADO: sin regresiones significativas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
