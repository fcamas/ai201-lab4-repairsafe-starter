import json
import os
from datetime import datetime, timezone
from config import LOG_FILE


def log_interaction(question: str, tier: str, response: str) -> None:
    """
    Append a structured record of this interaction to the audit log.

    Each record is one JSON object written as a single line to LOG_FILE.
    Creates the logs/ directory if it doesn't exist.
    Prints a one-line summary to the terminal after writing.
    """
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    question_truncated = question[:300]
    response_preview = response[:200]

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tier": tier,
        "question": question_truncated,
        "question_length": len(question),
        "response_preview": response_preview,
        "response_length": len(response),
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    short_q = question_truncated[:60] + ("…" if len(question) > 60 else "")
    print(f'[LOGGED] tier={tier} | "{short_q}" → {len(response)} chars')
