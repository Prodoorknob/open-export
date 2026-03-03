"""CLI entry point for open-export."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@click.command()
@click.option(
    "--output", "-o",
    default="./open_export_output",
    type=click.Path(),
    help="Output directory for exported files.",
)
@click.option(
    "--cdp-url",
    default="http://localhost:9222",
    help="Chrome DevTools Protocol URL.",
)
@click.option(
    "--delay",
    default=1.0,
    type=float,
    help="Seconds to wait between API requests (rate limiting).",
)
@click.option(
    "--page-size",
    default=100,
    type=int,
    help="Number of conversations per page when listing.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.version_option(version="0.1.0", prog_name="open-export")
def main(output: str, cdp_url: str, delay: float, page_size: int, verbose: bool) -> None:
    """Download all ChatGPT conversations and export as JSON + Markdown.

    \b
    Prerequisites:
      1. Start Chrome with: chrome --remote-debugging-port=9222
      2. Open chatgpt.com and log in
      3. Run this command
    """
    _setup_logging(verbose)
    asyncio.run(_download(output, cdp_url, delay, page_size))


async def _download(output: str, cdp_url: str, delay: float, page_size: int) -> None:
    from open_export.browser import ChatGPTBrowser
    from open_export.exporter import export_all
    from open_export.scraper import fetch_all_conversations

    output_dir = Path(output)

    console.print(
        f"\n[bold cyan]Open Export[/bold cyan]\n\n"
        f"  CDP URL:    {cdp_url}\n"
        f"  Output:     {output_dir.resolve()}\n"
        f"  Delay:      {delay}s between requests\n"
        f"  Page size:  {page_size}\n"
    )

    console.print("[bold]Connecting to Chrome...[/bold]")
    try:
        async with ChatGPTBrowser(cdp_url=cdp_url) as browser:
            console.print("[green]Connected.[/green]\n")

            progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console,
            )

            with progress:
                task_id = progress.add_task("Fetching conversation list...", total=None)

                def on_progress(current: int, total: int, title: str) -> None:
                    if progress.tasks[task_id].total is None:
                        progress.update(
                            task_id, total=total, description="Downloading conversations"
                        )
                    progress.update(task_id, completed=current)

                result = await fetch_all_conversations(
                    browser,
                    page_size=page_size,
                    delay=delay,
                    on_progress=on_progress,
                )

            console.print(
                f"\n[bold]Download complete.[/bold]\n"
                f"  Fetched:  {len(result.conversations)} conversations\n"
                f"  Failed:   {len(result.failed)}\n"
                f"  Total:    {result.total_listed}\n"
            )

            if result.failed:
                console.print("[yellow]Failed conversations:[/yellow]")
                for conv_id, title, error in result.failed:
                    console.print(f"  - {title} ({conv_id[:8]}...): {error[:80]}")
                console.print()

    except ConnectionError as e:
        console.print(f"\n[red bold]Connection failed:[/red bold] {e}")
        console.print(
            "\n[yellow]Make sure Chrome is running with:[/yellow]\n"
            "  chrome.exe --remote-debugging-port=9222\n"
            "\nThen open chatgpt.com and log in before running this tool.\n"
        )
        sys.exit(1)

    if not result.conversations:
        console.print("[red]No conversations to export.[/red]")
        sys.exit(1)

    console.print("[bold]Exporting files...[/bold]")
    json_paths, md_paths = export_all(result.conversations, output_dir)

    console.print(
        f"\n[green bold]Done![/green bold]\n"
        f"  JSON files:     {len(json_paths)} -> {output_dir / 'json'}\n"
        f"  Markdown files: {len(md_paths)} -> {output_dir / 'markdown'}\n"
    )


if __name__ == "__main__":
    main()
