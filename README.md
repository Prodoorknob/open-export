# open-export

[![PyPI](https://img.shields.io/pypi/v/open-export?v=2)](https://pypi.org/project/open-export/)
[![Python](https://img.shields.io/pypi/pyversions/open-export?v=2)](https://pypi.org/project/open-export/)
[![License](https://img.shields.io/pypi/l/open-export?v=2)](https://github.com/Prodoorknob/open-export/blob/main/LICENSE)
[![GitHub](https://img.shields.io/github/stars/Prodoorknob/open-export?v=2)](https://github.com/Prodoorknob/open-export)

Download and archive all your ChatGPT conversations as JSON and Markdown files.

---

> **BEFORE YOU USE THIS TOOL, READ THIS.**
>
> **Why does this tool exist?** ChatGPT does not provide an API to export your conversation history. The built-in "Export data" feature emails you a zip file hours later and cannot be automated. Many users on enterprise, university, or managed accounts have this option disabled entirely. This tool gives you a way to programmatically back up your own conversations.
>
> **How does it work?** It connects to your browser through the Chrome DevTools Protocol (CDP). You open your browser with a special flag (`--remote-debugging-port=9222`), and the tool reads your ChatGPT data through that browser session. It never sees your password or login credentials.
>
> **What is the risk?** While port 9222 is open, **any program running on your computer** can access your browser session -- your cookies, your tabs, your logged-in accounts. This is the same mechanism used by browser developer tools, but it also means malicious software on your machine could exploit it.
>
> **How to stay safe:**
> 1. Only run this tool on a machine you trust
> 2. Do not run untrusted software while port 9222 is open
> 3. **Close your browser completely as soon as the export finishes** -- this kills the debugging port
> 4. Review the source code yourself: the entire tool is ~400 lines across 4 Python files — [view source on GitHub](https://github.com/Prodoorknob/open-export)

---

## Installation

```bash
pip install open-export
```

## Usage

### 1. Close all browser windows

Fully quit your browser first (check the system tray on Windows). The debugging flag is ignored if the browser is already running.

### 2. Relaunch with remote debugging enabled

**Edge** (Windows):
```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

**Chrome** (Windows):
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Chrome** (macOS/Linux):
```bash
google-chrome --remote-debugging-port=9222
```

### 3. Log into ChatGPT

Navigate to [chatgpt.com](https://chatgpt.com) in that browser window and make sure you're logged in.

### 4. Run the exporter

```bash
open-export -o ./my_chats
```

Or:

```bash
python -m open_export.cli -o ./my_chats
```

### 5. Close your browser

Once the export finishes, **close all browser windows immediately** to shut down the debugging port.

## Options

| Option | Default | Description |
|---|---|---|
| `--output`, `-o` | `./open_export_output` | Output directory |
| `--cdp-url` | `http://localhost:9222` | Chrome DevTools Protocol URL |
| `--delay` | `1.0` | Seconds between API requests |
| `--page-size` | `100` | Conversations per page |
| `--verbose`, `-v` | off | Debug logging |
| `--version` | | Show version |

## Output

```
my_chats/
  json/           # Raw API responses (one file per conversation)
  markdown/       # Human-readable formatted conversations
```

## How it works

1. Connects to your running browser via CDP (`connect_over_cdp`)
2. Finds an open ChatGPT tab (or navigates to one)
3. Fetches an access token from ChatGPT's session endpoint
4. Paginates through the conversation list API
5. Downloads each conversation's full data
6. Exports as JSON (raw) and Markdown (readable)

The access token is used only during the session and cleared from memory on exit. No credentials are stored on disk.

## Security details

- **No network calls** are made to any server other than `chatgpt.com`. The tool writes files locally and does not transmit your data anywhere.
- **Fully open source.** Every line of code is in this repository.
- **Access tokens are ephemeral.** The token is fetched from ChatGPT's own session endpoint, used for the download, and cleared from memory on exit. It is never written to disk or logged.
- **No credentials stored.** The tool does not ask for, store, or transmit your username or password.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
