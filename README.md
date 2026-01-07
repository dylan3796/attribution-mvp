# Attribution MVP

Track which partners helped close your deals and calculate their revenue share automatically.

## Quick Start

```bash
# Install and run
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 and click **"Skip Login (Demo Mode)"** to explore with sample data.

## What It Does

**The Problem:** You work with partners (resellers, consultants, referrers) who help close deals. You need to track who helped with what and calculate their commission/attribution fairly.

**The Solution:** Import your deals, tag which partners touched them, and let the system calculate attribution based on your rules.

## Key Features

- **Dashboard** - See partner performance at a glance
- **Deal Tracking** - Import deals from CSV or Salesforce
- **Partner Attribution** - Tag partners on deals with their role
- **Flexible Rules** - Split credit equally, by role, by timing, or custom
- **Audit Trail** - Full history of who got credit and why
- **Exports** - CSV, Excel, and PDF reports

## How Attribution Works

When a deal closes, credit is split among partners based on your rules:

| Model | How It Works |
|-------|--------------|
| **Equal Split** | Everyone gets the same % |
| **Role-Based** | SI gets 60%, Referral gets 40%, etc. |
| **First Touch** | First partner to engage gets 100% |
| **Last Touch** | Most recent partner gets 100% |
| **Time Decay** | Recent touches weighted more heavily |

## Getting Your Data In

**Option 1: Demo Data**
- Go to Data Import tab → Click "Load Demo Data"

**Option 2: CSV Upload**
- Go to Data Import tab → Download a template → Fill it out → Upload

**Option 3: Salesforce**
- Go to Salesforce Integration tab → Connect your org → Sync

## Configuration

Create a `.env` file (optional):

```bash
OPENAI_API_KEY=sk-...  # For AI features (optional)
DATABASE_URL=...       # For PostgreSQL (optional, defaults to SQLite)
```

## Need Help?

- **Stuck?** Delete `attribution.db` and restart to reset everything
- **Port in use?** Run `streamlit run app.py --server.port 8502`
- **Questions?** See [DEMO_GUIDE.md](DEMO_GUIDE.md) for a walkthrough

## For Developers

See [CLAUDE.md](CLAUDE.md) for architecture details and development guidelines.

```bash
# Run tests
pytest

# Run with coverage
pytest --cov
```

## License

MIT
