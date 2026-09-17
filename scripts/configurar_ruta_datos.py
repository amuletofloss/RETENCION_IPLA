"""Compatibilidad: prepara un workspace seguro sin modificar el PBIP canónico."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, "-m", "siespbip", "prepare", "--profile", "author"]
    if len(sys.argv) > 1:
        command.extend(["--sies-root", sys.argv[1]])
    print("Este comando ya no modifica expressions.tmdl; delegando a siespbip prepare.")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
