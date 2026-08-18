"""Deprecated compatibility entry point for the former local vector prototype.

Use scripts/init_rag.py and scripts/ingest_novels.py for the current Milvus RAG
pipeline. Private source files must be supplied through environment variables
or ignored local data directories.
"""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    source = Path(
        os.getenv(
            "NOVEL_SOURCE_FILE",
            Path(__file__).resolve().parent.parent / "data" / "novels" / "三国演义.txt",
        )
    )
    if not source.exists():
        print(f"Source file not found: {source}")
        print("Set NOVEL_SOURCE_FILE or place an authorized corpus under data/novels.")
        return 1
    print("This prototype script is deprecated.")
    print("Run: python scripts/init_rag.py")
    print("Then ingest the authorized source configured by NOVEL_SOURCE_DIR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

