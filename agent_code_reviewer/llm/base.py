"""Base LLM interface."""
from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstract base class for LLM backends."""

    def __init__(self):
        """Initialize token usage counters."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all calls."""
        return self.total_prompt_tokens + self.total_completion_tokens

    def reset_token_counts(self) -> None:
        """Reset token usage counters to zero."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def get_token_summary(self) -> dict:
        """Get token usage summary."""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Send a chat completion request and return the response text.

        Args:
            system_prompt: The system instructions for the model.
            user_prompt: The user message / task description.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            The model's text response.
        """
        pass

    @abstractmethod
    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        """Send a chat request expecting JSON response. Returns parsed dict.

        Args:
            system_prompt: The system instructions for the model.
            user_prompt: The user message / task description.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            Parsed JSON as a dictionary.
        """
        pass
