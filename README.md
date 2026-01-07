# Attribution MVP

A multi-segment partner attribution tracking system built with Streamlit. It manages relationships between accounts, partners, and use cases (opportunities), automatically calculating revenue attribution splits based on configurable business rules.

## Features

### Core Attribution
- **Partner Management**: Track partners and their roles (Implementation/SI, Influence, Referral, ISV)
- **Use Case Tracking**: Manage deals/opportunities with stages, estimated values, and target close dates
- **Automated Attribution**: Calculate revenue splits based on partner involvement
- **Rule Engine**: Configure business rules for partner assignment (based on role, stage, deal size)
- **Natural Language Rules**: Convert plain English to business rules with AI
- **Revenue Attribution Ledger**: Track and explain how revenue is attributed to partners
- **AI-Powered Insights**: Generate relationship summaries and partner recommendations (optional OpenAI integration)
- **Audit Trail**: Complete history of all split changes and decisions

### Partner Ecosystem
- **Partner Portal**: Self-service portal for partner access
- **Deal Registration**: Partners can register deals for attribution
- **Approval Workflows**: Configurable approval processes for deals and registrations
- **Partner Analytics**: Detailed performance metrics and insights

### Integrations
- **Salesforce Connector**: Sync accounts, opportunities, and partner data
- **Data Ingestion**: Flexible import from multiple sources
- **Bulk Operations**: CSV import/export for accounts, partners, use cases, and relationships

### Dashboards & Visualizations
- **Executive Dashboard**: Interactive overview with key metrics and charts
- **Partner Dashboard**: Partner-specific performance views
- **Revenue Trends**: Line charts showing revenue over time
- **Partner Performance**: Bar charts and leaderboards
- **Attribution Distribution**: Pie charts and waterfall visualizations
- **Pipeline Funnel**: Visual representation of deal stages
- **Partner Role Distribution**: Donut charts showing role breakdown

### Export & Reporting
- **CSV Export**: Export any data table to CSV format
- **Excel Reports**: Multi-sheet workbooks with professional formatting
- **PDF Reports**: Publication-ready executive reports with summaries and tables
- **Bulk Export**: Complete data backup in Excel format
- **Report Types**: Partner Performance, Account Drilldown, Audit Trail

## Tech Stack

- **Streamlit** - Web UI framework
- **SQLite** - Development database
- **PostgreSQL** - Production database
- **Pandas** - Data manipulation
- **Plotly / Altair** - Interactive charts and visualizations
- **ReportLab** - PDF generation
- **OpenPyXL & XlsxWriter** - Excel export with formatting
- **OpenAI API** - AI features (optional)
- **Python 3.9+** - Core language

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
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

See [SECRETS_CONFIG.md](SECRETS_CONFIG.md) for detailed configuration options.

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### 5. Demo Mode

Click **"Skip Login (Demo Mode)"** on the login page for instant access with sample data.

## Usage

### Main Tabs

The application is organized into 12 tabs grouped by workflow:

#### Operational Views (Daily Use)

1. **Executive Dashboard**
   - C-suite overview with key metrics
   - Interactive charts (revenue trends, partner performance, attribution distribution)
   - Pipeline funnel visualization
   - Export capabilities (CSV, Excel, PDF)

2. **Partner Sales**
   - Partner performance and revenue tracking
   - Sales leaderboards and rankings
   - Revenue attribution by partner

3. **Partner Management**
   - Partner health monitoring and alerts
   - Relationship status tracking
   - Partner onboarding and lifecycle management

4. **Deal Drilldown**
   - Detailed deal/opportunity analysis
   - Dispute resolution tools
   - Attribution explanations per deal

5. **Approval Queue**
   - Partner touchpoint approvals
   - Pending approval workflows
   - Approval history and statistics

#### Setup & Configuration (Admin)

6. **Data Import**
   - CSV upload for bulk data
   - Downloadable templates
   - Manual data entry options

7. **Salesforce Integration**
   - Connect and sync with Salesforce CRM
   - Segment mode configuration
   - Field mapping and sync settings

8. **Rule Builder**
   - Visual no-code rule creator
   - Drag-and-drop rule configuration
   - Rule testing and validation

9. **Rules & Templates**
   - Manage existing business rules
   - Rule templates library
   - Import/export rule configurations

10. **Measurement Workflows**
    - Advanced attribution methods
    - Custom measurement configurations
    - Workflow automation settings

#### Advanced (Audit & Deep Dive)

11. **Period Management**
    - Close and lock attribution periods
    - Period analytics and reporting
    - Historical period management

12. **Ledger Explorer**
    - Immutable audit trail
    - Complete change history
    - Filter by date, event type, account
    - Export audit logs (CSV, Excel, PDF)

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

- Use the export buttons in each tab to download data as CSV, Excel, or PDF
- Exports include all visible data with proper formatting

## Database

### Supported Databases

- **SQLite** - Default for development (zero configuration)
- **PostgreSQL** - Recommended for production deployments

See [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) for production database configuration.

### Schema Overview

**Core entities:**
- `accounts` - Customer accounts
- `partners` - Partner organizations
- `use_cases` - Deals/opportunities
- `use_case_partners` - Partner-to-use-case links
- `account_partners` - Account-level split percentages

**Attribution tracking:**
- `revenue_events` - Daily revenue data
- `attribution_events` - Attribution ledger (who gets credit)
- `attribution_explanations` - Detailed explanations for splits
- `audit_trail` - Complete history of changes

**System:**
- `users`, `sessions`, `organizations` - Authentication
- `settings` - Application configuration
- `activities` - Activity log

## Development

### Project Structure

```
attribution-mvp/
├── app.py                    # Main Streamlit application
├── db.py                     # Database operations and schema
├── db_connection.py          # Database connection management
├── rules.py                  # Rule engine logic
├── attribution.py            # Attribution calculation logic
├── attribution_engine.py     # Enhanced attribution computation
├── models.py                 # Data models and types
├── models_new.py             # Extended data models
│
├── # Authentication & Session
├── auth.py                   # Authentication and user management
├── session_manager.py        # Session state and DB persistence
├── login_page.py             # Login UI components
│
├── # UI & Dashboards
├── dashboards.py             # Plotly visualization components
├── dashboards_partner.py     # Partner-specific dashboards
├── templates.py              # UI templates
│
├── # AI & Intelligence
├── ai.py                     # OpenAI-powered features
├── llm.py                    # LLM integration wrapper
├── inference_engine.py       # ML inference capabilities
├── nl_rule_parser.py         # Natural language rule parsing
│
├── # Data Operations
├── exports.py                # CSV/Excel/PDF export functionality
├── pdf_executive_report.py   # Executive PDF report generation
├── bulk_operations.py        # Bulk import/export operations
├── data_ingestion.py         # Data import from various sources
├── demo_data.py              # Demo data generation
│
├── # Partner & Deal Management
├── partner_portal.py         # Partner self-service portal
├── partner_analytics.py      # Partner performance analytics
├── deal_registration.py      # Deal registration workflows
├── approval_workflow.py      # Approval process management
├── period_management.py      # Time period handling
│
├── # Integrations
├── salesforce_connector.py   # Salesforce CRM integration
├── repository.py             # Data repository patterns
│
├── # Utilities
├── config.py                 # Environment configuration
├── utils.py                  # Helper functions
├── utils_partner.py          # Partner-specific utilities
├── validate_workflows.py     # Workflow validation
│
├── # Configuration
├── requirements.txt          # Python dependencies
├── pytest.ini                # Test configuration
├── .env.example              # Environment template
│
├── # Tests
├── tests/
│   ├── test_db.py            # Database operations
│   ├── test_rules.py         # Rule engine logic
│   ├── test_attribution.py   # Attribution calculations
│   ├── test_ai_and_utils.py  # AI features and utilities
│   ├── test_helpers.py       # Helper functions
│   ├── test_workflows.py     # End-to-end workflows
│   └── test_universal_architecture.py  # Architecture tests
│
├── # Documentation
├── README.md                 # This file
├── CLAUDE.md                 # AI assistant guide
├── AGENTS.md                 # Development guidelines
├── QUICKSTART.md             # Quick start guide
├── DEMO_GUIDE.md             # Demo walkthrough
├── POSTGRESQL_SETUP.md       # Production database setup
├── SECRETS_CONFIG.md         # Configuration reference
├── QUICK_REFERENCE.md        # Command reference
├── PLATFORM_OVERVIEW.md      # Architecture overview
├── CHANGELOG.md              # Version history
└── IMPROVEMENTS.md           # Planned improvements
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
- Keep functions small and focused (<50 lines preferred)
- Document complex logic

### Database Reset

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

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | (optional) |
| `DB_PATH` | Database file path | `attribution.db` |
| `DATABASE_URL` | PostgreSQL connection string | (optional) |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `attribution.log` |

## AI Features

The app includes optional AI-powered features:

- **Relationship Summaries**: Generate concise summaries of account relationships
- **Partner Recommendations**: Get AI suggestions for partner attributions
- **Natural Language Rules**: Convert plain English to business rules

These features work without an API key using deterministic fallbacks, but provide better results with OpenAI integration.

## Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Get up and running quickly |
| [DEMO_GUIDE.md](DEMO_GUIDE.md) | Walkthrough of demo features |
| [CLAUDE.md](CLAUDE.md) | Guide for AI assistants |
| [AGENTS.md](AGENTS.md) | Development guidelines |
| [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) | Production database setup |
| [SECRETS_CONFIG.md](SECRETS_CONFIG.md) | Configuration reference |
| [PLATFORM_OVERVIEW.md](PLATFORM_OVERVIEW.md) | Architecture deep-dive |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Command reference |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

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

See [AGENTS.md](AGENTS.md) for detailed development guidelines and best practices.

For AI assistants working on this codebase, see [CLAUDE.md](CLAUDE.md).

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check existing issues
2. Review [AGENTS.md](AGENTS.md) for development guidelines
3. Create a new issue with details about your problem
