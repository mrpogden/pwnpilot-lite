"""Manager for autonomous mode operations."""

import time
from typing import Optional


class AutonomousManager:
    """Manages autonomous mode state and limits."""

    def __init__(
        self,
        max_iterations: Optional[int] = None,
        max_tokens: Optional[int] = None,
        iteration_delay: float = 2.0,
    ):
        """
        Initialize autonomous manager.

        Args:
            max_iterations: Maximum iterations before pausing (None = unlimited)
            max_tokens: Maximum tokens to spend before pausing (None = unlimited)
            iteration_delay: Delay in seconds between iterations (default: 2.0)
        """
        self.active = False
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.iteration_delay = iteration_delay

        self.iterations = 0
        self.tokens_used = 0
        self.pause_requested = False
        self.last_iteration_time = 0.0

    def start(self) -> None:
        """Start autonomous mode."""
        self.active = True
        self.iterations = 0
        self.tokens_used = 0
        self.pause_requested = False

    def pause(self) -> None:
        """Request pause of autonomous mode."""
        self.pause_requested = True

    def stop(self) -> None:
        """Stop autonomous mode."""
        self.active = False
        self.pause_requested = False

    def increment_iteration(self) -> None:
        """Increment iteration counter and enforce rate limiting."""
        if self.active:
            self.iterations += 1

            # Enforce rate limiting between iterations
            if self.last_iteration_time > 0:
                elapsed = time.time() - self.last_iteration_time
                if elapsed < self.iteration_delay:
                    sleep_time = self.iteration_delay - elapsed
                    time.sleep(sleep_time)

            self.last_iteration_time = time.time()

    def add_tokens(self, token_count: int) -> None:
        """Add to token counter."""
        if self.active:
            self.tokens_used += token_count

    def should_continue(self) -> bool:
        """Check if autonomous mode should continue."""
        if not self.active:
            return False

        if self.pause_requested:
            return False

        if self.max_iterations and self.iterations >= self.max_iterations:
            return False

        if self.max_tokens and self.tokens_used >= self.max_tokens:
            return False

        return True

    def get_status(self) -> str:
        """Get current autonomous mode status."""
        if not self.active:
            return "Autonomous mode: Inactive"

        lines = ["🤖 Autonomous Mode Active"]

        # Iteration status
        if self.max_iterations:
            lines.append(f"   Iterations: {self.iterations}/{self.max_iterations}")
        else:
            lines.append(f"   Iterations: {self.iterations} (unlimited)")

        # Token status
        if self.max_tokens:
            lines.append(f"   Tokens: {self.tokens_used:,}/{self.max_tokens:,}")
        else:
            lines.append(f"   Tokens: {self.tokens_used:,} (unlimited)")

        # Pause status
        if self.pause_requested:
            lines.append("   Status: ⏸️  Pause requested")

        lines.append("\n   Type /prompt to return to prompt mode")

        return "\n".join(lines)

    def get_stop_reason(self) -> str:
        """Get reason why autonomous mode stopped."""
        if self.pause_requested:
            return "User requested pause"

        if self.max_iterations and self.iterations >= self.max_iterations:
            return f"Maximum iterations reached ({self.max_iterations})"

        if self.max_tokens and self.tokens_used >= self.max_tokens:
            return f"Maximum tokens reached ({self.max_tokens:,})"

        return "Unknown reason"
