"""Director - orchestrates the multi-agent pipeline."""
import logging
from typing import Optional, Callable
from agent_code_reviewer.config import Config
from agent_code_reviewer.llm.qwen import QwenLLM
from agent_code_reviewer.agents.requirement_analyst import RequirementAnalyst
from agent_code_reviewer.agents.code_reader import CodeReader
from agent_code_reviewer.agents.tester import Tester
from agent_code_reviewer.agents.reviewer import Reviewer
from agent_code_reviewer.integrations.github import GitHubLoader
from agent_code_reviewer.models.schemas import (
    ReviewReport, TestRequirement, CodeContext, TestScript, SecurityReview,
)

logger = logging.getLogger(__name__)


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
    ) -> ReviewReport:
        """Execute the full multi-agent code review pipeline.

        Args:
            user_requirement: Natural language description of what to test/review.
            repo_url: GitHub repository URL to analyze.
            progress_callback: Optional callback(stage, message) for progress updates.

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

        # Stage 0: Clone repository
        notify("clone", "正在克隆代码仓库...")
        loader = GitHubLoader(self.config.analysis)
        try:
            loader.clone_repo(repo_url)
            notify("clone", "代码仓库克隆完成")

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

            # Stage 3: Test Generation
            notify("testing", "🧪 测试工程师正在生成测试脚本...")
            try:
                test_data = self.tester.execute({
                    "requirement": requirement_data,
                    "code_context": code_data if not code_data.get("parse_error") else {},
                })
                report.test_script = self._build_test_script(test_data)
                notify("testing", "测试脚本生成完成")
            except Exception as e:
                logger.error(f"Test generation failed: {e}")
                notify("testing", f"测试脚本生成出现异常: {e}")
                report.test_script = TestScript(
                    strategy="自动测试生成失败，建议手动编写测试用例。"
                )

            # Stage 4: Security Review
            notify("review", "🛡️ 安全审查员正在进行安全与架构审查...")
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

        notify("done", "✅ 综合报告生成完毕")
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
