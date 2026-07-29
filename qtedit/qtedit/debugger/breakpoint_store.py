"""Breakpoint persistence across app restarts -- same JSON-sibling-file
idiom as session.py/prefs.py, keyed by absolute file path rather than
per-project (a breakpoint belongs to the file itself, wherever it gets
opened from), so this stays a single flat global store.
"""
import json
import os

FILENAME = "breakpoints.json"


def _load_all(store_path):
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load_breakpoints(store_path, path):
    """Returns the list of {"line", "condition", "ignore_count"} dicts
    saved for `path` (absolute), or [] if none were saved."""
    return _load_all(store_path).get(path, [])


def save_breakpoints(store_path, path, breakpoints):
    """Persist `path`'s breakpoint list, or drop its entry entirely once
    the list is empty (so files that never had or no longer have
    breakpoints don't accumulate empty stanzas in the store forever)."""
    all_breakpoints = _load_all(store_path)
    if breakpoints:
        all_breakpoints[path] = breakpoints
    else:
        all_breakpoints.pop(path, None)
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(all_breakpoints, f, indent=2)
