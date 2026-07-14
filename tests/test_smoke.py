"""Smoke test: schema, route principali, CSRF, ciclo prospect/gift/cestino."""
import re

import db as dbmod

ROUTES_200 = [
    "/", "/prospects", "/research", "/ask", "/tasks", "/activity", "/goals",
    "/campaigns", "/network", "/duplicates", "/tags", "/import", "/organization",
    "/usage", "/settings", "/trash", "/welcome", "/guide",
    "/export/prospects.csv", "/export/gifts.csv", "/export/full.json",
]


def test_schema_init(flask_app):
    with dbmod.cursor() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for t in ("prospects", "gifts", "campaigns", "goals", "tasks", "research_jobs"):
        assert t in tables
    with dbmod.cursor() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(prospects)").fetchall()}
    assert {"last_contact_date", "next_contact_date", "contact_cadence_days", "deleted_at"} <= cols
    with dbmod.cursor() as conn:
        gcols = {r[1] for r in conn.execute("PRAGMA table_info(gifts)").fetchall()}
    assert {"campaign_id", "is_deductible", "receipt_sent"} <= gcols


def test_routes_render(client):
    for r in ROUTES_200:
        resp = client.get(r, follow_redirects=True)
        assert resp.status_code == 200, f"{r} -> {resp.status_code}"


def test_csrf_blocks_post_without_token(flask_app, client):
    flask_app.testing = False
    try:
        resp = client.post("/tags", data={"name": "x"})
        assert resp.status_code == 400
    finally:
        flask_app.testing = True


def test_csrf_token_roundtrip(flask_app, client):
    flask_app.testing = False
    try:
        html = client.get("/campaigns").get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
        resp = client.post("/campaigns", data={"name": "Campagna test", "csrf_token": token},
                           follow_redirects=True)
        assert resp.status_code == 200
    finally:
        flask_app.testing = True


def test_prospect_gift_trash_cycle(client):
    with dbmod.cursor() as conn:
        pid = conn.execute(
            "INSERT INTO prospects(full_name,type) VALUES ('Test Donatore','individual')").lastrowid

    # gift deducibile
    client.post(f"/prospects/{pid}/gifts",
                data={"amount_eur": "500", "status": "received", "kind": "one_off",
                      "is_deductible": "1"})
    with dbmod.cursor() as conn:
        g = conn.execute("SELECT * FROM gifts WHERE prospect_id=?", (pid,)).fetchone()
    assert g["is_deductible"] == 1 and g["amount_eur"] == 500

    # cadenza + contattato
    client.post(f"/prospects/{pid}/cadence",
                data={"next_contact_date": "2020-01-01", "contact_cadence_days": "30"})
    client.post(f"/prospects/{pid}/contacted")
    with dbmod.cursor() as conn:
        row = conn.execute(
            "SELECT last_contact_date, next_contact_date FROM prospects WHERE id=?",
            (pid,)).fetchone()
    assert row["last_contact_date"] is not None
    assert row["next_contact_date"] > row["last_contact_date"]

    # cestino → restore → purge con cascade
    client.post(f"/prospects/{pid}/delete")
    assert "Test Donatore" not in client.get("/prospects").get_data(as_text=True)
    client.post(f"/trash/{pid}/restore")
    assert "Test Donatore" in client.get("/prospects").get_data(as_text=True)
    client.post(f"/prospects/{pid}/delete")
    client.post(f"/trash/{pid}/purge")
    with dbmod.cursor() as conn:
        assert conn.execute("SELECT 1 FROM prospects WHERE id=?", (pid,)).fetchone() is None
        assert conn.execute("SELECT COUNT(*) AS n FROM gifts WHERE prospect_id=?",
                            (pid,)).fetchone()["n"] == 0


def test_export_csv_formula_escape(client):
    with dbmod.cursor() as conn:
        pid = conn.execute(
            "INSERT INTO prospects(full_name,type) VALUES ('=SUM(A1:A9)','individual')").lastrowid
    try:
        body = client.get("/export/prospects.csv").get_data(as_text=True)
        assert "'=SUM(A1:A9)" in body
    finally:
        with dbmod.cursor() as conn:
            conn.execute("DELETE FROM prospects WHERE id=?", (pid,))
