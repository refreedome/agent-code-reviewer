"""Sandbox test runner - executes generated test scripts and captures results."""
import os
import sys
import tempfile
import subprocess
import traceback
from pathlib import Path
from typing import Optional


class SandboxRunner:
    """Runs test scripts in an isolated subprocess and captures errors.

    Uses a temporary directory to avoid polluting the working directory.
    Supports a timeout to prevent runaway test execution.
    """

    def __init__(self, timeout: int = 30, work_dir: Optional[str] = None):
        """Initialize the sandbox runner.

        Args:
            timeout: Maximum seconds to allow a test to run (default 30).
            work_dir: Optional working directory for test execution.
                      If not provided, uses a temporary directory.
        """
        self.timeout = timeout
        self._work_dir = work_dir

    def run_test_script(self, code: str, filename: str = "test_temp.py") -> dict:
        """Run a single test script and return results.

        Args:
            code: The Python test code to execute.
            filename: Name for the temporary test file.

        Returns:
            dict with keys:
                - success (bool): Whether the script ran without errors.
                - output (str): Captured stdout.
                - errors (str): Captured stderr / traceback.
                - exit_code (int): Process exit code.
        """
        work_dir = self._work_dir or tempfile.mkdtemp(prefix="acr_sandbox_")
        script_path = Path(work_dir) / filename

        try:
            # Write the test script to a temp file
            script_path.write_text(code, encoding="utf-8")

            # Run with subprocess in isolation
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(script_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=work_dir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout[-3000:] if result.stdout else "",
                "errors": result.stderr[-2000:] if result.stderr else "",
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": f"测试执行超时（超过 {self.timeout} 秒）",
                "exit_code": -1,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "errors": "pytest 未安装，请执行 pip install pytest",
                "exit_code": -2,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"执行异常: {traceback.format_exc()[:2000]}",
                "exit_code": -3,
            }
        finally:
            # Clean up temp file
            if not self._work_dir and script_path.exists():
                try:
                    script_path.unlink()
                except OSError:
                    pass

    def run_all_scripts(self, scripts: list) -> list:
        """Run multiple test scripts and collect results.

        Args:
            scripts: List of dicts with 'code' and 'filename' keys.

        Returns:
            List of result dicts, one per script.
        """
        results = []
        for script in scripts:
            code = script.get("code", "")
            filename = script.get("filename", "test_unknown.py")
            result = self.run_test_script(code, filename)
            result["filename"] = filename
            results.append(result)
        return results

    def extract_syntax_errors(self, code: str) -> list:
        """Quick syntax check without running the test.

        Args:
            code: Python code to check.

        Returns:
            List of error messages (empty if no errors).
        """
        try:
            compile(code, "<sandbox>", "exec")
            return []
        except SyntaxError as e:
            return [f"第 {e.lineno} 行语法错误: {e.msg} (代码: {e.text.strip() if e.text else ''})"]
