# Backend Services

Database models, log processing, and utility scripts for the analytics dashboard.

## Setup with UV

```bash
cd backend

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Project Structure

```
backend/
├── database/           # SQLAlchemy models and connection management
├── log_processor/      # CloudFront log parsing (Phase 2)
├── scripts/           # Utility scripts
└── pyproject.toml     # UV project configuration
```

## Usage

### Initialize Database
```bash
uv run python scripts/init_database.py
```

### Test Connection
```bash
uv run python scripts/test_connection.py
```

## Development

### Install dev dependencies
```bash
uv sync --all-extras
```

### Run tests
```bash
uv run pytest
```

### Format code
```bash
uv run black .
uv run ruff check .
```
