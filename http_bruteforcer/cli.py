"""Command-line interface definition and orchestration entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from http_bruteforcer.analyzer import Analyzer
from http_bruteforcer.calibrator import Calibrator
from http_bruteforcer.engine import BruteForceEngine
from http_bruteforcer.models import CalibrationProfile
from http_bruteforcer.reporter import Reporter, export_csv, export_json
from http_bruteforcer.requester import Requester
from http_bruteforcer.wordlist import count_total_paths, generate_paths


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser adhering to the engineering specification."""
    parser = argparse.ArgumentParser(
        prog="http-brute",
        description="Multi-Threaded HTTP Directory & Endpoint Brute-Forcer",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Core target & wordlist arguments
    parser.add_argument(
        "-u", "--url",
        required=True,
        help="Target base URL (e.g. https://example.com)",
    )
    parser.add_argument(
        "-w", "--wordlist",
        required=True,
        help="Path to directory/endpoint wordlist",
    )
    parser.add_argument(
        "-x", "--extensions",
        default="",
        help="Comma-separated extensions to append (e.g. php,html,txt)",
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=50,
        help="Number of concurrent workers (default: 50)",
    )
    parser.add_argument(
        "-m", "--method",
        default="GET",
        choices=["GET", "HEAD", "POST"],
        help="HTTP method to use (default: GET)",
    )
    parser.add_argument(
        "-H", "--header",
        action="append",
        dest="headers",
        help='Custom header (e.g. "X-Forwarded-For: 127.0.0.1"). Can be repeated.',
    )
    parser.add_argument(
        "-a", "--user-agent",
        default=None,
        help="Custom User-Agent string or 'random'",
    )

    # Filtering & matching options
    parser.add_argument(
        "--mc", "--match-codes",
        dest="match_codes",
        default="200,204,301,302,307,401,403",
        help="Status codes to display (default: 200,204,301,302,307,401,403)",
    )
    parser.add_argument(
        "--fc", "--filter-codes",
        dest="filter_codes",
        default=None,
        help="Status codes to hide (e.g. 404)",
    )
    parser.add_argument(
        "--fl", "--filter-length",
        dest="filter_length",
        default=None,
        help="Filter response content-lengths (comma-separated)",
    )
    parser.add_argument(
        "--filter-length-range",
        dest="filter_length_range",
        default=None,
        help="Filter response length range (e.g. 100-200)",
    )
    parser.add_argument(
        "--filter-regex",
        dest="filter_regex",
        default=None,
        help="Filter out responses containing regex pattern",
    )

    # HTTP client flags
    parser.add_argument(
        "--follow-redirects",
        action="store_true",
        default=False,
        help="Follow HTTP redirects (default: False)",
    )
    parser.add_argument(
        "-k", "--insecure",
        action="store_true",
        default=False,
        help="Disable SSL/TLS certificate verification",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=None,
        help="Maximum requests per second limit (default: unlimited)",
    )

    # Export & output options
    parser.add_argument(
        "-oJ", "--json",
        dest="output_json",
        default=None,
        help="Export valid results to JSON file",
    )
    parser.add_argument(
        "-oC", "--csv",
        dest="output_csv",
        default=None,
        help="Export valid results to CSV file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Verbose debug logging",
    )
    parser.add_argument(
        "--add-slash",
        action="store_true",
        default=False,
        help="Append trailing slash to directories",
    )
    parser.add_argument(
        "--no-calibration",
        action="store_true",
        default=False,
        help="Skip automatic baseline calibration",
    )

    return parser


async def async_main(args: argparse.Namespace, console: Optional[Console] = None) -> int:
    """Async coordinator for calibration, scanning, and reporting."""
    reporter = Reporter(console=console, verbose=args.verbose)
    reporter.print_banner(
        target_url=args.url,
        wordlist_file=args.wordlist,
        concurrency=args.concurrency,
        method=args.method,
    )

    wordlist_path = Path(args.wordlist)
    if not wordlist_path.is_file():
        reporter.console.print(f"[bold red][!] Error:[/bold red] Wordlist file not found: {args.wordlist}")
        return 1

    try:
        total_paths = count_total_paths(
            wordlist_path=args.wordlist,
            extensions=args.extensions,
            add_slash=args.add_slash,
        )
    except Exception as exc:
        reporter.console.print(f"[bold red][!] Error reading wordlist:[/bold red] {exc}")
        return 1

    reporter.console.print(f"[bold white]Total requests to dispatch:[/bold white] [cyan]{total_paths}[/cyan]")

    async with Requester(
        base_url=args.url,
        concurrency=args.concurrency,
        method=args.method,
        headers=args.headers,
        user_agent=args.user_agent,
        follow_redirects=args.follow_redirects,
        insecure=args.insecure,
        rate_limit=args.rate_limit,
    ) as requester:
        # Calibration
        if args.no_calibration:
            calibration = CalibrationProfile()
            reporter.console.print("[dim]Baseline calibration skipped by flag.[/dim]")
        else:
            reporter.console.print("[dim]Calibrating baseline against target server...[/dim]")
            calibrator = Calibrator(requester)
            calibration = await calibrator.calibrate()
            reporter.print_calibration(calibration)

        # Analyzer
        analyzer = Analyzer(
            calibration=calibration,
            match_codes=args.match_codes,
            filter_codes=args.filter_codes,
            filter_lengths=args.filter_length,
            filter_length_range=args.filter_length_range,
            filter_regex=args.filter_regex,
        )

        # Engine
        paths_iter = generate_paths(
            wordlist_path=args.wordlist,
            extensions=args.extensions,
            add_slash=args.add_slash,
        )

        engine = BruteForceEngine(
            requester=requester,
            analyzer=analyzer,
            reporter=reporter,
            concurrency=args.concurrency,
            show_progress=True,
        )

        try:
            results = await engine.run(paths_iter, total_count=total_paths)
        except (KeyboardInterrupt, asyncio.CancelledError):
            reporter.console.print("\n[bold yellow][!] Scan aborted by user.[/bold yellow]")
            results = engine.results

        # Summary Table
        if results:
            reporter.console.print()
            table = reporter.build_summary_table(results)
            reporter.console.print(table)
        else:
            reporter.console.print("\n[yellow]No endpoints discovered matching criteria.[/yellow]")

        # Exporters
        if args.output_json:
            export_json(results, args.output_json)
            reporter.console.print(f"[bold green][+][/bold green] Results exported to JSON: [cyan]{args.output_json}[/cyan]")

        if args.output_csv:
            export_csv(results, args.output_csv)
            reporter.console.print(f"[bold green][+][/bold green] Results exported to CSV: [cyan]{args.output_csv}[/cyan]")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
