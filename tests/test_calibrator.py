import httpx
import pytest

from http_bruteforcer.calibrator import Calibrator
from http_bruteforcer.requester import Requester


@pytest.mark.asyncio
async def test_calibrator_standard_404():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found on this server")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        requester = Requester(base_url="https://example.com", client=client)
        calibrator = Calibrator(requester, probe_count=4)
        profile = await calibrator.calibrate()

        assert not profile.has_wildcard
        assert profile.wildcard_status is None
        assert len(profile.baseline_lengths) == 1
        assert len(profile.baseline_hashes) == 1
        assert profile.redirect_target is None


@pytest.mark.asyncio
async def test_calibrator_soft_404_wildcard_200():
    counter = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal counter
        counter += 1
        # Simulate slight byte deviation (timestamp or nonce)
        return httpx.Response(200, text=f"<html>SPA Catch-all Error {counter}</html>")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        requester = Requester(base_url="https://example.com", client=client)
        calibrator = Calibrator(requester, probe_count=4)
        profile = await calibrator.calibrate()

        assert profile.has_wildcard is True
        assert profile.wildcard_status == 200
        assert len(profile.baseline_lengths) > 0
        assert len(profile.baseline_words) > 0


@pytest.mark.asyncio
async def test_calibrator_uniform_redirect():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://example.com/login"}, text="")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        requester = Requester(base_url="https://example.com", client=client)
        calibrator = Calibrator(requester, probe_count=3)
        profile = await calibrator.calibrate()

        assert profile.has_wildcard is True
        assert profile.wildcard_status == 302
        assert profile.redirect_target == "https://example.com/login"
