import pytest
from pathlib import Path
from aiohttp.test_utils import TestServer
from rich.console import Console

from http_bruteforcer.calibrator import Calibrator
from http_bruteforcer.analyzer import Analyzer
from http_bruteforcer.engine import BruteForceEngine
from http_bruteforcer.requester import Requester
from http_bruteforcer.reporter import Reporter
from http_bruteforcer.wordlist import generate_paths, count_total_paths
from http_bruteforcer.cli import build_parser, async_main
from tests.mock_server import create_mock_app


@pytest.fixture
async def mock_server():
    """Start the mock server on an ephemeral local port."""
    app = create_mock_app()
    server = TestServer(app)
    await server.start_server()
    base_url = f"http://127.0.0.1:{server.port}"
    try:
        yield base_url
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_calibrator_detects_soft_404(mock_server: str):
    """Test 1: Verify calibrator identifies soft-404 and filters out random probe paths."""
    async with Requester(base_url=mock_server) as requester:
        calibrator = Calibrator(requester, probe_count=4)
        profile = await calibrator.calibrate()

        # Target returns status 200 with dynamic timestamp for random paths
        assert profile.has_wildcard is True
        assert profile.wildcard_status == 200
        assert len(profile.baseline_lengths) > 0
        assert len(profile.baseline_words) > 0

        # Anomaly analyzer using this calibration profile should filter random non-existent paths
        analyzer = Analyzer(calibration=profile, match_codes="200,301,302")
        random_result = await requester.request("/completely_random_path_12345")
        assert random_result is not None
        assert analyzer.is_valid(random_result) is False


@pytest.mark.asyncio
async def test_valid_endpoints_discovery(mock_server: str, tmp_path: Path):
    """Test 2: Verify valid endpoints (/admin, /login.php) are successfully discovered."""
    wordlist_file = tmp_path / "words.txt"
    wordlist_file.write_text("admin\nnonexistent1\nlogin.php\nfake_page\n")

    async with Requester(base_url=mock_server) as requester:
        calibrator = Calibrator(requester)
        profile = await calibrator.calibrate()
        analyzer = Analyzer(calibration=profile, match_codes="200")
        reporter = Reporter(console=Console(quiet=True))

        engine = BruteForceEngine(
            requester=requester,
            analyzer=analyzer,
            reporter=reporter,
            concurrency=5,
            show_progress=False,
        )

        paths = generate_paths(wordlist_file)
        results = await engine.run(paths)

        discovered = {r.path for r in results}
        assert "/admin" in discovered
        assert "/login.php" in discovered
        assert "/nonexistent1" not in discovered
        assert "/fake_page" not in discovered


@pytest.mark.asyncio
async def test_extension_permutations(mock_server: str, tmp_path: Path):
    """Test 3: Verify extension permutations (-x php) expand words correctly."""
    wordlist_file = tmp_path / "words.txt"
    wordlist_file.write_text("login\n")

    async with Requester(base_url=mock_server) as requester:
        calibrator = Calibrator(requester)
        profile = await calibrator.calibrate()
        analyzer = Analyzer(calibration=profile, match_codes="200")
        reporter = Reporter(console=Console(quiet=True))

        engine = BruteForceEngine(
            requester=requester,
            analyzer=analyzer,
            reporter=reporter,
            concurrency=2,
            show_progress=False,
        )

        # Word 'login' with extension 'php' should yield '/login' and '/login.php'
        paths = generate_paths(wordlist_file, extensions=["php"])
        results = await engine.run(paths)

        discovered = {r.path for r in results}
        assert "/login.php" in discovered


@pytest.mark.asyncio
async def test_end_to_end_cli_with_exports(mock_server: str, tmp_path: Path):
    """Test 4: Verify end-to-end CLI execution including JSON and CSV exports."""
    wordlist_file = tmp_path / "words.txt"
    wordlist_file.write_text("admin\nlogin\nrandom_fake\n")
    json_out = tmp_path / "results.json"
    csv_out = tmp_path / "results.csv"

    parser = build_parser()
    args = parser.parse_args([
        "-u", mock_server,
        "-w", str(wordlist_file),
        "-x", "php",
        "-c", "5",
        "-oJ", str(json_out),
        "-oC", str(csv_out),
    ])

    exit_code = await async_main(args, console=Console(quiet=True))
    assert exit_code == 0
    assert json_out.is_file()
    assert csv_out.is_file()

    import json
    data = json.loads(json_out.read_text())
    paths = [item["path"] for item in data]
    assert "/admin" in paths
    assert "/login.php" in paths
