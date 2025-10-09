from __future__ import annotations

import json
import re
from typing import Any, Optional


def parse_json_loose(text: str) -> Optional[Any]:
    """Best-effort parse: try full text; else extract first JSON object/array.
    Returns None if nothing parseable.
    """
    text = text.strip()
    for candidate in (text, _extract_json_block(text, kind="array"), _extract_json_block(text, kind="object")):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _extract_json_block(s: str, kind: str) -> Optional[str]:
    if kind == "array":
        pattern = r"\[.*?\]"
    else:
        pattern = r"\{.*?\}"
    m = re.search(pattern, s, flags=re.S)
    return m.group(0) if m else None

