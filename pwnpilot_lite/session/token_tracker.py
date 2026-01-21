"""Token tracking and cost calculation for AI model usage."""

from typing import Any, Dict, Optional


class TokenTracker:
    """Track token usage and costs across the session."""

    # Pricing per 1K tokens (as of Jan 2025) - varies by region
    PRICING = {
        "claude-3-5-sonnet": {
            "input": 0.003,
            "output": 0.015,
            "cache_write": 0.00375,
            "cache_read": 0.0003,
        },
        "claude-3-5-haiku": {
            "input": 0.001,
            "output": 0.005,
            "cache_write": 0.00125,
            "cache_read": 0.0001,
        },
        "claude-3-opus": {
            "input": 0.015,
            "output": 0.075,
            "cache_write": 0.01875,
            "cache_read": 0.0015,
        },
    }

    # Context limits per model
    CONTEXT_LIMITS = {
        "claude-3-5-sonnet": 200000,
        "claude-3-5-haiku": 200000,
        "claude-3-opus": 200000,
    }

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_cache_read_tokens = 0
        self.request_count = 0

        # Detect model family for pricing
        self.model_family = self._detect_model_family(model_id)

        # Track which warning levels have been shown
        self.warnings_shown = set()
        self.summarization_performed = False

    def _detect_model_family(self, model_id: str) -> Optional[str]:
        """Detect which model family this is for pricing."""
        lower_id = model_id.lower()
        if "sonnet" in lower_id:
            return "claude-3-5-sonnet"
        elif "haiku" in lower_id:
            return "claude-3-5-haiku"
        elif "opus" in lower_id:
            return "claude-3-opus"
        return None

    def update(self, usage: Dict[str, Any]) -> None:
        """Update token counts from a Bedrock response."""
        self.request_count += 1
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)

        # Cache metrics (Bedrock specific)
        self.total_cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
        self.total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)

    def calculate_cost(self) -> float:
        """Calculate total cost in USD."""
        if not self.model_family or self.model_family not in self.PRICING:
            return 0.0

        pricing = self.PRICING[self.model_family]

        # Regular input tokens (not cached)
        regular_input = self.total_input_tokens - self.total_cache_read_tokens
        cost = (regular_input / 1000.0) * pricing["input"]

        # Output tokens
        cost += (self.total_output_tokens / 1000.0) * pricing["output"]

        # Cache creation tokens
        cost += (self.total_cache_creation_tokens / 1000.0) * pricing["cache_write"]

        # Cache read tokens
        cost += (self.total_cache_read_tokens / 1000.0) * pricing["cache_read"]

        return cost

    def get_context_usage(self) -> float:
        """Get percentage of context window used."""
        if not self.model_family or self.model_family not in self.CONTEXT_LIMITS:
            return 0.0

        limit = self.CONTEXT_LIMITS[self.model_family]
        used = self.total_input_tokens + self.total_output_tokens
        return (used / limit) * 100.0

    def should_warn_context(self) -> bool:
        """Check if we should warn about context usage."""
        return self.get_context_usage() > 80.0

    def get_warning_level(self) -> Optional[str]:
        """Get current warning level based on context usage."""
        usage = self.get_context_usage()
        if usage >= 90.0:
            return "critical"
        elif usage >= 80.0:
            return "high"
        elif usage >= 70.0:
            return "medium"
        return None

    def should_show_warning(self) -> bool:
        """Check if a new warning should be displayed."""
        level = self.get_warning_level()
        if level and level not in self.warnings_shown:
            self.warnings_shown.add(level)
            return True
        return False

    def should_summarize(self) -> bool:
        """Check if context should be summarized (at 85% and not yet done)."""
        usage = self.get_context_usage()
        return usage >= 85.0 and not self.summarization_performed

    def reset_context_tracking(self) -> None:
        """
        Reset context tracking after summarization.

        This resets the input/output token totals to reflect reduced context,
        while preserving cache token counts (which are request-specific).
        The context is estimated based on summary + recent messages.
        """
        # Reset cumulative context tokens (not cache tokens)
        # Keep a small baseline for summary + recent messages (estimate ~2000 tokens)
        self.total_input_tokens = 2000
        self.total_output_tokens = 0

        # Reset warnings so they can trigger again if context grows
        self.warnings_shown.clear()

        # Mark that summarization was performed
        self.summarization_performed = True

    def format_summary(self, last_request_usage: Optional[Dict[str, Any]] = None) -> str:
        """Format a summary string for display."""
        lines = []

        if last_request_usage:
            lines.append("📊 Last request:")
            lines.append(f"   Input: {last_request_usage.get('input_tokens', 0):,} tokens")
            lines.append(f"   Output: {last_request_usage.get('output_tokens', 0):,} tokens")

            cache_read = last_request_usage.get('cache_read_input_tokens', 0)
            cache_create = last_request_usage.get('cache_creation_input_tokens', 0)

            if cache_read > 0:
                lines.append(f"   💚 Cache read: {cache_read:,} tokens (90% savings!)")
            if cache_create > 0:
                lines.append(f"   📝 Cache created: {cache_create:,} tokens")

        lines.append(f"\n📈 Session totals ({self.request_count} requests):")
        lines.append(f"   Input: {self.total_input_tokens:,} tokens")
        lines.append(f"   Output: {self.total_output_tokens:,} tokens")

        if self.total_cache_read_tokens > 0:
            lines.append(f"   💚 Cache reads: {self.total_cache_read_tokens:,} tokens")
        if self.total_cache_creation_tokens > 0:
            lines.append(f"   📝 Cache created: {self.total_cache_creation_tokens:,} tokens")

        cost = self.calculate_cost()
        if cost > 0:
            lines.append(f"   💰 Est. cost: ${cost:.4f}")

        context_pct = self.get_context_usage()
        if context_pct > 0:
            lines.append(f"   🧠 Context: {context_pct:.1f}% used")

            # Progressive warnings
            warning_level = self.get_warning_level()
            if warning_level == "critical":
                lines.append(f"   🚨 CRITICAL: Context nearly full! Summarization strongly recommended.")
            elif warning_level == "high":
                lines.append(f"   ⚠️  HIGH: Context usage is high. Consider summarization.")
            elif warning_level == "medium":
                lines.append(f"   ℹ️  MEDIUM: Context usage increasing. Monitor usage.")

        return "\n".join(lines)
