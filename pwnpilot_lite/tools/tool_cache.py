"""Tool result caching to avoid redundant command execution."""

import json
import time
from typing import Any, Dict, Optional, Tuple


class ToolResultCache:
    """Cache tool execution results to avoid redundant command execution."""

    def __init__(self, ttl_seconds: int = 300, enabled: bool = True):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 5 minutes)
            enabled: Whether caching is enabled
        """
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self.cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.hits = 0
        self.misses = 0
        self.bypasses = 0

    def _normalize_key(self, tool_name: str, payload: Dict[str, Any]) -> str:
        """
        Create a normalized cache key from tool name and payload.

        Sorts dict keys to ensure consistent keys regardless of argument order.
        """
        # Sort payload by keys for consistency
        sorted_payload = json.dumps(payload, sort_keys=True)
        return f"{tool_name}:{sorted_payload}"

    def get(self, tool_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and not expired.

        Returns None if cache miss or expired.
        """
        if not self.enabled:
            self.bypasses += 1
            return None

        cache_key = self._normalize_key(tool_name, payload)

        if cache_key not in self.cache:
            self.misses += 1
            return None

        result, timestamp = self.cache[cache_key]
        age = time.time() - timestamp

        # Check if expired
        if age > self.ttl_seconds:
            del self.cache[cache_key]
            self.misses += 1
            return None

        self.hits += 1
        return result

    def set(self, tool_name: str, payload: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Store a result in the cache."""
        if not self.enabled:
            return

        cache_key = self._normalize_key(tool_name, payload)
        self.cache[cache_key] = (result, time.time())

    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        print(f"🗑️  Cache cleared ({len(self.cache)} entries removed)")

    def clear_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        if not self.enabled:
            return 0

        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "enabled": self.enabled,
            "entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "bypasses": self.bypasses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }

    def format_stats(self) -> str:
        """Format cache statistics for display."""
        stats = self.get_stats()

        if not stats["enabled"]:
            return "🔄 Tool result caching: DISABLED"

        lines = ["🔄 Tool result cache statistics:"]
        lines.append(f"   Entries: {stats['entries']}")
        lines.append(f"   Hits: {stats['hits']}")
        lines.append(f"   Misses: {stats['misses']}")

        if stats['bypasses'] > 0:
            lines.append(f"   Bypasses: {stats['bypasses']}")

        total = stats['hits'] + stats['misses']
        if total > 0:
            lines.append(f"   Hit rate: {stats['hit_rate']:.1f}%")

        lines.append(f"   TTL: {stats['ttl_seconds']}s")

        return "\n".join(lines)
