"""Tests for the Markdown parser."""

from pathlib import Path

import pytest

from cv_maker.models.cv import Company, ConsultancyCompany
from cv_maker.parser.markdown_parser import MarkdownParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestMarkdownParser:
    def setup_method(self):
        self.parser = MarkdownParser()

    # ------------------------------------------------------------------
    # Personal section
    # ------------------------------------------------------------------

    def test_parse_personal_name(self):
        md = "# Personal\nname: Cenk Corapci\ntitle: Engineer\n"
        cv = self.parser.parse(md)
        assert cv.personal_info.name == "Cenk Corapci"
        assert cv.personal_info.title == "Engineer"

    def test_parse_personal_contact(self):
        md = (
            "# Personal\n"
            "name: Alice\n"
            "email: alice@example.com\n"
            "phone: +1 555 0000\n"
            "location: New York\n"
        )
        cv = self.parser.parse(md)
        assert cv.personal_info.email == "alice@example.com"
        assert cv.personal_info.phone == "+1 555 0000"
        assert cv.personal_info.location == "New York"

    def test_parse_personal_social_links(self):
        md = (
            "# Personal\n"
            "name: Bob\n"
            "linkedin: https://linkedin.com/in/bob\n"
            "github: https://github.com/bob\n"
            "website: https://bob.dev\n"
        )
        cv = self.parser.parse(md)
        assert cv.personal_info.linkedin == "https://linkedin.com/in/bob"
        assert cv.personal_info.github == "https://github.com/bob"
        assert cv.personal_info.website == "https://bob.dev"

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def test_parse_summary(self):
        md = "# Personal\nname: Alice\n\n# Summary\n\nExperienced engineer.\n"
        cv = self.parser.parse(md)
        assert cv.summary == "Experienced engineer."

    def test_summary_none_when_absent(self):
        md = "# Personal\nname: Alice\n"
        cv = self.parser.parse(md)
        assert cv.summary is None

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def test_parse_skills_bullets(self):
        md = "# Personal\nname: A\n\n# Skills\n\n- Python\n- Scala\n"
        cv = self.parser.parse(md)
        assert "Python" in cv.skills
        assert "Scala" in cv.skills

    def test_parse_skills_comma_separated(self):
        md = "# Personal\nname: A\n\n# Skills\n\nPython, Scala, Spark\n"
        cv = self.parser.parse(md)
        assert "Python" in cv.skills
        assert "Scala" in cv.skills
        assert "Spark" in cv.skills

    # ------------------------------------------------------------------
    # Experience – regular company
    # ------------------------------------------------------------------

    def test_parse_single_company(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Experience\n\n"
            "## KLM\n\n"
            "role: Staff Engineer\n"
            "start: 2025-01\n"
            "end: Present\n\n"
            "### Responsibilities\n\n"
            "- Built things\n"
            "- Led team\n"
        )
        cv = self.parser.parse(md)
        assert len(cv.experience) == 1
        entry = cv.experience[0]
        assert isinstance(entry, Company)
        assert entry.name == "KLM"
        assert entry.role == "Staff Engineer"
        assert entry.start_date == "2025-01"
        assert "Built things" in entry.responsibilities

    def test_parse_company_with_stack(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Experience\n\n"
            "## Acme\n\n"
            "role: Engineer\n\n"
            "### Responsibilities\n\n"
            "- Did stuff\n\n"
            "### Stack\n\n"
            "Python, Spark\n"
        )
        cv = self.parser.parse(md)
        entry = cv.experience[0]
        assert isinstance(entry, Company)
        assert "Python" in entry.stack or entry.stack is not None

    # ------------------------------------------------------------------
    # Experience – consultancy
    # ------------------------------------------------------------------

    def test_parse_consultancy_basic(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Experience\n\n"
            "## Consultancy: Adyen\n\n"
            "role: Senior Data Engineer\n"
            "start: 2024-10\n"
            "end: 2025-09\n\n"
            "### Client: ING\n\n"
            "role: Data Engineer\n"
            "start: 2024-10\n"
            "end: 2025-03\n\n"
            "- Built streaming pipelines\n\n"
            "### Client: ABN AMRO\n\n"
            "role: Senior Data Engineer\n"
            "start: 2025-03\n"
            "end: 2025-09\n\n"
            "- Built ML infrastructure\n"
        )
        cv = self.parser.parse(md)
        assert len(cv.experience) == 1
        entry = cv.experience[0]
        assert isinstance(entry, ConsultancyCompany)
        assert entry.name == "Adyen"
        assert entry.role == "Senior Data Engineer"
        assert len(entry.clients) == 2

        ing = entry.clients[0]
        assert ing.client_name == "ING"
        assert ing.role == "Data Engineer"
        assert "Built streaming pipelines" in ing.achievements

        abn = entry.clients[1]
        assert abn.client_name == "ABN AMRO"
        assert "Built ML infrastructure" in abn.achievements

    def test_parse_consultancy_and_regular_mixed(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Experience\n\n"
            "## KLM\n\nrole: Engineer\n\n"
            "## Consultancy: Accenture\n\nrole: Consultant\n\n"
            "### Client: BigBank\n\nrole: Analyst\n\n- Did analysis\n"
        )
        cv = self.parser.parse(md)
        assert len(cv.experience) == 2
        assert isinstance(cv.experience[0], Company)
        assert isinstance(cv.experience[1], ConsultancyCompany)

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------

    def test_parse_education(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Education\n\n"
            "## TU Delft\n\n"
            "degree: MSc\n"
            "field: Computer Science\n"
            "start: 2017\n"
            "end: 2019\n"
        )
        cv = self.parser.parse(md)
        assert len(cv.education) == 1
        edu = cv.education[0]
        assert edu.institution == "TU Delft"
        assert edu.degree == "MSc"
        assert edu.start_date == "2017"
        assert edu.end_date == "2019"

    # ------------------------------------------------------------------
    # Certifications & Achievements
    # ------------------------------------------------------------------

    def test_parse_certifications(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Certifications\n\n"
            "- GCP Data Engineer\n"
            "- AWS Solutions Architect\n"
        )
        cv = self.parser.parse(md)
        assert "GCP Data Engineer" in cv.certifications
        assert "AWS Solutions Architect" in cv.certifications

    def test_parse_achievements(self):
        md = (
            "# Personal\nname: A\n\n"
            "# Achievements\n\n"
            "- Speaker at Summit 2024\n"
        )
        cv = self.parser.parse(md)
        assert "Speaker at Summit 2024" in cv.achievements

    # ------------------------------------------------------------------
    # Full fixture
    # ------------------------------------------------------------------

    def test_parse_full_sample_fixture(self):
        cv = self.parser.parse_file(str(FIXTURES_DIR / "sample.md"))
        assert cv.personal_info.name == "Cenk Corapci"
        assert cv.personal_info.email == "cenk@example.com"
        assert cv.summary is not None
        assert len(cv.experience) == 2  # KLM + Adyen
        assert isinstance(cv.experience[0], Company)
        assert isinstance(cv.experience[1], ConsultancyCompany)
        assert len(cv.experience[1].clients) == 2
        assert "Python" in cv.skills
        assert len(cv.education) == 2
        assert len(cv.certifications) == 2
        assert len(cv.achievements) == 2

    def test_validate_file_no_warnings(self):
        cv, warnings = self.parser.validate_file(str(FIXTURES_DIR / "sample.md"))
        assert warnings == []
