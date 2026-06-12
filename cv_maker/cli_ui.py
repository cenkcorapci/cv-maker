"""Shared terminal output helpers for the cvgen CLI."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import click


@dataclass
class UI:
    """Format CLI messages consistently across commands."""

    verbose: bool = False
    quiet: bool = False

    def step(self, message: str) -> None:
        if not self.quiet:
            click.echo(click.style("→ ", fg="cyan", bold=True) + message)

    def detail(self, message: str) -> None:
        if self.verbose and not self.quiet:
            click.echo(click.style("  ", dim=True) + message)

    def info(self, message: str) -> None:
        if not self.quiet:
            click.echo(message)

    def success(self, message: str) -> None:
        if not self.quiet:
            click.secho(f"✓ {message}", fg="green")

    def result_path(self, path: str, label: str = "Generated") -> None:
        if self.quiet:
            click.echo(path)
        else:
            click.secho(f"✓ {label} {path}", fg="green")

    def warn(self, message: str) -> None:
        click.secho(f"⚠  {message}", fg="yellow", err=True)

    def error(self, message: str) -> None:
        click.secho(f"✗ {message}", fg="red", err=True)

    def heading(self, title: str) -> None:
        if not self.quiet:
            click.echo()
            click.secho(title, fg="cyan", bold=True)

    def summary_row(self, label: str, value: str) -> None:
        if not self.quiet:
            click.echo(f"  {label:<14} {value}")

    def exit_with_error(self, message: str, code: int = 1) -> None:
        self.error(message)
        sys.exit(code)


def default_pdf_output(data_path: str) -> str:
    """Derive an output PDF path from a Markdown data file."""
    from pathlib import Path

    return str(Path(data_path).with_suffix(".pdf"))
