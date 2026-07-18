"""Knowledge store - RAG-based team standard injection and knowledge extraction.

Uses a simple keyword-based retrieval (no external vector DB needed).
Stores:
  - team_specs: Coding standards, naming conventions, assertion styles
  - good_examples: High-quality test cases as few-shot examples
  - corrections: Human correction pairs (error -> fix) for continuous learning
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def _get_store_dir() -> Path:
    """Get knowledge base directory."""
    store_dir = Path.home() / ".agent-code-reviewer" / "knowledge"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


def _get_specs_path() -> Path:
    return _get_store_dir() / "team_specs.json"


def _get_examples_path() -> Path:
    return _get_store_dir() / "good_examples.json"


def _get_corrections_path() -> Path:
    return _get_store_dir() / "corrections.json"


# ---- Team Specs (RAG injection) ---- #

def list_specs() -> list:
    """List all team specs."""
    path = _get_specs_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def add_spec(tag: str, content: str) -> None:
    """Add a team spec entry.

    Args:
        tag: Category tag like "naming", "assertion", "fixture"
        content: The spec text content.
    """
    specs = list_specs()
    specs.append({
        "id": len(specs) + 1,
        "tag": tag,
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _get_specs_path().write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_spec(spec_id: int) -> bool:
    """Remove a spec by ID."""
    specs = list_specs()
    new_specs = [s for s in specs if s.get("id") != spec_id]
    if len(new_specs) == len(specs):
        return False
    _get_specs_path().write_text(json.dumps(new_specs, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def search_specs(query: str, max_results: int = 3) -> list:
    """Simple keyword-based RAG retrieval.

    Args:
        query: Search query to match against spec content and tags.
        max_results: Maximum specs to return.

    Returns:
        List of matching spec dicts.
    """
    specs = list_specs()
    if not specs or not query:
        return specs[:max_results] if specs else []

    # Simple keyword scoring
    keywords = set(re.findall(r'\w+', query.lower()))
    scored = []
    for spec in specs:
        text = (spec.get("tag", "") + " " + spec.get("content", "")).lower()
        score = sum(1 for kw in keywords if kw in text and len(kw) > 1)
        if score > 0:
            scored.append((score, spec))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:max_results]]


# ---- Good Examples (Few-shot) ---- #

def list_examples() -> list:
    """List all good examples."""
    path = _get_examples_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def add_example(title: str, code: str, tags: list = None) -> None:
    """Add a high-quality test example for few-shot learning.

    Args:
        title: Short description.
        code: The example test code.
        tags: List of category tags.
    """
    examples = list_examples()
    examples.append({
        "id": len(examples) + 1,
        "title": title,
        "code": code,
        "tags": tags or [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _get_examples_path().write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8")


def search_examples(query: str, max_results: int = 2) -> list:
    """Retrieve relevant good examples by keyword match."""
    examples = list_examples()
    if not examples or not query:
        return examples[:max_results] if examples else []

    keywords = set(re.findall(r'\w+', query.lower()))
    scored = []
    for ex in examples:
        text = (ex.get("title", "") + " " + " ".join(ex.get("tags", []))).lower()
        score = sum(1 for kw in keywords if kw in text and len(kw) > 1)
        if score > 0:
            scored.append((score, ex))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:max_results]]


# ---- Corrections (Knowledge Extraction for continuous learning) ---- #

def list_corrections() -> list:
    """List all correction pairs."""
    path = _get_corrections_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def record_correction(error_code: str, fixed_code: str, error_info: str = "") -> None:
    """Record a human correction pair for continuous learning.

    Args:
        error_code: The original code that had issues.
        fixed_code: The human-corrected version.
        error_info: What was wrong (syntax error, logic bug, etc.)
    """
    corrections = list_corrections()
    corrections.append({
        "id": len(corrections) + 1,
        "error_code": error_code[:500],
        "fixed_code": fixed_code[:500],
        "error_info": error_info[:200],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    # Keep only latest 20 corrections
    if len(corrections) > 20:
        corrections = corrections[-20:]
    _get_corrections_path().write_text(json.dumps(corrections, ensure_ascii=False, indent=2), encoding="utf-8")


def get_recent_corrections(limit: int = 3) -> list:
    """Get most recent correction pairs for few-shot learning."""
    corrections = list_corrections()
    return list(reversed(corrections))[:limit]


def get_rag_context(query: str) -> str:
    """Build RAG context string for prompt injection.

    Combines relevant team specs, good examples, and recent corrections.

    Args:
        query: The test requirement description.

    Returns:
        Formatted context string to inject into Agent prompts.
    """
    parts = []

    # Relevant team specs
    specs = search_specs(query)
    if specs:
        parts.append("## 团队编码规范")
        for s in specs:
            parts.append(f"[{s.get('tag', '通用')}] {s.get('content', '')}")

    # Relevant good examples
    examples = search_examples(query)
    if examples:
        parts.append("\n## 参考测试用例（Few-shot）")
        for ex in examples:
            parts.append(f"### {ex.get('title', '示例')}")
            parts.append(f"```python\n{ex.get('code', '')}\n```")

    # Recent corrections (always included for continuous learning)
    corrections = get_recent_corrections()
    if corrections:
        parts.append("\n## 历史修正记录（避免重复错误）")
        for c in corrections:
            parts.append(f"- 问题: {c.get('error_info', '')[:100]}")
            parts.append(f"  -> 修正: 将 `{c.get('error_code', '')[:80]}...` 改为 `{c.get('fixed_code', '')[:80]}...`")

    return "\n\n".join(parts) if parts else ""
