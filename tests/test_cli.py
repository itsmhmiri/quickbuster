from pathlib import Path
import pytest
from rich.console import Console

from http_bruteforcer.cli import async_main, build_parser


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["-u", "http://example.com", "-w", "test_words.txt"])
    assert args.url == "http://example.com"
    assert args.wordlist == "test_words.txt"
    assert args.concurrency == 50
    assert args.method == "GET"
    assert args.match_codes == "200,204,301,302,307,401,403"
    assert not args.follow_redirects
    assert not args.insecure


def test_build_parser_options():
    parser = build_parser()
    args = parser.parse_args([
        "-u", "https://target.com",
        "-w", "/tmp/words.txt",
        "-x", "php,html",
        "-c", "25",
        "-m", "POST",
        "-H", "X-Custom: 1",
        "-H", "Authorization: test",
        "-a", "random",
        "--mc", "200,301",
        "--fc", "404,500",
        "--fl", "123,456",
        "--filter-length-range", "100-200",
        "--filter-regex", "not found",
        "--follow-redirects",
        "-k",
        "--rate-limit", "10",
        "-oJ", "out.json",
        "-oC", "out.csv",
        "-v",
        "--add-slash",
        "--no-calibration",
    ])
    assert args.url == "https://target.com"
    assert args.extensions == "php,html"
    assert args.concurrency == 25
    assert args.method == "POST"
    assert len(args.headers) == 2
    assert args.user_agent == "random"
    assert args.match_codes == "200,301"
    assert args.filter_codes == "404,500"
    assert args.filter_length == "123,456"
    assert args.filter_length_range == "100-200"
    assert args.filter_regex == "not found"
    assert args.follow_redirects is True
    assert args.insecure is True
    assert args.rate_limit == 10.0
    assert args.output_json == "out.json"
    assert args.output_csv == "out.csv"
    assert args.verbose is True
    assert args.add_slash is True
    assert args.no_calibration is True


@pytest.mark.asyncio
async def test_async_main_missing_wordlist():
    parser = build_parser()
    args = parser.parse_args(["-u", "http://example.com", "-w", "/nonexistent_file_path.txt"])
    console = Console(quiet=True)
    exit_code = await async_main(args, console=console)
    assert exit_code == 1
