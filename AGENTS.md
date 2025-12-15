# Repository Guidelines

This repo hosts a single-file Streamlit demo (`app.py`) with a lightweight SQLite backing store (`attribution.db`). Use the guidance below to make safe, incremental changes.

## Project Structure & Data
- `app.py` holds DB schema setup, seed data, business logic for partner splits, and all Streamlit UI tabs.
- `attribution.db` is the local state; it is auto-created on startup and can be rebuilt via the in-app “Reset demo data” button (runs `reset_demo`).
- `.venv/` is a local Python virtual environment; regenerate it as needed, but keep it untracked.

## Setup, Run, and Development Commands
- Create/refresh the venv: `python -m venv .venv` then `source .venv/bin/activate`.
- Install deps (minimal): `pip install streamlit pandas`.
- Run the app locally: `streamlit run app.py`.
- If you change DB schema logic, delete `attribution.db` or use the in-app reset to let `init_db` reapply migrations and seed data.

## Coding Style & Naming
- Follow PEP 8 with 4-space indentation; keep functions small and side-effect aware (DB writes go through `run_sql`).
- Reuse existing helpers (`upsert_account_partner_from_use_case_partner`, `upsert_manual_account_partner`, `will_exceed_split_cap`) instead of duplicating SQL.
- UI: prefer explicit Streamlit layout primitives (e.g., `st.columns`, `st.tabs`) and keep labels concise; avoid heavy custom HTML/CSS beyond small readability tweaks already present.
- IDs are stable strings (e.g., `UC-<UUID>`); avoid reformatting existing keys when extending logic.

## Testing Guidelines
- No automated test suite exists today; sanity-test manually by running the app, linking partners to use cases, toggling “Enforce account split cap,” and confirming rollups and revenue views update.
- For new logic, favor fast, isolated functions that are easy to cover with future `pytest` tests (e.g., split-cap calculations, DB migrations). Use an in-memory SQLite connection for unit tests if you add them.

## Database & Settings Notes
- All schema creation and migrations live in `init_db`; modify there so first run + reset paths stay consistent.
- Feature flags/settings are stored in the `settings` table; use `get_setting_bool`/`set_setting_bool` to access them instead of ad hoc queries.
- Respect the split-cap guardrail: return the same status shapes (`blocked_split_cap`, `skipped_manual`, `upserted`) when adding new flows so the UI messaging stays consistent.

## Commit & Pull Request Guidelines
- Commit messages: short, imperative summaries (e.g., “Add manual split override form”).
- Keep diffs focused and note DB-impacting changes explicitly. If you adjust schema or seed data, mention the migration/reset steps in the commit or PR description.
- In PRs, include: a brief purpose, how to run/verify (commands or UI steps), and screenshots/GIFs for UI changes. Link related issues if available.
