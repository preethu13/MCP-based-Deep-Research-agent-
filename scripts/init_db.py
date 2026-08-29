"""Initialize the research database schema and vector-store directory.

Idempotent — safe to run repeatedly.  Usage::

    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so ``src`` is importable whether this
# script is run as ``python scripts/init_db.py`` or via ``python -m scripts.init_db``.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import get_settings
from src.memory.sqlite_store import SQLiteStore


def main() -> None:
    settings = get_settings()

    store = SQLiteStore(settings.db_path)
    store.initialize()
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)

    print("[OK] SQLite schema ready:", settings.db_path)
    print("[OK] ChromaDB directory ready:", settings.chroma_dir)
    print("\nDatabase initialized. You can now run:  research ask \"your question\"")



if __name__ == "__main__":
    main()
