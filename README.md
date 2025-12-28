# Attribution MVP

A partner attribution tracking system that manages relationships between accounts, partners, and use cases, automatically calculating revenue attribution splits based on configurable business rules.

## Features

### Core Attribution
- **Partner Management**: Track partners and their roles (Implementation/SI, Influence, Referral, ISV)
- **Use Case Tracking**: Manage deals/opportunities with stages, estimated values, and target close dates
- **Automated Attribution**: Calculate revenue splits based on partner involvement
- **Rule Engine**: Configure business rules for partner assignment (based on role, stage, deal size)
- **Revenue Attribution Ledger**: Track and explain how revenue is attributed to partners
- **AI-Powered Insights**: Generate relationship summaries and partner recommendations (optional OpenAI integration)
- **Audit Trail**: Complete history of all split changes and decisions

### Dashboards & Visualizations
- **Executive Dashboard**: Interactive overview with key metrics and charts
- **Revenue Trends**: Line charts showing revenue over time
- **Partner Performance**: Bar charts and leaderboards
- **Attribution Distribution**: Pie charts and waterfall visualizations
- **Pipeline Funnel**: Visual representation of deal stages
- **Partner Role Distribution**: Donut charts showing role breakdown

### Export & Reporting
- **CSV Export**: Export any data table to CSV format
- **Excel Reports**: Multi-sheet workbooks with professional formatting
- **PDF Reports**: Publication-ready reports with summaries and tables
- **Bulk Export**: Complete data backup in Excel format
- **Report Types**: Partner Performance, Account Drilldown, Audit Trail

### Bulk Operations
- **Bulk Import**: CSV import for accounts, partners, use cases, and relationships
- **Import Validation**: Error handling and progress feedback
- **CSV Templates**: Downloadable templates for each data type
- **Conflict Resolution**: Automatic upsert on duplicate records

## Tech Stack

- **Streamlit** - Web UI framework
- **SQLite** - Local database
- **Pandas** - Data manipulation
- **Plotly** - Interactive charts and visualizations
- **ReportLab** - PDF generation
- **OpenPyXL & XlsxWriter** - Excel export with formatting
- **OpenAI API** - AI features (optional)
- **Python 3.9+** - Core language

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### 2. Installation

```bash
# Clone or navigate to the repository
cd attribution-mvp

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration (Optional)

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key (optional)
# The app works without it using deterministic fallbacks
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Six Main Tabs

1. **Dashboard**
   - Executive overview with key metrics
   - Interactive charts (revenue trends, partner performance, attribution distribution)
   - Pipeline funnel visualization
   - Export capabilities (CSV, Excel, PDF)
   - Customizable time periods

2. **Admin**
   - Configure split cap enforcement
   - Set Implementation (SI) auto-split rules
   - Manage business rules
   - Bulk import/export operations
   - CSV template downloads
   - Reset demo data
   - Recompute attribution ledger
   - LLM prompt configuration

3. **Account Partner 360**
   - Link partners to use cases
   - View and manage partner splits
   - Apply rules automatically
   - Advanced filtering (account, stage, partner)
   - Partner leaderboard with export

4. **Account Drilldown**
   - View attributed revenue by partner
   - See detailed explanations for attribution decisions
   - Review revenue events
   - Export account reports (Excel, PDF)

5. **Relationship Summary (AI)**
   - Generate AI-powered relationship summaries
   - View activity history
   - Get partner recommendations

6. **Audit Trail**
   - Complete change history
   - Filter by date, event type, account
   - Export audit logs (CSV, Excel, PDF)
   - Metrics dashboard

### Key Workflows

#### Adding a Partner to a Use Case

1. Go to "Account Partner 360" tab
2. Select an account
3. Choose a use case
4. Select a partner and their role
5. Click "Link partner to use case"
6. The system will automatically calculate splits based on your configured rules

#### Configuring Business Rules

1. Go to "Admin" tab
2. Scroll to "Rule Engine"
3. Add account-level or use-case-level rules
4. Rules can allow or deny based on:
   - Partner role
   - Deal stage
   - Estimated value (min/max)

#### Exporting Data

- Use the export buttons in each tab to download data as CSV
- Exports include all visible data with proper formatting

## Database Schema

The application uses SQLite with the following main tables:

- `accounts` - Customer accounts
- `partners` - Partner organizations
- `use_cases` - Deals/opportunities
- `use_case_partners` - Partner-to-use-case links
- `account_partners` - Account-level split percentages
- `revenue_events` - Daily revenue data
- `attribution_events` - Attribution ledger (who gets credit)
- `attribution_explanations` - Detailed explanations for splits
- `activities` - Activity log
- `audit_trail` - Complete history of changes
- `settings` - Application configuration

## Development

### Project Structure

```
attribution-mvp/
├── app.py                 # Main Streamlit application
├── db.py                  # Database operations and schema
├── rules.py               # Rule engine logic
├── attribution.py         # Attribution calculation logic
├── models.py              # Data models and types
├── ui.py                  # Streamlit UI components
├── llm.py                 # OpenAI integration
├── requirements.txt       # Python dependencies
├── tests/                 # Test suite
│   ├── test_db.py
│   ├── test_rules.py
│   ├── test_attribution.py
│   └── test_helpers.py
└── AGENTS.md             # Development guidelines
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_rules.py
```

### Code Style

- Follow PEP 8
- Use 4-space indentation
- Add type hints to all functions
- Keep functions small and focused
- Document complex logic

### Database Migrations

To reset the database:
1. Use the "Reset demo data" button in the Admin tab, or
2. Delete `attribution.db` and restart the app

The app will automatically create tables and seed demo data on first run.

## Configuration Options

### Settings (via Admin UI)

- **Enforce account split cap**: Prevent total splits from exceeding 100% per account
- **SI auto-split mode**: Choose how Implementation partner splits are calculated
  - `live_share`: Based on use case value vs account totals
  - `fixed_percent`: Use a fixed percentage
  - `manual_only`: Always set manually
- **Default splits**: Configure default percentages for each partner role

### Environment Variables

- `OPENAI_API_KEY`: OpenAI API key for AI features (optional)
- `DB_PATH`: Database file path (default: attribution.db)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: attribution.log)

## AI Features

The app includes optional AI-powered features:

- **Relationship Summaries**: Generate concise summaries of account relationships
- **Partner Recommendations**: Get AI suggestions for partner attributions
- **Natural Language Rules**: Convert plain English to business rules

These features work without an API key using deterministic fallbacks, but provide better results with OpenAI integration.

## Troubleshooting

### Database Issues

If you see database errors:
1. Stop the app
2. Delete `attribution.db`
3. Restart the app to recreate the database

### Import Errors

If you see import errors:
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

If port 8501 is already in use:
```bash
streamlit run app.py --server.port 8502
```

## Contributing

See `AGENTS.md` for detailed development guidelines and best practices.

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check existing issues
2. Review AGENTS.md for development guidelines
3. Create a new issue with details about your problem
