# Changelog

All notable changes to the Attribution MVP project will be documented in this file.

## [2.0.0] - 2025-12-27

### Major Features Added

#### Dashboard & Visualizations
- **New Dashboard Tab**: Executive overview with interactive charts and key metrics
  - Revenue over time line charts
  - Partner performance bar charts
  - Attribution distribution pie charts
  - Pipeline funnel charts by stage
  - Partner role distribution donut charts
  - Attribution waterfall charts
  - Time period selector (7, 30, 60, 90, 180 days)
  - Top performers table

#### Export Functionality
- **CSV Export**: Export any data table to CSV format
- **Excel Export**: Multi-sheet Excel workbooks with formatting
  - Auto-formatted columns (currency, percentages, dates)
  - Color-coded headers
  - Auto-width columns
- **PDF Reports**: Professional PDF reports with:
  - Executive summaries
  - Data tables
  - Automatic formatting
  - Multiple report types (Partner Performance, Account Drilldown, Audit Trail)

#### Bulk Operations
- **Bulk Import**: CSV import for accounts, partners, use cases, and relationships
  - Error handling and validation
  - Progress feedback
  - Conflict resolution (upsert on conflict)
- **Bulk Export**: Complete data backup in Excel format
  - All 9 tables exported
  - Timestamped filenames
- **CSV Templates**: Downloadable templates for each import type

#### Audit Trail
- **New Audit Trail Tab**: Complete change history
  - Filterable by date range, event type, and account
  - Show/hide detail view
  - Metrics display (events, accounts affected, partners involved)
  - Export to CSV, Excel, and PDF

#### Enhanced UI/UX
- Loading spinners for long operations
- Better data formatting (currency, percentages)
- Improved table layouts with auto-width
- Interactive charts with hover tooltips
- Professional color schemes
- Responsive design
- Empty state messaging

### Technical Improvements

#### New Modules
- `dashboards.py`: Chart generation and visualization functions
- `exports.py`: Export utilities (CSV, Excel, PDF)
- `bulk_operations.py`: Bulk import/export operations

#### Dependencies Added
- `plotly`: Interactive charts and visualizations
- `altair`: Additional charting options
- `openpyxl`: Excel file generation
- `xlsxwriter`: Advanced Excel formatting
- `reportlab`: PDF report generation

#### Code Quality
- All 29 tests passing (100% pass rate)
- Fixed test compatibility issues
- Maintained modular architecture
- Added comprehensive error handling
- Improved logging throughout

### Enhanced Features

#### Dashboard Features
- 5 key metrics at a glance
- 6 interactive charts
- Export functionality for all data
- Refresh button
- Time period selector

#### Admin Tab
- Bulk import/export section
- CSV template downloads
- Full data export capability

#### Account Drilldown Tab
- Added export buttons for account-specific reports
- Excel and PDF report generation

#### Existing Tabs
- All existing functionality preserved
- Enhanced with export capabilities
- Improved filtering and search

### Breaking Changes
None - all existing functionality maintained and enhanced.

### Migration Notes
- New dependencies require `pip install -r requirements.txt`
- Database schema unchanged
- All existing data compatible

## [1.0.0] - 2024-12-XX

### Initial Release
- Basic attribution tracking
- Partner management
- Use case tracking
- Rule engine
- AI-powered insights
- SQLite database
- Streamlit UI with 4 tabs
