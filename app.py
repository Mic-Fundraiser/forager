"""Flask app — CRM per Major Donor & Corporate Fundraising."""
import csv
import io
import json
import os
from datetime import datetime, date, timedelta
from urllib.parse import quote_plus, quote

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)

import i18n
from i18n import t, LANGS, LANG_LABELS, DEFAULT_LANG
import ai_engine
import hunter
import pdf_export
import avatars
from db import (cursor, init_db, rows_to_dicts, dict_from_row, get_org, save_org,
                backup_db, latest_backup, list_backups, start_backup_scheduler)

import config as cfg

app = Flask(__name__)
app.secret_key = cfg.SECRET_KEY
# Mitigazione CSRF base: il cookie di sessione non viene inviato su richieste
# cross-site, riducendo la superficie per POST malevoli verso l'app locale.
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)


# ---------- CSRF (token di sessione, senza dipendenze) ----------

def _csrf_token() -> str:
    tok = session.get("_csrf")
    if not tok:
        import secrets
        tok = secrets.token_urlsafe(32)
        session["_csrf"] = tok
    return tok


@app.context_processor
def _inject_csrf():
    return {"csrf_token": _csrf_token}


@app.before_request
def _csrf_protect():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    if app.testing or app.config.get("WTF_CSRF_ENABLED") is False:
        return
    import hmac
    expected = session.get("_csrf") or ""
    sent = request.headers.get("X-CSRFToken") or request.form.get("csrf_token") or ""
    if not expected or not sent or not hmac.compare_digest(expected, sent):
        abort(400, description="Token CSRF mancante o non valido. Ricarica la pagina e riprova.")


@app.before_request
def _set_lang():
    """Risolve la lingua corrente: cookie → org.language → Accept-Language → 'it'."""
    cookie = request.cookies.get("lang")
    if cookie in LANGS:
        g.lang = cookie
        return
    org = get_org()
    olang = (org or {}).get("language") if org else None
    if olang in LANGS:
        g.lang = olang
        return
    g.lang = request.accept_languages.best_match(LANGS) or DEFAULT_LANG


@app.route("/lang/<code>")
def set_lang(code):
    """Cambia lingua: salva nel cookie (UI istantanea) e in org.language (per l'AI nei job)."""
    if code not in LANGS:
        code = DEFAULT_LANG
    try:
        from db import set_language
        set_language(code)
    except Exception:
        pass
    resp = make_response(redirect(request.referrer or url_for("dashboard")))
    resp.set_cookie("lang", code, max_age=31536000, samesite="Lax")
    return resp


def _safe_int(value, default=0):
    """int() tollerante: input non numerico dai form non fa più crashare l'app (500)."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


# ---------- guard anti doppia-esecuzione per le azioni AI sincrone ----------
# Un doppio click su "Aggiorna insights" non deve lanciare due processi `claude`
# in parallelo sullo stesso prospect (costoso e con scritture che si pestano).
import threading as _threading
from contextlib import contextmanager

_AI_BUSY: set = set()
_AI_BUSY_LOCK = _threading.Lock()


@contextmanager
def _ai_slot(kind: str, pid: int):
    """Context manager: yield True se lo slot (kind,pid) è libero, False se occupato."""
    key = (kind, pid)
    with _AI_BUSY_LOCK:
        if key in _AI_BUSY:
            yield False
            return
        _AI_BUSY.add(key)
    try:
        yield True
    finally:
        with _AI_BUSY_LOCK:
            _AI_BUSY.discard(key)

STAGES = ["identified", "qualified", "cultivated", "solicited", "stewarded", "declined"]
STAGE_LABELS = {
    "identified": "Identificato",
    "qualified": "Qualificato",
    "cultivated": "In cultivation",
    "solicited": "Sollecitato",
    "stewarded": "Steward",
    "declined": "Declinato",
}
PRIORITY_LABELS = {"low": "Bassa", "medium": "Media", "high": "Alta"}
PROSPECT_TYPES = ["individual", "corporate", "foundation"]
TYPE_LABELS = {"individual": "Major donor", "corporate": "Corporate", "foundation": "Fondazione"}
TYPE_BADGE = {"individual": "indigo", "corporate": "cyan", "foundation": "teal"}
# Mappa colore→stage: UNICA fonte di verità (prima duplicata inline in molti template).
STAGE_BADGE = {
    "identified": "slate",
    "qualified": "blue",
    "cultivated": "teal",
    "solicited": "amber",
    "stewarded": "emerald",
    "declined": "rose",
}
PRIORITY_BADGE = {"high": "rose", "medium": "indigo", "low": "slate"}
# Confidenza/forza (high/medium/low) → colore, usato in wealth, connessioni, contatti.
LEVEL_BADGE = {"high": "emerald", "medium": "amber", "low": "rose"}

# Probabilità di conversione tipiche per stage del ciclo major-gift.
# Servono a calcolare un forecast PESATO (valore atteso) invece di sommare gli ask
# come se fossero tutti già acquisiti. Valori prudenti, modificabili.
STAGE_PROBABILITY = {
    "identified": 0.0,    # ancora speculativo: non entra nel forecast
    "qualified": 0.15,
    "cultivated": 0.35,
    "solicited": 0.55,
    "stewarded": 1.0,     # acquisito
    "declined": 0.0,
}

# Punteggio di priorità combinato (0-100): sintetizza capacity (0-5→0-100),
# propensity e affinity in un solo numero ordinabile. Espressione SQL riusabile.
PRIORITY_SCORE_SQL = (
    "(0.4*COALESCE(propensity_score,0) + 0.3*COALESCE(affinity_score,0) "
    "+ 0.3*COALESCE(capacity_rating,0)*20)"
)


def weighted_forecast():
    """Forecast pesato per probabilità di stage sulla pipeline APERTA (valore atteso,
    escluso l'acquisito) + potenziale lordo (somma ask senza pesi). Un solo giro DB."""
    open_stages = ("qualified", "cultivated", "solicited")
    with cursor() as conn:
        rows = conn.execute(
            "SELECT stage, COALESCE(SUM(ask_amount),0) AS amt FROM prospects "
            "WHERE ask_amount IS NOT NULL AND deleted_at IS NULL GROUP BY stage"
        ).fetchall()
    weighted = 0.0
    potential = 0
    for r in rows:
        if r["stage"] in open_stages:
            amt = r["amt"] or 0
            potential += amt
            weighted += amt * STAGE_PROBABILITY.get(r["stage"], 0.0)
    return int(round(weighted)), int(potential)


# ---------- helpers ----------

def avatar_url(name: str, photo_url: str | None = None, kind=False, domain: str | None = None) -> str:
    """Restituisce URL avatar — SVG generato locale, salvo foto utente esplicita.

    `kind` può essere un bool (legacy: corporate sì/no) oppure la stringa del tipo
    ('individual' | 'corporate' | 'foundation')."""
    # Filtra URL placeholder generati in passato (ui-avatars, clearbit auto)
    if photo_url:
        low = photo_url.lower()
        if not any(x in low for x in ("ui-avatars.com", "logo.clearbit.com", "boringavatars", "robohash")):
            return photo_url
    if isinstance(kind, str):
        ptype = kind if kind in ("individual", "corporate", "foundation") else "individual"
    else:
        ptype = "corporate" if kind else "individual"
    return url_for("avatar_svg", name=name or "?", ptype=ptype)


def domain_from(url: str | None):
    if not url:
        return None
    u = url.strip()
    u = u.replace("https://", "").replace("http://", "")
    return u.split("/")[0]


@app.context_processor
def inject_globals():
    # Etichette di dominio LOCALIZZATE nella lingua corrente (costruite da i18n).
    # I costanti modulo restano in italiano per gli usi Python interni (log attività).
    stage_labels = {s: t(f"stage.{s}") for s in STAGES}
    priority_labels = {k: t(f"priority.{k}") for k in ("low", "medium", "high")}
    type_labels = {k: t(f"type.{k}") for k in PROSPECT_TYPES}
    return {
        "STAGES": STAGES,
        "STAGE_LABELS": stage_labels,
        "PRIORITY_LABELS": priority_labels,
        "TYPE_LABELS": type_labels,
        "TYPE_BADGE": TYPE_BADGE,
        "STAGE_BADGE": STAGE_BADGE,
        "PRIORITY_BADGE": PRIORITY_BADGE,
        "LEVEL_BADGE": LEVEL_BADGE,
        "PROSPECT_TYPES": PROSPECT_TYPES,
        "GIFT_KINDS": {k: t(f"gift.kind.{k}") for k in ("one_off", "pledge", "recurring")},
        "GIFT_STATUS": {k: t(f"gift.status.{k}") for k in ("received", "promised")},
        "avatar_url": avatar_url,
        "domain_from": domain_from,
        "now": datetime.utcnow(),
        "tr": t,   # funzione di traduzione nei template (NON 't': collide con i loop {% for t in ... %})
        "lang": i18n.current_lang(),
        "LANGS": LANGS,
        "LANG_LABELS": LANG_LABELS,
        "app_version": cfg.__version__,
        "claude_ok": _claude_available(),
    }


_CLAUDE_CHECK = {"ok": None, "at": 0.0}

def _claude_available() -> bool:
    """True se il CLI `claude` è nel PATH. Cache 60s: shutil.which a ogni request è inutile."""
    import time as _time, shutil as _shutil
    now = _time.monotonic()
    if _CLAUDE_CHECK["ok"] is None or now - _CLAUDE_CHECK["at"] > 60:
        _CLAUDE_CHECK["ok"] = bool(_shutil.which(cfg.CLAUDE_BIN or "claude"))
        _CLAUDE_CHECK["at"] = now
    return _CLAUDE_CHECK["ok"]


@app.template_filter("money")
def fmt_money(v):
    #   = narrow no-break space: in font mono lo spazio pieno tra € e cifra
    # sembrava un errore di battitura, e il valore non va mai spezzato a capo.
    try:
        v = int(v)
    except Exception:
        return "—"
    if v >= 1_000_000:
        return f"€ {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"€ {v/1_000:.0f}k"
    return f"€ {v}"


@app.template_filter("nl2br")
def nl2br(v):
    if not v:
        return ""
    from markupsafe import Markup, escape
    return Markup("<br>".join(escape(v).split("\n")))


@app.template_filter("md")
def md_filter(text):
    """Markdown leggero → HTML. Safe: l'input viene escapato prima."""
    import re as _re
    from markupsafe import Markup, escape as _esc
    if not text:
        return ""
    s = str(_esc(text))
    # code blocks ``` ... ```
    s = _re.sub(r"```([\s\S]*?)```", lambda m: f"<pre><code>{m.group(1).strip()}</code></pre>", s)
    # inline code `x`
    s = _re.sub(r"`([^`\n]+)`", r"<code>\1</code>", s)
    # bold **x**
    s = _re.sub(r"\*\*([^*\n]+?)\*\*", r"<strong>\1</strong>", s)
    # italic *x* o _x_
    s = _re.sub(r"(?<![*\w])\*([^*\n]+?)\*(?!\w)", r"<em>\1</em>", s)
    s = _re.sub(r"(?<![_\w])_([^_\n]+?)_(?!\w)", r"<em>\1</em>", s)
    # headings (riga intera)
    s = _re.sub(r"(?m)^####\s+(.+)$", r"<h5>\1</h5>", s)
    s = _re.sub(r"(?m)^###\s+(.+)$", r"<h4>\1</h4>", s)
    s = _re.sub(r"(?m)^##\s+(.+)$", r"<h3>\1</h3>", s)
    s = _re.sub(r"(?m)^#\s+(.+)$", r"<h2>\1</h2>", s)
    # blockquote
    s = _re.sub(r"(?m)^&gt;\s+(.+)$", r"<blockquote>\1</blockquote>", s)
    # bullet lists
    def _ul(m):
        items = "".join(f"<li>{line[2:].strip()}</li>"
                        for line in m.group(0).strip().splitlines() if line.strip().startswith(("- ", "* ")))
        return f"<ul>{items}</ul>"
    s = _re.sub(r"(?m)(?:^[-*]\s+.+(?:\n|$))+", _ul, s)
    # numbered lists
    def _ol(m):
        items = "".join(f"<li>{_re.sub(r'^[0-9]+\\.\\s+', '', line).strip()}</li>"
                        for line in m.group(0).strip().splitlines() if _re.match(r"^[0-9]+\.\s+", line))
        return f"<ol>{items}</ol>"
    s = _re.sub(r"(?m)(?:^[0-9]+\.\s+.+(?:\n|$))+", _ol, s)
    # links [text](url)
    s = _re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    # autolink urls plain
    s = _re.sub(r"(?<![\"'>=])(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    # paragraphs: blocchi separati da blank line
    blocks = _re.split(r"\n{2,}", s)
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith(("<h", "<ul", "<ol", "<pre", "<blockquote")):
            out.append(b)
        else:
            out.append("<p>" + b.replace("\n", "<br>") + "</p>")
    return Markup("\n".join(out))


# ---------- dashboard ----------

def _prospect_tags(pid):
    with cursor() as conn:
        return rows_to_dicts(conn.execute(
            "SELECT t.* FROM tags t JOIN prospect_tags pt ON pt.tag_id=t.id WHERE pt.prospect_id=? ORDER BY t.name",
            (pid,),
        ).fetchall())


def _all_tags():
    with cursor() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM tags ORDER BY name").fetchall())


def _today_tasks_count():
    today = date.today().isoformat()
    with cursor() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status='open' AND (due_date <= ? OR due_date IS NULL)",
            (today,),
        ).fetchone()["n"]


@app.context_processor
def inject_org():
    return {
        "org_ctx": get_org(),
        "global_tasks_count": _today_tasks_count(),
    }


@app.route("/welcome", methods=["GET", "POST"])
def welcome():
    org = get_org() or {}
    if request.method == "POST":
        data = {
            "name": (request.form.get("name") or "").strip(),
            "legal_form": (request.form.get("legal_form") or None),
            "country": "Italia",
            "mission": (request.form.get("mission") or "").strip(),
            "cause_areas": (request.form.get("cause_areas") or "").strip(),
            "typical_ask_individual_eur": _safe_int(request.form.get("typical_ask_individual_eur")) or None,
            "typical_ask_corporate_eur": _safe_int(request.form.get("typical_ask_corporate_eur")) or None,
        }
        # merge with existing org (for hunter step we don't touch name etc.)
        for k, v in data.items():
            org[k] = v if v else org.get(k)
        save_org(org)
        flash("Briefing iniziale salvato. Puoi sempre rifinirlo da 'La mia org'.", "success")
        return redirect(url_for("dashboard"))
    return render_template("welcome.html", org=org)


@app.route("/")
def dashboard():
    # First-run: nessun prospect E nessuna org → wizard
    with cursor() as conn:
        any_p = conn.execute("SELECT 1 FROM prospects WHERE deleted_at IS NULL LIMIT 1").fetchone()
    org = get_org()
    if not any_p and not (org and org.get("name")):
        return redirect(url_for("welcome"))

    today = date.today().isoformat()
    with cursor() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM prospects WHERE deleted_at IS NULL").fetchone()["n"]
        individuals = conn.execute("SELECT COUNT(*) AS n FROM prospects WHERE type='individual' AND deleted_at IS NULL").fetchone()["n"]
        corporates = conn.execute("SELECT COUNT(*) AS n FROM prospects WHERE type='corporate' AND deleted_at IS NULL").fetchone()["n"]
        foundations = conn.execute("SELECT COUNT(*) AS n FROM prospects WHERE type='foundation' AND deleted_at IS NULL").fetchone()["n"]
        pipeline_value = conn.execute("SELECT COALESCE(SUM(ask_amount),0) AS s FROM prospects WHERE deleted_at IS NULL AND stage IN ('qualified','cultivated','solicited')").fetchone()["s"]
        secured_value = conn.execute("SELECT COALESCE(SUM(ask_amount),0) AS s FROM prospects WHERE stage='stewarded' AND deleted_at IS NULL").fetchone()["s"]
        by_stage = rows_to_dicts(conn.execute("SELECT stage, COUNT(*) AS n, COALESCE(SUM(ask_amount),0) AS amount FROM prospects WHERE deleted_at IS NULL GROUP BY stage").fetchall())
        top_prospects = rows_to_dicts(conn.execute("SELECT * FROM prospects WHERE deleted_at IS NULL ORDER BY propensity_score DESC, capacity_rating DESC LIMIT 6").fetchall())
        recent = rows_to_dicts(conn.execute("SELECT a.*, p.full_name FROM activities a LEFT JOIN prospects p ON p.id=a.prospect_id ORDER BY a.happened_at DESC LIMIT 8").fetchall())
        running_jobs = conn.execute("SELECT COUNT(*) AS n FROM research_jobs WHERE status IN ('pending','running')").fetchone()["n"]
        overdue_count = conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status='open' AND due_date IS NOT NULL AND due_date < ?",
            (today,),
        ).fetchone()["n"]
        tasks_today = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='open' AND (t.due_date <= ? OR t.due_date IS NULL) ORDER BY t.due_date NULLS LAST, t.priority DESC LIMIT 6",
            (today,),
        ).fetchall())
        active_goals = rows_to_dicts(conn.execute("SELECT * FROM goals WHERE archived=0 ORDER BY id DESC LIMIT 3").fetchall())
        # Segnali "opportunity" recenti dalle news (già nel DB): in dashboard, non sepolti nei profili
        news_signals = rows_to_dicts(conn.execute(
            """SELECT n.title, n.url, n.publisher, n.published_at, n.signal_note, n.prospect_id,
                      p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb
               FROM news_items n JOIN prospects p ON p.id=n.prospect_id
               WHERE n.signal='opportunity'
               ORDER BY COALESCE(n.published_at, n.fetched_at) DESC LIMIT 5"""
        ).fetchall())
        # Coda "da ringraziare": donazioni incassate non ancora ringraziate (ciclo stewardship)
        thank_queue = rows_to_dicts(conn.execute(
            """SELECT g.id, g.amount_eur, g.gift_date, g.prospect_id,
                      p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb
               FROM gifts g JOIN prospects p ON p.id=g.prospect_id
               WHERE g.status='received' AND g.thanked=0 AND p.deleted_at IS NULL
               ORDER BY COALESCE(g.gift_date, g.created_at) DESC LIMIT 6"""
        ).fetchall())
        # Coda "da ricontattare": prospect con next_contact_date scaduto o di oggi
        recontact_queue = rows_to_dicts(conn.execute(
            """SELECT id, full_name, type, stage, photo_url, website, next_contact_date, last_contact_date
               FROM prospects
               WHERE deleted_at IS NULL AND next_contact_date IS NOT NULL AND next_contact_date <= ?
               ORDER BY next_contact_date ASC LIMIT 8""",
            (today,),
        ).fetchall())

    forecast_weighted, forecast_potential = weighted_forecast()
    raised = raised_totals()

    stage_map = {s["stage"]: s for s in by_stage}
    pipeline_breakdown = [
        {
            "stage": s,
            "label": STAGE_LABELS[s],
            "count": stage_map.get(s, {}).get("n", 0),
            "amount": stage_map.get(s, {}).get("amount", 0),
        }
        for s in STAGES
    ]

    return render_template(
        "dashboard.html",
        total=total, individuals=individuals, corporates=corporates, foundations=foundations,
        pipeline_value=pipeline_value, secured_value=secured_value,
        forecast_weighted=forecast_weighted, forecast_potential=forecast_potential,
        raised=raised, thank_queue=thank_queue, recontact_queue=recontact_queue,
        pipeline_breakdown=pipeline_breakdown,
        top_prospects=top_prospects, recent=recent,
        running_jobs=running_jobs,
        overdue_count=overdue_count,
        news_signals=news_signals,
        tasks_today=tasks_today,
        active_goals=active_goals,
        today=date.today(),
    )


# ---------- prospects ----------

@app.route("/prospects")
def prospects_list():
    q = request.args.get("q", "").strip()
    ptype = request.args.get("type", "")
    stage = request.args.get("stage", "")
    sort = request.args.get("sort", "priority")
    PER_PAGE = 50
    page = max(1, _safe_int(request.args.get("page"), 1) or 1)

    where = " WHERE deleted_at IS NULL"
    args = []
    if q:
        where += " AND (full_name LIKE ? OR company LIKE ? OR role LIKE ? OR location LIKE ? OR sectors LIKE ?)"
        like = f"%{q}%"
        args += [like, like, like, like, like]
    if ptype in PROSPECT_TYPES:
        where += " AND type = ?"
        args.append(ptype)
    if stage in STAGES:
        where += " AND stage = ?"
        args.append(stage)
    sort_sql = {
        "priority": f"{PRIORITY_SCORE_SQL} DESC",
        "score": "propensity_score DESC, capacity_rating DESC",
        "recent": "updated_at DESC",
        "name": "full_name COLLATE NOCASE ASC",
        "ask": "ask_amount DESC NULLS LAST",
    }.get(sort, f"{PRIORITY_SCORE_SQL} DESC")

    with cursor() as conn:
        filtered = conn.execute(f"SELECT COUNT(*) AS n FROM prospects{where}", args).fetchone()["n"]
        offset = (page - 1) * PER_PAGE
        rows = rows_to_dicts(conn.execute(
            f"SELECT *, {PRIORITY_SCORE_SQL} AS priority_calc FROM prospects{where} ORDER BY {sort_sql} LIMIT ? OFFSET ?",
            [*args, PER_PAGE, offset],
        ).fetchall())
        # "pipeline aperta": solo gli stage attivi, coerente con la dashboard
        stats = conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN stage IN ('qualified','cultivated','solicited') THEN ask_amount END),0) AS pipeline "
            "FROM prospects"
        ).fetchone()

    total_pages = max(1, (filtered + PER_PAGE - 1) // PER_PAGE)
    return render_template(
        "prospects/list.html",
        prospects=rows,
        q=q,
        ptype=ptype,
        stage=stage,
        sort=sort,
        stats=stats,
        page=page,
        total_pages=total_pages,
        filtered=filtered,
        per_page=PER_PAGE,
    )


@app.route("/prospects/new", methods=["GET", "POST"])
def prospects_new():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Nome richiesto", "error")
            return redirect(url_for("prospects_new"))
        ptype = request.form.get("type", "individual")
        if ptype not in PROSPECT_TYPES:
            ptype = "individual"
        # anti-duplicato: se esiste già un simile e non hai confermato, chiedi
        if request.form.get("confirm_duplicate") != "1":
            dup = find_possible_duplicate(full_name, request.form.get("email"), ptype,
                                          request.form.get("website"), request.form.get("linkedin"))
            if dup:
                return render_template("prospects/new.html", dup=dup, form=request.form)
        with cursor() as conn:
            cur = conn.execute(
                """INSERT INTO prospects(full_name,type,company,role,location,country,email,linkedin,website,notes,stage,priority,source,sectors)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    full_name,
                    ptype,
                    request.form.get("company") or None,
                    request.form.get("role") or None,
                    request.form.get("location") or None,
                    request.form.get("country") or None,
                    request.form.get("email") or None,
                    request.form.get("linkedin") or None,
                    request.form.get("website") or None,
                    request.form.get("notes") or None,
                    request.form.get("stage", "identified"),
                    request.form.get("priority", "medium"),
                    request.form.get("source") or "manual",
                    request.form.get("sectors") or None,
                ),
            )
            pid = cur.lastrowid
        # le connection altrui che citavano questo nome si agganciano subito alla scheda nuova
        ai_engine.link_connections_to(pid)
        if request.form.get("run_research") == "1":
            ai_engine.start_research_job(
                prospect_id=pid,
                ptype=ptype,
                full_name=full_name,
                context=request.form.get("company") or request.form.get("website") or "",
                country=request.form.get("country") or "",
                notes=request.form.get("notes") or "",
            )
            flash("Prospect creato. Ricerca AI avviata in background.", "success")
        else:
            flash("Prospect creato.", "success")
        return redirect(url_for("prospects_detail", pid=pid))
    # GET: pre-compila da query string (es. "Crea scheda" di un'entità citata nel grafo: ?name=...)
    prefill = {}
    if request.args.get("name"):
        prefill["full_name"] = request.args.get("name")
        prefill["type"] = request.args.get("type") or "foundation"
    return render_template("prospects/new.html", form=prefill or None)


@app.route("/prospects/<int:pid>")
def prospects_detail(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        p = dict_from_row(row)
        if p.get("deleted_at"):
            flash(t("trash.in_trash_hint"), "error")
            return redirect(url_for("trash"))
        wealth = rows_to_dicts(conn.execute("SELECT * FROM wealth_indicators WHERE prospect_id=? ORDER BY value_eur DESC NULLS LAST", (pid,)).fetchall())
        affils = rows_to_dicts(conn.execute("SELECT * FROM affiliations WHERE prospect_id=?", (pid,)).fetchall())
        giving = rows_to_dicts(conn.execute("SELECT * FROM giving_history WHERE prospect_id=? ORDER BY year DESC NULLS LAST", (pid,)).fetchall())
        conns = rows_to_dicts(conn.execute("SELECT * FROM connections WHERE prospect_id=?", (pid,)).fetchall())
        sources = rows_to_dicts(conn.execute("SELECT * FROM sources WHERE prospect_id=? ORDER BY fetched_at DESC", (pid,)).fetchall())
        acts = rows_to_dicts(conn.execute("SELECT * FROM activities WHERE prospect_id=? ORDER BY happened_at DESC LIMIT 50", (pid,)).fetchall())
        latest_job = conn.execute("SELECT * FROM research_jobs WHERE prospect_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    contacts = hunter.existing_contacts(pid)
    derived_domain = hunter.derive_domain(p)
    with cursor() as conn:
        tasks_p = rows_to_dicts(conn.execute(
            "SELECT * FROM tasks WHERE prospect_id=? ORDER BY status, due_date NULLS LAST, created_at DESC",
            (pid,),
        ).fetchall())
        drafts = rows_to_dicts(conn.execute(
            "SELECT * FROM email_drafts WHERE prospect_id=? ORDER BY created_at DESC LIMIT 10",
            (pid,),
        ).fetchall())
        news = rows_to_dicts(conn.execute(
            "SELECT * FROM news_items WHERE prospect_id=? ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT 30",
            (pid,),
        ).fetchall())
        sequences = rows_to_dicts(conn.execute(
            """SELECT s.*,
                      (SELECT COUNT(*) FROM sequence_steps WHERE sequence_id=s.id) AS steps_n,
                      (SELECT COUNT(*) FROM sequence_steps WHERE sequence_id=s.id AND sent=1) AS sent_n
               FROM sequences s WHERE prospect_id=? ORDER BY id DESC""",
            (pid,),
        ).fetchall())
    sources_stats = {
        "total": len(sources),
        "verified_ok": sum(1 for s in sources if s.get("verified") == 1),
        "verified_ko": sum(1 for s in sources if s.get("verified") == -1),
        "verified_restricted": sum(1 for s in sources if s.get("verified") == 2),
        "unchecked": sum(1 for s in sources if not s.get("verified")),
        "grounded_ok": sum(1 for s in sources if s.get("grounded") == "supported"),
        "grounded_ko": sum(1 for s in sources if s.get("grounded") == "contradicted"),
    }
    gifts_p = _gifts_for(pid)
    return render_template(
        "prospects/detail.html",
        active_campaigns=_active_campaigns(),
        today=date.today().isoformat(),
        p=p,
        wealth=wealth,
        affils=affils,
        giving=giving,
        conns=conns,
        sources=sources,
        sources_stats=sources_stats,
        acts=acts,
        latest_job=dict_from_row(latest_job),
        contacts=contacts,
        derived_domain=derived_domain,
        prospect_tags=_prospect_tags(pid),
        all_tags=_all_tags(),
        tasks_p=tasks_p,
        drafts=drafts,
        news=news,
        sequences=sequences,
        gifts=gifts_p,
        gift_received=sum(g["amount_eur"] for g in gifts_p if g.get("status") == "received"),
    )


@app.route("/prospects/<int:pid>/edit", methods=["POST"])
def prospects_edit(pid):
    fields = {
        "full_name": request.form.get("full_name"),
        "headline": request.form.get("headline"),
        "company": request.form.get("company"),
        "role": request.form.get("role"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "location": request.form.get("location"),
        "country": request.form.get("country"),
        "linkedin": request.form.get("linkedin"),
        "website": request.form.get("website"),
        "twitter": request.form.get("twitter"),
        "notes": request.form.get("notes"),
        "stage": request.form.get("stage"),
        "priority": request.form.get("priority"),
        "ask_amount": request.form.get("ask_amount") or None,
        "estimated_net_worth": request.form.get("estimated_net_worth"),
        "sectors": request.form.get("sectors"),
        "tags": request.form.get("tags"),
    }
    # type solo se valido (non sovrascrivere con NULL se assente dal form)
    _t = request.form.get("type")
    if _t in PROSPECT_TYPES:
        fields["type"] = _t
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    vals = list(fields.values()) + [pid]
    with cursor() as conn:
        conn.execute(f"UPDATE prospects SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?", vals)
    flash("Profilo aggiornato.", "success")
    return redirect(url_for("prospects_detail", pid=pid))


@app.route("/prospects/<int:pid>/delete", methods=["POST"])
def prospects_delete(pid):
    """Soft-delete: nel cestino, non perso. Le donazioni e lo storico restano recuperabili."""
    with cursor() as conn:
        conn.execute("UPDATE prospects SET deleted_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
    flash(t("trash.moved"), "success")
    return redirect(url_for("prospects_list"))


@app.route("/trash")
def trash():
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            """SELECT p.*, (SELECT COUNT(*) FROM gifts g WHERE g.prospect_id=p.id) AS gifts_count
               FROM prospects p WHERE p.deleted_at IS NOT NULL ORDER BY p.deleted_at DESC"""
        ).fetchall())
    return render_template("trash.html", rows=rows)


@app.route("/trash/<int:pid>/restore", methods=["POST"])
def trash_restore(pid):
    with cursor() as conn:
        conn.execute("UPDATE prospects SET deleted_at=NULL WHERE id=?", (pid,))
    flash(t("trash.restored"), "success")
    return redirect(url_for("trash"))


@app.route("/trash/<int:pid>/purge", methods=["POST"])
def trash_purge(pid):
    """Eliminazione DEFINITIVA (cascade su tutti i record figli)."""
    with cursor() as conn:
        conn.execute("DELETE FROM prospects WHERE id=? AND deleted_at IS NOT NULL", (pid,))
    flash(t("trash.purged"), "success")
    return redirect(url_for("trash"))


@app.route("/prospects/<int:pid>/stage", methods=["POST"])
def prospects_stage(pid):
    stage = request.form.get("stage")
    if stage not in STAGES:
        return ("Bad stage", 400)
    with cursor() as conn:
        conn.execute("UPDATE prospects SET stage=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (stage, pid))
        conn.execute("INSERT INTO activities(prospect_id,type,title) VALUES (?,?,?)", (pid, "stage_change", f"Stage → {STAGE_LABELS[stage]}"))
    return ("", 204)


@app.route("/api/prospects/<int:pid>/quick-action", methods=["POST"])
def api_quick_action(pid):
    """Azioni eseguite dalla chat senza cambiare schermata. Returns JSON {ok, message}."""
    with cursor() as conn:
        row = conn.execute("SELECT id, full_name FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect non trovato"}), 404
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()
    params = data.get("params") or {}

    if action == "create_task":
        title = (params.get("title") or "").strip()
        if not title:
            return jsonify({"ok": False, "error": "Titolo task mancante"}), 400
        due = (params.get("due_date") or "").strip() or None
        with cursor() as conn:
            conn.execute(
                "INSERT INTO tasks(prospect_id,title,body,due_date,priority) VALUES (?,?,?,?,?)",
                (pid, title, params.get("body") or None, due, params.get("priority") or "medium"),
            )
        return jsonify({"ok": True, "message": f"Task creato: «{title}»" + (f" (scadenza {due})" if due else "")})

    if action == "change_stage":
        stage = (params.get("stage") or "").strip()
        if stage not in STAGES:
            return jsonify({"ok": False, "error": "Stage non valido"}), 400
        with cursor() as conn:
            conn.execute("UPDATE prospects SET stage=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (stage, pid))
            conn.execute("INSERT INTO activities(prospect_id,type,title) VALUES (?,?,?)", (pid, "stage_change", f"Stage → {STAGE_LABELS[stage]}"))
        return jsonify({"ok": True, "message": f"Stage aggiornato a «{STAGE_LABELS[stage]}»"})

    if action == "add_note":
        body = (params.get("body") or params.get("text") or "").strip()
        if not body:
            return jsonify({"ok": False, "error": "Nota vuota"}), 400
        with cursor() as conn:
            conn.execute("INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)", (pid, "note", "Nota", body))
        return jsonify({"ok": True, "message": "Nota salvata nel diario attività"})

    return jsonify({"ok": False, "error": "Azione sconosciuta"}), 400


@app.route("/prospects/<int:pid>/activity", methods=["POST"])
def prospects_activity(pid):
    title = request.form.get("title") or "Nota"
    body = request.form.get("body") or ""
    atype = request.form.get("type") or "note"
    with cursor() as conn:
        conn.execute("INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)", (pid, atype, title, body))
    _touch_last_contact(pid, atype)
    return redirect(url_for("prospects_detail", pid=pid) + "#activity")


# =========================================================
#                  GIFTS — donazioni reali
# =========================================================

GIFT_KINDS = {"one_off": "Una tantum", "pledge": "Pledge / impegno", "recurring": "Ricorrente"}
GIFT_STATUS = {"received": "Incassato", "promised": "Promesso"}


def _gifts_for(pid):
    with cursor() as conn:
        return rows_to_dicts(conn.execute(
            "SELECT g.*, c.name AS campaign_name FROM gifts g LEFT JOIN campaigns c ON c.id=g.campaign_id "
            "WHERE g.prospect_id=? ORDER BY COALESCE(g.gift_date, g.created_at) DESC", (pid,)
        ).fetchall())


# ---------- cadenze di ricontatto ----------

CONTACT_ACTIVITY_TYPES = ("email", "call", "meeting")


def _touch_last_contact(pid: int, atype: str, when: str | None = None):
    """Aggiorna last_contact_date quando viene registrato un contatto reale
    (email/call/meeting) e, se c'è una cadenza, ricalcola next_contact_date."""
    if atype not in CONTACT_ACTIVITY_TYPES:
        return
    day = (when or date.today().isoformat())[:10]
    with cursor() as conn:
        row = conn.execute("SELECT contact_cadence_days FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            return
        cad = row["contact_cadence_days"]
        if cad:
            try:
                nxt = (date.fromisoformat(day) + timedelta(days=int(cad))).isoformat()
            except ValueError:
                nxt = None
            conn.execute(
                "UPDATE prospects SET last_contact_date=?, next_contact_date=COALESCE(?, next_contact_date), "
                "updated_at=CURRENT_TIMESTAMP WHERE id=?", (day, nxt, pid))
        else:
            conn.execute(
                "UPDATE prospects SET last_contact_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (day, pid))


@app.route("/prospects/<int:pid>/cadence", methods=["POST"])
def prospects_cadence(pid):
    """Imposta prossimo contatto e/o cadenza dal dettaglio prospect."""
    nxt = (request.form.get("next_contact_date") or "").strip() or None
    cad = _safe_int(request.form.get("contact_cadence_days"), 0) or None
    with cursor() as conn:
        if not conn.execute("SELECT 1 FROM prospects WHERE id=?", (pid,)).fetchone():
            abort(404)
        conn.execute(
            "UPDATE prospects SET next_contact_date=?, contact_cadence_days=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (nxt, cad, pid))
    flash(t("cadence.saved"), "success")
    return redirect(request.form.get("next") or url_for("prospects_detail", pid=pid))


@app.route("/prospects/<int:pid>/contacted", methods=["POST"])
def prospects_contacted(pid):
    """Segna 'contattato oggi': logga attività + aggiorna cadenza (per la coda dashboard)."""
    atype = request.form.get("type") or "call"
    if atype not in CONTACT_ACTIVITY_TYPES:
        atype = "call"
    with cursor() as conn:
        row = conn.execute("SELECT id FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        conn.execute("INSERT INTO activities(prospect_id,type,title) VALUES (?,?,?)",
                     (pid, atype, t("cadence.contacted_log")))
        # senza cadenza: il prossimo contatto va deciso a mano → svuota per uscire dalla coda
        conn.execute("UPDATE prospects SET next_contact_date=NULL WHERE id=? AND contact_cadence_days IS NULL", (pid,))
    _touch_last_contact(pid, atype)
    flash(t("cadence.contacted_ok"), "success")
    return redirect(request.form.get("next") or url_for("prospects_detail", pid=pid))


def raised_totals():
    """Soldi REALI: incassato (received) e promesso (promised), totale e anno corrente."""
    year = f"{date.today().year}-"
    with cursor() as conn:
        received = conn.execute("SELECT COALESCE(SUM(amount_eur),0) AS s FROM gifts g JOIN prospects p ON p.id=g.prospect_id AND p.deleted_at IS NULL WHERE g.status='received'").fetchone()["s"]
        promised = conn.execute("SELECT COALESCE(SUM(amount_eur),0) AS s FROM gifts g JOIN prospects p ON p.id=g.prospect_id AND p.deleted_at IS NULL WHERE g.status='promised'").fetchone()["s"]
        received_year = conn.execute(
            "SELECT COALESCE(SUM(amount_eur),0) AS s FROM gifts g JOIN prospects p ON p.id=g.prospect_id AND p.deleted_at IS NULL WHERE g.status='received' AND COALESCE(g.gift_date,'') LIKE ?",
            (year + "%",),
        ).fetchone()["s"]
    return {"received": received, "promised": promised, "received_year": received_year}


def find_possible_duplicate(full_name, email=None, ptype="individual", website=None, linkedin=None, exclude_id=None):
    """Ritorna un prospect esistente che sembra lo stesso (email/linkedin/dominio esatti,
    o nome normalizzato + stesso tipo), altrimenti None. Usato per fermare i duplicati
    all'INGRESSO (import + creazione), non solo on-demand in /duplicates."""
    em = (email or "").strip().lower()
    li = (linkedin or "").strip().lower().rstrip("/")
    dom = (domain_from(website or "") or "").lower().strip()
    org = ptype in ("corporate", "foundation")
    nname = _normalize_name(_strip_company_suffix(full_name) if org else (full_name or ""))
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            "SELECT id, full_name, type, email, linkedin, website FROM prospects WHERE deleted_at IS NULL"
        ).fetchall())
    for r in rows:
        if exclude_id and r["id"] == exclude_id:
            continue
        if em and (r.get("email") or "").strip().lower() == em:
            return r
        if li and (r.get("linkedin") or "").strip().lower().rstrip("/") == li:
            return r
        r_org = r["type"] in ("corporate", "foundation")
        if dom and r_org and (domain_from(r.get("website") or "") or "").lower().strip() == dom:
            return r
        rn = _normalize_name(_strip_company_suffix(r["full_name"]) if r_org else r["full_name"])
        if nname and len(nname) >= 4 and rn == nname and r["type"] == ptype:
            return r
    return None


@app.route("/prospects/<int:pid>/gifts", methods=["POST"])
def gifts_add(pid):
    amount = _safe_int(request.form.get("amount_eur"))
    if amount <= 0:
        flash("Inserisci un importo valido.", "error")
        return redirect(url_for("prospects_detail", pid=pid) + "#gifts")
    kind = request.form.get("kind") if request.form.get("kind") in GIFT_KINDS else "one_off"
    status = request.form.get("status") if request.form.get("status") in GIFT_STATUS else "received"
    gift_date = (request.form.get("gift_date") or date.today().isoformat()).strip() or None
    campaign_id = _safe_int(request.form.get("campaign_id"), 0) or None
    is_deductible = 1 if request.form.get("is_deductible") else 0
    receipt_sent = 1 if request.form.get("receipt_sent") else 0
    with cursor() as conn:
        campaign_name = None
        if campaign_id:
            crow = conn.execute("SELECT name FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
            campaign_name = crow["name"] if crow else None
            if not crow:
                campaign_id = None
        conn.execute(
            "INSERT INTO gifts(prospect_id,amount_eur,kind,status,gift_date,campaign,campaign_id,designation,notes,is_deductible,receipt_sent) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (pid, amount, kind, status, gift_date, campaign_name,
             campaign_id, request.form.get("designation") or None, request.form.get("notes") or None,
             is_deductible, receipt_sent),
        )
        label = "Donazione incassata" if status == "received" else "Donazione promessa"
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (pid, "gift", f"{label}: € {amount:,}".replace(",", "."),
             " · ".join(x for x in [GIFT_KINDS[kind], campaign_name, request.form.get("designation")] if x)),
        )
        # se incassiamo e lo stage è precedente, avanziamo a steward (chiusura)
        if status == "received":
            conn.execute("UPDATE prospects SET stage='stewarded', updated_at=CURRENT_TIMESTAMP WHERE id=? AND stage NOT IN ('stewarded','declined')", (pid,))
    flash("Donazione registrata.", "success")
    return redirect(url_for("prospects_detail", pid=pid) + "#gifts")


@app.route("/gifts/<int:gid>/thank", methods=["POST"])
def gifts_thank(gid):
    with cursor() as conn:
        g = conn.execute("SELECT * FROM gifts WHERE id=?", (gid,)).fetchone()
        if not g:
            abort(404)
        new = 0 if g["thanked"] else 1
        conn.execute("UPDATE gifts SET thanked=?, thanked_at=? WHERE id=?",
                     (new, datetime.utcnow().isoformat(timespec="seconds") if new else None, gid))
        if new:
            conn.execute("INSERT INTO activities(prospect_id,type,title) VALUES (?,?,?)",
                         (g["prospect_id"], "thank", f"Ringraziato per donazione € {g['amount_eur']:,}".replace(",", ".")))
    return redirect(request.referrer or (url_for("prospects_detail", pid=g["prospect_id"]) + "#gifts"))


@app.route("/gifts/<int:gid>/receipt", methods=["POST"])
def gifts_receipt(gid):
    """Toggle 'ricevuta emessa' sul gift (erogazioni liberali)."""
    with cursor() as conn:
        g = conn.execute("SELECT * FROM gifts WHERE id=?", (gid,)).fetchone()
        if not g:
            abort(404)
        conn.execute("UPDATE gifts SET receipt_sent=? WHERE id=?", (0 if g["receipt_sent"] else 1, gid))
    return redirect(request.referrer or (url_for("prospects_detail", pid=g["prospect_id"]) + "#gifts"))


@app.route("/gifts/<int:gid>/delete", methods=["POST"])
def gifts_delete(gid):
    with cursor() as conn:
        g = conn.execute("SELECT prospect_id FROM gifts WHERE id=?", (gid,)).fetchone()
        if not g:
            return redirect(url_for("prospects_list"))
        conn.execute("DELETE FROM gifts WHERE id=?", (gid,))
    return redirect(url_for("prospects_detail", pid=g["prospect_id"]) + "#gifts")


# ---------- research ----------

@app.route("/research", methods=["GET", "POST"])
def research_index():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Nome richiesto", "error")
            return redirect(url_for("research_index"))
        ptype = request.form.get("type", "individual")
        if ptype not in PROSPECT_TYPES:
            ptype = "individual"
        context = request.form.get("context", "").strip()
        country = request.form.get("country", "").strip()
        notes = request.form.get("notes", "").strip()
        # anti-duplicato all'ingresso
        if request.form.get("confirm_duplicate") != "1":
            dup = find_possible_duplicate(full_name, None, ptype)
            if dup:
                with cursor() as conn:
                    jobs = rows_to_dicts(conn.execute("SELECT j.*, p.full_name FROM research_jobs j LEFT JOIN prospects p ON p.id=j.prospect_id ORDER BY j.id DESC LIMIT 20").fetchall())
                return render_template("research/index.html", jobs=jobs, dup=dup, form=request.form)
        with cursor() as conn:
            cur = conn.execute(
                "INSERT INTO prospects(full_name,type,company,country,notes,source) VALUES (?,?,?,?,?,?)",
                (full_name, ptype, context if ptype == "individual" else None, country or None, notes or None, "ricerca_research"),
            )
            pid = cur.lastrowid
        ai_engine.start_research_job(
            prospect_id=pid,
            ptype=ptype,
            full_name=full_name,
            context=context,
            country=country,
            notes=notes,
        )
        return redirect(url_for("prospects_detail", pid=pid))
    with cursor() as conn:
        jobs = rows_to_dicts(conn.execute("SELECT j.*, p.full_name FROM research_jobs j LEFT JOIN prospects p ON p.id=j.prospect_id ORDER BY j.id DESC LIMIT 20").fetchall())
    return render_template("research/index.html", jobs=jobs)


@app.route("/prospects/<int:pid>/research", methods=["POST"])
def prospects_research(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
    p = dict_from_row(row)
    ai_engine.start_research_job(
        prospect_id=pid,
        ptype=p["type"],
        full_name=p["full_name"],
        context=p.get("company") or p.get("website") or "",
        country=p.get("country") or "",
        notes=p.get("notes") or "",
    )
    flash("Ricerca AI avviata.", "success")
    return redirect(url_for("prospects_detail", pid=pid))


@app.route("/prospects/<int:pid>/refresh", methods=["POST"])
def prospects_refresh(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    profile_json = json.dumps(dict_from_row(row), ensure_ascii=False, default=str)
    with _ai_slot("refresh", pid) as free:
        if not free:
            flash("Aggiornamento già in corso per questo prospect: attendi che finisca.", "error")
            return redirect(url_for("prospects_detail", pid=pid))
        result = ai_engine.refresh_insights(pid, profile_json)
    if result.get("ok"):
        flash("Insights AI aggiornati.", "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid))


@app.route("/prospects/<int:pid>/suggest-ask", methods=["POST"])
def prospects_suggest_ask(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    with _ai_slot("suggest_ask", pid) as free:
        if not free:
            flash("Suggerimento ask già in corso: attendi che finisca.", "error")
            return redirect(url_for("prospects_detail", pid=pid) + "#ask")
        result = ai_engine.suggest_ask(dict_from_row(row))
    if result.get("ok"):
        flash(f"Ask suggerito: € {result['ask_eur']:,}".replace(",", ".") + ".", "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#ask")


@app.route("/prospects/<int:pid>/use-suggested-ask", methods=["POST"])
def prospects_use_suggested_ask(pid):
    """Copia l'ask suggerito dall'AI nel campo ask_amount, così entra nel forecast
    della pipeline (prima il suggerimento restava decorativo)."""
    with cursor() as conn:
        row = conn.execute("SELECT suggested_ask_eur FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        ask = row["suggested_ask_eur"]
        if not ask:
            flash("Nessun ask suggerito da applicare: genera prima il suggerimento.", "error")
            return redirect(url_for("prospects_detail", pid=pid) + "#ask")
        conn.execute("UPDATE prospects SET ask_amount=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (ask, pid))
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (pid, "note", "Ask applicato alla pipeline", f"ask_amount impostato a € {ask:,}".replace(",", ".")),
        )
    flash("Ask applicato: ora alimenta il forecast della pipeline.", "success")
    return redirect(url_for("prospects_detail", pid=pid) + "#ask")


@app.route("/prospects/<int:pid>/calendar.ics")
def prospects_calendar_ics(pid):
    """Genera un evento .ics per una call con il prospect (no dipendenze esterne)."""
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    p = dict_from_row(row)
    name = p.get("full_name") or "prospect"
    # parametri: date=YYYY-MM-DD, time=HH:MM, minutes=N
    d = (request.args.get("date") or date.today().isoformat()).strip()
    t = (request.args.get("time") or "10:00").strip()
    minutes = _safe_int(request.args.get("minutes"), 30) or 30
    try:
        start = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
    except ValueError:
        start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=1)
    end = start + timedelta(minutes=minutes)

    def _ics_dt(x):
        return x.strftime("%Y%m%dT%H%M%S")

    def _esc_ics(s):
        return (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    detail_url = url_for("prospects_detail", pid=pid, _external=True)
    notes_parts = []
    if p.get("ai_next_action"):
        notes_parts.append("Next action: " + p["ai_next_action"])
    if p.get("ask_rationale"):
        notes_parts.append("Ask: " + p["ask_rationale"])
    notes_parts.append("Scheda Forager: " + detail_url)
    description = _esc_ics("\n".join(notes_parts))

    uid = f"forager-{pid}-{_ics_dt(start)}@local"
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Forager CRM//IT", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_dt(datetime.now())}",
        f"DTSTART:{_ics_dt(start)}",
        f"DTEND:{_ics_dt(end)}",
        f"SUMMARY:{_esc_ics('Call · ' + name)}",
        f"DESCRIPTION:{description}",
        "BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY",
        f"DESCRIPTION:{_esc_ics('Promemoria call con ' + name)}", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    ics = "\r\n".join(lines)
    fname = "".join(c if c.isalnum() else "_" for c in name)[:40] or "call"
    return Response(ics, mimetype="text/calendar",
                    headers={"Content-Disposition": f"attachment; filename=forager_{fname}.ics"})


@app.route("/prospects/<int:pid>/find-emails", methods=["POST"])
def prospects_find_emails(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    p = dict_from_row(row)
    domain = request.form.get("domain") or hunter.derive_domain(p)
    force = request.form.get("force") == "1"
    if not domain:
        flash("Nessun dominio aziendale disponibile. Inserisci il sito web nel profilo prima.", "error")
        return redirect(url_for("prospects_detail", pid=pid))
    result = hunter.find_decision_makers(pid, domain, force=force)
    if result.get("ok"):
        if result.get("cached"):
            flash(f"Mostrati {result['count']} decision maker dalla cache (dominio già cercato di recente, nessun credito usato).", "success")
        else:
            flash(f"Hunter.io: trovati {result['count']} decision maker su {result['domain']}.", "success")
    else:
        flash(f"Hunter.io errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#contacts")


@app.route("/prospects/<int:pid>/find-personal", methods=["POST"])
def prospects_find_personal(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    p = dict_from_row(row)
    domain = request.form.get("domain") or hunter.derive_domain(p)
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    if not domain or not first or not last:
        flash("Servono dominio, nome e cognome.", "error")
        return redirect(url_for("prospects_detail", pid=pid))
    result = hunter.find_personal_email(pid, domain, first, last)
    if result.get("ok"):
        if result.get("found"):
            flash(f"Email trovata: {result['email']} (score {result.get('score')})", "success")
        else:
            flash("Nessuna email trovata per quel nome su quel dominio.", "error")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#contacts")


@app.route("/api/hunter/account")
def api_hunter_account():
    return jsonify(hunter.account_info())


@app.route("/api/jobs/<int:job_id>")
def api_job(job_id):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM research_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict_from_row(row))


@app.route("/api/prospects/<int:pid>/job")
def api_prospect_latest_job(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM research_jobs WHERE prospect_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    return jsonify(dict_from_row(row) or {})


@app.route("/api/search")
def api_search():
    """Ricerca globale per la command palette (⌘K): prospect per nome/azienda/ruolo."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"prospects": []})
    like = f"%{q}%"
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            """SELECT id, full_name, company, role, type, stage, photo_url
               FROM prospects
               WHERE deleted_at IS NULL AND (full_name LIKE ? OR company LIKE ? OR role LIKE ? OR location LIKE ? OR sectors LIKE ?)
               ORDER BY
                 CASE WHEN full_name LIKE ? THEN 0 ELSE 1 END,
                 updated_at DESC
               LIMIT 8""",
            (like, like, like, like, like, f"{q}%"),
        ).fetchall())
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "name": r["full_name"],
            "subtitle": " · ".join(x for x in [r.get("role"), r.get("company")] if x) or TYPE_LABELS.get(r["type"], "Major donor"),
            "stage": STAGE_LABELS.get(r.get("stage"), r.get("stage")),
            "avatar": avatar_url(r["full_name"], r.get("photo_url"), r["type"]),
            "url": url_for("prospects_detail", pid=r["id"]),
        })
    return jsonify({"prospects": out})


# ---------- export ----------

def _csv_safe(value):
    """Anti formula-injection: Excel/Sheets interpretano celle che iniziano con
    = + @ - TAB come formule. Prefissa con apostrofo (neutro alla lettura)."""
    if isinstance(value, str) and value and value[0] in ("=", "+", "@", "\t") :
        return "'" + value
    return value


def _csv_response(rows: list[dict], filename: str) -> Response:
    import csv
    import io
    if not rows:
        return Response("", mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={filename}"})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: _csv_safe(v) for k, v in r.items()})
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.route("/export/prospects.csv")
def export_csv():
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM prospects WHERE deleted_at IS NULL ORDER BY id").fetchall())
    return _csv_response(rows, "prospects.csv")


@app.route("/export/gifts.csv")
def export_gifts_csv():
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            "SELECT g.*, p.full_name AS prospect_name FROM gifts g "
            "JOIN prospects p ON p.id=g.prospect_id ORDER BY COALESCE(g.gift_date, g.created_at) DESC"
        ).fetchall())
    return _csv_response(rows, "gifts.csv")


@app.route("/export/full.json")
def export_full_json():
    """Dump JSON completo: tutti i dati, zero lock-in. Per migrare altrove o per archivio."""
    tables = ["organization", "prospects", "gifts", "campaigns", "goals", "tasks", "tags",
              "prospect_tags", "activities", "sources", "wealth_indicators", "affiliations",
              "giving_history", "connections", "news_items", "prospect_contacts",
              "email_drafts", "chat_messages"]
    out = {"forager_version": cfg.__version__, "exported_at": datetime.utcnow().isoformat() + "Z"}
    with cursor() as conn:
        for t_ in tables:
            try:
                out[t_] = rows_to_dicts(conn.execute(f"SELECT * FROM {t_}").fetchall())
            except Exception:
                continue
    return Response(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                    mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=forager-export.json"})


# =========================================================
#                  TASKS
# =========================================================

@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if request.method == "POST":
        with cursor() as conn:
            pid = request.form.get("prospect_id") or None
            conn.execute(
                "INSERT INTO tasks(prospect_id,title,body,due_date,priority) VALUES (?,?,?,?,?)",
                (
                    _safe_int(pid, None) if pid else None,
                    request.form.get("title", "").strip(),
                    request.form.get("body") or None,
                    request.form.get("due_date") or None,
                    request.form.get("priority", "medium"),
                ),
            )
        flash("Task creato.", "success")
        next_url = request.form.get("next") or url_for("tasks")
        return redirect(next_url)

    today = date.today()
    in_7 = (today + timedelta(days=7)).isoformat()
    with cursor() as conn:
        overdue = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='open' AND t.due_date IS NOT NULL AND t.due_date < ? ORDER BY t.due_date",
            (today.isoformat(),),
        ).fetchall())
        today_t = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='open' AND t.due_date = ? ORDER BY t.priority DESC, t.created_at",
            (today.isoformat(),),
        ).fetchall())
        upcoming = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='open' AND t.due_date > ? AND t.due_date <= ? ORDER BY t.due_date",
            (today.isoformat(), in_7),
        ).fetchall())
        no_date = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='open' AND t.due_date IS NULL ORDER BY t.created_at DESC LIMIT 50",
        ).fetchall())
        done = rows_to_dicts(conn.execute(
            "SELECT t.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM tasks t LEFT JOIN prospects p ON p.id=t.prospect_id WHERE t.status='done' ORDER BY t.completed_at DESC LIMIT 30",
        ).fetchall())
        all_prospects = rows_to_dicts(conn.execute("SELECT id, full_name FROM prospects WHERE deleted_at IS NULL ORDER BY full_name COLLATE NOCASE").fetchall())

    return render_template(
        "tasks.html",
        overdue=overdue, today_t=today_t, upcoming=upcoming, no_date=no_date, done=done,
        today=today, all_prospects=all_prospects,
    )


@app.route("/tasks/<int:tid>/toggle", methods=["POST"])
def tasks_toggle(tid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not row:
            abort(404)
        if row["status"] == "done":
            conn.execute("UPDATE tasks SET status='open', completed_at=NULL WHERE id=?", (tid,))
        else:
            conn.execute("UPDATE tasks SET status='done', completed_at=CURRENT_TIMESTAMP WHERE id=?", (tid,))
            if row["prospect_id"]:
                conn.execute(
                    "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
                    (row["prospect_id"], "task", f"Task completato: {row['title']}", row["body"] or ""),
                )
    if request.headers.get("HX-Request"):
        return ("", 204)
    return redirect(request.referrer or url_for("tasks"))


@app.route("/tasks/<int:tid>/delete", methods=["POST"])
def tasks_delete(tid):
    with cursor() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
    return redirect(request.referrer or url_for("tasks"))


# =========================================================
#                  AI COMPOSE / DRAFTS
# =========================================================

@app.route("/compose/<int:pid>", methods=["GET", "POST"])
def compose(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        p = dict_from_row(row)
        contacts = rows_to_dicts(conn.execute(
            "SELECT * FROM prospect_contacts WHERE prospect_id=? ORDER BY confidence DESC NULLS LAST",
            (pid,),
        ).fetchall())

    if request.method == "POST":
        purpose = request.form.get("purpose", "cold_intro")
        tone = request.form.get("tone", "warm")
        try:
            word_target = _safe_int(request.form.get("word_target"), 180)
        except Exception:
            word_target = 180
        contact_email = request.form.get("contact_email", "").strip() or p.get("email") or ""
        contact_name = request.form.get("contact_name", "").strip() or p.get("full_name") or ""
        key_points = request.form.get("key_points", "").strip()

        with _ai_slot("compose", pid) as free:
            if not free:
                flash("Generazione email già in corso per questo prospect: attendi che finisca.", "error")
                return redirect(url_for("compose", pid=pid))
            result = ai_engine.compose_email(
                prospect_id=pid, profile=p,
                purpose=purpose, tone=tone, word_target=word_target,
                contact_name=contact_name, contact_email=contact_email,
                key_points=key_points,
            )
        if result.get("ok"):
            flash("Bozza email generata.", "success")
            return redirect(url_for("draft_detail", did=result["draft_id"]))
        else:
            flash(f"Errore: {result.get('error')}", "error")
            return redirect(url_for("compose", pid=pid))

    with cursor() as conn:
        email_tpls = rows_to_dicts(conn.execute(
            "SELECT id, name, description, category FROM email_templates ORDER BY category, name"
        ).fetchall())
    return render_template("compose.html", p=p, contacts=contacts, email_templates=email_tpls)


@app.route("/drafts/<int:did>", methods=["GET", "POST"])
def draft_detail(did):
    with cursor() as conn:
        d = dict_from_row(conn.execute("SELECT * FROM email_drafts WHERE id=?", (did,)).fetchone())
        if not d:
            abort(404)
        p = dict_from_row(conn.execute("SELECT * FROM prospects WHERE id=?", (d["prospect_id"],)).fetchone())

    if request.method == "POST":
        if request.form.get("delete"):
            with cursor() as conn:
                conn.execute("DELETE FROM email_drafts WHERE id=?", (did,))
            flash("Bozza eliminata.", "success")
            return redirect(url_for("prospects_detail", pid=p["id"]))
        with cursor() as conn:
            conn.execute(
                "UPDATE email_drafts SET subject=?, body=?, contact_email=?, contact_name=? WHERE id=?",
                (
                    request.form.get("subject"),
                    request.form.get("body"),
                    request.form.get("contact_email"),
                    request.form.get("contact_name"),
                    did,
                ),
            )
        flash("Bozza salvata.", "success")
        return redirect(url_for("draft_detail", did=did))

    mailto = ""
    if d.get("contact_email"):
        mailto = f"mailto:{d['contact_email']}?subject={quote(d.get('subject') or '')}&body={quote(d.get('body') or '')}"
    return render_template("draft_detail.html", d=d, p=p, mailto=mailto)


@app.route("/drafts/<int:did>/sent", methods=["POST"])
def draft_mark_sent(did):
    with cursor() as conn:
        d = conn.execute("SELECT * FROM email_drafts WHERE id=?", (did,)).fetchone()
        if not d:
            abort(404)
        conn.execute("UPDATE email_drafts SET sent=1, sent_at=CURRENT_TIMESTAMP WHERE id=?", (did,))
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (d["prospect_id"], "email", f"Email inviata: {d['subject']}", f"To: {d['contact_email'] or '—'}"),
        )
    _touch_last_contact(d["prospect_id"], "email")
    flash("Marcata come inviata.", "success")
    return redirect(url_for("draft_detail", did=did))


# =========================================================
#                  TAGS
# =========================================================

@app.route("/tags", methods=["GET", "POST"])
def tags():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Nome tag richiesto.", "error")
        else:
            try:
                with cursor() as conn:
                    conn.execute(
                        "INSERT INTO tags(name,color,description) VALUES (?,?,?)",
                        (name, request.form.get("color", "slate"), request.form.get("description")),
                    )
                flash("Tag creato.", "success")
            except Exception as e:
                flash(f"Errore: {e}", "error")
        return redirect(url_for("tags"))
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM prospect_tags WHERE tag_id=t.id) AS n FROM tags t ORDER BY n DESC, t.name",
        ).fetchall())
    return render_template("tags.html", tags=rows)


@app.route("/tags/<int:tid>/delete", methods=["POST"])
def tags_delete(tid):
    with cursor() as conn:
        conn.execute("DELETE FROM tags WHERE id=?", (tid,))
    flash("Tag eliminato.", "success")
    return redirect(url_for("tags"))


@app.route("/prospects/<int:pid>/tag", methods=["POST"])
def prospects_tag(pid):
    tag_id = request.form.get("tag_id")
    new_tag = (request.form.get("new_tag") or "").strip()
    with cursor() as conn:
        if new_tag and not tag_id:
            cur = conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (new_tag,))
            tag_id = cur.lastrowid or conn.execute("SELECT id FROM tags WHERE name=?", (new_tag,)).fetchone()["id"]
        if tag_id:
            conn.execute(
                "INSERT OR IGNORE INTO prospect_tags(prospect_id, tag_id) VALUES (?,?)",
                (pid, _safe_int(tag_id, None)),
            )
    return redirect(url_for("prospects_detail", pid=pid))


@app.route("/prospects/<int:pid>/untag/<int:tid>", methods=["POST"])
def prospects_untag(pid, tid):
    with cursor() as conn:
        conn.execute("DELETE FROM prospect_tags WHERE prospect_id=? AND tag_id=?", (pid, tid))
    return redirect(url_for("prospects_detail", pid=pid))


# =========================================================
#                  BULK ACTIONS
# =========================================================

@app.route("/prospects/bulk", methods=["POST"])
def prospects_bulk():
    ids = request.form.getlist("ids")
    if not ids:
        flash("Nessun prospect selezionato.", "error")
        return redirect(request.referrer or url_for("prospects_list"))
    ids = [n for n in (_safe_int(x, None) for x in ids) if n is not None]
    if not ids:
        flash("Selezione non valida.", "error")
        return redirect(request.referrer or url_for("prospects_list"))
    placeholders = ",".join("?" for _ in ids)
    action = request.form.get("action")
    with cursor() as conn:
        if action == "stage":
            new_stage = request.form.get("stage")
            if new_stage in STAGES:
                conn.execute(f"UPDATE prospects SET stage=?, updated_at=CURRENT_TIMESTAMP WHERE id IN ({placeholders})", [new_stage, *ids])
                flash(f"Stage aggiornato per {len(ids)} prospect.", "success")
        elif action == "delete":
            conn.execute(f"UPDATE prospects SET deleted_at=CURRENT_TIMESTAMP WHERE id IN ({placeholders})", ids)
            flash(f"{len(ids)} prospect spostati nel cestino.", "success")
        elif action == "tag":
            tag_id = request.form.get("tag_id")
            if tag_id:
                for pid in ids:
                    conn.execute("INSERT OR IGNORE INTO prospect_tags(prospect_id, tag_id) VALUES (?,?)", (pid, _safe_int(tag_id, None)))
                flash(f"Tag applicato a {len(ids)} prospect.", "success")
        elif action == "research":
            rows = rows_to_dicts(conn.execute(
                f"SELECT id, type, full_name, company, website, country, notes FROM prospects WHERE id IN ({placeholders})",
                ids,
            ).fetchall())
            for p in rows:
                ai_engine.start_research_job(
                    prospect_id=p["id"], ptype=p["type"], full_name=p["full_name"],
                    context=p.get("company") or p.get("website") or "",
                    country=p.get("country") or "", notes=p.get("notes") or "",
                )
            flash(f"Avviate {len(rows)} ricerche AI in background.", "success")
        elif action == "priority":
            prio = request.form.get("priority")
            if prio in ("low","medium","high"):
                conn.execute(f"UPDATE prospects SET priority=?, updated_at=CURRENT_TIMESTAMP WHERE id IN ({placeholders})", [prio, *ids])
                flash(f"Priorità aggiornata per {len(ids)} prospect.", "success")
    return redirect(request.referrer or url_for("prospects_list"))


# =========================================================
#                  IMPORT CSV
# =========================================================

@app.route("/import", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST":
        f = request.files.get("file")
        if not f:
            flash("Nessun file.", "error")
            return redirect(url_for("import_csv"))
        run_ricerca = request.form.get("run_ricerca") == "1"
        default_type = request.form.get("default_type", "individual")
        try:
            raw = f.read(10 * 1024 * 1024 + 1)  # limite 10MB: un CSV più grande non è una lista prospect
            if len(raw) > 10 * 1024 * 1024:
                flash("File troppo grande (max 10MB). Dividi il CSV in più parti.", "error")
                return redirect(url_for("import_csv"))
            text = raw.decode("utf-8", errors="ignore")
            # try both ; and ,
            sample = text[:2048]
            sniff = csv.Sniffer()
            try:
                dialect = sniff.sniff(sample, delimiters=",;\t")
            except Exception:
                dialect = csv.excel
            reader = csv.DictReader(io.StringIO(text), dialect=dialect)
            created = 0
            queued = 0
            skipped = 0
            # indice anti-dup in memoria: una sola lettura della tabella, aggiornato a
            # ogni insert → niente N query full-table e intercetta anche i doppioni
            # DENTRO lo stesso CSV.
            with cursor() as _c:
                _existing = rows_to_dicts(_c.execute("SELECT full_name, type, email, linkedin, website FROM prospects WHERE deleted_at IS NULL").fetchall())
            seen_email = {(r.get("email") or "").strip().lower() for r in _existing if r.get("email")}
            seen_li = {(r.get("linkedin") or "").strip().lower().rstrip("/") for r in _existing if r.get("linkedin")}
            seen_dom = {(domain_from(r.get("website") or "") or "").lower() for r in _existing if r["type"] in ("corporate", "foundation") and r.get("website")}
            seen_dom.discard("")
            seen_name = {(r["type"], _normalize_name(_strip_company_suffix(r["full_name"]) if r["type"] in ("corporate", "foundation") else r["full_name"])) for r in _existing}

            def _is_dup(nm, em, pt, web, li):
                em = (em or "").strip().lower()
                li = (li or "").strip().lower().rstrip("/")
                dom = (domain_from(web or "") or "").lower().strip()
                nn = _normalize_name(_strip_company_suffix(nm) if pt in ("corporate", "foundation") else nm)
                if em and em in seen_email:
                    return True
                if li and li in seen_li:
                    return True
                if dom and pt in ("corporate", "foundation") and dom in seen_dom:
                    return True
                if nn and len(nn) >= 4 and (pt, nn) in seen_name:
                    return True
                # registra per intercettare duplicati successivi nello stesso file
                if em:
                    seen_email.add(em)
                if li:
                    seen_li.add(li)
                if dom and pt in ("corporate", "foundation"):
                    seen_dom.add(dom)
                if nn:
                    seen_name.add((pt, nn))
                return False
            MAX_ROWS = 10_000
            for row in reader:
                if created >= MAX_ROWS:
                    flash(f"Limite di {MAX_ROWS} righe per import raggiunto: le restanti sono state ignorate. "
                          "Ripeti l'import con il resto del file (i già presenti verranno saltati).", "error")
                    break
                # support multiple common header names
                name = (row.get("full_name") or row.get("name") or row.get("nome") or row.get("Nome") or "").strip()
                if not name:
                    continue
                ptype = (row.get("type") or row.get("tipo") or default_type).strip().lower()
                # accetta sinonimi italiani per le fondazioni
                if ptype in ("fondazione", "fondazioni", "foundation"):
                    ptype = "foundation"
                elif ptype in ("azienda", "aziende", "impresa", "company"):
                    ptype = "corporate"
                if ptype not in PROSPECT_TYPES:
                    ptype = default_type
                # ANTI-DUPLICATI all'ingresso: non re-importare chi è già nel CRM
                # (un secondo import della stessa lista raddoppiava tutto in silenzio)
                _email = (row.get("email") or None)
                _li = (row.get("linkedin") or None)
                _web = (row.get("website") or row.get("sito") or None)
                if _is_dup(name, _email, ptype, _web, _li):
                    skipped += 1
                    continue
                with cursor() as conn:
                    cur = conn.execute(
                        """INSERT INTO prospects(full_name,type,company,role,location,country,email,linkedin,website,notes,source)
                           VALUES (?,?,?,?,?,?,?,?,?,?, 'csv_import')""",
                        (
                            name, ptype,
                            (row.get("company") or row.get("azienda") or None) or None,
                            (row.get("role") or row.get("ruolo") or None) or None,
                            (row.get("location") or row.get("città") or row.get("citta") or None) or None,
                            (row.get("country") or row.get("paese") or None) or None,
                            (row.get("email") or None) or None,
                            (row.get("linkedin") or None) or None,
                            (row.get("website") or row.get("sito") or None) or None,
                            (row.get("notes") or row.get("note") or None) or None,
                        ),
                    )
                    pid = cur.lastrowid
                created += 1
                if run_ricerca:
                    ai_engine.start_research_job(
                        prospect_id=pid, ptype=ptype, full_name=name,
                        context=(row.get("company") or row.get("website") or ""),
                        country=row.get("country") or "",
                        notes=row.get("notes") or "",
                    )
                    queued += 1
            if created:
                # un solo passaggio bulk: aggancia le connection esistenti ai nomi appena importati
                ai_engine.relink_all_connections()
            msg = f"Importati {created} prospect. {queued} ricerche AI in coda."
            if skipped:
                msg += f" {skipped} già presenti, saltati."
            flash(msg, "success")
            return redirect(url_for("prospects_list"))
        except Exception as e:
            flash(f"Errore parsing CSV: {e}", "error")
            return redirect(url_for("import_csv"))
    return render_template("import.html")


# =========================================================
#                  CAMPAGNE
# =========================================================

@app.route("/campaigns", methods=["GET", "POST"])
def campaigns():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash(t("camp.name_required"), "error")
            return redirect(url_for("campaigns"))
        with cursor() as conn:
            conn.execute(
                "INSERT INTO campaigns(name, description, start_date, end_date, target_eur) VALUES (?,?,?,?,?)",
                (name, request.form.get("description") or None,
                 request.form.get("start_date") or None, request.form.get("end_date") or None,
                 _safe_int(request.form.get("target_eur"), 0) or None),
            )
        flash(t("camp.created"), "success")
        return redirect(url_for("campaigns"))

    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            """SELECT c.*,
                      COALESCE((SELECT SUM(g.amount_eur) FROM gifts g JOIN prospects p ON p.id=g.prospect_id AND p.deleted_at IS NULL
                                WHERE g.campaign_id=c.id AND g.status='received'),0) AS raised,
                      COALESCE((SELECT SUM(g.amount_eur) FROM gifts g JOIN prospects p ON p.id=g.prospect_id AND p.deleted_at IS NULL
                                WHERE g.campaign_id=c.id AND g.status='promised'),0) AS promised,
                      (SELECT COUNT(*) FROM gifts g WHERE g.campaign_id=c.id) AS gifts_count,
                      (SELECT COUNT(DISTINCT g.prospect_id) FROM gifts g WHERE g.campaign_id=c.id) AS donors_count
               FROM campaigns c
               ORDER BY c.status='closed', COALESCE(c.start_date, c.created_at) DESC"""
        ).fetchall())
    return render_template("campaigns.html", campaigns_rows=rows)


@app.route("/campaigns/<int:cid>/status", methods=["POST"])
def campaigns_status(cid):
    new = "closed" if request.form.get("status") == "closed" else "active"
    with cursor() as conn:
        conn.execute("UPDATE campaigns SET status=? WHERE id=?", (new, cid))
    return redirect(url_for("campaigns"))


@app.route("/campaigns/<int:cid>/delete", methods=["POST"])
def campaigns_delete(cid):
    """Elimina la campagna: i gift restano (campaign_id → NULL via FK)."""
    with cursor() as conn:
        conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
    flash(t("camp.deleted"), "success")
    return redirect(url_for("campaigns"))


def _active_campaigns():
    with cursor() as conn:
        return rows_to_dicts(conn.execute(
            "SELECT id, name FROM campaigns WHERE status='active' ORDER BY name COLLATE NOCASE").fetchall())


# =========================================================
#                  GOALS
# =========================================================

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        target = _safe_int(request.form.get("target_eur"))
        with cursor() as conn:
            conn.execute(
                "INSERT INTO goals(label, period_year, period_label, target_eur, notes) VALUES (?,?,?,?,?)",
                (
                    request.form.get("label", "").strip() or "Obiettivo senza nome",
                    _safe_int(request.form.get("period_year"), date.today().year),
                    request.form.get("period_label") or str(date.today().year),
                    target,
                    request.form.get("notes") or None,
                ),
            )
        flash("Obiettivo creato.", "success")
        return redirect(url_for("goals"))

    with cursor() as conn:
        goals_l = rows_to_dicts(conn.execute("SELECT * FROM goals WHERE archived=0 ORDER BY period_year DESC, id DESC").fetchall())
        # forecast: pipeline value (qualified + cultivated + solicited)
        pipeline_value = conn.execute(
            "SELECT COALESCE(SUM(ask_amount),0) AS s FROM prospects WHERE deleted_at IS NULL AND stage IN ('qualified','cultivated','solicited')"
        ).fetchone()["s"]
        secured_value = conn.execute(
            "SELECT COALESCE(SUM(ask_amount),0) AS s FROM prospects WHERE stage='stewarded' AND deleted_at IS NULL"
        ).fetchone()["s"]
    forecast_weighted, forecast_potential = weighted_forecast()
    raised = raised_totals()
    return render_template("goals.html", goals=goals_l, pipeline_value=pipeline_value,
                           secured_value=secured_value, raised=raised,
                           forecast_weighted=forecast_weighted, forecast_potential=forecast_potential)


@app.route("/goals/<int:gid>/archive", methods=["POST"])
def goals_archive(gid):
    with cursor() as conn:
        conn.execute("UPDATE goals SET archived=1 WHERE id=?", (gid,))
    return redirect(url_for("goals"))


# =========================================================
#                  ACTIVITY FEED (global)
# =========================================================

@app.route("/activity")
def activity_feed():
    with cursor() as conn:
        items = rows_to_dicts(conn.execute(
            "SELECT a.*, p.full_name AS pname, p.photo_url AS pphoto, p.type AS ptype, p.website AS pweb FROM activities a LEFT JOIN prospects p ON p.id=a.prospect_id ORDER BY a.happened_at DESC LIMIT 200",
        ).fetchall())
    return render_template("activity.html", items=items)


# =========================================================
#                  NETWORK GRAPH (per prospect)
# =========================================================

@app.route("/prospects/<int:pid>/network")
def prospects_network(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        p = dict_from_row(row)
        # connections outgoing
        outgoing = rows_to_dicts(conn.execute(
            """SELECT c.*, mp.id AS m_id, mp.full_name AS m_full_name, mp.photo_url AS m_photo, mp.type AS m_type, mp.website AS m_website
               FROM connections c LEFT JOIN prospects mp ON mp.id=c.matched_prospect_id
               WHERE c.prospect_id=?""",
            (pid,),
        ).fetchall())
        # who mentions me as connection (other prospects whose connections matched this one)
        incoming = rows_to_dicts(conn.execute(
            """SELECT c.*, sp.id AS s_id, sp.full_name AS s_full_name, sp.photo_url AS s_photo, sp.type AS s_type, sp.website AS s_website
               FROM connections c JOIN prospects sp ON sp.id=c.prospect_id
               WHERE c.matched_prospect_id=?""",
            (pid,),
        ).fetchall())
    return render_template("network.html", p=p, outgoing=outgoing, incoming=incoming)


@app.route("/organization", methods=["GET", "POST"])
def organization():
    if request.method == "POST":
        def _int(name):
            v = request.form.get(name, "").strip()
            try:
                return int(v) if v else None
            except ValueError:
                return None
        data = {k: (request.form.get(k, "").strip() or None) for k in [
            "name","legal_form","website","hq_city","country","size",
            "annual_budget","mission","vision","value_proposition",
            "unique_positioning","cause_areas","programs","target_beneficiaries",
            "key_achievements","recent_campaigns","partnerships_history",
            "ideal_donor_profile","giving_levels","exclusion_criteria",
            "tone_of_voice","fundraiser_name","fundraiser_email","fundraiser_phone","extra_notes",
        ]}
        data["founding_year"] = _int("founding_year")
        data["annual_budget_eur"] = _int("annual_budget_eur")
        data["typical_ask_individual_eur"] = _int("typical_ask_individual_eur")
        data["typical_ask_corporate_eur"] = _int("typical_ask_corporate_eur")
        save_org(data)
        flash("Contesto organizzazione salvato. Verrà incluso in tutte le prossime ricerche AI.", "success")
        return redirect(url_for("organization"))
    org = get_org() or {}
    import prompts as _prompts
    preview = _prompts.org_context_block(org) if org.get("name") else ""
    return render_template("organization.html", org=org, preview_block=preview)


@app.route("/settings")
def settings():
    import shutil
    import config as cfg
    info = {
        "claude_bin": shutil.which("claude"),
        "db_path": "data/crm.db",
    }
    try:
        acc = hunter.account_info()
    except Exception as e:
        acc = {"ok": False, "error": str(e)}
    if not acc.get("ok"):
        acc["friendly"] = _hunter_friendly_error(acc)
    return render_template(
        "settings.html",
        info=info,
        hunter_acc=acc,
        hunter_cache_days=cfg.HUNTER_CACHE_DAYS,
        hunter_max=cfg.HUNTER_MAX_PER_DOMAIN,
        hunter_seniority=cfg.HUNTER_SENIORITY,
        hunter_key_set=bool(cfg.HUNTER_API_KEY),
        claude_bin_cfg=cfg.CLAUDE_BIN,
        env_path=_config_env_path(),
        backups=list_backups(),
    )


def _config_env_path() -> str:
    """Path del .env nella cartella dati scrivibile (configurazione utente)."""
    base = os.getenv("FORAGER_DATA_DIR") or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ".env")


def _write_env(updates: dict) -> None:
    """Aggiorna/aggiunge chiavi nel .env utente preservando le altre righe."""
    path = _config_env_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f]
    idx = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            idx[s.split("=", 1)[0].strip()] = i
    for k, v in updates.items():
        newline = f"{k}={v}"
        if k in idx:
            lines[idx[k]] = newline
        else:
            lines.append(newline)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


@app.route("/settings/save", methods=["POST"])
def settings_save():
    import config as cfg
    import shutil as _sh
    updates = {}

    key = request.form.get("hunter_api_key", "").strip()
    if request.form.get("hunter_remove"):
        updates["HUNTER_API_KEY"] = ""
    elif key:
        updates["HUNTER_API_KEY"] = key

    seniority = request.form.get("hunter_seniority", "").strip()
    if seniority:
        updates["HUNTER_SENIORITY"] = seniority
    max_dom = request.form.get("hunter_max", "").strip()
    if max_dom.isdigit():
        updates["HUNTER_MAX_PER_DOMAIN"] = max_dom
    cache_days = request.form.get("hunter_cache_days", "").strip()
    if cache_days.isdigit():
        updates["HUNTER_CACHE_DAYS"] = cache_days
    if "claude_bin" in request.form:  # solo se il form include il campo
        updates["CLAUDE_BIN"] = request.form.get("claude_bin", "").strip()

    if not updates:
        flash("Nessuna modifica.", "info")
        return redirect(url_for("settings"))

    _write_env(updates)

    # applica subito, senza riavvio
    for k, v in updates.items():
        os.environ[k] = v
    cfg.HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "").strip()
    cfg.HUNTER_SENIORITY = os.environ.get("HUNTER_SENIORITY", cfg.HUNTER_SENIORITY)
    try:
        cfg.HUNTER_MAX_PER_DOMAIN = int(os.environ.get("HUNTER_MAX_PER_DOMAIN", cfg.HUNTER_MAX_PER_DOMAIN))
        cfg.HUNTER_CACHE_DAYS = int(os.environ.get("HUNTER_CACHE_DAYS", cfg.HUNTER_CACHE_DAYS))
    except ValueError:
        pass
    cfg.CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "").strip()
    ai_engine.CLAUDE_BIN = cfg.CLAUDE_BIN or _sh.which("claude") or "claude"
    _CLAUDE_CHECK["ok"] = None  # forza un nuovo check del CLI

    flash("Chiave Hunter rimossa." if request.form.get("hunter_remove")
          else "Impostazioni salvate.", "success")
    return redirect(url_for("settings"))


def _hunter_friendly_error(acc: dict) -> str:
    """Traduce l'errore tecnico di Hunter in un'indicazione operativa per l'utente."""
    err = (acc.get("error") or "").lower()
    status = acc.get("status")
    if not cfg.HUNTER_API_KEY or "non configurato" in err:
        return t("settings.hunter_err_missing")
    if status in (401, 403) or "unauthorized" in err or "invalid" in err or "api key" in err:
        return t("settings.hunter_err_key")
    if status == 429 or "rate" in err or "quota" in err or "exceeded" in err or "limit" in err:
        return t("settings.hunter_err_quota")
    if err.startswith("network") or "timeout" in err or "connection" in err:
        return t("settings.hunter_err_network")
    return acc.get("error") or t("settings.hunter_err_network")


@app.route("/backup/now", methods=["POST"])
def backup_now():
    dest = backup_db()
    if dest:
        flash(f"Backup creato: {dest.name}", "success")
    else:
        flash("Backup non riuscito. Controlla i permessi della cartella backups/.", "error")
    return redirect(url_for("settings"))


@app.route("/backup/download")
def backup_download():
    """Scarica l'ultimo backup (snapshot coerente del DB)."""
    latest = latest_backup()
    if not latest:
        latest = backup_db()  # creane uno al volo se non esiste
    if not latest:
        flash("Nessun backup disponibile.", "error")
        return redirect(url_for("settings"))
    with open(latest, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/x-sqlite3",
                    headers={"Content-Disposition": f'attachment; filename="{latest.name}"'})


# =========================================================
#                  AI EDITOR — API
# =========================================================

def _prospect_for_ai(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    return dict_from_row(row) if row else {}


@app.route("/api/ai/edit", methods=["POST"])
def api_ai_edit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    action = data.get("action") or "rephrase"
    pid = data.get("prospect_id")
    if not text:
        return jsonify({"ok": False, "error": "Testo vuoto"}), 400
    prospect = _prospect_for_ai(pid) if pid else {}
    result = ai_engine.edit_text(text, action, prospect)
    return jsonify(result)


@app.route("/api/ai/subjects", methods=["POST"])
def api_ai_subjects():
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    n = int(data.get("n") or 5)
    pid = data.get("prospect_id")
    prospect = _prospect_for_ai(pid) if pid else {}
    result = ai_engine.generate_subjects(body, prospect, n=n)
    return jsonify(result)


@app.route("/api/ai/continue", methods=["POST"])
def api_ai_continue():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    pid = data.get("prospect_id")
    if not text:
        return jsonify({"ok": False, "error": "Testo vuoto"}), 400
    prospect = _prospect_for_ai(pid) if pid else {}
    result = ai_engine.continue_writing(text, prospect)
    return jsonify(result)


# =========================================================
#                  SNIPPETS
# =========================================================

@app.route("/snippets", methods=["GET", "POST"])
def snippets():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        body = (request.form.get("body") or "").strip()
        cat = request.form.get("category") or "custom"
        if name and body:
            with cursor() as conn:
                conn.execute("INSERT INTO snippets(name,body,category) VALUES (?,?,?)", (name, body, cat))
            flash("Snippet salvato.", "success")
        return redirect(url_for("snippets"))
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM snippets ORDER BY category, name").fetchall())
    return render_template("snippets.html", snippets=rows)


@app.route("/snippets/<int:sid>/delete", methods=["POST"])
def snippets_delete(sid):
    with cursor() as conn:
        conn.execute("DELETE FROM snippets WHERE id=?", (sid,))
    return redirect(url_for("snippets"))


@app.route("/api/snippets", methods=["GET", "POST"])
def api_snippets():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        body = (data.get("body") or "").strip()
        cat = data.get("category") or "custom"
        if not name or not body:
            return jsonify({"ok": False, "error": "name e body richiesti"}), 400
        with cursor() as conn:
            cur = conn.execute("INSERT INTO snippets(name,body,category) VALUES (?,?,?)", (name, body, cat))
        return jsonify({"ok": True, "id": cur.lastrowid})
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute("SELECT id,name,body,category FROM snippets ORDER BY category, name").fetchall())
    return jsonify(rows)


# =========================================================
#                  BRIEFING ONE-PAGER
# =========================================================

@app.route("/prospects/<int:pid>/briefing", methods=["GET", "POST"])
def briefing(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        abort(404)
    p = dict_from_row(row)

    briefing_data = None
    error = None
    if request.method == "POST":
        result = ai_engine.briefing(p)
        if result.get("ok"):
            briefing_data = result["data"]
            with cursor() as conn:
                conn.execute(
                    "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
                    (pid, "ai_research", "Briefing one-pager generato", briefing_data.get("headline", "")),
                )
        else:
            error = result.get("error")

    return render_template("briefing.html", p=p, briefing=briefing_data, error=error)


# =========================================================
#                  CHAT AI sul prospect
# =========================================================

@app.route("/prospects/<int:pid>/chat")
def prospects_chat(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        p = dict_from_row(row)
        messages = rows_to_dicts(conn.execute(
            "SELECT * FROM chat_messages WHERE prospect_id=? ORDER BY created_at",
            (pid,)
        ).fetchall())
    return render_template("chat.html", p=p, messages=messages)


@app.route("/api/chat/<int:pid>", methods=["POST"])
def api_chat(pid):
    """Risposta sincrona — mantenuto per compatibilità."""
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "Messaggio vuoto"}), 400
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect non trovato"}), 404
    prospect = dict_from_row(row)

    with cursor() as conn:
        history = rows_to_dicts(conn.execute(
            "SELECT role, content FROM chat_messages WHERE prospect_id=? ORDER BY created_at DESC LIMIT 20",
            (pid,)
        ).fetchall())
        history.reverse()
        conn.execute("INSERT INTO chat_messages(prospect_id,role,content) VALUES (?,?,?)", (pid, "user", msg))

    result = ai_engine.chat_message(prospect, msg, history)
    if not result.get("ok"):
        return jsonify(result), 500

    with cursor() as conn:
        conn.execute("INSERT INTO chat_messages(prospect_id,role,content) VALUES (?,?,?)", (pid, "assistant", result["text"]))
    return jsonify({"ok": True, "text": result["text"]})


@app.route("/api/chat/<int:pid>/stream", methods=["POST"])
def api_chat_stream(pid):
    """Risposta streaming via SSE — testo che si srotola token per token."""
    from flask import stream_with_context
    import json as _json
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "Messaggio vuoto"}), 400
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect non trovato"}), 404
    prospect = dict_from_row(row)

    with cursor() as conn:
        history = rows_to_dicts(conn.execute(
            "SELECT role, content FROM chat_messages WHERE prospect_id=? ORDER BY created_at DESC LIMIT 20",
            (pid,)
        ).fetchall())
        history.reverse()
        conn.execute("INSERT INTO chat_messages(prospect_id,role,content) VALUES (?,?,?)", (pid, "user", msg))

    # build prompt
    import prompts as _prompts
    org_ctx = ai_engine.build_context()
    hist_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in (history or [])[-10:])
    prompt = _prompts.CHAT_PROSPECT_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(ai_engine.enrich_prospect_context(prospect), ensure_ascii=False, default=str),
        history=hist_text or "(nessuna)",
        message=msg,
    )

    def gen():
        full = ""
        for evt in ai_engine.run_claude_stream(prompt, allowed_tools=[], usage_kind="chat", prospect_id=pid, timeout=180):
            if evt.get("type") == "chunk":
                full += evt["text"]
            yield "data: " + _json.dumps(evt, ensure_ascii=False) + "\n\n"
            if evt.get("type") == "done":
                # persisti assistant message SOLO se non vuoto: una risposta tronca o vuota
                # (es. stream interrotto) inquinerebbe la cronologia e i prompt successivi.
                final_text = (evt.get("text") or full or "").strip()
                if final_text:
                    try:
                        with cursor() as c2:
                            c2.execute("INSERT INTO chat_messages(prospect_id,role,content) VALUES (?,?,?)", (pid, "assistant", final_text))
                    except Exception:
                        pass

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/compose/<int:pid>/stream", methods=["POST"])
def api_compose_stream(pid):
    """Streaming AI Compose: yield testo token-per-token, no scrittura draft (l'utente salva esplicitamente)."""
    from flask import stream_with_context
    import json as _json
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect non trovato"}), 404
    p = dict_from_row(row)
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose", "cold_intro")
    tone = data.get("tone", "warm")
    try: word_target = int(data.get("word_target") or 180)
    except Exception: word_target = 180
    contact_name = (data.get("contact_name") or p.get("full_name") or "").strip()
    contact_email = (data.get("contact_email") or p.get("email") or "").strip()
    key_points = (data.get("key_points") or "").strip() or "(autonomo)"

    import prompts as _prompts
    # opzionale: template di stile (few-shot)
    template_id = data.get("template_id")
    style_example = ""
    if template_id:
        try:
            with cursor() as conn:
                trow = conn.execute("SELECT * FROM email_templates WHERE id=?", (int(template_id),)).fetchone()
            if trow:
                style_example = _prompts.style_example_block(dict_from_row(trow))
        except Exception:
            pass

    org_ctx = ai_engine.build_context()
    prompt = _prompts.COMPOSE_EMAIL_STREAM_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(p, ensure_ascii=False, default=str),
        purpose=purpose, tone=tone, word_target=word_target,
        contact_name=contact_name or "—", contact_email=contact_email or "—",
        key_points=key_points,
        style_example_block=style_example,
    )

    def gen():
        for evt in ai_engine.run_claude_stream(prompt, allowed_tools=[], usage_kind="compose", prospect_id=pid, timeout=240):
            yield "data: " + _json.dumps(evt, ensure_ascii=False) + "\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/compose/<int:pid>/save", methods=["POST"])
def api_compose_save(pid):
    """Salva una bozza email (subject + body) — chiamato dopo streaming.

    Parser tollerante: gestisce 'Oggetto: X', '**Oggetto:** X', 'Subject: X',
    "Oggetto" su prima riga e corpo separato da 1+ newline, ecc.
    Se non trova nessun oggetto esplicito, usa la prima riga come oggetto.
    """
    import re as _re
    data = request.get_json(silent=True) or {}
    raw = (data.get("text") or "").strip()
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()

    if (not subject or not body) and raw:
        # rimuovi marker markdown (** **, *, _, fence ```)
        cleaned = raw
        cleaned = _re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = _re.sub(r"\n```\s*$", "", cleaned)
        # cerca il primo "Oggetto:" o "Subject:" ovunque nelle prime 3 righe
        m = _re.search(
            r"(?im)^\s*(?:\*\*|__)?\s*(?:Oggetto|Subject)\s*:?\s*(?:\*\*|__)?\s*(.+?)\s*$",
            cleaned[:600], _re.MULTILINE,
        )
        if m:
            subject = subject or m.group(1).strip().strip("*_`\"' ")
            # body = tutto dopo la riga matched
            rest = cleaned[m.end():].lstrip("\n").strip()
            body = body or rest
        else:
            # fallback: prima riga = oggetto, resto = corpo
            lines = cleaned.split("\n", 1)
            first = lines[0].strip().strip("*_`\"' ")
            subject = subject or first[:120]
            body = body or (lines[1].strip() if len(lines) > 1 else cleaned)

    # rifinisci subject
    subject = _re.sub(r"^\s*(?:Oggetto|Subject)\s*:\s*", "", subject, flags=_re.IGNORECASE).strip()
    subject = subject.strip("*_`\"' ")
    body = body.strip("`\n ")

    if not subject and not body:
        return jsonify({"ok": False, "error": "Testo vuoto, nulla da salvare."}), 400
    if not subject:
        subject = body.split("\n", 1)[0][:80] or "Bozza senza oggetto"
    if not body:
        body = subject
        subject = "Bozza"

    purpose = data.get("purpose") or "custom"
    tone = data.get("tone") or "warm"
    word_target = data.get("word_target") or None
    contact_name = data.get("contact_name") or None
    contact_email = data.get("contact_email") or None
    key_points = data.get("key_points") or None
    with cursor() as conn:
        cur = conn.execute(
            """INSERT INTO email_drafts(prospect_id, contact_email, contact_name, subject, body, purpose, tone, word_target, key_points)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, contact_email, contact_name, subject, body, purpose, tone, word_target, key_points),
        )
        draft_id = cur.lastrowid
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (pid, "email", f"Bozza email AI: {subject}", f"Generata in streaming · purpose: {purpose} · tone: {tone}"),
        )
    return jsonify({"ok": True, "draft_id": draft_id, "url": url_for("draft_detail", did=draft_id)})


@app.route("/api/chat/<int:pid>/clear", methods=["POST"])
def api_chat_clear(pid):
    with cursor() as conn:
        conn.execute("DELETE FROM chat_messages WHERE prospect_id=?", (pid,))
    return jsonify({"ok": True})


# =========================================================
#                  SEQUENCE BUILDER
# =========================================================

@app.route("/prospects/<int:pid>/sequence/new", methods=["GET"])
def sequence_new(pid):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            abort(404)
        p = dict_from_row(row)
        existing = rows_to_dicts(conn.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM sequence_steps WHERE sequence_id=s.id) AS n FROM sequences s WHERE prospect_id=? ORDER BY id DESC LIMIT 5",
            (pid,)
        ).fetchall())
    return render_template("sequence_new.html", p=p, existing=existing)


@app.route("/api/sequences/<int:pid>/start", methods=["POST"])
def api_sequence_start(pid):
    data = request.get_json(silent=True) or {}
    goal = data.get("goal") or "cultivation"
    try:
        n_steps = int(data.get("n_steps") or 4)
    except Exception:
        n_steps = 4
    with cursor() as conn:
        row = conn.execute("SELECT id FROM prospects WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Prospect non trovato"}), 404
    job_id = ai_engine.start_sequence_job(pid, goal, n_steps)
    return jsonify({"ok": True, "job_id": job_id, "n_steps": n_steps})


@app.route("/api/sequences/job/<int:job_id>")
def api_sequence_job(job_id):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM research_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Job non trovato"}), 404
    d = dict_from_row(row)
    seq_id = None
    if d.get("status") == "done" and d.get("raw_output"):
        try:
            seq_id = json.loads(d["raw_output"]).get("seq_id")
        except Exception:
            pass
    return jsonify({
        "ok": True,
        "status": d.get("status"),
        "error": d.get("error"),
        "seq_id": seq_id,
        "started_at": d.get("started_at"),
        "finished_at": d.get("finished_at"),
        "url": url_for("sequence_detail", seq_id=seq_id) if seq_id else None,
    })


@app.route("/sequences/<int:seq_id>", methods=["GET", "POST"])
def sequence_detail(seq_id):
    with cursor() as conn:
        seq = dict_from_row(conn.execute("SELECT * FROM sequences WHERE id=?", (seq_id,)).fetchone())
        if not seq:
            abort(404)
        p = dict_from_row(conn.execute("SELECT * FROM prospects WHERE id=?", (seq["prospect_id"],)).fetchone())
        steps = rows_to_dicts(conn.execute("SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_index", (seq_id,)).fetchall())
    return render_template("sequence_detail.html", seq=seq, p=p, steps=steps)


@app.route("/sequences/<int:seq_id>/step/<int:step_id>/edit", methods=["POST"])
def sequence_step_edit(seq_id, step_id):
    with cursor() as conn:
        conn.execute(
            "UPDATE sequence_steps SET subject=?, body=?, delay_days=? WHERE id=?",
            (
                request.form.get("subject"),
                request.form.get("body"),
                _safe_int(request.form.get("delay_days")),
                step_id,
            ),
        )
    flash("Step salvato.", "success")
    return redirect(url_for("sequence_detail", seq_id=seq_id) + f"#step-{step_id}")


@app.route("/sequences/<int:seq_id>/step/<int:step_id>/sent", methods=["POST"])
def sequence_step_sent(seq_id, step_id):
    with cursor() as conn:
        s = conn.execute("SELECT * FROM sequence_steps WHERE id=?", (step_id,)).fetchone()
        if not s:
            abort(404)
        conn.execute("UPDATE sequence_steps SET sent=1, sent_at=CURRENT_TIMESTAMP WHERE id=?", (step_id,))
        seq = conn.execute("SELECT * FROM sequences WHERE id=?", (seq_id,)).fetchone()
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (seq["prospect_id"], "email", f"Sequence step {s['step_index']} inviato", s["subject"] or ""),
        )
    return redirect(url_for("sequence_detail", seq_id=seq_id))


@app.route("/sequences/<int:seq_id>/delete", methods=["POST"])
def sequence_delete(seq_id):
    with cursor() as conn:
        s = conn.execute("SELECT prospect_id FROM sequences WHERE id=?", (seq_id,)).fetchone()
        conn.execute("DELETE FROM sequences WHERE id=?", (seq_id,))
    flash("Sequence eliminata.", "success")
    return redirect(url_for("prospects_detail", pid=s["prospect_id"]) if s else url_for("prospects_list"))


# =========================================================
#                  AVATAR SVG
# =========================================================

@app.route("/avatar.svg")
def avatar_svg():
    """Genera un avatar SVG deterministico dal nome.

    Query params:
      name=<full_name>        (required)
      ptype=individual|corporate  (default: individual)
      size=<px>               (default: 256)
    """
    name = request.args.get("name", "?")
    ptype = request.args.get("ptype", "individual")
    try:
        size = max(64, min(512, int(request.args.get("size", 256))))
    except Exception:
        size = 256
    svg = avatars.generate_svg(name=name, ptype=ptype, size=size)
    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=2592000"   # 30 giorni
    return resp


# =========================================================
#                  EMAIL TEMPLATES (esempi di stile)
# =========================================================

EMAIL_TEMPLATE_CATEGORIES = {
    "cold_intro": "Cold intro",
    "ask": "Ask / richiesta",
    "followup": "Follow-up",
    "thank": "Ringraziamento",
    "custom": "Custom",
}


@app.route("/email-templates", methods=["GET", "POST"])
def email_templates():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        body = (request.form.get("body") or "").strip()
        if not name or not body:
            flash("Nome e corpo email obbligatori.", "error")
        else:
            with cursor() as conn:
                conn.execute(
                    "INSERT INTO email_templates(name, description, body, category) VALUES (?,?,?,?)",
                    (name, request.form.get("description") or None, body, request.form.get("category") or "custom"),
                )
            flash(f"Template '{name}' salvato.", "success")
        return redirect(url_for("email_templates"))

    with cursor() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM email_templates ORDER BY created_at DESC").fetchall())
    return render_template("email_templates.html", templates=rows, categories=EMAIL_TEMPLATE_CATEGORIES)


@app.route("/email-templates/<int:tid>/delete", methods=["POST"])
def email_templates_delete(tid):
    with cursor() as conn:
        conn.execute("DELETE FROM email_templates WHERE id=?", (tid,))
    flash("Template eliminato.", "success")
    return redirect(url_for("email_templates"))


@app.route("/email-templates/<int:tid>/edit", methods=["POST"])
def email_templates_edit(tid):
    with cursor() as conn:
        conn.execute(
            "UPDATE email_templates SET name=?, description=?, body=?, category=? WHERE id=?",
            (
                (request.form.get("name") or "").strip() or "Senza nome",
                request.form.get("description") or None,
                (request.form.get("body") or "").strip(),
                request.form.get("category") or "custom",
                tid,
            ),
        )
    flash("Template aggiornato.", "success")
    return redirect(url_for("email_templates"))


@app.route("/api/email-templates")
def api_email_templates():
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute("SELECT id, name, description, body, category FROM email_templates ORDER BY category, name").fetchall())
    return jsonify(rows)


# =========================================================
#                  PDF EXPORT
# =========================================================

def _gather_prospect_pdf_data(pid: int):
    """Fetcha tutti i dati del prospect serviti al template PDF."""
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
        if not row:
            return None
        p = dict_from_row(row)
        wealth = rows_to_dicts(conn.execute("SELECT * FROM wealth_indicators WHERE prospect_id=? ORDER BY value_eur DESC NULLS LAST", (pid,)).fetchall())
        affils = rows_to_dicts(conn.execute("SELECT * FROM affiliations WHERE prospect_id=?", (pid,)).fetchall())
        giving = rows_to_dicts(conn.execute("SELECT * FROM giving_history WHERE prospect_id=? ORDER BY year DESC NULLS LAST", (pid,)).fetchall())
        conns = rows_to_dicts(conn.execute("SELECT * FROM connections WHERE prospect_id=?", (pid,)).fetchall())
        sources = rows_to_dicts(conn.execute("SELECT * FROM sources WHERE prospect_id=? ORDER BY verified DESC, fetched_at DESC", (pid,)).fetchall())
        news = rows_to_dicts(conn.execute("SELECT * FROM news_items WHERE prospect_id=? ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT 20", (pid,)).fetchall())
    contacts = hunter.existing_contacts(pid)
    return {
        "p": p,
        "wealth": wealth,
        "affils": affils,
        "giving": giving,
        "conns": conns,
        "sources": sources,
        "news": news,
        "contacts": contacts,
        "prospect_tags": _prospect_tags(pid),
    }


@app.route("/prospects/<int:pid>/pdf")
def prospects_pdf(pid):
    """Download PDF server-side via WeasyPrint."""
    data = _gather_prospect_pdf_data(pid)
    if not data:
        abort(404)
    html_str = render_template("pdf/prospect.html", browser_print=False, **data)

    pdf_bytes = pdf_export.render_pdf(html_str, base_url=request.url_root)
    if pdf_bytes is None:
        # fallback: redirect alla print page del browser
        flash("Export PDF server non disponibile, apertura modalità stampa browser.", "success")
        return redirect(url_for("prospects_print", pid=pid))

    safe_name = "".join(c for c in (data["p"].get("full_name") or "prospect") if c.isalnum() or c in " -_").strip().replace(" ", "_") or f"prospect_{pid}"
    fname = f"forager-{safe_name}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.route("/prospects/<int:pid>/print")
def prospects_print(pid):
    """Pagina print-ready: l'utente fa Stampa→Salva PDF dal browser."""
    data = _gather_prospect_pdf_data(pid)
    if not data:
        abort(404)
    return render_template("pdf/prospect.html", browser_print=True, **data)


# =========================================================
#                  VERIFICA FONTI
# =========================================================

@app.route("/prospects/<int:pid>/verify-sources", methods=["POST"])
def prospects_verify_sources(pid):
    force = request.form.get("force") == "1"
    result = ai_engine.verify_sources(pid, force=force)
    if result.get("ok"):
        restr = result.get("restricted_count") or 0
        skipped = result.get("skipped") or 0
        msg = f"{result['ok_count']} fonti OK"
        if restr:
            msg += f", {restr} con accesso limitato"
        msg += f", {result['ko_count']} non raggiungibili"
        if skipped:
            msg += f" ({skipped} già verificate di recente, non ricontrollate)"
        msg += "."
        flash(msg, "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#sources")


@app.route("/prospects/<int:pid>/ground-sources", methods=["POST"])
def prospects_ground_sources(pid):
    """Grounding: verifica se le fonti SUPPORTANO davvero le affermazioni (via WebFetch AI)."""
    with _ai_slot("ground", pid) as free:
        if not free:
            flash("Verifica già in corso per questo prospect: attendi che finisca.", "error")
            return redirect(url_for("prospects_detail", pid=pid) + "#sources")
        result = ai_engine.ground_sources(pid)
    if result.get("ok"):
        flash(f"Grounding: {result['supported']} fonti confermano, {result['contradicted']} contraddicono, "
              f"{result['not_found']} non trovano il dato." + (f" — {result['summary']}" if result.get("summary") else ""), "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#sources")


# =========================================================
#                  CHIEDI AI DATI (chat sull'intero CRM)
# =========================================================

def _db_snapshot(limit=400):
    """Riga compatta per ogni prospect: alimenta la chat in linguaggio naturale sull'intero CRM."""
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            f"""SELECT p.id, p.full_name, p.type, p.stage, p.capacity_rating, p.propensity_score,
                       p.affinity_score, p.ask_amount, p.location, p.sectors, p.company,
                       COALESCE((SELECT SUM(amount_eur) FROM gifts g WHERE g.prospect_id=p.id AND g.status='received'),0) AS raised,
                       (SELECT GROUP_CONCAT(t.name, ', ') FROM tags t JOIN prospect_tags pt ON pt.tag_id=t.id WHERE pt.prospect_id=p.id) AS tags
                FROM prospects p WHERE p.deleted_at IS NULL
                ORDER BY {PRIORITY_SCORE_SQL} DESC LIMIT ?""",
            (limit,),
        ).fetchall())
        total = conn.execute("SELECT COUNT(*) AS n FROM prospects WHERE deleted_at IS NULL").fetchone()["n"]
    lines = []
    for r in rows:
        parts = [f"#{r['id']} {r['full_name']}",
                 TYPE_LABELS.get(r['type'], r['type']),
                 STAGE_LABELS.get(r['stage'], r['stage']),
                 f"cap {r['capacity_rating'] or 0}/5 prop {r['propensity_score'] or 0} aff {r['affinity_score'] or 0}"]
        if r.get('company'): parts.append(r['company'])
        if r.get('location'): parts.append(r['location'])
        if r.get('sectors'): parts.append("settori: " + r['sectors'])
        if r.get('ask_amount'): parts.append(f"ask €{r['ask_amount']}")
        if r.get('raised'): parts.append(f"raccolto €{r['raised']}")
        if r.get('tags'): parts.append("tag: " + r['tags'])
        lines.append(" | ".join(str(x) for x in parts))
    head = f"{total} prospect totali" + (f" (qui i primi {limit} per priorità)" if total > limit else "")
    return head + "\n" + "\n".join(lines)


@app.route("/ask")
def ask_page():
    with cursor() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM prospects").fetchone()["n"]
    return render_template("ask.html", total=n)


@app.route("/api/ask/stream", methods=["POST"])
def api_ask_stream():
    from flask import stream_with_context
    import json as _json
    import prompts as _prompts
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "Domanda vuota"}), 400
    prompt = _prompts.ASK_DB_PROMPT.format(
        org_context=ai_engine.build_context(),
        snapshot=_db_snapshot(),
        question=q,
    )

    def gen():
        for evt in ai_engine.run_claude_stream(prompt, allowed_tools=[], usage_kind="ask_db", timeout=180):
            yield "data: " + _json.dumps(evt, ensure_ascii=False) + "\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# =========================================================
#                  DEEP DIVE
# =========================================================

@app.route("/prospects/<int:pid>/deep-dive/<section>", methods=["POST"])
def prospects_deep_dive(pid, section):
    if section not in ai_engine.DEEP_DIVE_SECTIONS:
        flash("Sezione non valida.", "error")
        return redirect(url_for("prospects_detail", pid=pid))
    with _ai_slot("deep_dive", pid) as free:
        if not free:
            flash("Deep dive già in corso per questo prospect: attendi che finisca.", "error")
            return redirect(url_for("prospects_detail", pid=pid))
        result = ai_engine.deep_dive_section(pid, section)
    if result.get("ok"):
        msg = f"Deep dive {section}: +{result['added']} record"
        if result.get("sources_added"):
            msg += f", +{result['sources_added']} fonti"
        if result.get("note"):
            msg += f" — {result['note']}"
        flash(msg, "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid))


# =========================================================
#                  NEWS ALERTS
# =========================================================

@app.route("/prospects/<int:pid>/news/fetch", methods=["POST"])
def prospects_news_fetch(pid):
    with _ai_slot("news", pid) as free:
        if not free:
            flash("Ricerca news già in corso per questo prospect: attendi che finisca.", "error")
            return redirect(url_for("prospects_detail", pid=pid) + "#news")
        result = ai_engine.fetch_news(pid)
    if result.get("ok"):
        flash(f"News fetch: +{result['added']} nuove (totale trovate: {result['total_items']}).", "success")
    else:
        flash(f"Errore: {result.get('error')}", "error")
    return redirect(url_for("prospects_detail", pid=pid) + "#news")


@app.route("/prospects/<int:pid>/news/<int:nid>/delete", methods=["POST"])
def prospects_news_delete(pid, nid):
    with cursor() as conn:
        conn.execute("DELETE FROM news_items WHERE id=? AND prospect_id=?", (nid, pid))
    return redirect(url_for("prospects_detail", pid=pid) + "#news")


# =========================================================
#                  NETWORK GLOBALE
# =========================================================

@app.route("/network/relink", methods=["POST"])
def network_relink():
    """Riapplica il matching (migliorato) delle connessioni su tutti i prospect esistenti."""
    with cursor() as conn:
        before = conn.execute("SELECT COUNT(*) AS n FROM connections WHERE matched_prospect_id IS NOT NULL").fetchone()["n"]
        # ripulisci i link automatici per ricalcolarli con le nuove regole
        conn.execute("UPDATE connections SET matched_prospect_id=NULL")
    ai_engine.relink_all_connections()
    with cursor() as conn:
        after = conn.execute("SELECT COUNT(*) AS n FROM connections WHERE matched_prospect_id IS NOT NULL").fetchone()["n"]
    flash(f"Connessioni ricollegate: {after} link interni (prima {before}).", "success")
    return redirect(url_for("network_global"))


_ORG_GENERIC = {
    "fondazione", "fondazioni", "foundation", "gruppo", "group", "banca", "compagnia", "di",
    "onlus", "ente", "associazione", "internazionale", "italia", "italiana", "italiane",
    "spa", "srl", "holding", "aps", "ets", "odv", "cooperativa", "coop", "the", "and",
}


def _org_strong_tokens(name: str) -> set:
    """Token distintivi del nome di un'organizzazione (senza forme societarie e parole
    generiche come 'fondazione'/'gruppo'). Usati per collegare affiliazioni/erogazioni
    a un prospect esistente."""
    s = _strip_company_suffix(name or "")
    return {t for t in _normalize_name(s).split() if len(t) >= 3 and t not in _ORG_GENERIC}


@app.route("/network")
def network_global():
    with cursor() as conn:
        prospects = rows_to_dicts(conn.execute(
            "SELECT id, full_name, type, stage, photo_url, website, propensity_score, capacity_rating, ask_amount FROM prospects WHERE deleted_at IS NULL ORDER BY id"
        ).fetchall())
        # archi prospect↔prospect dalle connection già matchate
        conn_edges = rows_to_dicts(conn.execute(
            """SELECT c.prospect_id AS source, c.matched_prospect_id AS target, c.relationship, c.strength
               FROM connections c WHERE c.matched_prospect_id IS NOT NULL"""
        ).fetchall())
        external_counts = {r["pid"]: r["n"] for r in conn.execute(
            "SELECT prospect_id AS pid, COUNT(*) AS n FROM connections WHERE matched_prospect_id IS NULL GROUP BY prospect_id"
        ).fetchall()}
        # legami istituzionali: affiliazioni (board/partner) ed erogazioni/donazioni
        affils = rows_to_dicts(conn.execute(
            "SELECT prospect_id, organization, role FROM affiliations WHERE organization IS NOT NULL AND organization!='—'"
        ).fetchall())
        giving = rows_to_dicts(conn.execute(
            "SELECT prospect_id, organization, amount_eur FROM giving_history WHERE organization IS NOT NULL AND organization!='—'"
        ).fetchall())

    # indice token-distintivi dei prospect, per risolvere un nome-org → prospect esistente
    p_strong = [(p["id"], _org_strong_tokens(p["full_name"])) for p in prospects]

    def resolve_org(orgname, source_pid):
        ost = _org_strong_tokens(orgname)
        if not ost:
            return None
        best, best_len = None, 0
        for pid, pst in p_strong:
            if pid == source_pid or not pst:
                continue
            if pst <= ost and len(pst) > best_len:  # nome del prospect contenuto nell'org
                best, best_len = pid, len(pst)
        return best

    import re as _re
    def clean_org_label(nm):
        # rimuove i chiarimenti tra parentesi: etichette corte e leggibili sul grafo
        s = _re.sub(r"\s*\([^)]*\)", "", nm or "").strip(" ,;–-")
        return s or (nm or "").strip()

    def ent_key(nm):
        base = _strip_company_suffix(clean_org_label(nm))
        toks = [t for t in _normalize_name(base).split() if t not in ("onlus", "italia", "italiana", "italiane")]
        return " ".join(toks)

    entities = {}        # key → label visualizzata (entità citate, non nel CRM)
    entity_funder = set()  # entità che sono fondazioni/finanziatori (mostrate di default)
    inst_edges = []
    seen_edge = set()

    def add_inst_edge(src, orgname, label, rel):
        if not src:
            return
        tgt = resolve_org(orgname, src)
        if tgt is None:
            k = ent_key(orgname)
            if not k or len(k) < 2:
                return
            entities.setdefault(k, clean_org_label(orgname))
            if rel == "giving":
                entity_funder.add(k)  # un ente che riceve un'erogazione è rilevante per il fundraising
            tgt = "e:" + k
        key = (src, tgt, rel)
        if src == tgt or key in seen_edge:
            return
        seen_edge.add(key)
        inst_edges.append({"from": src, "to": tgt, "label": label, "rel": rel, "strength": "medium"})

    for a in affils:
        add_inst_edge(a["prospect_id"], a["organization"], (a.get("role") or "affiliazione")[:40], "board")
    for g in giving:
        add_inst_edge(g["prospect_id"], g["organization"], "finanzia", "giving")

    # un'entità è "funder" (rilevante, mostrata di default) se è una fondazione/trust
    # o se riceve erogazioni; il resto (partner, associazioni di categoria, ecc.) è rumore
    _FUND_KW = ("fondazion", "foundation", "trust", "fonds", "fundación", "stiftung")
    for k, label in entities.items():
        if any(w in label.lower() for w in _FUND_KW):
            entity_funder.add(k)

    # Costruisco dataset per vis-network — NODI COLORATI PER TIPO
    type_palette = {"individual": "#6366f1", "corporate": "#0891b2", "foundation": "#0d9488"}
    nodes = []
    for p in prospects:
        nodes.append({
            "id": p["id"],
            "label": p["full_name"],
            "title": f"{p['full_name']} · {TYPE_LABELS.get(p['type'], p['type'])} · {STAGE_LABELS.get(p['stage'], p['stage'])}",
            "type": p["type"],
            "stage": p["stage"],
            "stage_label": STAGE_LABELS.get(p["stage"], p["stage"]),
            "type_label": TYPE_LABELS.get(p["type"], p["type"]),
            "kind": "prospect",
            "color": type_palette.get(p["type"], "#6366f1"),
            "score": p.get("propensity_score") or 0,
            "capacity": p.get("capacity_rating") or 0,
            "ask": p.get("ask_amount"),
            "img": avatar_url(p["full_name"], p.get("photo_url"), p["type"], domain_from(p.get("website"))),
            "ext": external_counts.get(p["id"], 0),
        })
    for k, disp in entities.items():
        is_funder = k in entity_funder
        nodes.append({
            "id": "e:" + k,
            "label": disp,
            "title": f"{disp} · {'fondazione/ente finanziato' if is_funder else 'entità citata'} (non ancora una scheda nel CRM)",
            "kind": "entity",
            "funder": is_funder,
        })

    conn_links = [{"from": e["source"], "to": e["target"], "label": e.get("relationship") or "",
                   "rel": "connection", "strength": e.get("strength") or "medium"} for e in conn_edges]
    links = conn_links + inst_edges
    internal_edges = len(conn_links) + sum(1 for e in inst_edges if not str(e["to"]).startswith("e:"))

    return render_template("network_global.html",
                           nodes_json=json.dumps(nodes, ensure_ascii=False),
                           edges_json=json.dumps(links, ensure_ascii=False),
                           total_prospects=len(prospects),
                           total_entities=len(entities),
                           total_edges=len(links),
                           internal_edges=internal_edges)


# =========================================================
#                  DUPLICATE DETECTION
# =========================================================

def _normalize_name(s: str) -> str:
    import re
    import unicodedata
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _strip_company_suffix(s: str) -> str:
    """Rimuove le forme societarie finali (SpA, S.r.l., Holding, Group…) così
    'Banca Intesa' e 'Banca Intesa SpA' risultano lo stesso ente nel dedup."""
    import re
    if not s:
        return s
    pat = r"[\s,.\-]+(s\.?p\.?a\.?|s\.?r\.?l\.?s?|s\.?a\.?p\.?a\.?|s\.?a\.?s\.?|s\.?n\.?c\.?|s\.?c\.?a\.?r\.?l\.?|soc(?:ieta)?\.?\s*coop(?:erativa)?|coop(?:erativa)?|holding|group|gruppo|llc|inc\.?|ltd\.?|gmbh|a\.?g\.?|s\.?a\.?|plc|b\.?v\.?|n\.?v\.?)\s*$"
    prev = None
    while prev != s:  # rimuovi suffissi ripetuti (es. "... Group Holding")
        prev = s
        s = re.sub(pat, "", s, flags=re.I)
    return s.strip()


def _find_duplicate_groups():
    """Trova gruppi candidati di duplicati. Restituisce lista di gruppi (ognuno = lista prospect dict)."""
    from difflib import SequenceMatcher
    with cursor() as conn:
        prospects = rows_to_dicts(conn.execute(
            "SELECT id, full_name, type, email, linkedin, website, company, role, location, created_at, updated_at, photo_url FROM prospects WHERE deleted_at IS NULL ORDER BY id"
        ).fetchall())

    seen = set()
    groups = []

    def _add_group(ids, reason):
        ids = sorted(set(ids))
        key = tuple(ids) + (reason,)
        if key in seen or len(ids) < 2:
            return
        seen.add(key)
        members = [p for p in prospects if p["id"] in ids]
        groups.append({"reason": reason, "ids": ids, "members": members})

    # email exact
    by_email = {}
    for p in prospects:
        e = (p.get("email") or "").strip().lower()
        if e:
            by_email.setdefault(e, []).append(p["id"])
    for e, ids in by_email.items():
        if len(ids) >= 2:
            _add_group(ids, f"Stessa email · {e}")

    # linkedin exact
    by_li = {}
    for p in prospects:
        li = (p.get("linkedin") or "").strip().lower().rstrip("/")
        if li:
            by_li.setdefault(li, []).append(p["id"])
    for li, ids in by_li.items():
        if len(ids) >= 2:
            _add_group(ids, f"Stesso LinkedIn")

    # website domain exact (organizzazioni: corporate + fondazioni)
    by_domain = {}
    for p in prospects:
        if p["type"] not in ("corporate", "foundation"):
            continue
        d = domain_from(p.get("website") or "") or ""
        d = d.lower().strip()
        if d:
            by_domain.setdefault(d, []).append(p["id"])
    for d, ids in by_domain.items():
        if len(ids) >= 2:
            _add_group(ids, f"Stesso dominio · {d}")

    # fuzzy name — normalizzazione type-aware (i corporate perdono la forma societaria)
    norm = {}
    for p in prospects:
        nm = _strip_company_suffix(p["full_name"]) if p["type"] in ("corporate", "foundation") else p["full_name"]
        norm[p["id"]] = _normalize_name(nm)
    # Blocking key: confronta solo i nomi che condividono i primi 3 caratteri normalizzati.
    # Riduce le coppie da O(n²) sull'intero set a O(n²) per piccolo bucket → /duplicates
    # non va più in timeout con migliaia di prospect.
    for ptype in PROSPECT_TYPES:
        buckets = {}
        for p in prospects:
            if p["type"] != ptype:
                continue
            na = norm.get(p["id"], "")
            if not na or len(na) < 4:
                continue
            buckets.setdefault(na[:3], []).append(p)
        for items in buckets.values():
            for i in range(len(items)):
                a = items[i]
                na = norm[a["id"]]
                cluster = [a["id"]]
                for j in range(i + 1, len(items)):
                    b = items[j]
                    nb = norm[b["id"]]
                    if na == nb or SequenceMatcher(None, na, nb).ratio() >= 0.88:
                        cluster.append(b["id"])
                if len(cluster) >= 2:
                    _add_group(cluster, f"Nome simile ({TYPE_LABELS.get(ptype, ptype)})")

    # ordina per len gruppo desc
    groups.sort(key=lambda g: (-len(g["ids"]), g["reason"]))
    return groups


@app.route("/duplicates")
def duplicates():
    groups = _find_duplicate_groups()
    return render_template("duplicates.html", groups=groups)


@app.route("/duplicates/merge", methods=["POST"])
def duplicates_merge():
    """Merge: tieni `keep_id`, sposta tutti i child di `remove_ids` su `keep_id`, poi cancella i remove."""
    keep_id = request.form.get("keep_id")
    remove_ids = request.form.getlist("remove_ids")
    if not keep_id or not remove_ids:
        flash("Seleziona quale tenere e quali eliminare.", "error")
        return redirect(url_for("duplicates"))
    try:
        keep_id = int(keep_id)
        remove_ids = [int(x) for x in remove_ids if int(x) != keep_id]
    except Exception:
        flash("ID non validi.", "error")
        return redirect(url_for("duplicates"))
    if not remove_ids:
        flash("Nessun prospect da unire.", "error")
        return redirect(url_for("duplicates"))

    placeholders = ",".join("?" for _ in remove_ids)
    child_tables = [
        "wealth_indicators", "affiliations", "giving_history", "connections",
        "sources", "activities", "prospect_contacts", "tasks", "email_drafts",
        "chat_messages", "sequences", "news_items", "gifts"
    ]
    with cursor() as conn:
        # 1) Consolida i campi scalari: riempi i campi VUOTI del master con i valori
        #    dei duplicati prima di cancellarli (es. una email trovata con Hunter che
        #    sta solo sul duplicato non deve andare persa).
        keep_row = conn.execute("SELECT * FROM prospects WHERE id=?", (keep_id,)).fetchone()
        if keep_row:
            keep = dict(keep_row)
            removed_rows = rows_to_dicts(conn.execute(
                f"SELECT * FROM prospects WHERE id IN ({placeholders}) ORDER BY updated_at DESC, id DESC",
                remove_ids,
            ).fetchall())
            text_fields = [
                "headline", "company", "role", "email", "phone", "location", "country",
                "linkedin", "website", "twitter", "photo_url", "estimated_net_worth",
                "ai_summary", "ai_red_flags", "ai_next_action", "sectors", "notes",
                "ask_rationale",
            ]
            num_fields = [
                "ask_amount", "capacity_rating", "propensity_score", "affinity_score",
                "suggested_ask_eur", "suggested_ask_low_eur", "suggested_ask_high_eur",
            ]
            fills = {}
            for f in text_fields:
                cur = keep.get(f)
                empty = cur is None or (isinstance(cur, str) and not cur.strip())
                if empty:
                    for r in removed_rows:
                        v = r.get(f)
                        if v not in (None, "") and not (isinstance(v, str) and not v.strip()):
                            fills[f] = v
                            break
            for f in num_fields:
                if not keep.get(f):  # 0 o None = non valorizzato
                    best = max((r.get(f) or 0 for r in removed_rows), default=0)
                    if best:
                        fills[f] = best
            if fills:
                sets = ", ".join(f"{k}=?" for k in fills)
                conn.execute(
                    f"UPDATE prospects SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    [*fills.values(), keep_id],
                )

        # 2) Riassegna child rows al master
        for tbl in child_tables:
            try:
                conn.execute(f"UPDATE {tbl} SET prospect_id=? WHERE prospect_id IN ({placeholders})",
                             [keep_id, *remove_ids])
            except Exception:
                pass
        # prospect_tags: unisci senza duplicati
        try:
            conn.execute(f"INSERT OR IGNORE INTO prospect_tags(prospect_id, tag_id) SELECT ?, tag_id FROM prospect_tags WHERE prospect_id IN ({placeholders})",
                         [keep_id, *remove_ids])
            conn.execute(f"DELETE FROM prospect_tags WHERE prospect_id IN ({placeholders})", remove_ids)
        except Exception:
            pass
        # connections: aggiorna anche matched_prospect_id
        try:
            conn.execute(f"UPDATE connections SET matched_prospect_id=? WHERE matched_prospect_id IN ({placeholders})",
                         [keep_id, *remove_ids])
            # una connection non deve puntare a sé stessa dopo il merge
            conn.execute("UPDATE connections SET matched_prospect_id=NULL WHERE prospect_id=matched_prospect_id")
        except Exception:
            pass

        # 3) Dedup dei figli riassegnati: dopo il merge la stessa fonte/email/news
        #    comparirebbe due volte. Tieni la riga con id minore.
        try:
            conn.execute("DELETE FROM sources WHERE prospect_id=? AND id NOT IN (SELECT MIN(id) FROM sources WHERE prospect_id=? GROUP BY url)", (keep_id, keep_id))
            conn.execute("DELETE FROM news_items WHERE prospect_id=? AND id NOT IN (SELECT MIN(id) FROM news_items WHERE prospect_id=? GROUP BY url)", (keep_id, keep_id))
            conn.execute("DELETE FROM prospect_contacts WHERE prospect_id=? AND email IS NOT NULL AND id NOT IN (SELECT MIN(id) FROM prospect_contacts WHERE prospect_id=? AND email IS NOT NULL GROUP BY lower(email))", (keep_id, keep_id))
        except Exception:
            pass

        # Cancella i duplicati
        conn.execute(f"DELETE FROM prospects WHERE id IN ({placeholders})", remove_ids)
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (keep_id, "note", "Merge duplicati", f"Uniti {len(remove_ids)} record duplicati (ID rimossi: {','.join(str(x) for x in remove_ids)})"),
        )
    flash(f"Merge completato: {len(remove_ids)} duplicati uniti nel prospect #{keep_id}.", "success")
    return redirect(url_for("prospects_detail", pid=keep_id))


# =========================================================
#                  USAGE DASHBOARD
# =========================================================

@app.route("/usage")
def usage():
    from datetime import datetime as _dt
    today = date.today()
    start_30 = (today - timedelta(days=30)).isoformat()
    start_7 = (today - timedelta(days=7)).isoformat()

    with cursor() as conn:
        totals = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS cost, COALESCE(SUM(input_tokens),0) AS in_tok, COALESCE(SUM(output_tokens),0) AS out_tok, COALESCE(SUM(duration_ms),0) AS dur FROM usage_log"
        ).fetchone()
        last30 = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS cost FROM usage_log WHERE ts >= ?",
            (start_30,),
        ).fetchone()
        last7 = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS cost FROM usage_log WHERE ts >= ?",
            (start_7,),
        ).fetchone()
        by_kind = rows_to_dicts(conn.execute(
            "SELECT kind, COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS cost, COALESCE(AVG(duration_ms),0) AS avg_ms FROM usage_log GROUP BY kind ORDER BY n DESC"
        ).fetchall())
        # daily last 30
        daily = rows_to_dicts(conn.execute(
            """SELECT substr(ts,1,10) AS day, COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS cost
               FROM usage_log WHERE ts >= ? GROUP BY day ORDER BY day""",
            (start_30,),
        ).fetchall())
        top_prospects = rows_to_dicts(conn.execute(
            """SELECT u.prospect_id AS pid, p.full_name, p.type, COUNT(*) AS n, COALESCE(SUM(u.cost_usd),0) AS cost
               FROM usage_log u LEFT JOIN prospects p ON p.id=u.prospect_id
               WHERE u.prospect_id IS NOT NULL
               GROUP BY u.prospect_id ORDER BY n DESC LIMIT 12"""
        ).fetchall())
        recent = rows_to_dicts(conn.execute(
            """SELECT u.*, p.full_name FROM usage_log u LEFT JOIN prospects p ON p.id=u.prospect_id
               ORDER BY u.id DESC LIMIT 30"""
        ).fetchall())
        errors_n = conn.execute("SELECT COUNT(*) AS n FROM usage_log WHERE ok=0").fetchone()["n"]

    # Hunter quota
    try:
        hunter_acc = hunter.account_info()
    except Exception as e:
        hunter_acc = {"ok": False, "error": str(e)}

    return render_template(
        "usage.html",
        totals=dict(totals),
        last30=dict(last30),
        last7=dict(last7),
        by_kind=by_kind,
        daily=daily,
        daily_json=json.dumps(daily),
        top_prospects=top_prospects,
        recent=recent,
        errors_n=errors_n,
        hunter_acc=hunter_acc,
    )


@app.route("/guide")
def guide():
    from guide_content import GUIDE
    return render_template("guide.html", guide=GUIDE)


# ---------- bootstrap ----------

if __name__ == "__main__":
    init_db()
    # Con il reloader di Flask (debug on) __main__ gira due volte: esegui gli effetti
    # collaterali (ripresa job, scheduler backup) SOLO nel processo worker, una volta.
    if not cfg.DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        ai_engine.recover_orphan_jobs()  # riprende i job interrotti da un riavvio/crash
        start_backup_scheduler()         # backup automatico coerente in background
    print(f"\n  Forager CRM ready → http://{cfg.HOST}:{cfg.PORT}\n")
    app.run(debug=cfg.DEBUG, host=cfg.HOST, port=cfg.PORT)
