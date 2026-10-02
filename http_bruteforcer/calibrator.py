"""Baseline calibration and soft-404 / wildcard detection engine."""

from __future__ import annotations

import asyncio
import uuid
from typing import List, Optional

from http_bruteforcer.models import CalibrationProfile, EndpointResult
from http_bruteforcer.requester import Requester


class Calibrator:
    """Profiles the target web server using random non-existent probes to establish baseline behavior."""

    def __init__(self, requester: Requester, probe_count: int = 5):
        self.requester = requester
        self.probe_count = max(3, probe_count)

    def _generate_probes(self) -> List[str]:
        """Generate randomized paths unlikely to exist on the target server."""
        probes = []
        extensions = ["", ".html", ".php", ".json", ""]
        for i in range(self.probe_count):
            random_token = uuid.uuid4().hex
            ext = extensions[i % len(extensions)]
            probes.append(f"/probe_{random_token[:16]}{ext}")
        return probes

    async def calibrate(self) -> CalibrationProfile:
        """Execute calibration probes and construct a CalibrationProfile."""
        probes = self._generate_probes()
        tasks = [self.requester.request(p) for p in probes]
        results: List[Optional[EndpointResult]] = await asyncio.gather(*tasks, return_exceptions=False)

        valid_results = [r for r in results if r is not None]
        profile = CalibrationProfile()

        if not valid_results:
            return profile

        status_codes = [r.status_code for r in valid_results]
        redirect_targets = [r.redirect_url for r in valid_results if r.redirect_url]

        # Populate baseline metrics across all probes
        for r in valid_results:
            profile.baseline_lengths.add(r.content_length)
            if r.body_hash:
                profile.baseline_hashes.add(r.body_hash)
            profile.baseline_words.add(r.word_count)
            profile.baseline_lines.add(r.line_count)

        # Check for wildcard / soft-404 behavior (server returns non-404 for random probes)
        non_404 = [code for code in status_codes if code != 404]
        if len(non_404) >= len(valid_results) * 0.6:  # Majority returned non-404
            profile.has_wildcard = True
            # Find the most frequent status code among non-404s
            profile.wildcard_status = max(set(non_404), key=non_404.count)

        # Check for uniform redirect behavior
        if redirect_targets and len(redirect_targets) == len(valid_results):
            # Check if all redirect targets are identical
            if len(set(redirect_targets)) == 1:
                profile.redirect_target = redirect_targets[0]

        return profile
