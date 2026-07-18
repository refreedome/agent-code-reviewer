"""Tester agent - generates test scripts and test cases."""
from agent_code_reviewer.agents.base import BaseAgent
from agent_code_reviewer.knowledge.store import get_rag_context


class Tester(BaseAgent):
    """测试工程师 Agent.

    负责根据测试需求和代码上下文生成高质量的测试用例和测试脚本，
    覆盖正常流程、边界值、异常注入和并发场景。
    """

    @property
    def name(self) -> str:
        return "测试工程师"

    @property
    def system_prompt(self) -> str:
        return """你是一位经验丰富的高级测试工程师，精通 Python 测试框架（pytest、unittest）以及各种测试方法论。你的职责是根据测试需求和代码分析结果，生成可直接运行的高质量测试脚本。

## 你的核心能力

1. **测试策略制定**：根据需求制定全面的测试策略，包括单元测试、集成测试、边界测试
2. **测试用例设计**：运用等价类划分、边界值分析、因果图等测试设计方法
3. **脚本编写**：编写清晰、可维护、可重复执行的测试脚本
4. **Mock 与 Stub**：熟练使用 mock、patch、fixture 隔离外部依赖
5. **异常测试**：设计异常注入测试，验证系统的容错能力

## 工作规范

- 基于需求分析师提供的测试大纲编写测试用例
- 参考代码阅读专家提取的代码上下文，确保测试脚本与实际代码匹配
- 使用 pytest 框架编写 Python 项目的测试脚本
- 每个测试函数包含清晰的中文注释和 docstring
- 测试命名遵循 test_<功能>_<场景>_<预期> 的规范
- 包含 setup/teardown 或 fixture 来管理测试环境
- 覆盖正常路径（happy path）、边界值、异常输入、并发场景
- 指定测试所需的额外依赖包

## 测试覆盖要求

1. **正常流程测试**：验证核心功能在正常输入下的行为
2. **边界值测试**：测试最小值、最大值、空值、临界值
3. **异常处理测试**：模拟网络错误、数据库异常、超时等异常场景
4. **并发测试**：测试多线程/多进程/异步并发场景下的正确性（如果适用）
5. **数据验证测试**：验证数据格式、类型、范围的校验逻辑

## 输出格式要求

请严格按照以下 JSON 格式输出：
{
    "strategy": "测试策略描述，说明整体测试思路和方法",
    "scripts": [
        {
            "filename": "test_xxx.py",
            "code": "完整的测试脚本代码",
            "description": "该测试脚本的用途和覆盖范围"
        },
        ...
    ],
    "dependencies": ["pytest", "pytest-asyncio", "pytest-mock", ...],
    "notes": "运行说明、注意事项或特殊配置要求"
}

注意事项：
- scripts 中至少包含 1-3 个测试脚本文件
- 每个脚本的 code 必须是完整可运行的 Python 代码
- 代码中使用中文注释说明测试意图
- dependencies 列出运行测试所需的所有额外 pip 包
- notes 说明如何运行测试、需要哪些环境变量或配置"""

    def execute(self, input_data: dict) -> dict:
        """Generate test scripts based on requirements and code context.

        Args:
            input_data: Dictionary with keys:
                - requirement (dict): Structured test requirement
                - code_context (dict): Extracted code context
                - syntax_feedback (str, optional): Previous sandbox errors for retry

        Returns:
            Dictionary matching TestScript schema.
        """
        requirement = input_data.get("requirement", {})
        code_context = input_data.get("code_context", {})
        syntax_feedback = input_data.get("syntax_feedback", "")

        # RAG: retrieve relevant team specs and examples
        rag_context = get_rag_context(requirement.get("test_objective", ""))

        # Format requirement for prompt
        req_text = f"测试目标: {requirement.get('test_objective', '')}\n\n核心测试点:\n"
        for point in requirement.get("core_test_points", []):
            req_text += f"- {point.get('name', '')}: {point.get('criteria', '')}\n"
        if requirement.get("exception_scenarios"):
            req_text += "\n异常场景:\n"
            for s in requirement.get("exception_scenarios", []):
                req_text += f"- {s}\n"
        if requirement.get("boundary_conditions"):
            req_text += "\n边界条件:\n"
            for c in requirement.get("boundary_conditions", []):
                req_text += f"- {c}\n"

        # Format code context for prompt
        code_text = ""
        if code_context.get("logic_summary"):
            code_text += f"代码逻辑概要:\n{code_context['logic_summary']}\n\n"
        if code_context.get("modules"):
            code_text += "涉及模块:\n"
            for m in code_context.get("modules", []):
                code_text += f"- {m.get('name', '')} ({m.get('path', '')})\n"
        if code_context.get("code_snippets"):
            code_text += "\n核心代码片段:\n"
            for s in code_context.get("code_snippets", []):
                code_text += f"\n文件: {s.get('file', '')}\n```python\n{s.get('code', '')}\n```\n"
        if code_context.get("api_endpoints"):
            code_text += "\nAPI 接口:\n"
            for e in code_context.get("api_endpoints", []):
                code_text += f"- {e.get('method', '')} {e.get('path', '')}: {e.get('description', '')}\n"

        user_prompt = f"""请根据以下测试需求和代码上下文，生成完整的测试脚本。

## 测试需求
{req_text}

## 代码上下文
{code_text}

{f"## 知识参考（团队规范与历史用例）\n{rag_context}\n" if rag_context else ""}
{f"## 上次运行错误反馈（请修复这些问题）\n{syntax_feedback}\n" if syntax_feedback else ""}
请按照系统提示中的 JSON 格式输出测试脚本。确保代码完整可运行。"""

        result = self.llm.chat_json(self.system_prompt, user_prompt, temperature=0.3)
        return result
