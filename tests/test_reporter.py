import csv
import json
from pathlib import Path
from rich.console import Console

from http_bruteforcer.models import CalibrationProfile, EndpointResult
from http_bruteforcer.reporter import (
    Reporter,
    export_csv,
    export_json,
    format_status_code,
)


def test_format_status_code():
    assert "200" in format_status_code(200)
    assert "green" in format_status_code(200)
    assert "301" in format_status_code(301)
    assert "cyan" in format_status_code(301)
    assert "403" in format_status_code(403)
    assert "yellow" in format_status_code(403)
    assert "500" in format_status_code(500)
    assert "red" in format_status_code(500)


def test_reporter_console_output():
    console = Console(record=True)
    reporter = Reporter(console=console)

    reporter.print_banner("http://test.local", "wordlist.txt", 10, "GET")
    reporter.print_calibration(CalibrationProfile(has_wildcard=True, wildcard_status=200))

    sample = EndpointResult(
        url="http://test.local/admin",
        path="/admin",
        status_code=200,
        content_length=150,
        word_count=20,
        line_count=5,
        content_type="text/html",
        response_time_ms=15.2,
    )
    reporter.print_result_line(sample)

    table = reporter.build_summary_table([sample])
    console.print(table)

    output = console.export_text()
    assert "QuickBuster" in output
    assert "/admin" in output
    assert "150" in output


def test_export_json_and_csv(tmp_path: Path):
    results = [
        EndpointResult(
            url="http://test.local/login",
            path="/login",
            status_code=302,
            content_length=0,
            word_count=0,
            line_count=0,
            content_type="",
            redirect_url="http://test.local/auth",
            response_time_ms=10.5,
        ),
        EndpointResult(
            url="http://test.local/admin",
            path="/admin",
            status_code=200,
            content_length=500,
            word_count=50,
            line_count=10,
            content_type="text/html",
            response_time_ms=25.0,
        ),
    ]

    # JSON export
    json_path = tmp_path / "results.json"
    export_json(results, json_path)
    assert json_path.is_file()

    with json_path.open() as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert loaded[0]["path"] == "/login"
    assert loaded[1]["path"] == "/admin"

    # CSV export
    csv_path = tmp_path / "results.csv"
    export_csv(results, csv_path)
    assert csv_path.is_file()

    with csv_path.open(newline="") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 2
    assert reader[0]["path"] == "/login"
    assert reader[0]["redirect_url"] == "http://test.local/auth"
    assert reader[1]["status_code"] == "200"
