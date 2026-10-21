"""Executor do pipeline (equivalente ao Makefile, para máquinas sem `make`).

Uso:
  python -m matopiba.tarefas <alvo> [<alvo> ...]
  python -m matopiba.tarefas lista

Alvos: etapa0 … etapa7, analise (= os s08 exceto HonestDiD), testes, all, honestdid. Cada alvo grava o tempo em
outputs/logs/tempos.csv.
"""

import csv
import importlib
import subprocess
import sys
import time
from datetime import datetime

from matopiba.config import ROOT, path

ALVOS: dict[str, list[str]] = {
    "etapa0": ["matopiba.s00_check_auth"],
    "etapa1": ["matopiba.s01_universo"],
    "etapa2": ["matopiba.s02_mapbiomas"],
    "etapa3": ["matopiba.s03_luzes"],
    "etapa4": ["matopiba.s04_construido"],
    "etapa5": ["matopiba.s05_socio"],
    "etapa6": ["matopiba.s06_instrumento"],
    "etapa7": ["matopiba.s07_paineis"],
    "analise": ["matopiba.s08_descritiva", "matopiba.s08_did", "matopiba.s08_iv",
                "matopiba.s08_censos", "matopiba.s08_heterogeneidade", "matopiba.s08_robustez",
                "matopiba.s08_luzes_sensor"],
}
ALVOS["all"] = [m for k in [f"etapa{i}" for i in range(8)] + ["analise"] for m in ALVOS[k]]
# fora do "all": roda no ambiente opcional do HonestDiD (numpy < 2.4; ver README)
ALVOS["honestdid"] = ["matopiba.s08_honestdid"]


def rodar_modulo(mod: str) -> float:
    t = time.time()
    print(f"\n=== {mod} ===", flush=True)
    m = importlib.import_module(mod)
    argv, sys.argv = sys.argv, [mod]
    try:
        cod = m.main()
    finally:
        sys.argv = argv
    if cod:
        raise SystemExit(f"{mod} terminou com código {cod}")
    return time.time() - t


def testes() -> float:
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        str(ROOT / "tests")], check=False)
    if r.returncode:
        raise SystemExit("testes falharam")
    return time.time() - t


def registrar(alvo: str, mod: str, seg: float) -> None:
    arq = path("logs") / "tempos.csv"
    novo = not arq.exists()
    with open(arq, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["quando", "alvo", "modulo", "segundos"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), alvo, mod, f"{seg:.0f}"])


def main() -> int:
    alvos = sys.argv[1:] or ["lista"]
    if alvos == ["lista"]:
        for k, v in ALVOS.items():
            print(f"{k:8s} {', '.join(v)}")
        print("testes   pytest tests/")
        return 0
    for alvo in alvos:
        if alvo == "testes":
            registrar(alvo, "pytest", testes())
            continue
        if alvo not in ALVOS:
            raise SystemExit(f"alvo desconhecido: {alvo} (use 'lista')")
        for mod in ALVOS[alvo]:
            registrar(alvo, mod, rodar_modulo(mod))
        if alvo == "etapa7":
            registrar("testes", "pytest", testes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
