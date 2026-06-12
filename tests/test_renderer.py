"""Tests for the PDF renderer."""

import os
from pathlib import Path

import pytest

from cv_maker.models.cv import CV, ClientEngagement, Company, ConsultancyCompany, PersonalInfo
from cv_maker.parser.markdown_parser import MarkdownParser
from cv_maker.renderer.pdf_renderer import PDFRenderer
from cv_maker.template.extractor import TemplateStyle

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_cv() -> CV:
    return CV(
        personal_info=PersonalInfo(
            name="Alice Smith",
            title="Data Engineer",
            email="alice@example.com",
            phone="+1 555 0000",
            location="Amsterdam",
        ),
        summary="Experienced data engineer.",
        skills=["Python", "Spark"],
        languages=["English (C2)", "Dutch (B2)"],
        experience=[
            Company(
                name="Acme Corp",
                role="Engineer",
                start_date="2023-01",
                end_date="Present",
                responsibilities=["Built pipelines", "Led team"],
                stack="Python, Kafka",
            ),
            ConsultancyCompany(
                name="Consulting Inc",
                role="Senior Consultant",
                start_date="2021-01",
                end_date="2022-12",
                clients=[
                    ClientEngagement(
                        client_name="Big Bank",
                        role="Data Analyst",
                        start_date="2021-01",
                        end_date="2021-06",
                        achievements=["Improved reporting"],
                        tech_stack=["SQL", "Tableau"],
                    )
                ],
            ),
        ],
        certifications=["GCP Professional"],
        achievements=["Speaker at Summit"],
    )


class TestPDFRenderer:
    def test_render_creates_file(self, tmp_path):
        cv = _make_cv()
        renderer = PDFRenderer()
        out = tmp_path / "output.pdf"
        result = renderer.render(cv, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_render_pdf_has_pdf_header(self, tmp_path):
        cv = _make_cv()
        renderer = PDFRenderer()
        out = tmp_path / "output.pdf"
        renderer.render(cv, out)
        with open(out, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_render_with_custom_style(self, tmp_path):
        cv = _make_cv()
        style = TemplateStyle()
        style.primary_color = "#003366"
        style.accent_color = "#ff6600"
        renderer = PDFRenderer(template_style=style)
        out = tmp_path / "styled.pdf"
        renderer.render(cv, out)
        assert out.exists()

    def test_render_minimal_cv(self, tmp_path):
        cv = CV(personal_info=PersonalInfo(name="Bob"))
        renderer = PDFRenderer()
        out = tmp_path / "minimal.pdf"
        renderer.render(cv, out)
        assert out.exists()

    def test_render_creates_parent_dirs(self, tmp_path):
        cv = _make_cv()
        renderer = PDFRenderer()
        out = tmp_path / "nested" / "dir" / "cv.pdf"
        renderer.render(cv, out)
        assert out.exists()

    def test_render_from_full_fixture(self, tmp_path):
        parser = MarkdownParser()
        cv = parser.parse_file(str(FIXTURES_DIR / "sample.md"))
        renderer = PDFRenderer()
        out = tmp_path / "cenk_cv.pdf"
        renderer.render(cv, out)
        assert out.exists()
        assert out.stat().st_size > 0
