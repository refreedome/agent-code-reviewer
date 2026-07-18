"""CLI interface for Agent Code Reviewer."""
import sys
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown

from agent_code_reviewer import __version__
from agent_code_reviewer.config import Config
from agent_code_reviewer.orchestrator.director import Director
from agent_code_reviewer.report.formatter import save_report


try:
    # Windows GBK terminal workaround
    console = Console(encoding="utf-8")
except Exception:
    console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="agent-code-reviewer")
def main():
    """Agent Code Reviewer - 多 Agent 协同代码测试与架构审查系统

    通过 4 个专业 AI Agent 串行协作，自动完成代码审查：
    需求分析 → 代码阅读 → 测试生成 → 安全审查
    """
    pass


@main.command()
@click.argument("repo_url")
@click.argument("requirement")
@click.option("--config", "config_path", default=None, help="配置文件路径")
@click.option("--output-dir", "-o", default=".", help="报告输出目录")
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["markdown", "json", "both"]),
    default="both",
    help="报告输出格式",
)
def review(repo_url: str, requirement: str, config_path: str, output_dir: str, output_format: str):
    """对 GitHub 仓库执行代码审查

    REPO_URL     GitHub 仓库地址，例如 https://github.com/user/repo
    REQUIREMENT  测试需求描述，例如 "请帮我测试用户注册模块"
    """
    # Banner
    console.print(Panel.fit(
        "[bold cyan]Agent Code Reviewer[/bold cyan] v" + __version__,
        subtitle="多 Agent 协同代码测试与架构审查系统",
    ))

    # Load config
    try:
        config = Config.load(config_path)
    except Exception as e:
        console.print(f"[red]❌ 配置加载失败: {e}[/red]")
        sys.exit(1)

    # Override output config from CLI args
    config.output.directory = output_dir
    config.output.format = output_format

    # Validate API key
    if not config.llm.api_key:
        console.print("[red]❌ 未配置 API Key！[/red]")
        console.print("请通过以下方式之一配置：")
        console.print("  1. 设置环境变量: export DASHSCOPE_API_KEY=your_key")
        console.print("  2. 创建 config.yaml 配置文件（运行 [cyan]acr init[/cyan] 生成模板）")
        sys.exit(1)

    # Display info
    console.print(f"\n[bold]📦 仓库:[/bold] {repo_url}")
    console.print(f"[bold]📝 需求:[/bold] {requirement}")
    console.print(f"[bold]🤖 模型:[/bold] {config.llm.model} ({config.llm.provider})")
    console.print()

    # Initialize director
    director = Director(config)

    # Run pipeline with progress display
    stages = {
        "clone": "📥 克隆仓库",
        "requirement": "📋 需求分析",
        "code_reading": "🔍 代码阅读",
        "testing": "🧪 测试生成",
        "review": "🛡️ 安全审查",
        "cleanup": "🧹 清理资源",
        "done": "✅ 完成",
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("准备开始...", total=None)

        def on_progress(stage: str, message: str):
            description = stages.get(stage, stage)
            progress.update(task, description=f"{description}: {message}")

        try:
            report = director.run(
                user_requirement=requirement,
                repo_url=repo_url,
                progress_callback=on_progress,
            )
        except Exception as e:
            console.print(f"\n[red]❌ 审查过程出错: {e}[/red]")
            sys.exit(1)

    # Save report
    console.print("\n[bold]💾 保存报告...[/bold]")
    try:
        saved_files = save_report(report, config.output.directory, config.output.format)
        for f in saved_files:
            console.print(f"  [green]✓[/green] {f}")
    except Exception as e:
        console.print(f"[red]❌ 报告保存失败: {e}[/red]")
        sys.exit(1)

    # Print summary
    console.print()
    _print_summary(report)
    console.print()


@main.command()
def init():
    """初始化配置文件

    在当前目录生成 config.yaml 模板文件。
    """
    target = Path("config.yaml")
    if target.exists():
        console.print(f"[yellow]⚠️  config.yaml 已存在，是否覆盖？[y/N][/yellow]")
        if not click.confirm("覆盖", default=False):
            console.print("已取消。")
            return

    # Find the example config
    example_paths = [
        Path(__file__).parent.parent / "config.example.yaml",
        Path("config.example.yaml"),
    ]
    example_content = None
    for p in example_paths:
        if p.exists():
            example_content = p.read_text(encoding='utf-8')
            break

    if not example_content:
        # Inline fallback
        example_content = _get_default_config()

    target.write_text(example_content, encoding='utf-8')
    console.print(f"[green]✅ 已创建 config.yaml[/green]")
    console.print("请编辑配置文件，填入你的 API Key。")


def _print_summary(report) -> None:
    """Print a summary table of the review report."""
    table = Table(title="📊 审查报告摘要", show_header=True, header_style="bold cyan")
    table.add_column("维度", style="bold")
    table.add_column("结果")

    # Requirement summary
    req = report.requirement
    table.add_row(
        "📋 测试需求",
        f"目标: {req.test_objective[:80]}...\n"
        f"测试点: {len(req.core_test_points)} 个 | "
        f"异常场景: {len(req.exception_scenarios)} 个 | "
        f"边界条件: {len(req.boundary_conditions)} 个",
    )

    # Code context summary
    ctx = report.code_context
    table.add_row(
        "🔍 代码分析",
        f"模块: {len(ctx.modules)} 个 | "
        f"代码片段: {len(ctx.code_snippets)} 个 | "
        f"API 接口: {len(ctx.api_endpoints)} 个",
    )

    # Test script summary
    ts = report.test_script
    table.add_row(
        "🧪 测试脚本",
        f"脚本文件: {len(ts.scripts)} 个 | "
        f"依赖包: {len(ts.dependencies)} 个",
    )

    # Security review summary
    sr = report.security_review
    table.add_row(
        "🛡️ 安全审查",
        f"高危漏洞: {len(sr.high_risks)} 个 | "
        f"代码异味: {len(sr.code_smells)} 个",
    )

    console.print(table)


def _get_default_config() -> str:
    """Return default config YAML as fallback."""
    return """# Agent Code Reviewer Configuration

llm:
  provider: qwen
  qwen:
    api_key: ""  # 或设置环境变量 DASHSCOPE_API_KEY
    model: "qwen-plus"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  openai:
    api_key: ""
    model: "gpt-4"
  custom:
    api_key: ""
    model: ""
    base_url: ""

analysis:
  max_file_size: 50000
  include_extensions:
    - .py
    - .js
    - .ts
    - .java
    - .go
    - .rs
    - .cpp
    - .c
    - .h
    - .vue
    - .jsx
    - .tsx
  exclude_dirs:
    - node_modules
    - .git
    - __pycache__
    - .venv
    - venv
    - dist
    - build
    - .eggs

output:
  format: both
  directory: "."
"""


if __name__ == "__main__":
    main()
