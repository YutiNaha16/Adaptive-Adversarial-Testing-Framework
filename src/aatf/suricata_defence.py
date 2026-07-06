from __future__ import annotations

import json
import os
from pathlib import Path

from aatf.contracts import Action, DetectionResult
from aatf.defence import Defence, DefenceError


class SuricataDefence(Defence):
    def __init__(self, eve_path: str | Path) -> None:
        self._eve_path = Path(eve_path)
        self._cursor: int = 0

    def observe(self, action: Action) -> DetectionResult:
        try:
            file_size = os.path.getsize(self._eve_path)
        except OSError as exc:
            raise DefenceError(f"eve.json unreadable: {exc}", cause=exc) from exc

        if self._cursor > file_size:
            self._cursor = 0

        try:
            with self._eve_path.open("rb") as fh:
                fh.seek(self._cursor)
                new_bytes = fh.read()
                self._cursor = fh.tell()
        except OSError as exc:
            raise DefenceError(f"eve.json unreadable: {exc}", cause=exc) from exc

        sids: list[str] = []
        for raw_line in new_bytes.splitlines():
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event_type") == "alert":
                sig_id = event.get("alert", {}).get("signature_id")
                if sig_id is not None:
                    sids.append(str(sig_id))

        alerted = bool(sids)
        return DetectionResult(
            alerted=alerted,
            rule_ids=sids,
            anomaly_score=0.0,
            coverage="covered" if alerted else "uncovered",
        )
