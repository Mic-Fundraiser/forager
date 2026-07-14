"""Hunter.io integration — strictly limited to decision makers to avoid wasting credits.

Scope:
- domain_search filtered by seniority=executive (configurable)
- email_finder for a single named person (called explicitly)
- 30-day cache on domain searches to never repeat the same call
"""
import json
import re
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

import config
from db import cursor, dict_from_row, rows_to_dicts

HUNTER_BASE = "https://api.hunter.io/v2"


# ----------------- helpers -----------------

def _clean_domain(raw: str | None) -> str | None:
    if not raw:
        return None
    d = raw.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    d = d.replace("www.", "")
    # strip port and trailing dots
    d = d.split(":")[0].rstrip(".")
    if "." not in d:
        return None
    return d


def derive_domain(prospect: dict) -> str | None:
    """Best effort: extract a usable corporate domain from a prospect."""
    if prospect.get("website"):
        d = _clean_domain(prospect["website"])
        if d:
            return d
    if prospect.get("email") and "@" in prospect["email"]:
        d = _clean_domain(prospect["email"].split("@")[-1])
        if d:
            return d
    # company name → not enough by itself; we let the user manually configure website
    return None


def is_configured() -> bool:
    return bool(config.HUNTER_API_KEY)


def _request(endpoint: str, params: dict) -> dict:
    """Single GET to Hunter, returns {ok, data, error, status}."""
    if not config.HUNTER_API_KEY:
        return {
            "ok": False,
            "error": "Hunter.io non configurato. Aggiungi HUNTER_API_KEY in .env (gratis su hunter.io). Senza Hunter il tool funziona comunque, ma non potrai trovare email decision maker.",
            "status": 0,
        }
    params = {**params, "api_key": config.HUNTER_API_KEY}
    url = f"{HUNTER_BASE}/{endpoint}?{urlencode(params)}"
    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException as e:
        return {"ok": False, "error": f"Network: {e}", "status": 0}
    try:
        body = r.json()
    except Exception:
        return {"ok": False, "error": f"Invalid JSON (HTTP {r.status_code})", "status": r.status_code}
    if r.status_code >= 400:
        err = (body.get("errors") or [{}])[0].get("details") or body.get("message") or f"HTTP {r.status_code}"
        return {"ok": False, "error": err, "status": r.status_code, "raw": body}
    return {"ok": True, "data": body.get("data", {}), "meta": body.get("meta", {}), "status": r.status_code, "raw": body}


# ----------------- account -----------------

def account_info() -> dict:
    """Returns account/credits state."""
    res = _request("account", {})
    if not res["ok"]:
        return res
    d = res["data"]
    reqs = d.get("requests") or {}
    searches = reqs.get("searches") or {}
    verifs = reqs.get("verifications") or {}
    return {
        "ok": True,
        "email": d.get("email"),
        "plan": (d.get("plan_name") or "—"),
        "searches_used": searches.get("used"),
        "searches_available": searches.get("available"),
        "verifications_used": verifs.get("used"),
        "verifications_available": verifs.get("available"),
        "reset_date": d.get("reset_date"),
        "raw": d,
    }


# ----------------- cache -----------------

def _cached_for_domain(domain: str) -> dict | None:
    with cursor() as conn:
        row = conn.execute("SELECT * FROM hunter_cache WHERE domain=?", (domain,)).fetchone()
    if not row:
        return None
    row = dict_from_row(row)
    try:
        ts = datetime.fromisoformat(row["last_searched_at"].replace(" ", "T"))
    except Exception:
        return None
    if datetime.utcnow() - ts > timedelta(days=config.HUNTER_CACHE_DAYS):
        return None
    return row


def _save_cache(domain: str, data: dict):
    with cursor() as conn:
        conn.execute(
            """INSERT INTO hunter_cache(domain, company_name, industry, pattern, organization, country, raw_json, last_searched_at)
               VALUES (?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
               ON CONFLICT(domain) DO UPDATE SET
                 company_name=excluded.company_name,
                 industry=excluded.industry,
                 pattern=excluded.pattern,
                 organization=excluded.organization,
                 country=excluded.country,
                 raw_json=excluded.raw_json,
                 last_searched_at=CURRENT_TIMESTAMP""",
            (
                domain,
                data.get("organization") or data.get("company_name"),
                data.get("industry"),
                data.get("pattern"),
                data.get("organization"),
                data.get("country"),
                json.dumps(data, ensure_ascii=False),
            ),
        )


def existing_contacts(prospect_id: int) -> list[dict]:
    with cursor() as conn:
        rows = conn.execute(
            "SELECT * FROM prospect_contacts WHERE prospect_id=? ORDER BY confidence DESC NULLS LAST, last_name COLLATE NOCASE",
            (prospect_id,),
        ).fetchall()
    return rows_to_dicts(rows)


# ----------------- find decision makers -----------------

def _persist_decision_makers(conn, prospect_id: int, emails: list, domain: str,
                             company_name: str | None, pattern: str | None):
    """Sostituisce i contatti Hunter del prospect con la lista fornita (live o da cache)."""
    conn.execute("DELETE FROM prospect_contacts WHERE prospect_id=? AND source='hunter'", (prospect_id,))
    for e in emails:
        full = " ".join([x for x in [e.get("first_name"), e.get("last_name")] if x]).strip() or None
        conn.execute(
            """INSERT INTO prospect_contacts(prospect_id, full_name, first_name, last_name, email, position, seniority, department, linkedin, twitter, phone, confidence, verification, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'hunter')""",
            (
                prospect_id, full, e.get("first_name"), e.get("last_name"), e.get("value"),
                e.get("position"), e.get("seniority"), e.get("department"),
                e.get("linkedin"), e.get("twitter"), e.get("phone_number"), e.get("confidence"),
                (e.get("verification") or {}).get("status") if isinstance(e.get("verification"), dict) else None,
            ),
        )
    conn.execute(
        "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
        (prospect_id, "email", f"Hunter.io: {len(emails)} decision maker su {domain}",
         f"Company: {company_name or '—'} · Pattern email: {pattern or '—'}"),
    )


def find_decision_makers(prospect_id: int, domain: str, force: bool = False) -> dict:
    """Hunter domain-search filtered seniority=executive — 1 credit per call.

    Returns {ok, count, contacts, cached, error}.
    """
    domain = _clean_domain(domain)
    if not domain:
        return {"ok": False, "error": "Dominio non valido"}

    if not force:
        cached = _cached_for_domain(domain)
        if cached:
            # Cache onorata SEMPRE quando fresca, anche se il dominio non ha email
            # executive pubbliche (0 contatti): ricostruiamo i contatti dal raw_json
            # già pagato, senza bruciare un altro credito Hunter.
            existing = existing_contacts(prospect_id)
            if not existing:
                try:
                    cdata = json.loads(cached.get("raw_json") or "{}")
                except Exception:
                    cdata = {}
                cemails = cdata.get("emails") or []
                with cursor() as conn:
                    _persist_decision_makers(conn, prospect_id, cemails, domain,
                                             cached.get("company_name"), cached.get("pattern"))
                existing = existing_contacts(prospect_id)
            return {"ok": True, "count": len(existing), "contacts": existing, "cached": True,
                    "company": cached.get("company_name"), "pattern": cached.get("pattern")}

    params = {
        "domain": domain,
        "seniority": config.HUNTER_SENIORITY,   # executive
        "limit": config.HUNTER_MAX_PER_DOMAIN,
        "type": "personal",                      # exclude generic mailboxes
    }
    res = _request("domain-search", params)
    if not res["ok"]:
        # Hunter Free plan errore tipo "limited to 10 email addresses on your current plan"
        err_msg = (res.get("error") or "")
        m = re.search(r"limited to (\d+) email addresses", err_msg)
        if m:
            new_limit = int(m.group(1))
            params["limit"] = new_limit
            res = _request("domain-search", params)
        if not res["ok"]:
            return {"ok": False, "error": res.get("error")}

    data = res["data"]
    emails = data.get("emails") or []

    company_name = data.get("organization")
    pattern = data.get("pattern")

    _save_cache(domain, data)

    # Persist contacts (replace previous Hunter contacts for this prospect)
    with cursor() as conn:
        _persist_decision_makers(conn, prospect_id, emails, domain, company_name, pattern)

    contacts = existing_contacts(prospect_id)
    return {
        "ok": True,
        "count": len(emails),
        "contacts": contacts,
        "cached": False,
        "company": company_name,
        "pattern": pattern,
        "domain": domain,
    }


# ----------------- find single person email -----------------

def find_personal_email(prospect_id: int, domain: str, first_name: str, last_name: str) -> dict:
    """Hunter email-finder for a single named person — 1 credit per call."""
    domain = _clean_domain(domain)
    if not domain or not first_name or not last_name:
        return {"ok": False, "error": "Servono dominio, nome e cognome"}

    res = _request("email-finder", {"domain": domain, "first_name": first_name, "last_name": last_name})
    if not res["ok"]:
        return {"ok": False, "error": res.get("error")}
    data = res["data"]

    if not data.get("email"):
        return {"ok": True, "found": False}

    with cursor() as conn:
        # Dedup: niente doppioni della stessa email; un solo contatto "primario".
        conn.execute("DELETE FROM prospect_contacts WHERE prospect_id=? AND lower(email)=lower(?)", (prospect_id, data["email"]))
        conn.execute("UPDATE prospect_contacts SET is_primary=0 WHERE prospect_id=?", (prospect_id,))
        conn.execute(
            """INSERT INTO prospect_contacts(prospect_id, full_name, first_name, last_name, email, position, confidence, verification, source, is_primary)
               VALUES (?,?,?,?,?,?,?,?, 'hunter_finder', 1)""",
            (
                prospect_id,
                f"{first_name} {last_name}",
                first_name,
                last_name,
                data["email"],
                data.get("position"),
                data.get("score"),
                (data.get("verification") or {}).get("status") if isinstance(data.get("verification"), dict) else None,
            ),
        )
        # Also bubble to prospect.email if empty
        conn.execute("UPDATE prospects SET email = COALESCE(email, ?), updated_at=CURRENT_TIMESTAMP WHERE id=?", (data["email"], prospect_id))
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "email", f"Hunter: email trovata per {first_name} {last_name}", f"{data['email']} (score {data.get('score')})"),
        )

    return {"ok": True, "found": True, "email": data["email"], "score": data.get("score"), "position": data.get("position")}
