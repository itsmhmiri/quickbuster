"""Rich terminal UI, real-time result streaming, and JSON/CSV exporters."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional, Union

from rich.console import Console
from rich.table import Table
from rich.text import Text

from http_bruteforcer.models import CalibrationProfile, EndpointResult


def format_status_code(status_code: int) -> str:
    """Return colored Rich string representation of an HTTP status code."""
    if 200 <= status_code < 300:
        return f"[bold green]{status_code}[/bold green]"
    elif 300 <= status_code < 400:
        return f"[bold cyan]{status_code}[/bold cyan]"
    elif 400 <= status_code < 500:
        return f"[bold yellow]{status_code}[/bold yellow]"
    elif 500 <= status_code < 600:
        return f"[bold red]{status_code}[/bold red]"
    return f"[bold magenta]{status_code}[/bold magenta]"


class Reporter:
    """Manages terminal output, progress reporting, and file exports."""

    def __init__(self, console: Optional[Console] = None, verbose: bool = False):
        self.console = console or Console()
        self.verbose = verbose

    def print_banner(self, target_url: str, wordlist_file: str, concurrency: int, method: str) -> None:
        """Display startup information and banner."""
        self.console.print(
            "[bold cyan]=====================================================[/bold cyan]"
        )
        self.console.print(
            "[bold green] QuickBuster [/bold green] [bold white]- Multi-Threaded HTTP Directory & Endpoint Scanner[/bold white]"
        )
        self.console.print(
            "[bold cyan]=====================================================[/bold cyan]"
        )
        self.console.print(f" [bold white]Target URL :[/bold white] [cyan]{target_url}[/cyan]")
        self.console.print(f" [bold white]Wordlist   :[/bold white] [cyan]{wordlist_file}[/cyan]")
        self.console.print(f" [bold white]Method     :[/bold white] [yellow]{method}[/yellow]")
        self.console.print(f" [bold white]Concurrency:[/bold white] [yellow]{concurrency}[/yellow]")
        self.console.print(
            "[bold cyan]-----------------------------------------------------[/bold cyan]"
        )

    def print_calibration(self, profile: CalibrationProfile) -> None:
        """Display calibration profiling results."""
        if profile.has_wildcard:
            self.console.print(
                f"[bold yellow][!][/bold yellow] Wildcard/Soft-404 detected (Status: [bold red]{profile.wildcard_status}[/bold red]). Dynamic anomaly filtering active."
            )
            if profile.redirect_target:
                self.console.print(
                    f"    Catch-all redirect target: [cyan]{profile.redirect_target}[/cyan]"
                )
        else:
            self.console.print(
                "[bold green][+][/bold green] Baseline calibration complete: Standard 404 behavior detected."
            )
        self.console.print(
            "[bold cyan]-----------------------------------------------------[/bold cyan]"
        )

    def print_result_line(self, result: EndpointResult) -> None:
        """Stream a single finding line to the console."""
        status_colored = format_status_code(result.status_code)
        line = (
            f" {status_colored}  "
            f"[dim]Size:[/dim] {result.content_length:<7} "
            f"[dim]Words:[/dim] {result.word_count:<5} "
            f"[dim]Lines:[/dim] {result.line_count:<5} "
            f"[dim]Time:[/dim] {result.response_time_ms:>6.1f}ms  "
            f"[bold white]{result.path}[/bold white]"
        )
        if result.redirect_url:
            line += f" [cyan]-> {result.redirect_url}[/cyan]"

        self.console.print(line)

    def build_summary_table(self, results: List[EndpointResult]) -> Table:
        """Build a Rich summary table containing all discovered endpoints."""
        table = Table(title="Discovered Endpoints Summary", show_header=True, header_style="bold magenta")
        table.add_column("Status", justify="center")
        table.add_column("Path", style="bold white")
        table.add_column("Size", justify="right")
        table.add_column("Words", justify="right")
        table.add_column("Lines", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Redirect", style="cyan")

        for r in results:
            status_text = Text(str(r.status_code))
            if 200 <= r.status_code < 300:
                status_text.stylize("bold green")
            elif 300 <= r.status_code < 400:
                status_text.stylize("bold cyan")
            elif 400 <= r.status_code < 500:
                status_text.stylize("bold yellow")
            else:
                status_text.stylize("bold red")

            table.add_row(
                status_text,
                r.path,
                str(r.content_length),
                str(r.word_count),
                str(r.line_count),
                f"{r.response_time_ms:.1f}ms",
                r.redirect_url or "",
            )
        return table


def export_json(results: List[EndpointResult], filepath: Union[str, Path]) -> None:
    """Export list of EndpointResult objects to formatted JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.to_dict() for r in results]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_csv(results: List[EndpointResult], filepath: Union[str, Path]) -> None:
    """Export list of EndpointResult objects to CSV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "url",
        "path",
        "status_code",
        "content_length",
        "word_count",
        "line_count",
        "content_type",
        "redirect_url",
        "response_time_ms",
        "timestamp",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
