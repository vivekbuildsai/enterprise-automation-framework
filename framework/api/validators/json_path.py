from __future__ import annotations

import re
from typing import Any

_SEGMENT_PATTERN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def resolve_json_path(data: Any, path: str) -> Any:
    """Minimal dotted/indexed path resolver — enough for API response
    assertions without pulling in a full JSONPath engine. Supports
    `a.b.c`, `a.0.b`, and `a[0].b` (both index styles are accepted).

    Raises `KeyError`/`IndexError` on a missing segment, with the failing
    segment named, so validator failure messages point at exactly what's
    missing instead of a raw Python traceback.
    """
    current = data
    for key_match, index_match in _SEGMENT_PATTERN.findall(path):
        if index_match != "":
            index = int(index_match)
            if not isinstance(current, list):
                raise KeyError(f"Cannot index [{index}] into non-list value at '{path}'")
            if index >= len(current):
                raise IndexError(
                    f"Index [{index}] out of range in '{path}' (length={len(current)})"
                )
            current = current[index]
            continue

        key = key_match
        if isinstance(current, list) and key.isdigit():
            index = int(key)
            if index >= len(current):
                raise IndexError(
                    f"Index [{index}] out of range in '{path}' (length={len(current)})"
                )
            current = current[index]
        elif isinstance(current, dict):
            if key not in current:
                raise KeyError(f"Field '{key}' not found in response (path='{path}')")
            current = current[key]
        else:
            raise KeyError(
                f"Cannot resolve '{key}' on {type(current).__name__} value (path='{path}')"
            )
    return current
