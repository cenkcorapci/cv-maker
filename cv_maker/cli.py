"""CLI entry point for cvgen – the CV Template Generator."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Optional

import click

from cv_maker.cli_ui import UI, default_pdf_output
from cv_maker.parser.markdown_parser import MarkdownParser
from cv_maker.renderer.pdf_renderer import PDFRenderer
from cv_maker.template.extractor import TemplateExtractor, TemplateStyle

EXAMPLES = """
Examples:

  \b
  # Validate your Markdown CV before generating
  cvgen validate my-cv.md

  \b
  # Generate a PDF (output defaults to my-cv.pdf)
  cvgen generate --data my-cv.md

  \b
  # Match the look of an existing PDF résumé
  cvgen generate --data my-cv.md --template reference.pdf --output cv.pdf

  \b
  # Quick preview and open it (macOS)
  cvgen preview --data my-cv.md --open

  \b
  # Extract colours and layout from a reference PDF
  cvgen extract-template --input reference.pdf --output template.json
"""


def _ui_from_ctx(ctx: click.Context) -> UI:
    return ctx.ensure_object(UI)


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 100,
    },
    epilog=EXAMPLES,
)
@click.version_option(package_name="cvgen", prog_name="cvgen")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show extra detail while a command runs.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Only print errors and the final result path.",
)
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """Generate professional CV PDFs from Markdown.

    Write your CV in a simple Markdown format, optionally match the visual
    style of a reference PDF, and export a print-ready document.
    """
    ctx.obj = UI(verbose=verbose, quiet=quiet)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "-t",
    "--template",
    "template_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Reference PDF whose layout and colours are reproduced.",
)
@click.option(
    "-d",
    "--data",
    "data_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Markdown file with your CV content.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="Output PDF path (defaults to the data filename with a .pdf extension).",
)
@click.pass_context
def generate(
    ctx: click.Context,
    template_path: Optional[Path],
    data_path: Path,
    output_path: Optional[Path],
) -> None:
    """Build a CV PDF from Markdown data."""
    ui = _ui_from_ctx(ctx)
    out = output_path or Path(default_pdf_output(str(data_path)))
    parser = MarkdownParser()

    ui.step(f"Parsing {data_path}")
    try:
        cv = parser.parse_file(str(data_path))
    except Exception as exc:
        ui.exit_with_error(f"Could not parse Markdown: {exc}")

    ui.detail(
        f"{len(cv.experience)} experience, {len(cv.skills)} skills, "
        f"{len(cv.education)} education"
    )

    warnings = cv.validate_required_fields()
    for warning in warnings:
        ui.warn(warning)

    style: Optional[TemplateStyle] = None
    if template_path:
        ui.step(f"Reading template from {template_path}")
        extractor = TemplateExtractor()
        try:
            style = extractor.extract(str(template_path))
            ui.detail(
                f"Page {style.page_geometry.width:.0f}×{style.page_geometry.height:.0f} pt, "
                f"primary {style.primary_color}"
            )
        except Exception as exc:
            ui.warn(f"Could not read template ({exc}); using default style.")

    ui.step(f"Rendering {out}")
    renderer = PDFRenderer(template_style=style)
    try:
        renderer.render(cv, str(out))
    except Exception as exc:
        ui.exit_with_error(f"Could not render PDF: {exc}")

    ui.result_path(str(out))


# ---------------------------------------------------------------------------
# extract-template
# ---------------------------------------------------------------------------


@main.command("extract-template")
@click.option(
    "-i",
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Reference PDF to analyse.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="JSON file to write the extracted style to.",
)
@click.pass_context
def extract_template(
    ctx: click.Context,
    input_path: Path,
    output_path: Path,
) -> None:
    """Extract layout, fonts, and colours from a reference PDF."""
    ui = _ui_from_ctx(ctx)
    extractor = TemplateExtractor()

    ui.step(f"Analysing {input_path}")
    try:
        style = extractor.extract_to_file(str(input_path), str(output_path))
    except Exception as exc:
        ui.exit_with_error(f"Could not extract template: {exc}")

    ui.result_path(str(output_path), label="Template saved to")
    pg = style.page_geometry
    ui.heading("Extracted style")
    ui.summary_row("Page size", f"{pg.width:.1f} × {pg.height:.1f} pt")
    ui.summary_row("Primary", style.primary_color)
    ui.summary_row("Accent", style.accent_color)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@main.command()
@click.argument(
    "data_path",
    metavar="FILE",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.pass_context
def validate(ctx: click.Context, data_path: Path) -> None:
    """Check a CV Markdown file for structural issues."""
    ui = _ui_from_ctx(ctx)
    parser = MarkdownParser()

    ui.step(f"Validating {data_path}")
    try:
        cv, warnings = parser.validate_file(str(data_path))
    except Exception as exc:
        ui.exit_with_error(f"Parse error: {exc}")

    if warnings:
        ui.heading("Warnings")
        for warning in warnings:
            ui.warn(warning)
        ui.info("")
        ui.warn("Validation completed with warnings.")
    else:
        ui.success("Validation passed")

    ui.heading("Summary")
    ui.summary_row("Name", cv.personal_info.name)
    if cv.personal_info.title:
        ui.summary_row("Title", cv.personal_info.title)
    exp_label = "entry" if len(cv.experience) == 1 else "entries"
    ui.summary_row("Experience", f"{len(cv.experience)} {exp_label}")
    ui.summary_row("Skills", str(len(cv.skills)))
    ui.summary_row("Education", str(len(cv.education)))


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "-t",
    "--template",
    "template_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Reference PDF template.",
)
@click.option(
    "-d",
    "--data",
    "data_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Markdown file with your CV content.",
)
@click.option(
    "--open/--no-open",
    "open_file",
    default=False,
    help="Open the preview PDF after rendering (macOS and Linux).",
)
@click.pass_context
def preview(
    ctx: click.Context,
    template_path: Optional[Path],
    data_path: Path,
    open_file: bool,
) -> None:
    """Render a temporary preview PDF."""
    import tempfile

    ui = _ui_from_ctx(ctx)
    parser = MarkdownParser()

    ui.step(f"Parsing {data_path}")
    try:
        cv = parser.parse_file(str(data_path))
    except Exception as exc:
        ui.exit_with_error(f"Could not parse Markdown: {exc}")

    style: Optional[TemplateStyle] = None
    if template_path:
        ui.step(f"Reading template from {template_path}")
        extractor = TemplateExtractor()
        try:
            style = extractor.extract(str(template_path))
        except Exception as exc:
            ui.warn(f"Could not read template ({exc}); using default style.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    ui.step("Rendering preview")
    renderer = PDFRenderer(template_style=style)
    try:
        renderer.render(cv, tmp_path)
    except Exception as exc:
        ui.exit_with_error(f"Could not render preview: {exc}")

    ui.result_path(tmp_path, label="Preview written to")

    if open_file:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        try:
            subprocess.run([opener, tmp_path], check=True)
            ui.detail(f"Opened with {opener}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            ui.warn(f"Could not open preview automatically; run: {opener} {tmp_path}")
