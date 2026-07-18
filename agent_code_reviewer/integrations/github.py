"""GitHub repository loader - clones repos and extracts code files."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from git import Repo
from agent_code_reviewer.config import AnalysisConfig


class GitHubLoader:
    """Load and analyze GitHub repositories.

    Clones a repository to a temporary directory and extracts
    relevant source code files based on configuration.

    Supports context manager protocol for automatic cleanup.
    """

    def __init__(self, config: AnalysisConfig):
        """Initialize the GitHub loader.

        Args:
            config: Analysis configuration with file filters.
        """
        self.config = config
        self._repo_path: Optional[Path] = None
        self._temp_dir: Optional[str] = None

    def __enter__(self) -> 'GitHubLoader':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def clone_repo(self, url: str) -> Path:
        """Clone a GitHub repository to a temporary directory.

        Args:
            url: The GitHub repository URL.

        Returns:
            Path to the cloned repository.

        Raises:
            git.GitCommandError: If cloning fails.
        """
        self._temp_dir = tempfile.mkdtemp(prefix="acr_repo_")
        self._repo_path = Path(self._temp_dir) / "repo"

        Repo.clone_from(url, str(self._repo_path), depth=1)
        return self._repo_path

    def get_project_tree(self, max_depth: int = 3) -> str:
        """Generate a project directory tree string.

        Args:
            max_depth: Maximum directory depth to display.

        Returns:
            String representation of the project tree, similar to `tree` command output.

        Raises:
            RuntimeError: If no repository has been cloned yet.
        """
        if not self._repo_path:
            raise RuntimeError("No repository cloned. Call clone_repo() first.")

        lines = [self._repo_path.name]
        self._build_tree(self._repo_path, lines, prefix="", max_depth=max_depth, current_depth=0)
        return "\n".join(lines)

    def _build_tree(
        self, path: Path, lines: list, prefix: str, max_depth: int, current_depth: int
    ) -> None:
        """Recursively build the tree string.

        Args:
            path: Current directory path.
            lines: List of lines to append to.
            prefix: Current indentation prefix.
            max_depth: Maximum depth to traverse.
            current_depth: Current depth level.
        """
        if current_depth >= max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return

        # Filter out excluded directories and hidden files (except important ones)
        filtered = []
        for entry in entries:
            if entry.name in self.config.exclude_dirs:
                continue
            if entry.name.startswith('.') and entry.name not in ('.env.example', '.env.sample'):
                if entry.is_dir():
                    continue
            filtered.append(entry)

        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                self._build_tree(
                    entry, lines,
                    prefix=prefix + extension,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )

    def get_code_files(self) -> dict:
        """Read all relevant source code files from the cloned repository.

        Respects the AnalysisConfig for file extensions, excluded directories,
        and maximum file size.

        Returns:
            Dictionary mapping relative file paths to their contents.

        Raises:
            RuntimeError: If no repository has been cloned yet.
        """
        if not self._repo_path:
            raise RuntimeError("No repository cloned. Call clone_repo() first.")

        code_files = {}
        self._collect_files(self._repo_path, code_files)
        return code_files

    def _collect_files(self, path: Path, code_files: dict) -> None:
        """Recursively collect source code files.

        Args:
            path: Current directory to scan.
            code_files: Dictionary to populate with file paths and contents.
        """
        try:
            entries = sorted(path.iterdir(), key=lambda e: e.name.lower())
        except PermissionError:
            return

        for entry in entries:
            if entry.name in self.config.exclude_dirs:
                continue
            if entry.name.startswith('.'):
                continue

            if entry.is_dir():
                self._collect_files(entry, code_files)
            elif entry.is_file():
                # Check file extension
                if entry.suffix.lower() not in self.config.include_extensions:
                    continue

                # Check file size
                try:
                    file_size = entry.stat().st_size
                    if file_size > self.config.max_file_size:
                        continue
                except OSError:
                    continue

                # Read file content
                try:
                    content = entry.read_text(encoding='utf-8', errors='ignore')
                    if content.strip():
                        rel_path = str(entry.relative_to(self._repo_path))
                        code_files[rel_path] = content
                except (OSError, UnicodeDecodeError):
                    continue

    def get_project_summary(self) -> str:
        """Generate a brief project summary from README and structure.

        Returns:
            String summary of the project.
        """
        if not self._repo_path:
            raise RuntimeError("No repository cloned. Call clone_repo() first.")

        summary_parts = []

        # Try to read README
        for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
            readme_path = self._repo_path / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding='utf-8', errors='ignore')
                    # Take first 2000 chars
                    summary_parts.append(f"README:\n{content[:2000]}")
                    break
                except OSError:
                    pass

        # Add tree overview
        tree = self.get_project_tree(max_depth=2)
        summary_parts.append(f"\n项目结构:\n{tree}")

        # Count files by extension
        ext_counts: dict = {}
        self._count_extensions(self._repo_path, ext_counts)
        if ext_counts:
            ext_summary = ", ".join(f"{ext}: {count}" for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]))
            summary_parts.append(f"\n文件统计: {ext_summary}")

        return "\n".join(summary_parts)

    def _count_extensions(self, path: Path, counts: dict) -> None:
        """Count files by extension recursively.

        Args:
            path: Directory to scan.
            counts: Dictionary to populate with extension counts.
        """
        try:
            for entry in path.iterdir():
                if entry.name in self.config.exclude_dirs or entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    self._count_extensions(entry, counts)
                elif entry.is_file():
                    ext = entry.suffix.lower() or '(no ext)'
                    counts[ext] = counts.get(ext, 0) + 1
        except PermissionError:
            pass

    def cleanup(self) -> None:
        """Remove the temporary clone directory."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                # Make files writable before removal (git objects are read-only)
                for root, dirs, files in os.walk(self._temp_dir):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o755)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o644)
                shutil.rmtree(self._temp_dir)
            except OSError:
                pass
            finally:
                self._temp_dir = None
                self._repo_path = None
