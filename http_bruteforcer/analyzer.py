"""Response anomaly analyzer and false-positive filtering engine."""

from __future__ import annotations

import re
from typing import List, Optional, Pattern, Set, Tuple, Union

from http_bruteforcer.models import CalibrationProfile, EndpointResult

DEFAULT_MATCH_CODES = {200, 204, 301, 302, 307, 401, 403}


def parse_status_codes(codes: Optional[Union[str, List[int], Set[int]]]) -> Set[int]:
    """Parse comma-separated or collection of status codes into a set of integers."""
    if not codes:
        return set()
    if isinstance(codes, (set, list, tuple)):
        return {int(c) for c in codes}
    result = set()
    for part in codes.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def parse_lengths(lengths: Optional[Union[str, List[int], Set[int]]]) -> Set[int]:
    """Parse comma-separated or collection of byte lengths into a set of integers."""
    if not lengths:
        return set()
    if isinstance(lengths, (set, list, tuple)):
        return {int(l) for l in lengths}
    result = set()
    for part in lengths.split(","):
        part = part.strip()
        if part.isdigit():
            result.add(int(part))
    return result


def parse_length_range(length_range: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse length range string like '100-200' into a tuple (min_len, max_len)."""
    if not length_range:
        return None
    if "-" in length_range:
        parts = length_range.split("-", 1)
        try:
            return (int(parts[0].strip()), int(parts[1].strip()))
        except ValueError:
            return None
    return None


class Analyzer:
    """Heuristic engine to filter out noise, soft-404s, catch-alls, and false positives."""

    def __init__(
        self,
        calibration: Optional[CalibrationProfile] = None,
        match_codes: Optional[Union[Set[int], str]] = None,
        filter_codes: Optional[Union[Set[int], str]] = None,
        filter_lengths: Optional[Union[Set[int], str]] = None,
        filter_length_range: Optional[Union[Tuple[int, int], str]] = None,
        filter_regex: Optional[str] = None,
        tolerance: int = 15,
    ):
        self.calibration = calibration or CalibrationProfile()

        # Match codes: if None, use DEFAULT_MATCH_CODES
        if match_codes is None:
            self.match_codes = set(DEFAULT_MATCH_CODES)
        elif isinstance(match_codes, str):
            self.match_codes = parse_status_codes(match_codes)
        else:
            self.match_codes = set(match_codes)

        # Filter codes
        if isinstance(filter_codes, str):
            self.filter_codes = parse_status_codes(filter_codes)
        elif filter_codes:
            self.filter_codes = set(filter_codes)
        else:
            self.filter_codes = set()

        # Filter lengths
        if isinstance(filter_lengths, str):
            self.filter_lengths = parse_lengths(filter_lengths)
        elif filter_lengths:
            self.filter_lengths = set(filter_lengths)
        else:
            self.filter_lengths = set()

        # Filter length range
        if isinstance(filter_length_range, str):
            self.filter_length_range = parse_length_range(filter_length_range)
        else:
            self.filter_length_range = filter_length_range

        # Filter regex
        self.filter_regex_pattern: Optional[Pattern[str]] = None
        if filter_regex:
            self.filter_regex_pattern = re.compile(filter_regex, re.IGNORECASE)

        self.tolerance = tolerance

    def is_valid(self, result: EndpointResult, body: Optional[str] = None) -> bool:
        """Determine whether the EndpointResult is a valid finding or noise/soft-404.

        Returns True if valid finding, False if it should be filtered out.
        """
        # 1. Check explicit filter status codes
        if result.status_code in self.filter_codes:
            result.is_anomaly = False
            return False

        # 2. Check match status codes
        if self.match_codes and result.status_code not in self.match_codes:
            result.is_anomaly = False
            return False

        # 3. Check exact filter length
        if result.content_length in self.filter_lengths:
            result.is_anomaly = False
            return False

        # 4. Check length range filter
        if self.filter_length_range:
            min_l, max_l = self.filter_length_range
            if min_l <= result.content_length <= max_l:
                result.is_anomaly = False
                return False

        # 5. Check regex filter
        if self.filter_regex_pattern and body:
            if self.filter_regex_pattern.search(body):
                result.is_anomaly = False
                return False

        # 6. Baseline Calibration & Soft-404 Anomaly Detection
        if self.calibration.has_wildcard:
            # If the status code matches the wildcard probe status
            if self.calibration.wildcard_status == result.status_code:
                # A. Identical body hash
                if result.body_hash and result.body_hash in self.calibration.baseline_hashes:
                    result.is_anomaly = False
                    return False

                # B. Dynamic deviation margin check
                for b_len in self.calibration.baseline_lengths:
                    if abs(result.content_length - b_len) <= self.tolerance:
                        if (
                            result.word_count in self.calibration.baseline_words
                            or result.line_count in self.calibration.baseline_lines
                        ):
                            result.is_anomaly = False
                            return False

                # C. Catch-all uniform redirect check
                if self.calibration.redirect_target and result.redirect_url:
                    if (
                        result.redirect_url == self.calibration.redirect_target
                        or result.redirect_url.rstrip("/") == self.calibration.redirect_target.rstrip("/")
                    ):
                        result.is_anomaly = False
                        return False

        # If baseline has recorded 404 hashes/lengths, filter identical 404s
        if result.status_code == 404:
            if result.body_hash and result.body_hash in self.calibration.baseline_hashes:
                result.is_anomaly = False
                return False

        result.is_anomaly = True
        return True
