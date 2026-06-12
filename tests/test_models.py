"""Tests for CV domain models."""

import pytest
from pydantic import ValidationError

from cv_maker.models.cv import (
    CV,
    ClientEngagement,
    Company,
    ConsultancyCompany,
    Education,
    PersonalInfo,
)


class TestPersonalInfo:
    def test_basic_creation(self):
        p = PersonalInfo(name="Alice Smith", email="alice@example.com")
        assert p.name == "Alice Smith"
        assert p.email == "alice@example.com"

    def test_name_stripped(self):
        p = PersonalInfo(name="  Alice  ")
        assert p.name == "Alice"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            PersonalInfo(name="   ")

    def test_optional_fields_default_none(self):
        p = PersonalInfo(name="Alice")
        assert p.title is None
        assert p.phone is None
        assert p.location is None

    def test_all_fields(self):
        p = PersonalInfo(
            name="Cenk Corapci",
            title="Staff Data Engineer",
            email="cenk@example.com",
            phone="+31 612 345 678",
            location="Amsterdam",
            linkedin="https://linkedin.com/in/cenk",
            github="https://github.com/cenk",
            website="https://cenk.dev",
        )
        assert p.name == "Cenk Corapci"
        assert p.title == "Staff Data Engineer"


class TestCompany:
    def test_basic_company(self):
        c = Company(name="KLM", role="Engineer", start_date="2024-01", end_date="Present")
        assert c.name == "KLM"
        assert c.date_range == "2024-01 – Present"

    def test_date_range_only_start(self):
        c = Company(name="Corp", start_date="2022")
        assert c.date_range == "2022"

    def test_date_range_empty(self):
        c = Company(name="Corp")
        assert c.date_range == ""

    def test_responsibilities_default_empty(self):
        c = Company(name="Corp")
        assert c.responsibilities == []

    def test_responsibilities(self):
        c = Company(name="Corp", responsibilities=["Built X", "Led Y"])
        assert len(c.responsibilities) == 2


class TestClientEngagement:
    def test_basic(self):
        ce = ClientEngagement(
            client_name="ING",
            role="Data Engineer",
            start_date="2024-10",
            end_date="2025-03",
            achievements=["Built pipelines"],
        )
        assert ce.client_name == "ING"
        assert ce.date_range == "2024-10 – 2025-03"
        assert len(ce.achievements) == 1

    def test_tech_stack_default_empty(self):
        ce = ClientEngagement(client_name="Corp")
        assert ce.tech_stack == []


class TestConsultancyCompany:
    def test_basic(self):
        cc = ConsultancyCompany(
            name="Adyen",
            role="Senior Data Engineer",
            start_date="2024-10",
            end_date="2025-09",
            clients=[
                ClientEngagement(client_name="ING"),
                ClientEngagement(client_name="ABN AMRO"),
            ],
        )
        assert cc.name == "Adyen"
        assert len(cc.clients) == 2
        assert cc.date_range == "2024-10 – 2025-09"


class TestCV:
    def _make_cv(self, **kwargs):
        defaults = dict(
            personal_info=PersonalInfo(name="Alice"),
        )
        defaults.update(kwargs)
        return CV(**defaults)

    def test_minimal_cv(self):
        cv = self._make_cv()
        assert cv.personal_info.name == "Alice"
        assert cv.experience == []

    def test_validate_required_fields_all_present(self):
        cv = CV(
            personal_info=PersonalInfo(name="Alice", email="a@b.com"),
            summary="Great engineer",
            skills=["Python"],
            experience=[Company(name="Acme")],
        )
        assert cv.validate_required_fields() == []

    def test_validate_required_fields_missing(self):
        cv = CV(personal_info=PersonalInfo(name="Alice"))
        warnings = cv.validate_required_fields()
        assert any("email" in w for w in warnings)
        assert any("summary" in w for w in warnings)
        assert any("experience" in w for w in warnings)
        assert any("skills" in w for w in warnings)

    def test_mixed_experience(self):
        cv = CV(
            personal_info=PersonalInfo(name="Bob"),
            experience=[
                Company(name="KLM"),
                ConsultancyCompany(name="Adyen", clients=[]),
            ],
        )
        assert len(cv.experience) == 2

    def test_education_list(self):
        cv = CV(
            personal_info=PersonalInfo(name="Bob"),
            education=[Education(institution="TU Delft", degree="MSc")],
        )
        assert len(cv.education) == 1
        assert cv.education[0].institution == "TU Delft"
