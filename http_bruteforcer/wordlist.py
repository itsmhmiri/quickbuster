"""Wordlist reader and path/extension permutator."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, List, Optional, Union


def clean_extensions(extensions: Optional[Union[List[str], str]]) -> List[str]:
    """Clean and normalize extension list (removes leading dots and empty entries)."""
    if not extensions:
        return []
    if isinstance(extensions, str):
        extensions = extensions.split(",")
    cleaned = []
    for ext in extensions:
        ext = ext.strip()
        if not ext:
            continue
        if ext.startswith("."):
            ext = ext[1:]
        if ext and ext not in cleaned:
            cleaned.append(ext)
    return cleaned


def count_wordlist_lines(wordlist_path: Union[str, Path]) -> int:
    """Count valid (non-empty, non-comment) lines in wordlist."""
    path = Path(wordlist_path)
    if not path.is_file():
        raise FileNotFoundError(f"Wordlist file not found: {wordlist_path}")

    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
    return count


def count_total_paths(
    wordlist_path: Union[str, Path],
    extensions: Optional[Union[List[str], str]] = None,
    add_slash: bool = False,
) -> int:
    """Calculate the total number of paths that will be generated."""
    valid_lines = count_wordlist_lines(wordlist_path)
    ext_list = clean_extensions(extensions)
    multiplier = 1 + (1 if add_slash else 0) + len(ext_list)
    return valid_lines * multiplier


def generate_paths(
    wordlist_path: Union[str, Path],
    extensions: Optional[Union[List[str], str]] = None,
    add_slash: bool = False,
) -> Iterator[str]:
    """Stream paths directly from wordlist with optional extensions and trailing slashes.

    Yields formatted URL paths (always starting with '/').
    """
    path = Path(wordlist_path)
    if not path.is_file():
        raise FileNotFoundError(f"Wordlist file not found: {wordlist_path}")

    ext_list = clean_extensions(extensions)

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            word = line.strip()
            if not word or word.startswith("#"):
                continue

            # Normalize word without leading or trailing slashes
            clean_word = word.strip("/")
            if not clean_word:
                continue

            base_path = f"/{clean_word}"

            # 1. Base path
            yield base_path

            # 2. Directory probe with trailing slash (if requested)
            if add_slash:
                yield f"{base_path}/"

            # 3. Appended extensions
            for ext in ext_list:
                yield f"{base_path}.{ext}"
