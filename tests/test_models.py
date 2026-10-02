import datetime
from http_bruteforcer.models import CalibrationProfile, EndpointResult


def test_calibration_profile_defaults():
    profile = CalibrationProfile()
    assert not profile.has_wildcard
    assert profile.wildcard_status is None
    assert profile.baseline_lengths == set()
    assert profile.baseline_hashes == set()
    assert profile.baseline_words == set()
    assert profile.baseline_lines == set()
    assert profile.redirect_target is None


def test_endpoint_result_to_dict():
    result = EndpointResult(
        url="https://example.com/admin",
        path="/admin",
        status_code=200,
        content_length=1234,
        word_count=45,
        line_count=10,
        content_type="text/html",
        redirect_url=None,
        response_time_ms=12.3456,
        is_anomaly=True,
    )
    d = result.to_dict()
    assert d["url"] == "https://example.com/admin"
    assert d["path"] == "/admin"
    assert d["status_code"] == 200
    assert d["content_length"] == 1234
    assert d["word_count"] == 45
    assert d["line_count"] == 10
    assert d["content_type"] == "text/html"
    assert d["redirect_url"] is None
    assert d["response_time_ms"] == 12.35
    assert "timestamp" in d
