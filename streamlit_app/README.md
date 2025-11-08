# Streamlit Dashboard

Interactive analytics dashboard for visualizing CloudFront access log data.

## Setup with UV

```bash
cd streamlit_app

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Running the Dashboard

```bash
# Using uv (recommended)
uv run streamlit run Home.py

# Or with activated venv
streamlit run Home.py
```

The dashboard will be available at http://localhost:8501

## Configuration

The dashboard connects to the database using environment variables from the root `.env` file.
Make sure to set up your database connection before running the dashboard.

## Project Structure (Phase 4)

```
streamlit_app/
├── Home.py              # Main dashboard page
├── config.py            # Configuration and settings
├── utils.py             # Shared utilities
├── pages/               # Multi-page app sections
│   ├── 1_📊_Traffic_Analysis.py
│   ├── 2_🗺️_Geographic_Insights.py
│   ├── 3_📱_Device_Analytics.py
│   ├── 4_🔀_User_Journeys.py
│   ├── 5_📈_Cohort_Analysis.py
│   └── 6_🔍_SQL_Query_Explorer.py
└── pyproject.toml       # UV project configuration
```

## Development

### Format code
```bash
uv run black .
uv run ruff check .
```

## Features (Coming in Phase 4)

- 📊 Real-time metrics dashboard
- 📈 Interactive traffic visualizations
- 🗺️ Geographic heat maps
- 📱 Device and browser analytics
- 🔀 User journey flow diagrams
- 🔍 SQL query explorer with live results
