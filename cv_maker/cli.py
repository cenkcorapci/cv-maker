"""CLI entry point for cvgen – the CV Template Generator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from cv_maker.parser.markdown_parser import MarkdownParser
from cv_maker.renderer.pdf_renderer import PDFRenderer
from cv_maker.template.extractor import TemplateExtractor, TemplateStyle


@click.group()
@click.version_option(package_name="cvgen")
def main() -> None:
    """cvgen – Generate professional CVs from Markdown and a reference PDF template."""


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Reference PDF whose visual layout will be reproduced.",
)
@click.option(
    "--data",
    "data_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Markdown file containing CV data.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, writable=True),
    help="Output PDF path.",
)
def generate(
    template_path: Optional[str],
    data_path: str,
    output_path: str,
) -> None:
    """Generate a CV PDF from a Markdown data file.

    Optionally supply a reference PDF template whose visual design will be
    used for the generated output.
    """
    parser = MarkdownParser()

    click.echo(f"Parsing CV data from: {data_path}")
    try:
        cv = parser.parse_file(data_path)
    except Exception as exc:
        click.secho(f"Error parsing Markdown file: {exc}", fg="red", err=True)
        sys.exit(1)

    # Validate and surface any warnings
    warnings = cv.validate_required_fields()
    for w in warnings:
        click.secho(f"Warning: {w}", fg="yellow", err=True)

    # Extract template style if a reference PDF was supplied
    style: Optional[TemplateStyle] = None
    if template_path:
        click.echo(f"Extracting template style from: {template_path}")
        extractor = TemplateExtractor()
        try:
            style = extractor.extract(template_path)
        except Exception as exc:
            click.secho(
                f"Warning: could not extract template style ({exc}); "
                "using default style.",
                fg="yellow",
                err=True,
            )

    renderer = PDFRenderer(template_style=style)
    click.echo(f"Rendering PDF to: {output_path}")
    try:
        renderer.render(cv, output_path)
    except Exception as exc:
        click.secho(f"Error rendering PDF: {exc}", fg="red", err=True)
        sys.exit(1)

    click.secho(f"✓ Generated: {output_path}", fg="green")


# ---------------------------------------------------------------------------
# extract-template
# ---------------------------------------------------------------------------


@main.command("extract-template")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Reference PDF to analyse.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, writable=True),
    help="Output JSON file path.",
)
def extract_template(input_path: str, output_path: str) -> None:
    """Extract layout, fonts, and colour information from a reference PDF.

    The resulting JSON file can be inspected or used as a persistent template.
    """
    extractor = TemplateExtractor()
    click.echo(f"Extracting template from: {input_path}")
    try:
        style = extractor.extract_to_file(input_path, output_path)
    except Exception as exc:
        click.secho(f"Error extracting template: {exc}", fg="red", err=True)
        sys.exit(1)

    click.secho(f"✓ Template saved to: {output_path}", fg="green")
    pg = style.page_geometry
    click.echo(f"  Page: {pg.width:.1f} × {pg.height:.1f} pt")
    click.echo(f"  Primary colour: {style.primary_color}")
    click.echo(f"  Accent colour:  {style.accent_color}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@main.command()
@click.argument("data_path", metavar="FILE", type=click.Path(exists=True, dir_okay=False))
def validate(data_path: str) -> None:
    """Validate the structure and required fields of a CV Markdown file."""
    parser = MarkdownParser()
    click.echo(f"Validating: {data_path}")
    try:
        cv, warnings = parser.validate_file(data_path)
    except Exception as exc:
        click.secho(f"Parse error: {exc}", fg="red", err=True)
        sys.exit(1)

    if warnings:
        for w in warnings:
            click.secho(f"  ⚠  {w}", fg="yellow")
        click.secho("Validation completed with warnings.", fg="yellow")
    else:
        click.secho("✓ Validation passed – no issues found.", fg="green")

    # Print a brief summary
    click.echo(f"\n  Name:       {cv.personal_info.name}")
    if cv.personal_info.title:
        click.echo(f"  Title:      {cv.personal_info.title}")
    click.echo(f"  Experience: {len(cv.experience)} entr{'y' if len(cv.experience) == 1 else 'ies'}")
    click.echo(f"  Skills:     {len(cv.skills)}")
    click.echo(f"  Education:  {len(cv.education)}")


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Reference PDF template.",
)
@click.option(
    "--data",
    "data_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Markdown file containing CV data.",
)
def preview(template_path: Optional[str], data_path: str) -> None:
    """Generate a temporary preview PDF and print its path.

    The preview is written to a temp file; the caller is responsible for
    opening it.
    """
    import tempfile

    parser = MarkdownParser()
    try:
        cv = parser.parse_file(data_path)
    except Exception as exc:
        click.secho(f"Error parsing Markdown file: {exc}", fg="red", err=True)
        sys.exit(1)

    style: Optional[TemplateStyle] = None
    if template_path:
        extractor = TemplateExtractor()
        try:
            style = extractor.extract(template_path)
        except Exception as exc:
            click.secho(
                f"Warning: could not read template ({exc}); using default style.",
                fg="yellow",
                err=True,
            )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    renderer = PDFRenderer(template_style=style)
    try:
        renderer.render(cv, tmp_path)
    except Exception as exc:
        click.secho(f"Error rendering preview: {exc}", fg="red", err=True)
        sys.exit(1)

    click.secho(f"✓ Preview written to: {tmp_path}", fg="green")
