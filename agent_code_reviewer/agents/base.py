"""Base agent interface."""
from abc import ABC, abstractmethod
from agent_code_reviewer.llm.base import BaseLLM


class BaseAgent(ABC):
    """Abstract base class for all agents in the multi-agent system.

    Each agent wraps an LLM backend and provides a specialized
    system prompt and execute method for its role in the pipeline.
    """

    def __init__(self, llm: BaseLLM):
        """Initialize agent with an LLM backend.

        Args:
            llm: The LLM backend to use for inference.
        """
        self.llm = llm

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent display name."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt that defines this agent's role and behavior."""
        pass

    @abstractmethod
    def execute(self, input_data: dict) -> dict:
        """Execute the agent's task.

        Args:
            input_data: Dictionary containing the input data for this agent.

        Returns:
            Dictionary containing the agent's output.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
