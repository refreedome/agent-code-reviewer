"""Requirement Analyst agent - parses user requirements into structured test outlines."""
from agent_code_reviewer.agents.base import BaseAgent


class RequirementAnalyst(BaseAgent):
    """需求分析师 Agent.

    负责将用户的自然语言测试需求解析为结构化的测试大纲，
    包括核心测试点、验收标准、异常场景和边界条件。
    """

    @property
    def name(self) -> str:
        return "需求分析师"

    @property
    def system_prompt(self) -> str:
        return """你是一位资深的软件测试需求分析师，拥有丰富的软件质量保证经验。你的职责是将用户的自然语言测试需求转化为结构化、可执行的测试大纲。

## 你的核心能力

1. **需求理解**：深入理解用户的测试意图，识别显式和隐式的测试需求
2. **测试分解**：将模糊的需求拆解为具体的、可度量的测试点
3. **场景覆盖**：识别正常流程、异常流程、边界条件和并发场景
4. **验收标准**：为每个测试点定义明确的验收标准和通过条件

## 工作规范

- 仔细分析用户提供的测试需求描述和项目概要
- 将需求分解为独立的测试模块和测试点
- 为每个测试点编写清晰的验收标准（criteria）
- 识别可能被忽略的异常场景和边界条件
- 考虑并发、性能、安全等维度的测试需求
- 输出结构化的 JSON 格式，便于下游 Agent 使用

## 输出格式要求

请严格按照以下 JSON 格式输出：
{
    "test_objective": "一句话概括测试目标",
    "core_test_points": [
        {"name": "测试点名称", "criteria": "验收标准描述"},
        ...
    ],
    "exception_scenarios": ["异常场景描述1", "异常场景描述2", ...],
    "boundary_conditions": ["边界条件描述1", "边界条件描述2", ...]
}

注意：
- core_test_points 至少包含 3-5 个核心测试点
- exception_scenarios 至少包含 2-3 个异常场景
- boundary_conditions 至少包含 1-3 个边界条件
- 所有内容使用中文描述
- 测试点和标准要具体、可执行，避免模糊的表述"""

    def execute(self, input_data: dict) -> dict:
        """Parse user requirements into structured test outline.

        Args:
            input_data: Dictionary with keys:
                - user_requirement (str): Natural language test requirement
                - project_summary (str): Brief summary of the project

        Returns:
            Dictionary matching TestRequirement schema.
        """
        user_requirement = input_data.get("user_requirement", "")
        project_summary = input_data.get("project_summary", "")

        user_prompt = f"""请分析以下测试需求并生成结构化的测试大纲。

## 项目概要
{project_summary}

## 用户测试需求
{user_requirement}

请按照系统提示中的 JSON 格式输出结构化的测试大纲。"""

        result = self.llm.chat_json(self.system_prompt, user_prompt, temperature=0.2)
        return result
