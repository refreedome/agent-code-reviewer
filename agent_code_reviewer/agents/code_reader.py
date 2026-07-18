"""Code Reader agent - extracts relevant code context from the repository."""
from agent_code_reviewer.agents.base import BaseAgent


class CodeReader(BaseAgent):
    """代码阅读专家 Agent.

    负责从代码库中提取与测试需求相关的代码上下文，
    识别模块依赖关系、API 接口和数据流向。
    """

    @property
    def name(self) -> str:
        return "代码阅读专家"

    @property
    def system_prompt(self) -> str:
        return """你是一位精通多种编程语言的代码阅读与分析专家。你的职责是从代码库中快速定位与测试需求相关的代码，并提取关键的上下文信息。

## 你的核心能力

1. **代码结构分析**：快速理解项目的目录结构、模块划分和依赖关系
2. **关键代码提取**：根据测试需求精准定位相关的函数、类、模块
3. **API 识别**：识别 REST API 端点、RPC 接口、事件处理器等对外暴露的接口
4. **数据流追踪**：追踪数据在模块间的流动路径，识别输入输出边界
5. **依赖分析**：梳理模块间的依赖关系，识别核心模块和外围模块

## 工作规范

- 基于提供的项目目录树和文件内容进行深入分析
- 只分析实际提供的代码，绝不臆造或假设不存在的代码
- 优先关注与测试需求直接相关的模块和函数
- 识别代码中的设计模式、架构风格和技术栈
- 提取有代表性的代码片段（不要太长，每个片段控制在 50 行以内）
- 如果代码量过大，聚焦在最核心、最关键的模块上

## 输出格式要求

请严格按照以下 JSON 格式输出：
{
    "modules": [
        {"name": "模块名称", "path": "模块路径"},
        ...
    ],
    "code_snippets": [
        {"file": "文件路径", "code": "代码片段", "description": "代码功能说明"},
        ...
    ],
    "dependencies": ["模块A依赖模块B", ...],
    "api_endpoints": [
        {"method": "GET/POST/...", "path": "/api/xxx", "description": "接口说明"},
        ...
    ],
    "logic_summary": "对项目核心业务逻辑的整体解析"
}

注意事项：
- modules 列出所有与测试相关的关键模块
- code_snippets 提供最能体现业务逻辑的代码片段
- dependencies 描述模块间的实际依赖关系
- api_endpoints 列出所有发现的 API 接口（如果有的话）
- logic_summary 用 2-3 段文字总结核心业务逻辑
- 所有描述使用中文"""

    def execute(self, input_data: dict) -> dict:
        """Extract code context relevant to test requirements.

        Args:
            input_data: Dictionary with keys:
                - requirement (dict): Structured test requirement from RequirementAnalyst
                - project_tree (str): Project directory tree
                - code_files (dict): Mapping of file paths to file contents

        Returns:
            Dictionary matching CodeContext schema.
        """
        requirement = input_data.get("requirement", {})
        project_tree = input_data.get("project_tree", "")
        code_files = input_data.get("code_files", {})

        # Format code files for the prompt
        code_contents = []
        for file_path, content in code_files.items():
            code_contents.append(f"### 文件: {file_path}\n```\n{content}\n```")
        all_code = "\n\n".join(code_contents)

        # Build requirement summary
        req_summary = requirement.get("test_objective", "")
        test_points = requirement.get("core_test_points", [])
        points_text = "\n".join(
            f"- {p.get('name', '')}: {p.get('criteria', '')}" for p in test_points
        )

        user_prompt = f"""请分析以下代码库，提取与测试需求相关的代码上下文。

## 测试需求概要
{req_summary}

## 核心测试点
{points_text}

## 项目目录结构
```
{project_tree}
```

## 源代码文件内容
{all_code}

请按照系统提示中的 JSON 格式输出代码分析结果。只分析实际提供的代码，不要臆造不存在的代码。"""

        result = self.llm.chat_json(self.system_prompt, user_prompt, temperature=0.2)
        return result
