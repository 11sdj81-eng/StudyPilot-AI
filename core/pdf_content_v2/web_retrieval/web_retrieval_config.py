"""Web retrieval configuration — default OFF, course-agnostic."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class WebRetrievalConfig:
    enabled: bool = False           # ENABLE_WEB_RETRIEVAL env var
    max_results_per_query: int = 5
    max_queries_per_session: int = 10
    timeout_seconds: int = 15
    allowed_domains: list[str] = field(default_factory=lambda: [
        "edu.cn", ".edu", "khanacademy.org", "wikipedia.org",
        "github.com", "zhihu.com", "csdn.net", "jianshu.com",
    ])
    blocked_domains: list[str] = field(default_factory=lambda: [
        "z-lib", "libgen", "pirate", "baidu.com/s/",  # no pirate, no paywall bypass
    ])
    require_source_label: bool = True  # always label WEB_RETRIEVED
    max_snippet_length: int = 300     # never copy full pages

    @property
    def is_available(self) -> bool:
        return self.enabled

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled, "max_results_per_query": self.max_results_per_query,
            "max_queries_per_session": self.max_queries_per_session,
            "timeout_seconds": self.timeout_seconds,
            "allowed_domains": self.allowed_domains,
            "require_source_label": self.require_source_label,
        }


def get_config() -> WebRetrievalConfig:
    """Read config from environment, default OFF."""
    enabled = os.environ.get("ENABLE_WEB_RETRIEVAL", "false").lower() in ("true", "1", "yes")
    return WebRetrievalConfig(enabled=enabled)
