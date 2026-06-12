"""Tests for the CLI commands."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from cv_maker.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_MD = str(FIXTURES_DIR / "sample.md")


class TestCLIGenerate:
    def setup_method(self):
        self.runner = CliRunner()

    def test_generate_produces_pdf(self, tmp_path):
        out = str(tmp_path / "cv.pdf")
        result = self.runner.invoke(main, ["generate", "--data", SAMPLE_MD, "--output", out])
        assert result.exit_code == 0, result.output
        assert Path(out).exists()
        assert "Generated" in result.output

    def test_generate_missing_data_file(self, tmp_path):
        out = str(tmp_path / "cv.pdf")
        result = self.runner.invoke(
            main, ["generate", "--data", "/nonexistent/file.md", "--output", out]
        )
        assert result.exit_code != 0

    def test_generate_output_is_pdf(self, tmp_path):
        out = str(tmp_path / "cv.pdf")
        self.runner.invoke(main, ["generate", "--data", SAMPLE_MD, "--output", out])
        with open(out, "rb") as f:
            assert f.read(5) == b"%PDF-"


class TestCLIValidate:
    def setup_method(self):
        self.runner = CliRunner()

    def test_validate_good_file(self):
        result = self.runner.invoke(main, ["validate", SAMPLE_MD])
        assert result.exit_code == 0
        assert "Cenk Corapci" in result.output

    def test_validate_missing_file(self):
        result = self.runner.invoke(main, ["validate", "/nonexistent/file.md"])
        assert result.exit_code != 0

    def test_validate_minimal_file(self, tmp_path):
        md = tmp_path / "minimal.md"
        md.write_text("# Personal\nname: Bob\n")
        result = self.runner.invoke(main, ["validate", str(md)])
        # Exit 0 even with warnings
        assert result.exit_code == 0
        assert "Bob" in result.output


class TestCLIPreview:
    def setup_method(self):
        self.runner = CliRunner()

    def test_preview_produces_temp_file(self):
        result = self.runner.invoke(main, ["preview", "--data", SAMPLE_MD])
        assert result.exit_code == 0, result.output
        assert "Preview written to" in result.output
        # Clean up the temp file
        for line in result.output.splitlines():
            if "Preview written to:" in line:
                path = line.split("Preview written to:")[-1].strip()
                if os.path.exists(path):
                    os.unlink(path)


class TestCLIVersion:
    def setup_method(self):
        self.runner = CliRunner()

    def test_help_shows_commands(self):
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "validate" in result.output
        assert "preview" in result.output
        assert "extract-template" in result.output
