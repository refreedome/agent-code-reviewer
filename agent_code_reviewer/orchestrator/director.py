"""Director - orchestrates the multi-agent pipeline."""
import logging
import textwrap
from typing import Optional, Callable
from agent_code_reviewer.config import Config
from agent_code_reviewer.llm.qwen import QwenLLM
from agent_code_reviewer.agents.requirement_analyst import RequirementAnalyst
from agent_code_reviewer.agents.code_reader import CodeReader
from agent_code_reviewer.agents.tester import Tester
from agent_code_reviewer.agents.reviewer import Reviewer
from agent_code_reviewer.integrations.github import GitHubLoader
from agent_code_reviewer.sandbox.runner import SandboxRunner
from agent_code_reviewer.models.schemas import (
    ReviewReport, TestRequirement, CodeContext, TestScript, SecurityReview,
)

logger = logging.getLogger(__name__)


MAX_RETRIES = 4


class Director:
    """Director orchestrates the multi-agent code review pipeline.

    The pipeline runs 4 agents in sequence:
    1. RequirementAnalyst - Parse user requirements
    2. CodeReader - Extract code context
    3. Tester - Generate test scripts
    4. Reviewer - Security and architecture review

    The Director assembles the final report from all agent outputs.
    """

    def __init__(self, config: Config):
        """Initialize the Director with configuration.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.llm = QwenLLM(config.llm)

        # Initialize agents
        self.requirement_analyst = RequirementAnalyst(self.llm)
        self.code_reader = CodeReader(self.llm)
        self.tester = Tester(self.llm)
        self.reviewer = Reviewer(self.llm)

    def run(
        self,
        user_requirement: str,
        repo_url: str,
        progress_callback: Optional[Callable[[str, str], None]] = None,
        is_local: bool = False,
    ) -> ReviewReport:
        """Execute the full multi-agent code review pipeline.

        Args:
            user_requirement: Natural language description of what to test/review.
            repo_url: GitHub repository URL or local directory path to analyze.
            progress_callback: Optional callback(stage, message) for progress updates.
            is_local: If True, repo_url is treated as a local filesystem path.

        Returns:
            Comprehensive ReviewReport with all agent outputs.

        Raises:
            RuntimeError: If any critical stage fails.
        """

        def notify(stage: str, message: str):
            if progress_callback:
                progress_callback(stage, message)
            logger.info(f"[{stage}] {message}")

        # Initialize report
        report = ReviewReport(repo_url=repo_url)

        # Stage 0: Load repository (clone or local)
        source_label = "本地目录" if is_local else "GitHub 仓库"
        notify("clone", f"正在加载{source_label}...")
        loader = GitHubLoader(self.config.analysis)
        try:
            if is_local:
                loader.load_local(repo_url)
                notify("clone", f"本地目录加载完成: {repo_url}")
            else:
                loader.clone_repo(repo_url)
                notify("clone", "GitHub 仓库克隆完成")

            # Get project info
            project_tree = loader.get_project_tree()
            code_files = loader.get_code_files()
            project_summary = loader.get_project_summary()
            notify("clone", f"发现 {len(code_files)} 个源代码文件")

            # Stage 1: Requirement Analysis
            notify("requirement", "📋 需求分析师正在分析测试需求...")
            try:
                requirement_data = self.requirement_analyst.execute({
                    "user_requirement": user_requirement,
                    "project_summary": project_summary[:3000],  # Limit summary length
                })
                report.requirement = self._build_test_requirement(requirement_data)
                notify("requirement", "测试需求分析完成")
            except Exception as e:
                logger.error(f"Requirement analysis failed: {e}")
                notify("requirement", f"需求分析出现异常: {e}")
                report.requirement = TestRequirement(
                    test_objective=user_requirement,
                    core_test_points=[{"name": "手动分析", "criteria": "自动分析失败，请手动检查"}],
                )

            # Stage 2: Code Reading
            notify("code_reading", "🔍 代码阅读专家正在分析代码结构...")
            try:
                # Limit code files to avoid token limits
                limited_files = self._limit_code_files(code_files, max_chars=80000)
                code_data = self.code_reader.execute({
                    "requirement": requirement_data,
                    "project_tree": project_tree,
                    "code_files": limited_files,
                })
                report.code_context = self._build_code_context(code_data)
                notify("code_reading", "代码分析完成")
            except Exception as e:
                logger.error(f"Code reading failed: {e}")
                notify("code_reading", f"代码分析出现异常: {e}")
                report.code_context = CodeContext(
                    logic_summary="代码自动分析失败，请手动审查代码。"
                )

            # Stage 3: Test Generation with Sandbox Loop (闭环验证)
            notify("testing", "测试工程师正在生成测试脚本...")
            sandbox = SandboxRunner(timeout=30)

            test_req_context = requirement_data
            test_code_context = code_data if not code_data.get("parse_error") else {}

            retry_count = 0
            sandbox_results = []
            final_test_data = None
            last_errors = ""

            while retry_count <= MAX_RETRIES:
                if retry_count > 0:
                    notify("testing", f"第 {retry_count}/{MAX_RETRIES} 次重试修复...")

                try:
                    input_data = {
                        "requirement": test_req_context,
                        "code_context": test_code_context,
                    }
                    if last_errors:
                        input_data["syntax_feedback"] = last_errors

                    test_data = self.tester.execute(input_data)
                    final_test_data = test_data

                    scripts = test_data.get("scripts", [])
                    if not scripts:
                        notify("testing", "未生成测试脚本，跳过沙盒验证")
                        break

                    # Syntax check first (fast path)
                    all_syntax_ok = True
                    for s in scripts:
                        errs = sandbox.extract_syntax_errors(s.get("code", ""))
                        if errs:
                            all_syntax_ok = False
                            last_errors = "\n".join(errs)
                            notify("testing", f"发现语法错误: {s.get('filename', '')}")
                            break

                    if not all_syntax_ok:
                        retry_count += 1
                        continue

                    # Run sandbox on all scripts
                    results = sandbox.run_all_scripts(scripts)
                    sandbox_results = results

                    all_passed = all(r.get("success") for r in results)
                    if all_passed:
                        notify("testing", f"沙盒验证通过（{len(scripts)} 个脚本）")
                        break
                    else:
                        # Collect error info for retry
                        failed = [r for r in results if not r.get("success")]
                        error_details = []
                        for f in failed:
                            fname = f.get("filename", "unknown")
                            err = (f.get("errors") or f.get("output") or "未知错误")[:500]
                            error_details.append(f"### {fname} 执行失败\n{err}")
                        last_errors = "\n\n".join(error_details)
                        notify("testing", f"沙盒验证未通过（{len(failed)} 个脚本失败），准备重试")
                        retry_count += 1

                except Exception as e:
                    logger.error(f"Test generation failed: {e}")
                    notify("testing", f"测试生成异常: {e}")
                    retry_count += 1
                    last_errors = str(e)

            # Build TestScript with sandbox metadata
            if final_test_data:
                report.test_script = self._build_test_script(final_test_data)
                report.test_script.sandbox_results = sandbox_results
                report.test_script.retry_count = retry_count
                if retry_count > 0:
                    report.test_script.notes = (
                        f"经过 {retry_count} 轮沙盒验证修复后生成的测试脚本。"
                        + (f"最终版本仍有 {len([r for r in sandbox_results if not r.get('success')])} 个脚本未通过沙盒。"
                           if sandbox_results and not all(r.get("success") for r in sandbox_results)
                           else "")
                    )
            else:
                report.test_script = TestScript(
                    strategy="自动测试生成失败，建议手动编写测试用例。",
                    retry_count=retry_count,
                )

            notify("testing_result",
                   f"测试脚本生成完成（重试 {retry_count} 次，"
                   f"{len([r for r in sandbox_results if r.get('success')]) if sandbox_results else 0}/"
                   f"{len(sandbox_results) if sandbox_results else 0} 脚本通过沙盒）")

            # Stage 4: Security Review
            notify("review", "安全审查员正在进行安全与架构审查...")
            try:
                review_data = self.reviewer.execute({
                    "code_context": code_data if not code_data.get("parse_error") else {},
                    "test_script": test_data if not test_data.get("parse_error") else {},
                })
                report.security_review = self._build_security_review(review_data)
                notify("review", "安全与架构审查完成")
            except Exception as e:
                logger.error(f"Security review failed: {e}")
                notify("review", f"安全审查出现异常: {e}")
                report.security_review = SecurityReview(
                    architecture_assessment="自动安全审查失败，建议进行人工安全审计。"
                )

        finally:
            # Always clean up
            notify("cleanup", "正在清理临时文件...")
            loader.cleanup()
            notify("cleanup", "清理完成")

        notify("done", "综合报告生成完毕")
        # Collect token usage
        report.token_usage = self.llm.get_token_summary()
        logger.info(f"Token usage: {report.token_usage}")
        return report

    def _limit_code_files(self, code_files: dict, max_chars: int = 80000) -> dict:
        """Limit total characters across all code files.

        Args:
            code_files: Original code files dict.
            max_chars: Maximum total characters allowed.

        Returns:
            Filtered dict within the character limit.
        """
        limited = {}
        total = 0
        # Sort by path length (shorter paths first, usually more important)
        for path in sorted(code_files.keys(), key=len):
            content = code_files[path]
            if total + len(content) > max_chars:
                break
            limited[path] = content
            total += len(content)
        return limited

    @staticmethod
    def _build_test_requirement(data: dict) -> TestRequirement:
        """Build TestRequirement from agent output dict."""
        if data.get("parse_error"):
            return TestRequirement(test_objective=data.get("raw_response", "解析失败"))
        return TestRequirement(
            test_objective=data.get("test_objective", ""),
            core_test_points=data.get("core_test_points", []),
            exception_scenarios=data.get("exception_scenarios", []),
            boundary_conditions=data.get("boundary_conditions", []),
        )

    @staticmethod
    def _build_code_context(data: dict) -> CodeContext:
        """Build CodeContext from agent output dict."""
        if data.get("parse_error"):
            return CodeContext(logic_summary=data.get("raw_response", "解析失败"))
        return CodeContext(
            modules=data.get("modules", []),
            code_snippets=data.get("code_snippets", []),
            dependencies=data.get("dependencies", []),
            api_endpoints=data.get("api_endpoints", []),
            logic_summary=data.get("logic_summary", ""),
        )

    @staticmethod
    def _build_test_script(data: dict) -> TestScript:
        """Build TestScript from agent output dict."""
        if data.get("parse_error"):
            return TestScript(strategy=data.get("raw_response", "解析失败"))
        return TestScript(
            strategy=data.get("strategy", ""),
            scripts=data.get("scripts", []),
            dependencies=data.get("dependencies", []),
            notes=data.get("notes", ""),
        )

    @staticmethod
    def _build_security_review(data: dict) -> SecurityReview:
        """Build SecurityReview from agent output dict."""
        if data.get("parse_error"):
            return SecurityReview(architecture_assessment=data.get("raw_response", "解析失败"))
        return SecurityReview(
            high_risks=data.get("high_risks", []),
            code_smells=data.get("code_smells", []),
            architecture_assessment=data.get("architecture_assessment", ""),
        )
