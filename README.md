# open-export

Download and archive all your ChatGPT conversations as JSON and Markdown files.

Connects to your active browser session via Chrome DevTools Protocol (CDP) — no credentials or API keys needed. You stay logged in through your browser; the tool piggybacks on that authenticated session.

## Installation

```bash
pip install -e .
```

## Usage

### 1. Launch your browser with remote debugging enabled

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

> **Important:** Close all browser windows before running the command above. The `--remote-debugging-port` flag is ignored if the browser is already running.

### 2. Log into ChatGPT

Navigate to [chatgpt.com](https://chatgpt.com) in the browser you just launched and make sure you're logged in.

### 3. Run the exporter

```bash
python -m open_export.cli -o ./my_chats
```

Or if the CLI entry point is on your PATH:

```bash
open-export -o ./my_chats
```

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

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
