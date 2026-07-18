# 🤖 Agent Code Reviewer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License">
  <img src="https://img.shields.io/badge/LLM-Qwen%20%7C%20GPT--4-orange?logo=openai" alt="LLM Support">
</p>

<p align="center">
  <strong>多 Agent 协同代码测试与架构审查系统</strong><br>
  Multi-Agent Collaborative Code Testing & Architecture Review System
</p>

---

## 📖 概述

Agent Code Reviewer 是一个基于多 Agent 协作的智能代码审查工具。它接收 GitHub 仓库 URL，自动克隆代码，通过 4 个专业 LLM Agent 串行协作完成全面的代码审查，最终输出结构化的测试报告和安全审查报告。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Director (编排器)                            │
│                  负责流程编排、Agent 调度与结果汇总                      │
└──────┬──────────────┬──────────────┬──────────────┬────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│  Agent 1 │  │   Agent 2    │  │  Agent 3 │  │   Agent 4    │
│ 需求分析师 │→│  代码阅读专家  │→│ 测试工程师 │→│ 安全审查员    │
│          │  │              │  │          │  │              │
│ 解析需求  │  │  提取代码上下文│  │ 生成测试  │  │ 安全&架构审查 │
│ 生成大纲  │  │  识别依赖/API │  │ 编写脚本  │  │ 识别漏洞     │
└──────────┘  └──────────────┘  └──────────┘  └──────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      综合审查报告 (Report)                           │
│              Markdown + JSON 双格式输出                                │
└─────────────────────────────────────────────────────────────────────┘
```

**串行流水线**：每个 Agent 的输出作为下一个 Agent 的输入，形成完整的信息传递链。

## ✨ 特性

- 🤖 **4 个专业 Agent 协作** — 需求分析、代码阅读、测试生成、安全审查各司其职
- 🔗 **GitHub 集成** — 一键克隆仓库，自动提取项目结构和源代码
- 📋 **结构化报告** — 输出 Markdown + JSON 双格式的综合审查报告
- ⚙️ **灵活配置** — 支持通义千问（Qwen）、OpenAI、自定义 OpenAI 兼容端点
- 🖥️ **CLI 工具** — 简洁的命令行界面，Rich 进度展示
- 📦 **Python 库** — 可作为 Python 库集成到现有工作流
- 🔒 **安全优先** — 专门的安全审查 Agent 检测漏洞和代码异味

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/refreedome/agent-code-reviewer.git
cd agent-code-reviewer

# 安装依赖（开发模式）
pip install -e .
```

### 配置 API Key

**方式一：环境变量（推荐）**

```bash
# 通义千问 (DashScope)
export DASHSCOPE_API_KEY=your_api_key_here

# 或者 OpenAI
export OPENAI_API_KEY=your_api_key_here
```

**方式二：配置文件**

```bash
# 生成配置模板
acr init

# 编辑 config.yaml，填入 API Key
vim config.yaml
```

### 使用

```bash
# 基本用法：测试用户注册模块
acr review https://github.com/user/repo "请帮我测试用户注册模块，重点关注并发和异常处理"

# 全面安全审查
acr review https://github.com/user/repo "全面审查代码安全性和架构" --format json

# 指定输出目录
acr review https://github.com/user/repo "测试支付模块的核心流程" -o ./reports -f both

# 使用自定义配置文件
acr review https://github.com/user/repo "测试 API 接口" --config ./my-config.yaml
```

## 📖 CLI 命令

### `acr review`

对 GitHub 仓库执行代码审查。

```
acr review <REPO_URL> <REQUIREMENT> [OPTIONS]
```

| 参数/选项 | 说明 |
|-----------|------|
| `REPO_URL` | GitHub 仓库地址（必填） |
| `REQUIREMENT` | 测试需求描述（必填） |
| `--config` | 配置文件路径 |
| `-o, --output-dir` | 报告输出目录（默认当前目录） |
| `-f, --format` | 输出格式：`markdown` / `json` / `both`（默认 `both`） |

### `acr init`

在当前目录生成 `config.yaml` 配置模板。

## ⚙️ 配置指南

配置文件 `config.yaml` 支持以下配置项：

### LLM 后端配置

```yaml
llm:
  # 后端选择：qwen（通义千问）、openai、custom（自定义兼容端点）
  provider: qwen

  qwen:
    api_key: ""     # 或通过 DASHSCOPE_API_KEY 环境变量设置
    model: "qwen-plus"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

  openai:
    api_key: ""     # 或通过 OPENAI_API_KEY 环境变量设置
    model: "gpt-4"

  custom:
    api_key: ""
    model: ""
    base_url: ""    # 任意 OpenAI 兼容 API 端点
```

### 代码分析配置

```yaml
analysis:
  max_file_size: 50000          # 单文件最大分析字符数
  include_extensions:           # 需要分析的文件扩展名
    - .py
    - .js
    - .ts
  exclude_dirs:                 # 排除的目录
    - node_modules
    - .git
    - __pycache__
```

### 输出配置

```yaml
output:
  format: both    # markdown / json / both
  directory: "."  # 报告输出目录
```

## 🏛️ Agent 架构详解

### Agent 1: 需求分析师 (Requirement Analyst)

将用户的自然语言测试需求解析为结构化的测试大纲：
- 提取测试目标和核心测试点
- 为每个测试点定义验收标准
- 识别异常场景和边界条件
- 输出 JSON 格式的结构化需求

### Agent 2: 代码阅读专家 (Code Reader)

从代码库中提取与测试需求相关的代码上下文：
- 分析项目目录结构和模块划分
- 提取核心代码片段和关键函数
- 识别模块依赖关系和数据流向
- 梳理 API 接口定义

### Agent 3: 测试工程师 (Tester)

根据需求和代码上下文生成高质量测试脚本：
- 制定全面的测试策略
- 生成可直接运行的 pytest 测试脚本
- 覆盖正常路径、边界值、异常注入、并发场景
- 指定测试依赖和运行说明

### Agent 4: 安全与架构审查员 (Reviewer)

深度代码审查，识别安全和架构问题：
- 检测安全漏洞（SQL 注入、XSS、认证绕过等）
- 识别代码异味（过长函数、深层嵌套、职责违反等）
- 评估整体架构质量
- 提供具体可操作的修复建议

## 🔌 Python 库集成

Agent Code Reviewer 可以作为 Python 库集成到你的工作流中：

```python
from agent_code_reviewer.config import Config
from agent_code_reviewer.orchestrator.director import Director
from agent_code_reviewer.report.formatter import save_report

# 加载配置
config = Config.load("config.yaml")

# 创建 Director 并运行
director = Director(config)
report = director.run(
    user_requirement="测试用户注册模块的并发安全性",
    repo_url="https://github.com/user/repo",
)

# 保存报告
files = save_report(report, output_dir="./reports", output_format="both")
print(f"报告已保存: {files}")

# 访问报告内容
print(report.requirement.test_objective)
print(report.security_review.high_risks)
```

### 自定义 Agent

```python
from agent_code_reviewer.llm.qwen import QwenLLM
from agent_code_reviewer.agents.base import BaseAgent

class MyCustomAgent(BaseAgent):
    @property
    def name(self):
        return "自定义 Agent"

    @property
    def system_prompt(self):
        return "你是一个..."

    def execute(self, input_data: dict) -> dict:
        return self.llm.chat_json(self.system_prompt, "...")

# 使用自定义 Agent
llm = QwenLLM(config.llm)
agent = MyCustomAgent(llm)
result = agent.execute({"key": "value"})
```

## 💻 IDE 集成

### VS Code Tasks

在 `.vscode/tasks.json` 中添加：

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Code Review",
      "type": "shell",
      "command": "acr",
      "args": [
        "review",
        "${input:repoUrl}",
        "${input:requirement}",
        "-o", "${workspaceFolder}/reports"
      ],
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "repoUrl",
      "type": "promptString",
      "description": "GitHub 仓库 URL"
    },
    {
      "id": "requirement",
      "type": "promptString",
      "description": "测试需求描述"
    }
  ]
}
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit — 提交前自动触发代码审查
REPO_URL=$(git remote get-url origin 2>/dev/null)
if [ -n "$REPO_URL" ]; then
  echo "🔍 Running code review before commit..."
  acr review "$REPO_URL" "检查最新提交的代码质量" -o ./reports -f markdown
fi
```

## 🛠️ 开发指南

### 项目结构

```
agent-code-reviewer/
├── pyproject.toml                 # 项目配置与依赖
├── config.example.yaml            # 配置模板
├── README.md                      # 项目文档
└── agent_code_reviewer/
    ├── __init__.py
    ├── __main__.py                # python -m 入口
    ├── cli.py                     # CLI 命令行界面
    ├── config.py                  # 配置管理
    ├── models/
    │   └── schemas.py             # 数据模型定义
    ├── llm/
    │   ├── base.py                # LLM 抽象基类
    │   └── qwen.py                # Qwen/DashScope 实现
    ├── agents/
    │   ├── base.py                # Agent 抽象基类
    │   ├── requirement_analyst.py # 需求分析师
    │   ├── code_reader.py         # 代码阅读专家
    │   ├── tester.py              # 测试工程师
    │   └── reviewer.py            # 安全审查员
    ├── integrations/
    │   └── github.py              # GitHub 仓库加载器
    ├── orchestrator/
    │   └── director.py            # 流水线编排器
    └── report/
        └── formatter.py           # 报告格式化输出
```

### 本地开发

```bash
# 克隆项目
git clone https://github.com/refreedome/agent-code-reviewer.git
cd agent-code-reviewer

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行
acr review <repo_url> "<requirement>"
```

## 📄 License

MIT License © 2024 Agent Code Reviewer

---

<p align="center">
  <sub>Built with ❤️ using multi-agent architecture and LLM technology</sub>
</p>
