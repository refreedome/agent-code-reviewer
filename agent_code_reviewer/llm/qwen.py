"""Qwen (DashScope) LLM backend via OpenAI-compatible API."""
import json
from typing import Optional
from openai import OpenAI
from agent_code_reviewer.llm.base import BaseLLM
from agent_code_reviewer.config import LLMConfig


class QwenLLM(BaseLLM):
    """Qwen LLM backend using OpenAI-compatible DashScope API.

    This backend works with any OpenAI-compatible API endpoint by
    configuring the base_url appropriately.
    """

    def __init__(self, config: LLMConfig):
        """Initialize Qwen LLM backend.

        Args:
            config: LLM configuration with api_key, base_url, and model.
        """
        super().__init__()
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model = config.model

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Send chat completion request.

        Args:
            system_prompt: System instructions.
            user_prompt: User message.
            temperature: Sampling temperature.

        Returns:
            Model response text.

        Raises:
            openai.OpenAIError: If the API request fails.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        # Track token usage from response
        if response.usage:
            self.total_prompt_tokens += response.usage.prompt_tokens
            self.total_completion_tokens += response.usage.completion_tokens

        return response.choices[0].message.content

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        """Send chat request expecting JSON response.

        Appends JSON formatting instructions to the system prompt,
        then attempts to parse the response as JSON with multiple
        fallback strategies.

        Args:
            system_prompt: System instructions.
            user_prompt: User message.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON dictionary. Falls back to {"raw_response": ..., "parse_error": True}
            if JSON parsing fails entirely.
        """
        system_with_json = (
            system_prompt
            + "\n\n【输出要求】请严格以 JSON 格式输出，不要包含 markdown 代码块标记或其他非 JSON 内容。"
        )

        raw = self.chat(system_with_json, user_prompt, temperature)

        # Try to extract JSON from the response
        cleaned = raw.strip()

        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (``` marker)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's a closing ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            # Return raw text wrapped in dict if all parsing fails
            return {"raw_response": raw, "parse_error": True}
