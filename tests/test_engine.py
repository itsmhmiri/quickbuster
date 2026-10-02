import httpx
import pytest
from rich.console import Console

from http_bruteforcer.analyzer import Analyzer
from http_bruteforcer.engine import BruteForceEngine
from http_bruteforcer.reporter import Reporter
from http_bruteforcer.requester import Requester


@pytest.mark.asyncio
async def test_engine_run():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in ["/admin", "/login.php"]:
            return httpx.Response(200, text=f"Found: {request.url.path}")
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        requester = Requester(base_url="https://example.com", client=client)
        analyzer = Analyzer(match_codes="200")
        reporter = Reporter(console=Console(quiet=True))

        engine = BruteForceEngine(
            requester=requester,
            analyzer=analyzer,
            reporter=reporter,
            concurrency=3,
            show_progress=False,
        )

        paths = ["/admin", "/invalid1", "/login.php", "/invalid2"]
        results = await engine.run(iter(paths), total_count=len(paths))

        assert len(results) == 2
        paths_found = {r.path for r in results}
        assert paths_found == {"/admin", "/login.php"}
