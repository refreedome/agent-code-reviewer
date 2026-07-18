"""Reviewer agent - security vulnerability and architecture review."""
from agent_code_reviewer.agents.base import BaseAgent


class Reviewer(BaseAgent):
    """安全与架构审查员 Agent.

    负责对代码进行深度安全审查，识别安全漏洞和代码异味，
    评估整体架构质量并提供改进建议。
    """

    @property
    def name(self) -> str:
        return "安全与架构审查员"

    @property
    def system_prompt(self) -> str:
        return """你是一位资深的安全工程师和软件架构师，拥有多年代码安全审计和架构评审经验。你的职责是对代码进行深度审查，发现安全漏洞、代码异味和架构问题。

## 你的核心能力

1. **安全漏洞检测**：识别 SQL 注入、XSS 跨站脚本、CSRF、认证绕过、权限提升、敏感信息泄露、内存泄漏、缓冲区溢出等安全漏洞
2. **代码异味识别**：发现过长函数、深层嵌套、单一职责违反、魔法数字、重复代码、过度耦合、不当的异常处理等问题
3. **架构评估**：评估整体架构的合理性、可扩展性、可维护性和性能瓶颈
4. **修复建议**：为每个问题提供具体的、可操作的修复方案

## 审查维度

### 安全审查
- 输入验证：是否正确校验和清洗所有外部输入
- 认证授权：认证机制是否健全，权限控制是否严格
- 数据保护：敏感数据是否加密存储和传输
- 注入攻击：是否存在 SQL 注入、命令注入、XSS 等风险
- 依赖安全：第三方依赖是否存在已知漏洞
- 日志安全：是否在日志中泄露敏感信息

### 代码质量审查
- 函数复杂度：是否存在过长、过深的函数
- 异常处理：异常是否被正确捕获和处理，是否有静默吞异常
- 资源管理：文件句柄、网络连接、数据库连接是否正确释放
- 并发安全：共享资源是否有竞态条件、死锁风险
- 代码复用：是否存在大量重复代码

### 架构审查
- 分层合理性：是否遵循清晰的分层架构
- 模块耦合：模块间的依赖关系是否合理
- 扩展性：是否容易添加新功能或替换组件
- 错误处理策略：全局错误处理机制是否完善

## 输出格式要求

请严格按照以下 JSON 格式输出：
{
    "high_risks": [
        {
            "title": "漏洞/风险标题",
            "description": "详细描述问题和影响范围",
            "fix": "具体的修复方案和代码示例"
        },
        ...
    ],
    "code_smells": [
        {
            "title": "代码异味标题",
            "description": "描述问题现象和潜在影响",
            "suggestion": "改进建议"
        },
        ...
    ],
    "architecture_assessment": "整体架构评估，包括优点、不足和改进方向"
}

注意事项：
- high_risks 只列出真正有风险的问题，不要夸大
- code_smells 关注对代码可维护性有影响的问题
- architecture_assessment 用 2-4 段文字进行全面评估
- 修复建议要具体可操作，最好包含代码示例
- 如果没有发现问题，对应字段返回空数组
- 所有内容使用中文描述"""

    def execute(self, input_data: dict) -> dict:
        """Perform security and architecture review.

        Args:
            input_data: Dictionary with keys:
                - code_context (dict): Extracted code context from CodeReader
                - test_script (dict): Generated test scripts from Tester

        Returns:
            Dictionary matching SecurityReview schema.
        """
        code_context = input_data.get("code_context", {})
        test_script = input_data.get("test_script", {})

        # Format code context for prompt
        code_text = ""
        if code_context.get("logic_summary"):
            code_text += f"代码逻辑概要:\n{code_context['logic_summary']}\n\n"
        if code_context.get("modules"):
            code_text += "涉及模块:\n"
            for m in code_context.get("modules", []):
                code_text += f"- {m.get('name', '')} ({m.get('path', '')})\n"
            code_text += "\n"
        if code_context.get("code_snippets"):
            code_text += "核心代码片段:\n"
            for s in code_context.get("code_snippets", []):
                code_text += f"\n文件: {s.get('file', '')}\n```python\n{s.get('code', '')}\n```\n"
        if code_context.get("dependencies"):
            code_text += "\n模块依赖:\n"
            for d in code_context.get("dependencies", []):
                code_text += f"- {d}\n"
        if code_context.get("api_endpoints"):
            code_text += "\nAPI 接口:\n"
            for e in code_context.get("api_endpoints", []):
                code_text += f"- {e.get('method', '')} {e.get('path', '')}: {e.get('description', '')}\n"

        # Format test script info
        test_text = ""
        if test_script.get("strategy"):
            test_text += f"测试策略: {test_script['strategy']}\n\n"
        if test_script.get("scripts"):
            test_text += "测试脚本概要:\n"
            for s in test_script.get("scripts", []):
                test_text += f"- {s.get('filename', '')}: {s.get('description', '')}\n"

        user_prompt = f"""请对以下代码进行深度安全和架构审查。

## 代码上下文
{code_text}

## 测试脚本信息
{test_text}

请从安全漏洞、代码异味、架构质量三个维度进行全面审查，并按照系统提示中的 JSON 格式输出审查结果。"""

        result = self.llm.chat_json(self.system_prompt, user_prompt, temperature=0.2)
        return result
