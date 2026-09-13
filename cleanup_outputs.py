"""
Empties figures/, results/, and tables/ so a fresh run of paper.py /
make_tables.py never leaves stale files behind from a prior script version.

    python cleanup_outputs.py
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRS = [ROOT / "figures", ROOT / "results", ROOT / "tables"]


def main():
    for d in DIRS:
        if not d.exists():
            continue
        n = 0
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
                n += 1
        print(f"{d.name}/: removed {n} file(s)")


if __name__ == "__main__":
    main()
