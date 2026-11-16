"""Log estruturado em JSON Lines (um evento por linha)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


def system_clock() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StructuredLogger:
    def __init__(self, path: Optional[Path], clock: Callable[[], str] = system_clock) -> None:
        self._path = Path(path) if path is not None else None
        self._clock = clock

    def log(self, level: str, event: str, **fields: Any) -> None:
        if self._path is None:
            return
        record = {"ts": self._clock(), "level": level, "event": event}
        record.update(fields)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self._path), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
