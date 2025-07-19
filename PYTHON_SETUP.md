# Python Development Setup with uv

This project uses `uv` as the Python package and project manager.

## Prerequisites

Make sure you have `uv` installed. If not, install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS with Homebrew:

```bash
brew install uv
```

## Initial Setup

1. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Common Commands

### Adding Dependencies

Add a production dependency:
```bash
uv add package-name
```

Add a development dependency:
```bash
uv add --dev package-name
```

### Running Commands

Run commands in the virtual environment:
```bash
uv run python script.py
uv run pytest
uv run black .
uv run ruff check .
uv run mypy .
```

### Updating Dependencies

Update all dependencies:
```bash
uv sync --upgrade
```

Update a specific dependency:
```bash
uv add package-name@latest
```

### Development Tools

The project includes the following development tools:
- **pytest**: Testing framework
- **black**: Code formatter
- **ruff**: Fast Python linter
- **mypy**: Static type checker

Run all checks:
```bash
uv run black --check .
uv run ruff check .
uv run mypy .
uv run pytest
```

## Why uv?

- **Fast**: 10-100x faster than pip
- **Reliable**: Built in Rust with a focus on correctness
- **Modern**: Supports latest Python packaging standards
- **All-in-one**: Manages Python versions, virtual environments, and dependencies
