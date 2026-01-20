"""Abstract AI provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIProvider(ABC):
    """Abstract base class for AI model providers."""

    def __init__(self, model_id: str):
        """
        Initialize the AI provider.

        Args:
            model_id: The model identifier
        """
        self.model_id = model_id

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
        enable_caching: bool = True,
        enable_streaming: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a chat request to the AI model.

        Args:
            system_prompt: System instructions for the model
            messages: Conversation history
            tools: Available tools the model can use
            max_tokens: Maximum tokens in response
            enable_caching: Enable prompt caching
            enable_streaming: Enable streaming responses

        Returns:
            Response dictionary with content and usage info
        """
        pass

    @abstractmethod
    def summarize(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a summary of the conversation.

        Args:
            messages: Conversation history to summarize
            max_tokens: Maximum tokens for summary

        Returns:
            Summary text
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if this provider supports streaming responses."""
        pass

    @abstractmethod
    def supports_caching(self) -> bool:
        """Check if this provider supports prompt caching."""
        pass

    @abstractmethod
    def supports_token_tracking(self) -> bool:
        """Check if this provider supports token usage tracking."""
        pass

    @staticmethod
    @abstractmethod
    def list_available_models(**kwargs) -> List[Dict[str, Any]]:
        """
        List available models for this provider.

        Returns:
            List of model info dictionaries
        """
        pass

    @staticmethod
    @abstractmethod
    def get_provider_name() -> str:
        """Get the display name of this provider."""
        pass
