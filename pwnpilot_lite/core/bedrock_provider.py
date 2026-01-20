"""AWS Bedrock AI provider implementation."""

import json
from typing import Any, Dict, List

import boto3
from botocore.config import Config

from .ai_provider import AIProvider


class BedrockProvider(AIProvider):
    """AWS Bedrock implementation of AI provider."""

    def __init__(self, model_id: str, region: str = "us-east-1"):
        """
        Initialize Bedrock provider.

        Args:
            model_id: The Bedrock model ID or inference profile ID
            region: AWS region
        """
        super().__init__(model_id)
        self.region = region

        # Initialize Bedrock clients
        cfg = Config(
            retries={"max_attempts": 5, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=120
        )
        self.bedrock = boto3.client("bedrock", region_name=region, config=cfg)
        self.runtime = boto3.client("bedrock-runtime", region_name=region, config=cfg)

    def chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
        enable_caching: bool = True,
        enable_streaming: bool = True,
    ) -> Dict[str, Any]:
        """Send a chat request to Bedrock."""
        if enable_streaming:
            return self._chat_streaming(
                system_prompt, messages, tools, max_tokens, enable_caching
            )
        else:
            return self._chat_non_streaming(
                system_prompt, messages, tools, max_tokens, enable_caching
            )

    def _chat_non_streaming(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
        enable_caching: bool,
    ) -> Dict[str, Any]:
        """Non-streaming chat."""
        # Build system blocks with cache control for prompt caching
        system_blocks = []
        if enable_caching:
            system_blocks.append({
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            })
        else:
            system_blocks = system_prompt

        body: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system_blocks,
        }

        # Add tools with cache control on the last tool
        if tools and enable_caching:
            tools_with_cache = tools.copy()
            if len(tools_with_cache) > 0:
                tools_with_cache[-1] = {
                    **tools_with_cache[-1],
                    "cache_control": {"type": "ephemeral"}
                }
            body["tools"] = tools_with_cache
        elif tools:
            body["tools"] = tools

        response = self.runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        return json.loads(response["body"].read())

    def _chat_streaming(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int,
        enable_caching: bool,
    ) -> Dict[str, Any]:
        """Streaming chat with real-time output."""
        # Build system blocks with cache control
        system_blocks = []
        if enable_caching:
            system_blocks.append({
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            })
        else:
            system_blocks = system_prompt

        body: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system_blocks,
        }

        # Add tools with cache control on the last tool
        if tools and enable_caching:
            tools_with_cache = tools.copy()
            if len(tools_with_cache) > 0:
                tools_with_cache[-1] = {
                    **tools_with_cache[-1],
                    "cache_control": {"type": "ephemeral"}
                }
            body["tools"] = tools_with_cache
        elif tools:
            body["tools"] = tools

        # Invoke with streaming
        response = self.runtime.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=json.dumps(body)
        )

        # Process the event stream
        content_blocks = []
        current_text_block = ""
        current_tool_block = None
        tool_input_buffer = ""
        usage = {}
        stop_reason = None

        print("\n🤖 ", end='', flush=True)

        try:
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                chunk_type = chunk.get('type')

                if chunk_type == 'message_start':
                    message = chunk.get('message', {})
                    usage = message.get('usage', {})

                elif chunk_type == 'content_block_start':
                    index = chunk.get('index', 0)
                    block = chunk.get('content_block', {})

                    if block.get('type') == 'text':
                        current_text_block = ""
                    elif block.get('type') == 'tool_use':
                        if current_text_block:
                            content_blocks.append({"type": "text", "text": current_text_block})
                            current_text_block = ""
                        print("\n", flush=True)
                        current_tool_block = {
                            "type": "tool_use",
                            "id": block.get('id'),
                            "name": block.get('name')
                        }
                        tool_input_buffer = ""

                elif chunk_type == 'content_block_delta':
                    delta = chunk.get('delta', {})
                    delta_type = delta.get('type')

                    if delta_type == 'text_delta':
                        text = delta.get('text', '')
                        current_text_block += text
                        print(text, end='', flush=True)

                    elif delta_type == 'input_json_delta':
                        partial_json = delta.get('partial_json', '')
                        tool_input_buffer += partial_json

                elif chunk_type == 'content_block_stop':
                    if current_text_block:
                        content_blocks.append({"type": "text", "text": current_text_block})
                        current_text_block = ""

                    if current_tool_block:
                        try:
                            tool_input = json.loads(tool_input_buffer) if tool_input_buffer else {}
                        except json.JSONDecodeError:
                            tool_input = {}
                        current_tool_block["input"] = tool_input
                        content_blocks.append(current_tool_block)
                        current_tool_block = None
                        tool_input_buffer = ""

                elif chunk_type == 'message_delta':
                    delta = chunk.get('delta', {})
                    stop_reason = delta.get('stop_reason')
                    usage_delta = chunk.get('usage', {})
                    if usage_delta:
                        usage.update(usage_delta)

                elif chunk_type == 'message_stop':
                    pass

        except Exception as exc:
            print(f"\n\n❌ Streaming error: {exc}", flush=True)
            raise

        print("\n", flush=True)

        return {
            "content": content_blocks,
            "usage": usage,
            "stop_reason": stop_reason
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
            response = self._chat_non_streaming(
                "You are a security assistant that creates concise summaries of penetration testing sessions.",
                summary_messages,
                tools=[],
                max_tokens=max_tokens,
                enable_caching=False
            )

            # Extract text from response
            content = response.get("content", [])
            summary_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    summary_parts.append(block.get("text", ""))

            return "\n".join(summary_parts).strip()
        except Exception as exc:
            print(f"⚠️  Summarization failed: {exc}")
            return ""

    def supports_streaming(self) -> bool:
        """Bedrock supports streaming."""
        return True

    def supports_caching(self) -> bool:
        """Bedrock supports prompt caching."""
        return True

    def supports_token_tracking(self) -> bool:
        """Bedrock supports token tracking."""
        return True

    @staticmethod
    def list_available_models(region: str = "us-east-1") -> List[Dict[str, Any]]:
        """List available Bedrock models and inference profiles."""
        cfg = Config(
            retries={"max_attempts": 5, "mode": "adaptive"},
            connect_timeout=10,
            read_timeout=120
        )
        bedrock = boto3.client("bedrock", region_name=region, config=cfg)

        models = []

        # List inference profiles
        try:
            paginator = bedrock.get_paginator("list_inference_profiles")
            for page in paginator.paginate():
                profiles = page.get("inferenceProfileSummaries", [])
                for profile in profiles:
                    profile_id = profile.get("inferenceProfileId")
                    name = profile.get("inferenceProfileName") or profile_id
                    if profile_id and "anthropic" in profile_id.lower():
                        models.append({
                            "type": "profile",
                            "id": profile_id,
                            "name": name,
                            "display": f"PROFILE: {name}"
                        })
        except Exception as exc:
            print(f"⚠️  Could not list inference profiles: {exc}")

        # List foundation models
        try:
            # Try paginated approach first
            try:
                paginator = bedrock.get_paginator("list_foundation_models")
                for page in paginator.paginate(byOutputModality="TEXT"):
                    model_list = page.get("modelSummaries", [])
                    for model in model_list:
                        model_id = model.get("modelId")
                        provider = model.get("providerName") or "unknown"
                        if model_id and "anthropic" in model_id.lower():
                            models.append({
                                "type": "model",
                                "id": model_id,
                                "name": model_id,
                                "provider": provider,
                                "display": f"MODEL: {model_id} ({provider})"
                            })
            except Exception as paginator_exc:
                # Some regions don't support pagination, fallback to direct call
                if "cannot be paginated" in str(paginator_exc).lower():
                    response = bedrock.list_foundation_models(byOutputModality="TEXT")
                    model_list = response.get("modelSummaries", [])
                    for model in model_list:
                        model_id = model.get("modelId")
                        provider = model.get("providerName") or "unknown"
                        if model_id and "anthropic" in model_id.lower():
                            models.append({
                                "type": "model",
                                "id": model_id,
                                "name": model_id,
                                "provider": provider,
                                "display": f"MODEL: {model_id} ({provider})"
                            })
                else:
                    raise
        except Exception as exc:
            print(f"⚠️  Could not list foundation models: {exc}")

        return models

    @staticmethod
    def get_provider_name() -> str:
        """Get provider name."""
        return "AWS Bedrock"
