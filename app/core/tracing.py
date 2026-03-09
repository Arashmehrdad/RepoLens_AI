import json
from datetime import datetime, UTC

from app.core.config import LOGS_DIR


TRACE_FILE = LOGS_DIR / "traces.jsonl"


def log_trace(payload: dict) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)

    trace = {
        "timestamp": datetime.now(UTC).isoformat(),
        **payload,
    }

    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")