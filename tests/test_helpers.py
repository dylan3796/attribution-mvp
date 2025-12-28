import tempfile
from db import Database
from attribution import AttributionEngine
from rules import RuleEngine


def setup_db(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(str(db_file))
    db.init_db()
    db.seed_data_if_empty()
    return db


def test_compute_si_auto_split_live_share(tmp_path):
    db = setup_db(tmp_path)
    rule_engine = RuleEngine(db)
    attr_engine = AttributionEngine(db, rule_engine)
    split, reason = attr_engine.compute_si_auto_split(use_case_value=100, account_live_total=200, account_all_total=0, mode="live_share")
    assert split == 0.5
    assert "use case" in reason.lower()


def test_compute_si_auto_split_fixed_percent(tmp_path):
    db = setup_db(tmp_path)
    db.set_setting("si_fixed_percent", "30")
    rule_engine = RuleEngine(db)
    attr_engine = AttributionEngine(db, rule_engine)
    split, _ = attr_engine.compute_si_auto_split(100, 0, 0, mode="fixed_percent")
    assert split == 0.3


def test_will_exceed_split_cap(tmp_path):
    db = setup_db(tmp_path)
    db.run_sql("INSERT INTO account_partners(account_id, partner_id, split_percent, first_seen, last_seen, source) VALUES (?, ?, ?, date('now'), date('now'), 'auto');", ("A1", "P1", 0.6))
    rule_engine = RuleEngine(db)
    attr_engine = AttributionEngine(db, rule_engine)
    exceeds, total = attr_engine.will_exceed_split_cap("A1", "P2", 0.5)
    assert exceeds == True
    assert round(total, 2) == 1.1
