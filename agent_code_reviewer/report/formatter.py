"""Report formatter - saves review reports in various formats."""
import json
from datetime import datetime
from pathlib import Path
from agent_code_reviewer.models.schemas import ReviewReport


def save_report(
    report: ReviewReport,
    output_dir: str = ".",
    output_format: str = "both",
) -> list:
    """Save the review report to files.

    Args:
        report: The ReviewReport to save.
        output_dir: Directory to save report files in.
        output_format: Output format - "markdown", "json", or "both".

    Returns:
        List of file paths that were saved.

    Raises:
        OSError: If the output directory cannot be created or files cannot be written.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = []

    if output_format in ("markdown", "both"):
        md_path = output_path / f"review_report_{timestamp}.md"
        md_path.write_text(report.to_markdown(), encoding='utf-8')
        saved_files.append(str(md_path))

    if output_format in ("json", "both"):
        json_path = output_path / f"review_report_{timestamp}.json"
        json_content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
        json_path.write_text(json_content, encoding='utf-8')
        saved_files.append(str(json_path))

    return saved_files
