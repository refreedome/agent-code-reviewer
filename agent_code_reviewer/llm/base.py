"""Base LLM interface."""
from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstract base class for LLM backends."""

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
