# cvgen

Generate print-ready CV PDFs from Markdown. Optionally match the colours and layout of an existing PDF résumé.

## Quick start

```bash
# Install dependencies (requires [uv](https://docs.astral.sh/uv/))
make install

# Validate your CV data
make validate

# Generate a PDF from the included sample
make generate
```

Or use the CLI directly:

```bash
cvgen validate my-cv.md
cvgen generate --data my-cv.md                    # writes my-cv.pdf
cvgen generate -d my-cv.md -t reference.pdf -o cv.pdf
cvgen preview --data my-cv.md --open              # preview and open (macOS/Linux)
```

## Installation

**With uv (recommended):**

```bash
uv sync              # runtime dependencies
uv sync --extra dev  # include pytest and ruff
uv pip install -e .  # install the cvgen command
```

**With pip:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

| Command | Description |
|---------|-------------|
| `cvgen validate FILE` | Check Markdown structure and required fields |
| `cvgen generate` | Build a PDF from Markdown |
| `cvgen preview` | Render a temporary preview PDF |
| `cvgen extract-template` | Save layout/colours from a reference PDF to JSON |

Global flags: `-h` / `--help`, `-v` / `--verbose`, `-q` / `--quiet`, `--version`.

Run `cvgen --help` for copy-paste examples.

### generate

```bash
cvgen generate --data my-cv.md
cvgen generate -d my-cv.md -o dist/cv.pdf
cvgen generate -d my-cv.md -t reference.pdf -o cv.pdf
```

- `--data` / `-d` — Markdown CV file (required)
- `--output` / `-o` — PDF path (defaults to the data filename with `.pdf`)
- `--template` / `-t` — Optional reference PDF for visual styling

### validate

```bash
cvgen validate my-cv.md
```

Parses the file, reports warnings, and prints a short summary (name, experience count, etc.).

### preview

```bash
cvgen preview --data my-cv.md
cvgen preview -d my-cv.md --open
```

Writes a temp PDF and prints its path. Use `--open` to launch it in your default viewer.

### extract-template

```bash
cvgen extract-template --input reference.pdf --output template.json
```

Inspects a reference PDF and saves extracted page geometry, fonts, and colours.

## Markdown format

CV data lives in a single Markdown file with top-level sections (`# Heading`). See [`tests/fixtures/sample.md`](tests/fixtures/sample.md) for a full example.

### Personal

```markdown
# Personal

name: Jane Doe
title: Senior Engineer
email: jane@example.com
phone: +1 555 0100
location: Berlin, Germany
linkedin: https://linkedin.com/in/janedoe
github: https://github.com/janedoe
```

`name` is required; other fields are optional.

### Summary

```markdown
# Summary

Short professional summary paragraph.
```

### Experience

Regular employers use `## Company Name` with metadata:

```markdown
# Experience

## Acme Corp

role: Staff Engineer
location: Berlin
start: 2022-01
end: Present

### Responsibilities

- Led platform migration
- Mentored junior engineers

### Stack

Python, Kubernetes, PostgreSQL
```

Consultancy roles can nest client engagements under `### Client: Name`:

```markdown
## Consultancy: Example Partners

role: Senior Consultant
start: 2020-01
end: 2022-01

### Client: Big Bank

role: Data Engineer
start: 2020-01
end: 2021-06

- Built streaming pipelines
```

### Other sections

```markdown
# Skills
- Python
- SQL

# Languages
- English (C2)
- German (B2)

# Education

## University Name

degree: MSc
field: Computer Science
start: 2015
end: 2017

# Certifications
- AWS Certified Solutions Architect

# Achievements
- Speaker at ExampleConf 2024
```

## Make targets

```bash
make help       # list targets
make install    # sync dependencies
make dev        # install with dev extras
make test       # run pytest
make lint       # ruff check
make format     # ruff format + fix
make validate   # validate sample CV
make generate   # build dist/cv.pdf from sample
make preview    # preview sample and open it
make clean      # remove build artifacts
```

Override paths when generating:

```bash
make generate OUTPUT=my-cv.pdf SAMPLE=path/to/cv.md
```

## Development

```bash
make dev
make test
make lint
```

## License

See [LICENSE](LICENSE).
