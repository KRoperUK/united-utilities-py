# Contributing

## Setup

```sh
uv venv
uv pip install -e ".[dev]"
```

## Checks (the gate)

```sh
ruff check src tests
ruff format --check src tests
mypy
pytest
```

Or run everything via pre-commit:

```sh
pre-commit run --all-files
```

## Conventions

- Conventional Commits (`feat:`, `fix:`, `chore:` …) — release-please reads
  these to cut versions. Do not hand-edit the version in `pyproject.toml`.
- Keep the package free of Home Assistant imports.
- No real account data in tests or fixtures.
- GitHub Actions `uses:` are pinned to a commit SHA with a `# vX.Y.Z` comment.
