"""Data models and type contracts for HTTP brute-forcing and calibration."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


@dataclass
class CalibrationProfile:
    """Stores baseline metrics gathered during dynamic server calibration."""

    has_wildcard: bool = False
    wildcard_status: Optional[int] = None
    baseline_lengths: Set[int] = field(default_factory=set)
    baseline_hashes: Set[str] = field(default_factory=set)
    baseline_words: Set[int] = field(default_factory=set)
    baseline_lines: Set[int] = field(default_factory=set)
    redirect_target: Optional[str] = None


@dataclass
class EndpointResult:
    """Represents the discovery result and anomaly status of a single tested endpoint."""

    url: str
    path: str
    status_code: int
    content_length: int
    word_count: int
    line_count: int
    content_type: str
    redirect_url: Optional[str] = None
    response_time_ms: float = 0.0
    is_anomaly: bool = True
    body_hash: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert endpoint result to JSON-serializable dictionary."""
        return {
            "url": self.url,
            "path": self.path,
            "status_code": self.status_code,
            "content_length": self.content_length,
            "word_count": self.word_count,
            "line_count": self.line_count,
            "content_type": self.content_type,
            "redirect_url": self.redirect_url,
            "response_time_ms": round(self.response_time_ms, 2),
            "timestamp": self.timestamp,
        }
