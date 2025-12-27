# Quick Start Guide

Get the Attribution MVP running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

```bash
# 1. Navigate to the project directory
cd attribution-mvp

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 4. Install dependencies
pip install -r requirements.txt
```

## Configuration (Optional)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if you want to:
# - Use OpenAI API for AI features (add your API key)
# - Change database location
# - Adjust logging settings
```

## Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Verify Installation

Run the test suite to verify everything works:

```bash
pytest
```

You should see:
```
============================== 26 passed in 1.53s ==============================
```

## First Steps

1. **Explore the Admin Tab**
   - Review default settings
   - Configure split cap enforcement
   - Set up business rules

2. **Add Partners to Use Cases**
   - Go to "Account Partner 360" tab
   - Link partners to use cases
   - Watch splits calculate automatically

3. **View Attribution**
   - Go to "Account Drilldown" tab
   - See how revenue is attributed
   - Generate explanations

4. **Try AI Features**
   - Go to "Relationship Summary (AI)" tab
   - Generate account summaries
   - Get partner recommendations

## Troubleshooting

### Port Already in Use

```bash
streamlit run app.py --server.port 8502
```

### Database Issues

Delete the database and restart:
```bash
rm attribution.db
streamlit run app.py
```

### Import Errors

Reinstall dependencies:
```bash
pip install -r requirements.txt
```

## What's Included

- **Demo Data**: 5 accounts, 3 partners, 6 use cases, 60 days of revenue
- **Sample Rules**: Pre-configured business rules
- **AI Fallbacks**: Works without OpenAI API key

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Review [AGENTS.md](AGENTS.md) for development guidelines
- Check [IMPROVEMENTS.md](IMPROVEMENTS.md) for what changed

## Support

For issues or questions, check the troubleshooting section in the main README.

---

**Ready to go!** 🚀
