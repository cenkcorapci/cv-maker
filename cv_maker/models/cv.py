"""CV domain models using Pydantic."""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, field_validator


class PersonalInfo(BaseModel):
    """Personal contact and identity information."""

    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()


class Education(BaseModel):
    """Education entry."""

    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ClientEngagement(BaseModel):
    """A client engagement within a consultancy company."""

    client_name: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    achievements: List[str] = []
    tech_stack: List[str] = []

    @property
    def date_range(self) -> str:
        start = self.start_date or ""
        end = self.end_date or ""
        if start and end:
            return f"{start} – {end}"
        return start or end or ""


class Company(BaseModel):
    """A standard employment entry."""

    name: str
    role: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = []
    stack: Optional[str] = None

    @property
    def date_range(self) -> str:
        start = self.start_date or ""
        end = self.end_date or ""
        if start and end:
            return f"{start} – {end}"
        return start or end or ""


class ConsultancyCompany(BaseModel):
    """A consultancy employer containing multiple client engagements."""

    name: str
    role: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    clients: List[ClientEngagement] = []

    @property
    def date_range(self) -> str:
        start = self.start_date or ""
        end = self.end_date or ""
        if start and end:
            return f"{start} – {end}"
        return start or end or ""


#: Union type representing any experience entry.
ExperienceEntry = Union[Company, ConsultancyCompany]


class CV(BaseModel):
    """Full CV / resume model."""

    personal_info: PersonalInfo
    summary: Optional[str] = None
    skills: List[str] = []
    languages: List[str] = []
    education: List[Education] = []
    certifications: List[str] = []
    experience: List[ExperienceEntry] = []
    achievements: List[str] = []

    @field_validator("personal_info", mode="before")
    @classmethod
    def personal_info_must_have_name(cls, v: object) -> object:
        if isinstance(v, dict) and not v.get("name", "").strip():
            raise ValueError("personal_info.name is required")
        return v

    def validate_required_fields(self) -> list[str]:
        """Return a list of validation warnings for missing recommended fields."""
        warnings: list[str] = []
        if not self.personal_info.email:
            warnings.append("personal_info.email is missing")
        if not self.summary:
            warnings.append("summary section is missing")
        if not self.experience:
            warnings.append("experience section is empty")
        if not self.skills:
            warnings.append("skills section is empty")
        return warnings
