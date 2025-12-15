import tempfile

import app


def setup_db(tmp_path):
    db_file = tmp_path / "test.db"
    app.DB_PATH = str(db_file)
    app.init_db()
    return db_file


def test_compute_si_auto_split_live_share(tmp_path):
    setup_db(tmp_path)
    split, reason = app.compute_si_auto_split(use_case_value=100, account_live_total=200, account_all_total=0, mode="live_share")
    assert split == 0.5
    assert "use case" in reason.lower()


def test_compute_si_auto_split_fixed_percent(tmp_path):
    setup_db(tmp_path)
    app.set_setting("si_fixed_percent", "30")
    split, _ = app.compute_si_auto_split(100, 0, 0, mode="fixed_percent")
    assert split == 0.3


def test_will_exceed_split_cap(tmp_path):
    setup_db(tmp_path)
    app.run_sql("INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source) VALUES (?, ?, ?, date('now'), date('now'), 'auto');", ("A1", "P1", 0.6))
    exceeds, total = app.will_exceed_split_cap("A1", "P2", 0.5)
    assert exceeds is True
    assert round(total, 2) == 1.1
