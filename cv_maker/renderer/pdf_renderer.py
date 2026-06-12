"""PDF renderer – converts a :class:`CV` model into a styled PDF document.

Uses ReportLab as the rendering backend.  When a :class:`TemplateStyle` is
provided the renderer mirrors its typography and geometry; otherwise a clean
built-in default style is used.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as _xml_escape


def _esc(text: str) -> str:
    """Escape XML/HTML special characters in user-supplied text."""
    return _xml_escape(text)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:  # pragma: no cover
    raise ImportError(
        "reportlab is required. Install it with: pip install reportlab"
    )

from cv_maker.models.cv import (
    CV,
    ClientEngagement,
    Company,
    ConsultancyCompany,
)
from cv_maker.template.extractor import TemplateStyle


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _hex_to_color(hex_str: str) -> colors.Color:
    """Convert a ``#rrggbb`` string to a ReportLab :class:`Color`."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return colors.black
    r, g, b = (int(hex_str[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colors.Color(r, g, b)


# ---------------------------------------------------------------------------
# Style factory
# ---------------------------------------------------------------------------


class _StyleSheet:
    """Holds ReportLab ParagraphStyles derived from a :class:`TemplateStyle`."""

    def __init__(self, ts: TemplateStyle) -> None:
        self.ts = ts
        base = getSampleStyleSheet()
        pg = ts.page_geometry
        primary = _hex_to_color(ts.primary_color)
        accent = _hex_to_color(ts.accent_color)

        self.name = ParagraphStyle(
            "CVName",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=ts.name_font.size,
            textColor=primary,
            spaceAfter=2,
        )
        self.job_title = ParagraphStyle(
            "CVTitle",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=ts.title_font.size,
            textColor=accent,
            spaceAfter=6,
        )
        self.section_heading = ParagraphStyle(
            "CVSection",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=ts.section_heading_font.size,
            textColor=primary,
            spaceBefore=12,
            spaceAfter=4,
        )
        self.company = ParagraphStyle(
            "CVCompany",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=ts.company_font.size,
            textColor=primary,
            spaceAfter=1,
        )
        self.role = ParagraphStyle(
            "CVRole",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=ts.body_font.size + 0.5,
            textColor=_hex_to_color("#444444"),
            spaceAfter=1,
        )
        self.date = ParagraphStyle(
            "CVDate",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size,
            textColor=_hex_to_color("#666666"),
            spaceAfter=4,
        )
        self.body = ParagraphStyle(
            "CVBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size,
            textColor=colors.black,
            spaceAfter=2,
        )
        self.bullet = ParagraphStyle(
            "CVBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size,
            textColor=colors.black,
            leftIndent=12,
            spaceAfter=1,
        )
        self.client_company = ParagraphStyle(
            "CVClientCompany",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=ts.body_font.size,
            textColor=_hex_to_color("#333333"),
            leftIndent=20,
            spaceAfter=1,
        )
        self.client_role = ParagraphStyle(
            "CVClientRole",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=ts.body_font.size - 0.5,
            textColor=_hex_to_color("#555555"),
            leftIndent=20,
            spaceAfter=1,
        )
        self.client_date = ParagraphStyle(
            "CVClientDate",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size - 0.5,
            textColor=_hex_to_color("#777777"),
            leftIndent=20,
            spaceAfter=3,
        )
        self.client_bullet = ParagraphStyle(
            "CVClientBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size - 0.5,
            textColor=colors.black,
            leftIndent=32,
            spaceAfter=1,
        )
        self.stack = ParagraphStyle(
            "CVStack",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=ts.body_font.size - 0.5,
            textColor=_hex_to_color("#555555"),
            spaceAfter=4,
        )
        self.contact = ParagraphStyle(
            "CVContact",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=ts.body_font.size,
            textColor=_hex_to_color("#444444"),
            spaceAfter=2,
        )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class PDFRenderer:
    """Render a :class:`CV` to a PDF file."""

    def __init__(self, template_style: Optional[TemplateStyle] = None) -> None:
        self._ts = template_style or TemplateStyle()

    def render(self, cv: CV, output_path: str | Path) -> Path:
        """Render *cv* to *output_path* and return the resolved path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ts = self._ts
        pg = ts.page_geometry

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=(pg.width, pg.height),
            leftMargin=pg.margin_left,
            rightMargin=pg.margin_right,
            topMargin=pg.margin_top,
            bottomMargin=pg.margin_bottom,
        )

        ss = _StyleSheet(ts)
        story = self._build_story(cv, ss, ts)
        doc.build(story)
        return output_path

    # ------------------------------------------------------------------
    # Story builders
    # ------------------------------------------------------------------

    def _build_story(self, cv: CV, ss: _StyleSheet, ts: TemplateStyle) -> list:
        story: list = []
        primary_color = _hex_to_color(ts.primary_color)

        # ---- Header ----
        story.append(Paragraph(_esc(cv.personal_info.name), ss.name))
        if cv.personal_info.title:
            story.append(Paragraph(_esc(cv.personal_info.title), ss.job_title))

        contact_parts = []
        if cv.personal_info.email:
            e = _xml_escape(cv.personal_info.email)
            contact_parts.append(f'<a href="mailto:{e}">{e}</a>')
        if cv.personal_info.phone:
            contact_parts.append(_xml_escape(cv.personal_info.phone))
        if cv.personal_info.location:
            contact_parts.append(_xml_escape(cv.personal_info.location))
        if cv.personal_info.linkedin:
            url = _xml_escape(cv.personal_info.linkedin)
            contact_parts.append(f'<a href="{url}">{url}</a>')
        if cv.personal_info.github:
            url = _xml_escape(cv.personal_info.github)
            contact_parts.append(f'<a href="{url}">{url}</a>')
        if cv.personal_info.website:
            url = _xml_escape(cv.personal_info.website)
            contact_parts.append(f'<a href="{url}">{url}</a>')

        if contact_parts:
            story.append(Paragraph("  |  ".join(contact_parts), ss.contact))

        story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=6))

        # ---- Summary ----
        if cv.summary:
            story.append(Paragraph("SUMMARY", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            story.append(Paragraph(_esc(cv.summary), ss.body))

        # ---- Experience ----
        if cv.experience:
            story.append(Paragraph("EXPERIENCE", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            for entry in cv.experience:
                if isinstance(entry, ConsultancyCompany):
                    story.extend(self._render_consultancy(entry, ss))
                else:
                    story.extend(self._render_company(entry, ss))

        # ---- Skills ----
        if cv.skills:
            story.append(Paragraph("SKILLS", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            story.append(Paragraph(_esc(", ".join(cv.skills)), ss.body))

        # ---- Education ----
        if cv.education:
            story.append(Paragraph("EDUCATION", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            for edu in cv.education:
                story.append(Paragraph(_esc(edu.institution), ss.company))
                parts = []
                if edu.degree:
                    parts.append(_esc(edu.degree))
                if edu.field_of_study:
                    parts.append(_esc(edu.field_of_study))
                if parts:
                    story.append(Paragraph(", ".join(parts), ss.role))
                if edu.start_date or edu.end_date:
                    date_str = " – ".join(filter(None, [edu.start_date, edu.end_date]))
                    story.append(Paragraph(_esc(date_str), ss.date))
                if edu.description:
                    story.append(Paragraph(_esc(edu.description), ss.body))
                story.append(Spacer(1, 4))

        # ---- Languages ----
        if cv.languages:
            story.append(Paragraph("LANGUAGES", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            story.append(Paragraph(_esc(", ".join(cv.languages)), ss.body))

        # ---- Certifications ----
        if cv.certifications:
            story.append(Paragraph("CERTIFICATIONS", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            for cert in cv.certifications:
                story.append(Paragraph(f"• {_esc(cert)}", ss.bullet))

        # ---- Achievements ----
        if cv.achievements:
            story.append(Paragraph("ACHIEVEMENTS", ss.section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=primary_color, spaceAfter=4))
            for ach in cv.achievements:
                story.append(Paragraph(f"• {_esc(ach)}", ss.bullet))

        return story

    def _render_company(self, company: Company, ss: _StyleSheet) -> list:
        items: list = []
        items.append(Paragraph(_esc(company.name), ss.company))
        if company.role:
            items.append(Paragraph(_esc(company.role), ss.role))
        date_parts = filter(None, [company.start_date, company.end_date])
        date_str = " – ".join(date_parts)
        loc_date = "  |  ".join(filter(None, [company.location, date_str]))
        if loc_date:
            items.append(Paragraph(_esc(loc_date), ss.date))
        for resp in company.responsibilities:
            items.append(Paragraph(f"• {_esc(resp)}", ss.bullet))
        if company.stack:
            items.append(Paragraph(f"Stack: {_esc(company.stack)}", ss.stack))
        items.append(Spacer(1, 6))
        return items

    def _render_consultancy(self, company: ConsultancyCompany, ss: _StyleSheet) -> list:
        items: list = []
        items.append(Paragraph(_esc(company.name), ss.company))
        if company.role:
            items.append(Paragraph(_esc(company.role), ss.role))
        date_parts = list(filter(None, [company.start_date, company.end_date]))
        date_str = " – ".join(date_parts)
        loc_date = "  |  ".join(filter(None, [company.location, date_str]))
        if loc_date:
            items.append(Paragraph(_esc(loc_date), ss.date))

        for client in company.clients:
            items.extend(self._render_client(client, ss))

        items.append(Spacer(1, 6))
        return items

    def _render_client(self, client: ClientEngagement, ss: _StyleSheet) -> list:
        items: list = []
        items.append(Paragraph(_esc(client.client_name), ss.client_company))
        if client.role:
            items.append(Paragraph(_esc(client.role), ss.client_role))
        date_str = "  |  ".join(filter(None, [client.start_date, client.end_date]))
        if date_str:
            items.append(Paragraph(_esc(date_str), ss.client_date))
        for ach in client.achievements:
            items.append(Paragraph(f"• {_esc(ach)}", ss.client_bullet))
        if client.tech_stack:
            items.append(Paragraph(f"Stack: {_esc(', '.join(client.tech_stack))}", ss.client_date))
        return items
