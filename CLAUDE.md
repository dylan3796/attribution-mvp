# CLAUDE.md - AI Assistant Guide for Attribution MVP

This document provides essential context for AI assistants working on this codebase.

## Project Overview

Attribution MVP is a **multi-segment partner attribution tracking system** built with Streamlit. It manages relationships between accounts, partners, and use cases (opportunities), automatically calculating revenue attribution splits based on configurable business rules.

### Key Capabilities
- Partner relationship tracking with role-based attribution
- Configurable rule engine for business logic
- Revenue attribution ledger with audit trail
- AI-powered insights (optional OpenAI integration)
- Multi-format exports (CSV, Excel, PDF)
- Support for SQLite (dev) and PostgreSQL (prod)

## Quick Reference

### Running the Application
```bash
# Activate virtual environment
source .venv/bin/activate

# Start the app
streamlit run app.py

# App runs at http://localhost:8501
```

### Running Tests
```bash
pytest                           # Run all tests
pytest --cov                     # With coverage
pytest tests/test_rules.py       # Specific file
```

### Database Reset
- Use the "Reset demo data" button in Admin tab, or
- Delete `attribution.db` and restart the app

## Architecture

### Module Organization

| Module | Purpose |
|--------|---------|
| `app.py` | Main Streamlit entry point (~2000 lines), UI tabs, initialization |
| `db.py` | Database operations, schema creation, migrations |
| `rules.py` | Rule engine for business logic evaluation |
| `attribution.py` | Core attribution calculation logic |
| `attribution_engine.py` | Enhanced attribution computation |
| `models.py` | Data classes and type definitions |
| `config.py` | Environment variable configuration |
| `auth.py` | Authentication and user management |
| `session_manager.py` | Session state and DB persistence |
| `dashboards.py` | Plotly visualization components |
| `exports.py` | CSV/Excel/PDF export functionality |
| `ai.py` | OpenAI-powered features |
| `llm.py` | LLM integration wrapper |

### Data Flow
```
User Action (Streamlit UI)
    ↓
Tab Handler (app.py)
    ↓
Business Logic (attribution.py, rules.py)
    ↓
Database Operations (db.py)
    ↓
Update Session State & UI
```

### Database Tables (SQLite/PostgreSQL)

**Core entities:**
- `accounts` - Customer accounts
- `partners` - Partner organizations
- `use_cases` - Deals/opportunities with stages and values
- `use_case_partners` - Partner-to-use-case links with roles
- `account_partners` - Account-level split percentages

**Attribution tracking:**
- `revenue_events` - Daily revenue data
- `attribution_events` - Attribution ledger entries
- `attribution_explanations` - Detailed split explanations
- `audit_trail` - Complete change history

**System:**
- `users`, `sessions`, `organizations` - Authentication
- `settings` - Application configuration
- `activities` - Activity log

## Key Conventions

### ID Formats
- Accounts: `A-<UUID>` (e.g., `A-001`)
- Partners: `P-<UUID>` (e.g., `P-001`)
- Use Cases: `UC-<UUID>` (e.g., `UC-001`)

### Partner Roles
Valid values: `Implementation (SI)`, `Influence`, `Referral`, `ISV`

### Use Case Stages
Valid values: `Discovery`, `Evaluation`, `Commit`, `Live`

### Database Patterns
- Use UPSERT pattern: `INSERT ... ON CONFLICT DO UPDATE`
- All writes go through `run_sql()` helper
- Timestamps use ISO format strings
- JSON stored as TEXT fields

### Code Style
- PEP 8 with 4-space indentation
- Type hints on all functions
- Docstrings for modules and complex functions
- Small, focused functions (<50 lines preferred)

### UI Patterns (Streamlit)
- Six main tabs in app.py
- Use `st.columns()` for grid layouts
- Use `st.metric()` for KPIs
- Plotly for interactive charts
- Consistent export buttons (CSV, Excel, PDF)

## Common Development Tasks

### Adding a New Database Table

1. Add schema in `db.py` within `init_db()`:
```python
cursor.execute('''CREATE TABLE IF NOT EXISTS new_table (
    id TEXT PRIMARY KEY,
    ...
)''')
```

2. Add helper functions in `db.py`:
```python
def insert_new_table(self, ...):
    self.run_sql("INSERT INTO new_table ...", [...])
```

3. Delete `attribution.db` and restart to apply changes

### Adding a New Business Rule

1. Define rule in `rules.py`:
```python
# Rules are JSON objects with structure:
{
    "name": "rule_name",
    "action": "allow" | "deny",
    "when": {
        "partner_role": "...",
        "stage": "...",
        "min_value": 0,
        "max_value": 100000
    }
}
```

2. Use `RuleEngine.evaluate()` to check rules

### Adding Export Functionality

Use patterns from `exports.py`:
```python
def export_to_csv(df: pd.DataFrame, filename: str) -> bytes:
    return df.to_csv(index=False).encode('utf-8')

def export_to_excel(df: pd.DataFrame, filename: str) -> bytes:
    # Use openpyxl or xlsxwriter
    ...
```

### Adding a New UI Tab

1. Add tab in `app.py` within the main tab list:
```python
tabs = st.tabs(["Dashboard", "Admin", ..., "New Tab"])
```

2. Implement tab content:
```python
with tabs[n]:
    st.header("New Tab")
    # Tab content here
```

## Testing Guidelines

### Test Structure
```
tests/
├── test_db.py            # Database operations
├── test_rules.py         # Rule engine logic
├── test_attribution.py   # Attribution calculations
├── test_ai_and_utils.py  # AI features and utilities
├── test_helpers.py       # Helper functions
└── test_workflows.py     # End-to-end workflows
```

### Test Patterns
- Use temporary SQLite databases for isolation
- Mock external API calls (OpenAI)
- Test edge cases (split cap, empty data, invalid input)
- Verify audit trail entries are created

### Writing Tests
```python
import pytest
from db import Database

def test_example():
    # Create isolated database
    db = Database(":memory:")
    db.init_db()

    # Test logic
    result = db.some_operation(...)

    # Assert
    assert result == expected
```

## Configuration

### Environment Variables (`.env`)
```bash
OPENAI_API_KEY=sk-...    # Optional - AI features work without it
DB_PATH=attribution.db    # Database file location
LOG_LEVEL=INFO           # Logging verbosity
LOG_FILE=attribution.log # Log file path
```

### Settings (Database)
Access via `get_setting_bool()` / `set_setting_bool()`:
- `enforce_split_cap` - Prevent splits exceeding 100%
- `si_auto_split_mode` - How SI partner splits are calculated
- `use_ai_summaries` - Enable AI-generated content

## Important Guardrails

### Split Cap Enforcement
When `enforce_split_cap` is enabled:
- Total account splits cannot exceed 100%
- New attributions are blocked if they would exceed cap
- Return status `blocked_split_cap` to indicate rejection

### Attribution Status Values
Always use consistent status strings:
- `upserted` - Successfully created/updated
- `blocked_split_cap` - Rejected due to cap
- `blocked_rule` - Rejected by business rule
- `skipped_manual` - Skipped for manual handling

### Audit Trail
All significant changes must create audit entries:
```python
db.add_audit_entry(
    event_type="split_change",
    account_id=...,
    partner_id=...,
    changed_field="split_percent",
    old_value=str(old),
    new_value=str(new),
    source="auto" | "manual" | "ai"
)
```

## File Locations

| Purpose | Location |
|---------|----------|
| Main application | `app.py` |
| Database schema | `db.py:init_db()` |
| Business rules | `rules.py` |
| Attribution logic | `attribution.py`, `attribution_engine.py` |
| Data models | `models.py`, `models_new.py` |
| Configuration | `config.py`, `.env` |
| Tests | `tests/` |
| Documentation | `README.md`, `AGENTS.md` |
| Claude agents | `.claude/agents/` |

## Specialized Claude Agents

This repo includes specialized agents in `.claude/agents/`:

- **design/** - Dashboard preservation and UI design
- **engineering/** - Backend architecture, API design, data engineering
- **testing/** - Calculation validation, rule testing
- **product/** - Attribution strategy, CRM integration, partner operations

## Commit Guidelines

- Use short, imperative commit messages
- Note DB-impacting changes explicitly
- Include migration/reset steps if schema changes
- For PRs: purpose, verification steps, screenshots for UI changes

## Common Pitfalls

1. **Forgetting to reset DB after schema changes** - Delete `attribution.db` or use reset button
2. **Hardcoding IDs** - Always use the `A-`, `P-`, `UC-` prefix patterns
3. **Ignoring split cap** - Check `will_exceed_split_cap()` before writes
4. **Missing audit entries** - All changes should be tracked
5. **Breaking existing helpers** - Reuse `upsert_*` functions, don't duplicate SQL

## Dependencies

Core: `streamlit`, `pandas`, `openai`, `python-dotenv`
Database: `psycopg2-binary`, `sqlalchemy`
Charts: `plotly`, `altair`
Export: `openpyxl`, `reportlab`, `xlsxwriter`
Testing: `pytest`, `pytest-cov`
Quality: `black`, `flake8`, `mypy`
