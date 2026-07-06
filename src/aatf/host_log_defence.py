from __future__ import annotations

import os
from pathlib import Path

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence, DefenceError


class HostLogDefence(Defence):
    def __init__(self, log_path: str | Path, patterns: list[str]) -> None:
        self._log_path = Path(log_path)
        self._patterns = patterns
        self._cursor: int = 0

    def observe(self, action: Action) -> DetectionResult:
        try:
            file_size = os.path.getsize(self._log_path)
        except OSError as exc:
            raise DefenceError(f"host log unreadable: {exc}", cause=exc) from exc

        if self._cursor > file_size:
            self._cursor = 0

        try:
            with self._log_path.open("rb") as fh:
                fh.seek(self._cursor)
                new_bytes = fh.read()
                self._cursor = fh.tell()
        except OSError as exc:
            raise DefenceError(f"host log unreadable: {exc}", cause=exc) from exc

        matches: list[str] = []
        for raw_line in new_bytes.splitlines():
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            for pattern in self._patterns:
                if pattern in line:
                    matches.append(pattern)

        alerted = bool(matches)
        return DetectionResult(
            alerted=alerted,
            rule_ids=matches,
            anomaly_score=0.0,
            coverage="covered" if alerted else "uncovered",
        )
