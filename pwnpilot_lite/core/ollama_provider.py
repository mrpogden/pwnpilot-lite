"""Ollama AI provider implementation."""

import json
import re
import time
from typing import Any, Dict, List

import requests

from .ai_provider import AIProvider


class OllamaProvider(AIProvider):
    """Ollama implementation of AI provider."""

    def __init__(self, model_id: str, ollama_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.

        Args:
            model_id: The Ollama model name
            ollama_url: URL of the Ollama server
        """
        super().__init__(model_id)
        self.ollama_url = ollama_url

    def chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
        enable_caching: bool = True,
        enable_streaming: bool = True,
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama."""
        # Build system prompt with tool instructions
        full_system_prompt = self._build_system_prompt(system_prompt, tools)

        # Convert messages to Ollama format
        ollama_messages = self._build_ollama_messages(full_system_prompt, messages)

        # Make API call
        payload = {
            "model": self.model_id,
            "messages": ollama_messages,
            "stream": False,
        }

        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()

        # Parse response content
        raw_content = result.get("message", {}).get("content", "")

        # Extract tool blocks from response
        tool_blocks, cleaned_text = self._parse_tool_blocks(raw_content)

        # Build content blocks
        blocks = []
        if cleaned_text:
            blocks.append({"type": "text", "text": cleaned_text})
        blocks.extend(tool_blocks)

        # Print text blocks (since Ollama doesn't support streaming in this implementation)
        for block in blocks:
            if block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    print(f"\n🤖 {text}\n")

        return {
            "content": blocks,
            "usage": {},  # Ollama doesn't provide token usage
            "stop_reason": "end_turn"
        }

    def _build_system_prompt(self, system_prompt: str, tools: List[Dict[str, Any]]) -> str:
        """Build system prompt with tool definitions."""
        if not tools:
            return system_prompt

        tool_lines = []
        for tool in tools:
            name = tool.get("name", "")
            desc = tool.get("description", "")
            if name:
                tool_lines.append(f"- {name}: {desc}".strip())

        tool_section = "\n".join(tool_lines)
        instructions = (
            "\n\nAvailable tools:\n"
            f"{tool_section}\n\n"
            "To request a tool, output a JSON object in a code block with this format:\n"
            "```json\n"
            "{\"tool_use\": {\"name\": \"TOOL_NAME\", \"arguments\": {\"key\": \"value\"}}}\n"
            "```\n"
            "You may include normal text, but tool requests must follow this format and use only listed tools. "
            "Request only one tool at a time and wait for its output before proposing another."
        )
        return system_prompt + instructions

    def _build_ollama_messages(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Convert messages to Ollama format."""
        ollama_messages: List[Dict[str, str]] = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                parts: List[str] = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        parts.append(f"Tool result: {block.get('content', '')}")
                    elif isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    else:
                        parts.append(str(block))
                content = "\n".join([p for p in parts if p])
            else:
                content = str(content)
            ollama_messages.append({"role": role, "content": content})

        return ollama_messages

    def _parse_tool_blocks(self, content: str) -> tuple:
        """Parse tool request blocks from Ollama response."""
        if not content:
            return [], ""

        tool_blocks: List[Dict[str, Any]] = []
        cleaned = content
        counter = 0

        # Look for JSON code blocks
        code_block_re = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)
        for match in code_block_re.finditer(content):
            payload = match.group(1).strip()
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue

            tool_block = self._normalize_tool_block(obj, counter)
            if tool_block:
                tool_blocks.append(tool_block)
                cleaned = cleaned.replace(match.group(0), "").strip()
                counter += 1

        # Fallback: check if entire content is JSON
        if not tool_blocks:
            stripped = content.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    obj = None
                tool_block = self._normalize_tool_block(obj, counter) if obj else None
                if tool_block:
                    tool_blocks.append(tool_block)
                    cleaned = ""

        return tool_blocks, cleaned

    def _normalize_tool_block(self, obj: Dict[str, Any], counter: int) -> Dict[str, Any]:
        """Normalize a tool request object to standard format."""
        if not isinstance(obj, dict):
            return None

        if "tool_use" in obj and isinstance(obj["tool_use"], dict):
            inner = obj["tool_use"]
            name = inner.get("name") or inner.get("tool_name")
            args = inner.get("arguments") or inner.get("input") or {}
        else:
            name = obj.get("name")
            args = obj.get("arguments") or obj.get("input") or {}

        if not name:
            return None

        return {
            "type": "tool_use",
            "id": f"ollama-{int(time.time() * 1000)}-{counter}",
            "name": name,
            "input": args,
        }

    def summarize(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 2048,
    ) -> str:
        """Generate a summary of the conversation."""
        summary_prompt = (
            "Summarize this penetration testing session concisely. Include:\n"
            "1. Target(s) scanned or tested\n"
            "2. Tools used and key findings\n"
            "3. Vulnerabilities or issues discovered\n"
            "4. Current status and next steps\n\n"
            "Be extremely concise - aim for 200-300 words maximum. "
            "Focus only on actionable findings and critical information."
        )

        summary_messages = messages.copy()
        summary_messages.append({"role": "user", "content": summary_prompt})

        try:
            ollama_messages = self._build_ollama_messages(
                "You are a security assistant that creates concise summaries of penetration testing sessions.",
                summary_messages
            )

            payload = {
                "model": self.model_id,
                "messages": ollama_messages,
                "stream": False,
            }

            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()

            return result.get("message", {}).get("content", "").strip()
        except Exception as exc:
            print(f"⚠️  Summarization failed: {exc}")
            return ""

    def supports_streaming(self) -> bool:
        """Ollama doesn't support streaming in this implementation."""
        return False

    def supports_caching(self) -> bool:
        """Ollama doesn't support prompt caching."""
        return False

    def supports_token_tracking(self) -> bool:
        """Ollama doesn't provide token usage."""
        return False

    @staticmethod
    def list_available_models(ollama_url: str = "http://localhost:11434") -> List[Dict[str, Any]]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()

            models = []
            for m in data.get("models", []):
                name = m.get("name")
                if name:
                    models.append({
                        "type": "model",
                        "id": name,
                        "name": name,
                        "display": f"MODEL: {name}"
                    })
            return models
        except Exception as exc:
            print(f"⚠️  Could not list Ollama models: {exc}")
            return []

    @staticmethod
    def get_provider_name() -> str:
        """Get provider name."""
        return "Local (Ollama)"
