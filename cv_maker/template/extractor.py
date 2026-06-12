"""PDF template extractor – analyses a reference PDF and produces a
:class:`TemplateStyle` that the renderer can use to reproduce the look."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PageGeometry:
    """Physical dimensions and margins of a page."""

    width: float = 595.28  # A4 default in points
    height: float = 841.89
    margin_top: float = 50.0
    margin_bottom: float = 50.0
    margin_left: float = 50.0
    margin_right: float = 50.0


@dataclass
class FontStyle:
    """Describes font usage for a particular text role."""

    family: str = "Helvetica"
    size: float = 10.0
    bold: bool = False
    italic: bool = False
    color: str = "#000000"  # hex string


@dataclass
class LayoutRegion:
    """A named rectangular region on the page."""

    name: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class TemplateStyle:
    """All styling information extracted from a reference PDF."""

    page_geometry: PageGeometry = field(default_factory=PageGeometry)
    primary_color: str = "#1a1a2e"
    accent_color: str = "#e94560"
    background_color: str = "#ffffff"
    name_font: FontStyle = field(
        default_factory=lambda: FontStyle(family="Helvetica", size=24, bold=True)
    )
    title_font: FontStyle = field(
        default_factory=lambda: FontStyle(family="Helvetica", size=14, italic=True)
    )
    section_heading_font: FontStyle = field(
        default_factory=lambda: FontStyle(family="Helvetica", size=12, bold=True)
    )
    body_font: FontStyle = field(default_factory=lambda: FontStyle(size=9))
    company_font: FontStyle = field(
        default_factory=lambda: FontStyle(family="Helvetica", size=10, bold=True)
    )
    layout_regions: list[LayoutRegion] = field(default_factory=list)
    columns: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateStyle":
        pg = PageGeometry(**data.get("page_geometry", {}))
        def _font(d: dict[str, Any]) -> FontStyle:
            return FontStyle(**d) if d else FontStyle()

        regions = [LayoutRegion(**r) for r in data.get("layout_regions", [])]
        return cls(
            page_geometry=pg,
            primary_color=data.get("primary_color", "#1a1a2e"),
            accent_color=data.get("accent_color", "#e94560"),
            background_color=data.get("background_color", "#ffffff"),
            name_font=_font(data.get("name_font", {})),
            title_font=_font(data.get("title_font", {})),
            section_heading_font=_font(data.get("section_heading_font", {})),
            body_font=_font(data.get("body_font", {})),
            company_font=_font(data.get("company_font", {})),
            layout_regions=regions,
            columns=data.get("columns", 1),
        )

    def save_json(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load_json(cls, path: str | Path) -> "TemplateStyle":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def _rgb_to_hex(color: Any) -> str:
    """Convert a pdfplumber colour value to a hex string."""
    if color is None:
        return "#000000"
    if isinstance(color, (list, tuple)) and len(color) == 3:
        r, g, b = (int(c * 255) if isinstance(c, float) else int(c) for c in color)
        return f"#{r:02x}{g:02x}{b:02x}"
    if isinstance(color, str):
        return color
    return "#000000"


class TemplateExtractor:
    """Analyse a reference PDF and extract its visual style into a
    :class:`TemplateStyle` object."""

    def extract(self, pdf_path: str | Path) -> TemplateStyle:
        """Extract style information from *pdf_path*."""
        if pdfplumber is None:
            raise ImportError(
                "pdfplumber is required for template extraction. "
                "Install it with: pip install pdfplumber"
            )

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Template PDF not found: {pdf_path}")

        style = TemplateStyle()

        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return style

            first_page = pdf.pages[0]

            # Page geometry
            style.page_geometry = PageGeometry(
                width=float(first_page.width),
                height=float(first_page.height),
            )

            # Analyse text objects to infer font roles and colours
            chars = first_page.chars
            if chars:
                style = self._infer_fonts(chars, style)
                style = self._infer_colors(chars, style)
                style = self._infer_margins(chars, style)

        return style

    def extract_to_file(self, pdf_path: str | Path, output_path: str | Path) -> TemplateStyle:
        """Extract style from *pdf_path* and save JSON to *output_path*."""
        style = self.extract(pdf_path)
        style.save_json(output_path)
        return style

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _infer_fonts(self, chars: list[dict[str, Any]], style: TemplateStyle) -> TemplateStyle:
        """Heuristically map font sizes to named roles."""
        # Collect (size, text) pairs
        sizes: list[float] = sorted(
            {float(c.get("size", 10)) for c in chars}, reverse=True
        )
        if not sizes:
            return style

        def _font_from_char(c: dict[str, Any]) -> FontStyle:
            fontname = str(c.get("fontname", "Helvetica"))
            bold = "Bold" in fontname or "bold" in fontname
            italic = "Italic" in fontname or "italic" in fontname or "Oblique" in fontname
            family = fontname.split("-")[0].split("+")[-1]
            color = _rgb_to_hex(c.get("non_stroking_color"))
            return FontStyle(
                family=family,
                size=float(c.get("size", 10)),
                bold=bold,
                italic=italic,
                color=color,
            )

        # Build size → representative char map
        size_to_char: dict[float, dict[str, Any]] = {}
        for c in chars:
            sz = float(c.get("size", 10))
            if sz not in size_to_char:
                size_to_char[sz] = c

        if len(sizes) >= 1:
            style.name_font = _font_from_char(size_to_char[sizes[0]])
        if len(sizes) >= 2:
            style.title_font = _font_from_char(size_to_char[sizes[1]])
        if len(sizes) >= 3:
            style.section_heading_font = _font_from_char(size_to_char[sizes[2]])
        if len(sizes) >= 4:
            style.body_font = _font_from_char(size_to_char[sizes[-1]])
            style.company_font = _font_from_char(size_to_char[sizes[3]])

        return style

    def _infer_colors(self, chars: list[dict[str, Any]], style: TemplateStyle) -> TemplateStyle:
        """Try to detect primary and accent colours."""
        color_counts: dict[str, int] = {}
        for c in chars:
            col = _rgb_to_hex(c.get("non_stroking_color"))
            if col != "#000000" and col != "#ffffff":
                color_counts[col] = color_counts.get(col, 0) + 1

        if color_counts:
            sorted_colors = sorted(color_counts, key=lambda k: color_counts[k], reverse=True)
            style.primary_color = sorted_colors[0]
            if len(sorted_colors) > 1:
                style.accent_color = sorted_colors[1]

        return style

    def _infer_margins(self, chars: list[dict[str, Any]], style: TemplateStyle) -> TemplateStyle:
        """Estimate page margins from the bounding box of all characters."""
        x0s = [float(c["x0"]) for c in chars if "x0" in c]
        x1s = [float(c["x1"]) for c in chars if "x1" in c]
        y0s = [float(c["top"]) for c in chars if "top" in c]
        y1s = [float(c["bottom"]) for c in chars if "bottom" in c]

        if x0s:
            style.page_geometry.margin_left = min(x0s)
        if x1s:
            style.page_geometry.margin_right = style.page_geometry.width - max(x1s)
        if y0s:
            style.page_geometry.margin_top = min(y0s)
        if y1s:
            style.page_geometry.margin_bottom = style.page_geometry.height - max(y1s)

        return style

    def describe(self, pdf_path: str | Path) -> dict[str, Any]:
        """Return a human-readable description dict for *pdf_path*."""
        style = self.extract(pdf_path)
        return style.to_dict()
