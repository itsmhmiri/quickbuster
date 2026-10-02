import pytest
from http_bruteforcer.analyzer import (
    Analyzer,
    parse_length_range,
    parse_lengths,
    parse_status_codes,
)
from http_bruteforcer.models import CalibrationProfile, EndpointResult


def test_parsers():
    assert parse_status_codes("200, 301,404") == {200, 301, 404}
    assert parse_status_codes([200, 403]) == {200, 403}
    assert parse_status_codes(None) == set()

    assert parse_lengths("100, 200, 300") == {100, 200, 300}
    assert parse_lengths([500, 600]) == {500, 600}
    assert parse_lengths(None) == set()

    assert parse_length_range("100-200") == (100, 200)
    assert parse_length_range("invalid") is None
    assert parse_length_range(None) is None


def test_status_code_matching_and_filtering():
    analyzer = Analyzer(match_codes="200,301", filter_codes="500")

    res_200 = EndpointResult("http://t/ok", "/ok", 200, 100, 10, 5, "text/html")
    res_404 = EndpointResult("http://t/nf", "/nf", 404, 100, 10, 5, "text/html")
    res_500 = EndpointResult("http://t/err", "/err", 500, 100, 10, 5, "text/html")

    assert analyzer.is_valid(res_200) is True
    assert analyzer.is_valid(res_404) is False
    assert analyzer.is_valid(res_500) is False


def test_filter_length_and_range():
    analyzer = Analyzer(filter_lengths="500", filter_length_range="1000-2000")

    res_500 = EndpointResult("http://t/1", "/1", 200, 500, 10, 5, "text/html")
    res_1500 = EndpointResult("http://t/2", "/2", 200, 1500, 10, 5, "text/html")
    res_800 = EndpointResult("http://t/3", "/3", 200, 800, 10, 5, "text/html")

    assert analyzer.is_valid(res_500) is False
    assert analyzer.is_valid(res_1500) is False
    assert analyzer.is_valid(res_800) is True


def test_filter_regex():
    analyzer = Analyzer(filter_regex=r"Error 404|Custom Not Found")

    res_soft = EndpointResult("http://t/test", "/test", 200, 300, 15, 6, "text/html")
    assert analyzer.is_valid(res_soft, body="<html><body>Custom Not Found Here</body></html>") is False

    res_valid = EndpointResult("http://t/admin", "/admin", 200, 300, 15, 6, "text/html")
    assert analyzer.is_valid(res_valid, body="<html><body>Admin Dashboard</body></html>") is True


def test_soft_404_calibration_tolerance():
    profile = CalibrationProfile(
        has_wildcard=True,
        wildcard_status=200,
        baseline_lengths={500},
        baseline_hashes={"hash_abc123"},
        baseline_words={50},
        baseline_lines={10},
    )
    analyzer = Analyzer(calibration=profile, tolerance=15)

    # Identical hash -> soft-404 filtered
    res_exact = EndpointResult(
        "http://t/probe", "/probe", 200, 500, 50, 10, "text/html", body_hash="hash_abc123"
    )
    assert analyzer.is_valid(res_exact) is False

    # Dynamic variation within tolerance (e.g. length 505, word count 50) -> soft-404 filtered
    res_dynamic = EndpointResult(
        "http://t/probe2", "/probe2", 200, 505, 50, 10, "text/html", body_hash="hash_diff"
    )
    assert analyzer.is_valid(res_dynamic) is False

    # Real finding (different size outside tolerance, or different words/lines) -> valid!
    res_real = EndpointResult(
        "http://t/secret", "/secret", 200, 2400, 200, 45, "text/html", body_hash="hash_secret"
    )
    assert analyzer.is_valid(res_real) is True


def test_uniform_redirect_filtering():
    profile = CalibrationProfile(
        has_wildcard=True,
        wildcard_status=302,
        redirect_target="https://example.com/login",
    )
    analyzer = Analyzer(calibration=profile)

    res_catchall = EndpointResult(
        "http://t/random", "/random", 302, 0, 0, 0, "", redirect_url="https://example.com/login"
    )
    assert analyzer.is_valid(res_catchall) is False

    res_valid_redirect = EndpointResult(
        "http://t/admin", "/admin", 302, 0, 0, 0, "", redirect_url="https://example.com/admin/dashboard"
    )
    assert analyzer.is_valid(res_valid_redirect) is True
