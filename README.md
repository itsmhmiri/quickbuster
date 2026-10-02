# QuickBuster 🚀

A fast, smart HTTP directory and endpoint discovery tool built with Python and `asyncio`.

Most directory brute-forcers flood your screen with garbage when a site uses single-page application (SPA) catch-alls, custom 404 pages with timestamps, or wildcard redirects. QuickBuster solves this by running a quick calibration step before the scan, learning what "page not found" actually looks like on the target server, and filtering out the false positives automatically.

---

## Why QuickBuster?

- **Smart Soft-404 & Catch-all Filtering:** Automatically detects wildcard responses, dynamic timestamps, and catch-all redirects so you only see real endpoints.
- **Asynchronous & Fast:** Uses `httpx` and `asyncio` with persistent connection pooling to push hundreds of requests per second efficiently.
- **Low Memory Footprint:** Streams wordlists line-by-line from disk instead of buffering massive dictionaries into RAM.
- **Clean Terminal UI:** Real-time feedback with colored HTTP status codes and a live progress bar powered by `rich`.
- **Flexible Exporters:** Dump your findings straight to JSON or CSV for reporting or piping into other tools.
- **Pentester Friendly:** Built-in support for custom headers, User-Agent rotation, rate limiting, and SSL/TLS verification bypass.

---

## Tech Stack

- **Language:** Python 3.10+
- **HTTP Engine:** [httpx](https://www.python-httpx.org/) (async HTTP client with connection pooling and HTTP/2 support)
- **Concurrency:** Standard library `asyncio` (`asyncio.Queue` worker pool)
- **Terminal UI:** [rich](https://github.com/Textualize/rich) (tables, colors, progress bars)
- **Testing:** `pytest`, `pytest-asyncio`, and `aiohttp`

---

## Getting Started

### 1. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

You can install QuickBuster in editable mode:
```bash
pip install -e .
```

Or install the dependencies directly:
```bash
pip install -r requirements.txt
```

---

## Quick Usage Guide

Once installed, you can run the tool using `http-brute`, `quickbuster`, or `python -m http_bruteforcer`.

### 1. Basic Scan
Scan a website with a wordlist:
```bash
http-brute -u https://example.com -w wordlist.txt
```

### 2. Looking for Specific Extensions
Check for file extensions (e.g., `.php`, `.html`, `.bak`):
```bash
http-brute -u https://example.com -w wordlist.txt -x php,html,bak
```

### 3. Adjust Speed & Concurrency
Control how many async workers are running (default is 50):
```bash
http-brute -u https://example.com -w wordlist.txt -c 100
```
Or enforce a maximum requests-per-second limit if you don't want to overwhelm the target:
```bash
http-brute -u https://example.com -w wordlist.txt --rate-limit 20
```

### 4. Custom Headers & User-Agent
Rotate User-Agents randomly and pass custom headers:
```bash
http-brute -u https://example.com -w wordlist.txt \
  -H "Authorization: Bearer token123" \
  -H "X-Forwarded-For: 127.0.0.1" \
  -a random
```

### 5. Saving Results
Export valid discoveries to JSON or CSV:
```bash
http-brute -u https://example.com -w wordlist.txt -oJ results.json -oC results.csv
```

---

## Options & Flags Cheat Sheet

| Flag | Description | Default |
|---|---|---|
| `-u, --url` | Target base URL (e.g. `https://example.com`) | *Required* |
| `-w, --wordlist` | Path to your wordlist file | *Required* |
| `-x, --extensions` | Comma-separated extensions to test (e.g. `php,html,json`) | None |
| `-c, --concurrency` | Number of concurrent workers | `50` |
| `-m, --method` | HTTP method (`GET`, `HEAD`, `POST`) | `GET` |
| `-H, --header` | Add custom header (can be used multiple times) | None |
| `-a, --user-agent` | Custom User-Agent string or `'random'` | Default QuickBuster UA |
| `--mc, --match-codes`| Status codes to display | `200,204,301,302,307,401,403` |
| `--fc, --filter-codes`| Status codes to completely ignore | None |
| `--fl, --filter-length`| Hide responses by exact byte length | None |
| `--filter-length-range`| Hide responses within a byte range (e.g. `100-200`) | None |
| `--filter-regex` | Exclude responses matching a regex pattern | None |
| `--follow-redirects` | Follow HTTP redirects | `False` |
| `-k, --insecure` | Ignore self-signed or invalid SSL certificates | `False` |
| `--rate-limit` | Maximum requests per second (RPS) | Unlimited |
| `--add-slash` | Append trailing slash (`/`) to test directory routes | `False` |
| `--no-calibration` | Skip the automatic soft-404 baseline calibration | `False` |
| `-oJ, --json` | Export discoveries to a JSON file | None |
| `-oC, --csv` | Export discoveries to a CSV file | None |
| `-v, --verbose` | Enable verbose logging | `False` |

---

## Running the Tests

To run the full test suite:
```bash
pytest
```
