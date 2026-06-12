"""Parser that converts the custom CV Markdown format into CV domain models."""

from __future__ import annotations

import re
from typing import Any

from cv_maker.models.cv import (
    CV,
    ClientEngagement,
    Company,
    ConsultancyCompany,
    Education,
    ExperienceEntry,
    PersonalInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r"^([\w_]+)\s*:\s*(.+)$")


def _parse_key_value_block(text: str) -> dict[str, str]:
    """Parse a block of ``key: value`` lines into a dict."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        m = _KV_RE.match(line)
        if m:
            result[m.group(1).lower()] = m.group(2).strip()
    return result


def _parse_bullet_lines(text: str) -> list[str]:
    """Return non-empty stripped bullet-point lines (with or without leading dash)."""
    items: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("* "):
            items.append(line[2:].strip())
        elif line:
            items.append(line)
    return [i for i in items if i]


def _split_by_heading(text: str, level: int) -> list[tuple[str, str]]:
    """
    Split *text* into (heading_title, body) pairs at markdown headings of *level*.

    For example, with level=2 every ``## Title`` becomes a split point.
    Returns a list of (title, body) tuples in order.
    """
    pattern = re.compile(r"^#{" + str(level) + r"}\s+(.+)$", re.MULTILINE)
    parts: list[tuple[str, str]] = []
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        parts.append((title, body))
    return parts


def _split_top_sections(text: str) -> dict[str, str]:
    """
    Split the markdown text into top-level sections (``# Heading``).

    Returns a dict mapping lowercased heading names to their body text.
    """
    sections: dict[str, str] = {}
    parts = _split_by_heading(text, 1)
    for title, body in parts:
        sections[title.lower()] = body
    return sections


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------


def _parse_personal(body: str) -> PersonalInfo:
    kv = _parse_key_value_block(body)
    return PersonalInfo(
        name=kv.get("name", ""),
        title=kv.get("title"),
        email=kv.get("email"),
        phone=kv.get("phone"),
        location=kv.get("location"),
        linkedin=kv.get("linkedin"),
        github=kv.get("github"),
        website=kv.get("website"),
    )


def _parse_skills(body: str) -> list[str]:
    """Parse a skills section: bulleted list or comma-separated values."""
    skills: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ") or line.startswith("* "):
            skills.append(line[2:].strip())
        else:
            # Treat comma-separated values
            for item in line.split(","):
                item = item.strip()
                if item:
                    skills.append(item)
    return skills


def _parse_languages(body: str) -> list[str]:
    return _parse_skills(body)


def _parse_certifications(body: str) -> list[str]:
    return _parse_bullet_lines(body)


def _parse_achievements(body: str) -> list[str]:
    return _parse_bullet_lines(body)


def _parse_education(body: str) -> list[Education]:
    """Parse an education section.

    Each ``##`` heading is an institution; key-value lines beneath it supply
    degree, field, dates, etc.
    """
    educations: list[Education] = []
    for institution, entry_body in _split_by_heading(body, 2):
        kv = _parse_key_value_block(entry_body)
        desc_lines = [
            l.strip()
            for l in entry_body.splitlines()
            if l.strip() and not _KV_RE.match(l.strip())
        ]
        educations.append(
            Education(
                institution=institution,
                degree=kv.get("degree"),
                field_of_study=kv.get("field") or kv.get("field_of_study"),
                start_date=kv.get("start"),
                end_date=kv.get("end"),
                description=" ".join(desc_lines) if desc_lines else None,
            )
        )
    return educations


def _parse_client_engagement(client_name: str, body: str) -> ClientEngagement:
    """Parse a ``### Client: <name>`` block."""
    kv = _parse_key_value_block(body)
    achievements: list[str] = []
    tech_stack: list[str] = []

    # Look for ### sub-sub-sections (#### level) or inline bullets
    sub_sections = _split_by_heading(body, 4)
    if sub_sections:
        sub_map: dict[str, str] = {t.lower(): b for t, b in sub_sections}
        if "stack" in sub_map:
            tech_stack = [s.strip() for s in sub_map["stack"].split(",") if s.strip()]
        for key in ("responsibilities", "achievements", "accomplishments"):
            if key in sub_map:
                achievements = _parse_bullet_lines(sub_map[key])
                break
        # Any sub-section not stack/responsibilities counts as achievements
        if not achievements:
            for t, b in sub_sections:
                if t.lower() not in ("stack",):
                    achievements.extend(_parse_bullet_lines(b))
    else:
        # No sub-sections – parse bullets and kv from the body directly
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                achievements.append(line[2:].strip())

    return ClientEngagement(
        client_name=client_name,
        role=kv.get("role"),
        start_date=kv.get("start"),
        end_date=kv.get("end"),
        achievements=achievements,
        tech_stack=tech_stack,
    )


def _parse_company_entry(name: str, body: str) -> ExperienceEntry:
    """Parse a single ``## <Company>`` or ``## Consultancy: <Company>`` block."""
    is_consultancy = name.lower().startswith("consultancy:")
    if is_consultancy:
        name = name[len("consultancy:"):].strip()

    kv = _parse_key_value_block(body)

    if is_consultancy:
        # Look for ### Client: ... sub-sections
        clients: list[ClientEngagement] = []
        for heading, sub_body in _split_by_heading(body, 3):
            if heading.lower().startswith("client:"):
                client_name = heading[len("client:"):].strip()
                clients.append(_parse_client_engagement(client_name, sub_body))
        return ConsultancyCompany(
            name=name,
            role=kv.get("role"),
            location=kv.get("location"),
            start_date=kv.get("start"),
            end_date=kv.get("end"),
            clients=clients,
        )

    # Regular company – look for ### sub-sections
    responsibilities: list[str] = []
    stack: str | None = None
    sub_sections = _split_by_heading(body, 3)
    if sub_sections:
        sub_map: dict[str, str] = {t.lower(): b for t, b in sub_sections}
        if "stack" in sub_map:
            stack = sub_map["stack"].strip()
        for key in ("responsibilities", "achievements", "accomplishments", "projects"):
            if key in sub_map:
                responsibilities = _parse_bullet_lines(sub_map[key])
                break
        if not responsibilities:
            for t, b in sub_sections:
                if t.lower() not in ("stack",):
                    responsibilities.extend(_parse_bullet_lines(b))
    else:
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                responsibilities.append(line[2:].strip())

    return Company(
        name=name,
        role=kv.get("role"),
        location=kv.get("location"),
        start_date=kv.get("start"),
        end_date=kv.get("end"),
        responsibilities=responsibilities,
        stack=stack,
    )


def _parse_experience(body: str) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    for heading, entry_body in _split_by_heading(body, 2):
        entries.append(_parse_company_entry(heading, entry_body))
    return entries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MarkdownParser:
    """Parse CV data from the custom Markdown format into a :class:`CV` model."""

    def parse(self, text: str) -> CV:
        """Parse *text* and return a populated :class:`CV` instance."""
        sections = _split_top_sections(text)

        # Personal info is required
        personal_body = sections.get("personal", "")
        personal_info = _parse_personal(personal_body)

        # Summary
        summary: str | None = sections.get("summary", "").strip() or None

        # Skills
        skills = _parse_skills(sections.get("skills", ""))

        # Languages
        languages = _parse_languages(sections.get("languages", ""))

        # Education
        education = _parse_education(sections.get("education", ""))

        # Certifications
        certifications = _parse_certifications(sections.get("certifications", ""))

        # Achievements
        achievements_top = _parse_achievements(sections.get("achievements", ""))

        # Experience
        experience = _parse_experience(sections.get("experience", ""))

        return CV(
            personal_info=personal_info,
            summary=summary,
            skills=skills,
            languages=languages,
            education=education,
            certifications=certifications,
            experience=experience,
            achievements=achievements_top,
        )

    def parse_file(self, path: str) -> CV:
        """Read *path* and parse its contents."""
        with open(path, encoding="utf-8") as fh:
            return self.parse(fh.read())

    def validate_file(self, path: str) -> tuple[CV, list[str]]:
        """Parse *path* and return ``(cv, warnings)``."""
        cv = self.parse_file(path)
        warnings = cv.validate_required_fields()
        return cv, warnings

    @staticmethod
    def _collect_extra_sections(sections: dict[str, Any]) -> dict[str, str]:
        """Return sections that are not standard CV sections."""
        standard = {
            "personal",
            "summary",
            "skills",
            "languages",
            "education",
            "certifications",
            "experience",
            "achievements",
        }
        return {k: v for k, v in sections.items() if k not in standard}
