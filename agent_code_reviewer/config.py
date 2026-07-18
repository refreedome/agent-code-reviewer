"""Configuration management."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class LLMConfig:
    """LLM backend configuration."""
    provider: str = "qwen"
    api_key: str = ""
    model: str = "qwen-plus"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class AnalysisConfig:
    """Code analysis configuration."""
    max_file_size: int = 50000
    include_extensions: list = None
    exclude_dirs: list = None

    def __post_init__(self):
        if self.include_extensions is None:
            self.include_extensions = [
                '.py', '.js', '.ts', '.java', '.go', '.rs',
                '.cpp', '.c', '.h', '.vue', '.jsx', '.tsx'
            ]
        if self.exclude_dirs is None:
            self.exclude_dirs = [
                'node_modules', '.git', '__pycache__', '.venv',
                'venv', 'dist', 'build', '.eggs'
            ]


@dataclass
class OutputConfig:
    """Output configuration."""
    format: str = "both"  # markdown, json, or both
    directory: str = "."


@dataclass
class Config:
    """Main configuration container."""
    llm: LLMConfig = None
    analysis: AnalysisConfig = None
    output: OutputConfig = None

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.analysis is None:
            self.analysis = AnalysisConfig()
        if self.output is None:
            self.output = OutputConfig()

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from YAML file.

        Searches for config in the following order:
        1. Explicit path provided via config_path
        2. config.yaml in current directory
        3. acr-config.yaml in current directory
        4. ~/.config/agent-code-reviewer/config.yaml
        """
        data = {}

        # Try to find config file
        if config_path:
            path = Path(config_path)
        else:
            candidates = [
                Path("config.yaml"),
                Path("acr-config.yaml"),
                Path.home() / ".config" / "agent-code-reviewer" / "config.yaml",
            ]
            path = None
            for candidate in candidates:
                if candidate.exists():
                    path = candidate
                    break

        if path and path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

        # Build config with env var fallbacks
        llm_data = data.get('llm', {})
        provider = llm_data.get('provider', 'qwen')

        provider_config = llm_data.get(provider, {})
        api_key = provider_config.get('api_key', '')

        # Env var fallback
        if not api_key:
            if provider == 'qwen':
                api_key = os.environ.get('DASHSCOPE_API_KEY', '')
            elif provider == 'openai':
                api_key = os.environ.get('OPENAI_API_KEY', '')

        base_url = provider_config.get('base_url', '')
        if not base_url:
            if provider == 'qwen':
                base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
            elif provider == 'openai':
                base_url = 'https://api.openai.com/v1'

        model = provider_config.get('model', '')
        if not model:
            if provider == 'qwen':
                model = 'qwen-plus'
            elif provider == 'openai':
                model = 'gpt-4'

        llm_config = LLMConfig(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

        analysis_data = data.get('analysis', {})
        analysis_config = AnalysisConfig(
            max_file_size=analysis_data.get('max_file_size', 50000),
            include_extensions=analysis_data.get('include_extensions'),
            exclude_dirs=analysis_data.get('exclude_dirs'),
        )

        output_data = data.get('output', {})
        output_config = OutputConfig(
            format=output_data.get('format', 'both'),
            directory=output_data.get('directory', '.'),
        )

        return cls(llm=llm_config, analysis=analysis_config, output=output_config)
