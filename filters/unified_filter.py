#!/usr/bin/env python3
"""Unified filter pipeline for benchmark tests.

This module combines core safety filters into a single entry point.
It is intentionally lightweight and deterministic for local testing.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
import re
from typing import Dict, List


BLOCKED_PATTERNS = [
    r"googleapis",
    r"firebase",
    r"telemetry",
    r"tracking",
    r"analytics",
    r"pixel",
    r"http://",
    r"https://",
    r"\.doubleclick\.",
    r"\.facebook\.",
    r"\.tiktok\.",
    r"\.google\.",
    r"\.microsoft\.",
    r"api\.openai\.",
    r"anthropic\.com",
    r"huggingface\.co/api",
    r"amazonaws\.com",
    r"cloudflare\.com",
    r"\.ads\.",
    r"beacon",
    r"collect",
]

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"forget\s+everything\s+above",
    r"system\s*prompt",
    r"developer\s*mode",
    r"debug\s*mode",
    r"bypass",
    r"disable\s+filters",
]


@dataclass
class FilterResult:
    blocked: bool
    reasons: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class UnifiedFilter:
    """Single entry point that combines basic filters."""

    def __init__(self) -> None:
        self.blocked_count = 0
        self.total_checks = 0

    def _incident_mode(self) -> bool:
        return os.environ.get("GUARDIAN_MODE", "full").lower() == "incident"

    def _apply_pattern_set(self, text: str, patterns: List[str], label: str) -> FilterResult:
        matches = [p for p in patterns if re.search(p, text, re.IGNORECASE)]
        if matches:
            return FilterResult(
                blocked=True,
                reasons=[label],
                matched_patterns=matches,
            )
        return FilterResult(blocked=False)

    def apply(self, text: str) -> FilterResult:
        self.total_checks += 1

        if self._incident_mode():
            self.blocked_count += 1
            return FilterResult(blocked=True, reasons=["incident_mode"])

        result = self._apply_pattern_set(text, BLOCKED_PATTERNS, "blocked_patterns")
        if result.blocked:
            self.blocked_count += 1
            return result

        inj = self._apply_pattern_set(text, INJECTION_PATTERNS, "prompt_injection")
        if inj.blocked:
            self.blocked_count += 1
            return inj

        return FilterResult(blocked=False)

    def stats(self) -> Dict[str, float]:
        return {
            "total_checks": self.total_checks,
            "blocked_count": self.blocked_count,
            "block_rate": (self.blocked_count / self.total_checks * 100) if self.total_checks else 0.0,
        }
