"""HTTP async client wrapper, connection pooling, retries, headers, and rate limiting."""

from __future__ import annotations

import asyncio
import hashlib
import random
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from http_bruteforcer.models import EndpointResult

DEFAULT_USER_AGENT = "QuickBuster/0.1.0 (Security Scanner; https://github.com/quickbuster)"

RANDOM_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


def parse_header_list(headers: Optional[List[str]]) -> Dict[str, str]:
    """Parse list of 'Name: Value' strings into a dictionary."""
    parsed: Dict[str, str] = {}
    if not headers:
        return parsed
    for item in headers:
        if ":" in item:
            name, val = item.split(":", 1)
            parsed[name.strip()] = val.strip()
    return parsed


class RateLimiter:
    """Async token bucket rate limiter to restrict requests per second."""

    def __init__(self, rate: Optional[float] = None):
        self.rate = rate if rate and rate > 0 else 0.0
        self.capacity = max(1.0, self.rate)
        self.tokens = self.capacity
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self.rate <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated_at
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.updated_at = now
            if self.tokens < 1.0:
                needed = 1.0 - self.tokens
                wait_time = needed / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.updated_at = time.monotonic()
            else:
                self.tokens -= 1.0


class Requester:
    """Handles high-throughput asynchronous HTTP probing with retry logic and connection pooling."""

    def __init__(
        self,
        base_url: str,
        concurrency: int = 50,
        method: str = "GET",
        headers: Optional[Union[Dict[str, str], List[str]]] = None,
        user_agent: Optional[str] = None,
        follow_redirects: bool = False,
        insecure: bool = False,
        timeout: float = 10.0,
        connect_timeout: float = 3.0,
        read_timeout: float = 5.0,
        retries: int = 2,
        rate_limit: Optional[float] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        # Normalize base_url
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            base_url = f"http://{base_url}"
        self.base_url = base_url.rstrip("/")

        self.concurrency = max(1, concurrency)
        self.method = method.upper()
        self.follow_redirects = follow_redirects
        self.insecure = insecure
        self.retries = retries
        self.rate_limiter = RateLimiter(rate_limit)

        # Headers setup
        if isinstance(headers, list):
            self.custom_headers = parse_header_list(headers)
        elif isinstance(headers, dict):
            self.custom_headers = dict(headers)
        else:
            self.custom_headers = {}

        self.user_agent = user_agent
        self.rotate_ua = user_agent == "random"

        # Timeouts & Limits
        self.timeout_config = httpx.Timeout(
            timeout=timeout,
            connect=connect_timeout,
            read=read_timeout,
            write=5.0,
            pool=5.0,
        )
        self.limits_config = httpx.Limits(
            max_keepalive_connections=min(100, self.concurrency * 2),
            max_connections=self.concurrency,
        )

        self._client = client
        self._owned_client = client is None

    async def __aenter__(self) -> Requester:
        if self._client is None:
            self._client = httpx.AsyncClient(
                verify=not self.insecure,
                timeout=self.timeout_config,
                limits=self.limits_config,
                follow_redirects=self.follow_redirects,
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client if owned."""
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        """Construct request headers with UA rotation and custom headers."""
        headers = dict(self.custom_headers)
        if "User-Agent" not in headers and "user-agent" not in headers:
            if self.rotate_ua:
                headers["User-Agent"] = random.choice(RANDOM_USER_AGENTS)
            elif self.user_agent:
                headers["User-Agent"] = self.user_agent
            else:
                headers["User-Agent"] = DEFAULT_USER_AGENT
        return headers

    def build_url(self, path: str) -> str:
        """Construct full URL given a path."""
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    async def request(self, path: str) -> Optional[EndpointResult]:
        """Send request to the specified path with rate limiting and retry handling."""
        if self._client is None:
            raise RuntimeError("Requester client is not initialized. Use 'async with' or pass an initialized client.")

        await self.rate_limiter.acquire()
        url = self.build_url(path)
        headers = self._get_headers()

        for attempt in range(self.retries + 1):
            try:
                start_time = time.perf_counter()
                response = await self._client.request(
                    method=self.method,
                    url=url,
                    headers=headers,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000.0

                body_bytes = response.content
                body_hash = hashlib.md5(body_bytes).hexdigest()
                text = response.text
                word_count = len(text.split())
                line_count = len(text.splitlines())

                redirect_url = response.headers.get("location")

                return EndpointResult(
                    url=str(response.url),
                    path=path,
                    status_code=response.status_code,
                    content_length=len(body_bytes),
                    word_count=word_count,
                    line_count=line_count,
                    content_type=response.headers.get("content-type", "").split(";")[0].strip(),
                    redirect_url=redirect_url,
                    response_time_ms=duration_ms,
                    body_hash=body_hash,
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt >= self.retries:
                    return None
                await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception:
                return None
        return None
