import asyncio
import time
import httpx
import pytest

from http_bruteforcer.requester import (
    DEFAULT_USER_AGENT,
    RANDOM_USER_AGENTS,
    RateLimiter,
    Requester,
    parse_header_list,
)


def test_parse_header_list():
    raw = ["X-Forwarded-For: 127.0.0.1", "Authorization: Bearer token123", "InvalidHeaderNoColon"]
    parsed = parse_header_list(raw)
    assert parsed == {
        "X-Forwarded-For": "127.0.0.1",
        "Authorization": "Bearer token123",
    }


def test_requester_url_and_headers():
    req = Requester(
        base_url="https://example.com/api",
        headers=["X-Custom: test"],
        user_agent="CustomAgent/1.0",
    )
    assert req.base_url == "https://example.com/api"
    assert req.build_url("users") == "https://example.com/api/users"
    assert req.build_url("/users") == "https://example.com/api/users"

    headers = req._get_headers()
    assert headers["X-Custom"] == "test"
    assert headers["User-Agent"] == "CustomAgent/1.0"


def test_requester_random_ua():
    req = Requester(
        base_url="https://example.com",
        user_agent="random",
    )
    headers = req._get_headers()
    assert headers["User-Agent"] in RANDOM_USER_AGENTS


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter(rate=20.0)  # 20 req/s
    start = time.monotonic()
    for _ in range(5):
        await limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.0


@pytest.mark.asyncio
async def test_requester_request_with_mock_transport():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/test":
            return httpx.Response(
                status_code=200,
                headers={"content-type": "text/plain", "location": "https://example.com/done"},
                content=b"hello world\nline two",
            )
        return httpx.Response(status_code=404, content=b"not found")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        requester = Requester(base_url="https://example.com", client=client)
        result = await requester.request("/test")
        assert result is not None
        assert result.status_code == 200
        assert result.content_length == len(b"hello world\nline two")
        assert result.word_count == 4
        assert result.line_count == 2
        assert result.redirect_url == "https://example.com/done"
        assert result.body_hash is not None
