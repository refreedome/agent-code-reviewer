"""LLM backend abstractions."""
from agent_code_reviewer.llm.base import BaseLLM
from agent_code_reviewer.llm.qwen import QwenLLM

__all__ = ["BaseLLM", "QwenLLM"]
