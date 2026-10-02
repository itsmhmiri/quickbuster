import pytest
from pathlib import Path
from http_bruteforcer.wordlist import (
    clean_extensions,
    count_wordlist_lines,
    count_total_paths,
    generate_paths,
)


def test_clean_extensions():
    assert clean_extensions(["php", "html", "bak"]) == ["php", "html", "bak"]
    assert clean_extensions([".php", ".html", "txt"]) == ["php", "html", "txt"]
    assert clean_extensions("php,html,bak") == ["php", "html", "bak"]
    assert clean_extensions(".php, .html , txt") == ["php", "html", "txt"]
    assert clean_extensions(None) == []
    assert clean_extensions("") == []


def test_wordlist_generation(tmp_path: Path):
    wl = tmp_path / "words.txt"
    wl.write_text(
        "# Comment line\n"
        "dashboard\n"
        "\n"
        "admin/\n"
        "login\n"
        "   \n"
        "# Another comment\n"
    )

    assert count_wordlist_lines(wl) == 3
    assert count_total_paths(wl, extensions=["php", "html"], add_slash=True) == 3 * 4  # 1 base + 1 slash + 2 exts = 4 per word

    paths = list(generate_paths(wl, extensions=["php", "html", "bak"]))
    expected = [
        "/dashboard",
        "/dashboard.php",
        "/dashboard.html",
        "/dashboard.bak",
        "/admin",
        "/admin.php",
        "/admin.html",
        "/admin.bak",
        "/login",
        "/login.php",
        "/login.html",
        "/login.bak",
    ]
    assert paths == expected


def test_wordlist_generation_with_add_slash(tmp_path: Path):
    wl = tmp_path / "words.txt"
    wl.write_text("dashboard\n")

    paths = list(generate_paths(wl, extensions=["php"], add_slash=True))
    assert paths == [
        "/dashboard",
        "/dashboard/",
        "/dashboard.php",
    ]


def test_wordlist_missing_file():
    with pytest.raises(FileNotFoundError):
        list(generate_paths("/nonexistent/file/path/here.txt"))
    with pytest.raises(FileNotFoundError):
        count_wordlist_lines("/nonexistent/file/path/here.txt")
