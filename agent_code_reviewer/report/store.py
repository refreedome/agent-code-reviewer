"""Report store - manages a persistent index of historical reports."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_store_dir() -> Path:
    """Get the directory for storing report index."""
    store_dir = Path.home() / ".agent-code-reviewer"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


def _get_index_path() -> Path:
    """Get the path to the report index file."""
    return _get_store_dir() / "reports-index.json"


def _load_index() -> list:
    """Load the report index from disk."""
    index_path = _get_index_path()
    if not index_path.exists():
        return []
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(index: list) -> None:
    """Save the report index to disk."""
    index_path = _get_index_path()
    # Keep only latest 50 entries to avoid unlimited growth
    trimmed = index[-50:]
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)


def register_report(
    report_paths: list,
    repo_url: str,
    requirement: str,
    token_usage: Optional[dict] = None,
) -> None:
    """Register a completed review in the persistent index.

    Args:
        report_paths: List of saved report file paths.
        repo_url: The repository URL or local path that was reviewed.
        requirement: The test requirement summary.
        token_usage: Optional token usage statistics.
    """
    index = _load_index()
    entry = {
        "id": len(index) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "repo": repo_url,
        "requirement": requirement[:100],
        "files": report_paths,
        "token_usage": token_usage or {},
    }
    index.append(entry)
    _save_index(index)


def list_reports(limit: int = 10) -> list:
    """List recent reports from the index.

    Args:
        limit: Maximum number of entries to return.

    Returns:
        List of report entries (newest first, reversed).
    """
    index = _load_index()
    return list(reversed(index))[:limit]


def get_report(report_id: int) -> Optional[dict]:
    """Get a specific report by its ID.

    Args:
        report_id: The report ID (1-based).

    Returns:
        Report entry dict, or None if not found.
    """
    index = _load_index()
    for entry in index:
        if entry.get("id") == report_id:
            return entry
    return None


def clear_history() -> int:
    """Clear all report history.

    Returns:
        Number of entries removed.
    """
    index = _load_index()
    count = len(index)
    _save_index([])
    return count
