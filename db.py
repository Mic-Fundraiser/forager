"""SQLite schema + helpers."""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Cartella dati scrivibile: di default accanto al codice; nell'app pacchettizzata
# (Forager.app) si imposta FORAGER_DATA_DIR su ~/Library/Application Support/Forager.
_DATA_ROOT = Path(os.getenv("FORAGER_DATA_DIR") or Path(__file__).parent)
DB_PATH = _DATA_ROOT / "data" / "crm.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS organization (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT,
    legal_form TEXT,            -- ETS, APS, ODV, Fondazione, Partito politico, Comitato, ONG, Altro
    founding_year INTEGER,
    website TEXT,
    hq_city TEXT,
    country TEXT DEFAULT 'Italia',
    size TEXT,                   -- micro|small|medium|large
    annual_budget TEXT,
    annual_budget_eur INTEGER,
    mission TEXT,
    vision TEXT,
    value_proposition TEXT,
    unique_positioning TEXT,
    cause_areas TEXT,            -- comma separated
    programs TEXT,
    target_beneficiaries TEXT,
    key_achievements TEXT,
    recent_campaigns TEXT,
    partnerships_history TEXT,
    ideal_donor_profile TEXT,
    typical_ask_individual_eur INTEGER,
    typical_ask_corporate_eur INTEGER,
    giving_levels TEXT,          -- es. "50,100,500,1000,5000,25000"
    exclusion_criteria TEXT,     -- red flag donatori (es. tabacco, armi, ecc.)
    tone_of_voice TEXT,
    fundraiser_name TEXT,
    fundraiser_email TEXT,
    fundraiser_phone TEXT,
    extra_notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'individual',   -- individual | corporate
    full_name TEXT NOT NULL,
    headline TEXT,
    company TEXT,
    role TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    country TEXT,
    linkedin TEXT,
    website TEXT,
    twitter TEXT,
    photo_url TEXT,
    capacity_rating INTEGER DEFAULT 0,         -- 0-5
    propensity_score INTEGER DEFAULT 0,        -- 0-100
    affinity_score INTEGER DEFAULT 0,          -- 0-100
    estimated_net_worth TEXT,
    ask_amount INTEGER,
    stage TEXT DEFAULT 'identified',           -- identified|qualified|cultivated|solicited|stewarded|declined
    priority TEXT DEFAULT 'medium',            -- low|medium|high
    source TEXT,
    notes TEXT,
    ai_summary TEXT,
    ai_red_flags TEXT,
    ai_next_action TEXT,
    sectors TEXT,                              -- comma separated
    tags TEXT,                                 -- comma separated
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    category TEXT,        -- real_estate | salary | equity | board | foundation | giving_history | art | other
    label TEXT NOT NULL,
    detail TEXT,
    value_eur INTEGER,
    source TEXT,
    confidence TEXT DEFAULT 'medium',  -- low|medium|high
    origin TEXT DEFAULT 'research',    -- research | deep_dive | manual
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS affiliations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    organization TEXT NOT NULL,
    role TEXT,
    period TEXT,
    type TEXT,            -- corporate | nonprofit | political | academic | other
    source TEXT,
    origin TEXT DEFAULT 'research',   -- research | deep_dive | manual
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS giving_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    organization TEXT,
    year INTEGER,
    amount_eur INTEGER,
    cause TEXT,
    source TEXT,
    notes TEXT,
    origin TEXT DEFAULT 'research',   -- research | deep_dive | manual
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    relationship TEXT,
    context TEXT,
    strength TEXT DEFAULT 'medium',
    matched_prospect_id INTEGER REFERENCES prospects(id) ON DELETE SET NULL,
    origin TEXT DEFAULT 'research',   -- research | deep_dive | manual
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    verified INTEGER DEFAULT 0,         -- 0=non verificata, 1=OK, -1=KO, 2=accessibile con restrizioni
    verified_at TEXT,
    http_status INTEGER,
    verification_note TEXT,
    origin TEXT DEFAULT 'research',     -- research | deep_dive | manual
    grounded TEXT,                      -- supported | not_found | contradicted (verifica del DATO nel contenuto)
    grounding_note TEXT,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    title TEXT,
    url TEXT,
    publisher TEXT,
    snippet TEXT,
    published_at TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    relevance TEXT,         -- high|medium|low
    sentiment TEXT,         -- positive|neutral|negative
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    body TEXT NOT NULL,
    category TEXT,                  -- cold_intro | ask | followup | thank | custom
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    kind TEXT,                  -- research | refresh | deep_dive | news | edit | subjects | continue | briefing | chat | sequence | compose | verify
    prospect_id INTEGER,
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    ok INTEGER DEFAULT 1,
    error TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_news_prospect ON news_items(prospect_id);
CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage_log(ts);
CREATE INDEX IF NOT EXISTS idx_usage_kind ON usage_log(kind);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    type TEXT,            -- note|email|call|meeting|task|stage_change|ai_research
    title TEXT,
    body TEXT,
    happened_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prospect_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    position TEXT,
    seniority TEXT,
    department TEXT,
    linkedin TEXT,
    twitter TEXT,
    phone TEXT,
    confidence INTEGER,
    verification TEXT,
    source TEXT DEFAULT 'hunter',
    is_primary INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hunter_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE,
    last_searched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    company_name TEXT,
    industry TEXT,
    pattern TEXT,
    organization TEXT,
    country TEXT,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_contacts_prospect ON prospect_contacts(prospect_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON prospect_contacts(email);

CREATE TABLE IF NOT EXISTS research_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER,
    query TEXT,
    status TEXT DEFAULT 'pending',  -- pending|running|done|error
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    raw_output TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT 'slate',     -- slate|blue|violet|amber|emerald|rose|indigo|cyan
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prospect_tags (
    prospect_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (prospect_id, tag_id),
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER,
    title TEXT NOT NULL,
    body TEXT,
    due_date TEXT,                                -- ISO YYYY-MM-DD
    priority TEXT DEFAULT 'medium',               -- low|medium|high
    status TEXT DEFAULT 'open',                   -- open|done|cancelled
    completed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS email_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    contact_email TEXT,
    contact_name TEXT,
    subject TEXT,
    body TEXT,
    purpose TEXT,             -- cold_intro | warm_followup | ask | thank_you | event_invite | reactivation | custom
    tone TEXT,                -- formal | warm | direct | confidential
    word_target INTEGER,
    key_points TEXT,
    sent INTEGER DEFAULT 0,
    sent_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    period_year INTEGER,
    period_label TEXT,        -- 2026 | Q1 2026 | Campagna fine vita
    target_eur INTEGER NOT NULL,
    notes TEXT,
    archived INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Donazioni REALI (ciò che è entrato), distinte dall'ask (prospects.ask_amount).
-- È la spina dorsale del CRM: forecast/raccolto/retention/ringraziamenti derivano da qui.
CREATE TABLE IF NOT EXISTS gifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    amount_eur INTEGER NOT NULL,
    kind TEXT DEFAULT 'one_off',     -- one_off | pledge | recurring
    status TEXT DEFAULT 'received',  -- promised (promesso) | received (incassato)
    gift_date TEXT,                  -- ISO YYYY-MM-DD
    campaign TEXT,                   -- campagna/appello (testo libero per ora)
    designation TEXT,                -- causa / destinazione
    notes TEXT,
    thanked INTEGER DEFAULT 0,       -- 0/1 ringraziato
    thanked_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_gifts_prospect ON gifts(prospect_id);
CREATE INDEX IF NOT EXISTS idx_gifts_date ON gifts(gift_date);
CREATE INDEX IF NOT EXISTS idx_gifts_status ON gifts(status);

-- Campagne/appelli come ENTITÀ (non più testo libero sul gift): obiettivo,
-- periodo e attribuzione dei gift → "quale campagna ha reso di più?" ha risposta.
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date TEXT,                 -- ISO YYYY-MM-DD
    end_date TEXT,
    target_eur INTEGER,
    status TEXT DEFAULT 'active',    -- active | closed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);

CREATE INDEX IF NOT EXISTS idx_prospects_stage ON prospects(stage);
CREATE INDEX IF NOT EXISTS idx_prospects_type ON prospects(type);
CREATE INDEX IF NOT EXISTS idx_wealth_prospect ON wealth_indicators(prospect_id);
CREATE INDEX IF NOT EXISTS idx_activities_prospect ON activities(prospect_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_prospect ON tasks(prospect_id);
CREATE INDEX IF NOT EXISTS idx_drafts_prospect ON email_drafts(prospect_id);
CREATE INDEX IF NOT EXISTS idx_sources_prospect ON sources(prospect_id);
CREATE INDEX IF NOT EXISTS idx_affiliations_prospect ON affiliations(prospect_id);
CREATE INDEX IF NOT EXISTS idx_giving_prospect ON giving_history(prospect_id);
CREATE INDEX IF NOT EXISTS idx_connections_prospect ON connections(prospect_id);
CREATE INDEX IF NOT EXISTS idx_connections_matched ON connections(matched_prospect_id);
CREATE INDEX IF NOT EXISTS idx_jobs_prospect ON research_jobs(prospect_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON research_jobs(status);

CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT,                  -- intro | closing | ask | followup | custom
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    role TEXT NOT NULL,             -- user | assistant
    content TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    name TEXT,
    goal TEXT,                      -- cold_outreach | cultivation | reactivation | ask | thank_steward
    status TEXT DEFAULT 'draft',    -- draft | active | done
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sequence_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    step_index INTEGER NOT NULL,
    delay_days INTEGER DEFAULT 7,
    purpose TEXT,
    subject TEXT,
    body TEXT,
    sent INTEGER DEFAULT 0,
    sent_at TEXT,
    scheduled_for TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_prospect ON chat_messages(prospect_id);
CREATE INDEX IF NOT EXISTS idx_seq_prospect ON sequences(prospect_id);
CREATE INDEX IF NOT EXISTS idx_seqstep_seq ON sequence_steps(sequence_id);
"""


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout: se il DB è bloccato da un job AI in background, attende invece di
    # fallire subito con "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL: letture e scritture concorrenti senza lock reciproci (web + job thread).
    # busy_timeout: ulteriore rete di sicurezza a livello SQLite.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def cursor():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with cursor() as conn:
        conn.executescript(SCHEMA)
        # safe migrations (idempotent column adds)
        def _add_col(table, col, ddl):
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        _add_col("connections", "matched_prospect_id", "INTEGER REFERENCES prospects(id) ON DELETE SET NULL")
        _add_col("sources", "verified", "INTEGER DEFAULT 0")
        _add_col("sources", "verified_at", "TEXT")
        _add_col("sources", "http_status", "INTEGER")
        _add_col("sources", "verification_note", "TEXT")
        # ask suggerito con motivazione
        _add_col("prospects", "suggested_ask_eur", "INTEGER")
        _add_col("prospects", "suggested_ask_low_eur", "INTEGER")
        _add_col("prospects", "suggested_ask_high_eur", "INTEGER")
        _add_col("prospects", "ask_rationale", "TEXT")
        _add_col("prospects", "ask_suggested_at", "TEXT")
        # segnali dalle news (opportunity|neutral|risk)
        _add_col("news_items", "signal", "TEXT")
        _add_col("news_items", "signal_note", "TEXT")
        # origine dei record figli: distingue ricerca completa, deep-dive e inserimenti manuali
        # così una nuova ricerca NON cancella più deep-dive e dati aggiunti a mano.
        for _t in ("wealth_indicators", "affiliations", "giving_history", "connections", "sources"):
            _add_col(_t, "origin", "TEXT DEFAULT 'research'")
        # grounding: verifica del DATO nel contenuto della fonte
        _add_col("sources", "grounded", "TEXT")
        _add_col("sources", "grounding_note", "TEXT")
        # lingua interfaccia + AI (it/en)
        _add_col("organization", "language", "TEXT DEFAULT 'it'")
        # cadenze di ricontatto: il CRM deve dirti CHI richiamare e quando
        _add_col("prospects", "last_contact_date", "TEXT")     # ISO, auto da activities
        _add_col("prospects", "next_contact_date", "TEXT")     # ISO, manuale o da cadenza
        _add_col("prospects", "contact_cadence_days", "INTEGER")
        # soft-delete: i prospect eliminati vanno nel cestino, non persi per sempre
        _add_col("prospects", "deleted_at", "TEXT")
        # campagne: FK sul gift (il campo testo `campaign` resta per retro-compat/import)
        _add_col("gifts", "campaign_id", "INTEGER REFERENCES campaigns(id) ON DELETE SET NULL")
        # compliance Italia: deducibilità + ricevuta per erogazioni liberali
        _add_col("gifts", "is_deductible", "INTEGER DEFAULT 0")
        _add_col("gifts", "receipt_sent", "INTEGER DEFAULT 0")
        _add_col("gifts", "receipt_number", "TEXT")


def dict_from_row(row):
    return dict(row) if row else None


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


BACKUP_DIR = DB_PATH.parent.parent / "backups"


def backup_db(keep: int = 14) -> Path | None:
    """Backup COERENTE del DB (anche con WAL attivo) via API sqlite .backup(), non copia
    grezza del file. Ruota tenendo gli ultimi `keep`. Ritorna il path del backup."""
    import datetime
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = BACKUP_DIR / f"crm-{ts}.db"
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)          # snapshot transazionale e consistente
        dst.close()
        src.close()
        # rotazione: mantieni solo gli ultimi `keep`
        backups = sorted(BACKUP_DIR.glob("crm-*.db"))
        for old in backups[:-keep]:
            try:
                old.unlink()
            except Exception:
                pass
        return dest
    except Exception as e:
        print(f"  Backup fallito: {e}")
        return None


def latest_backup() -> Path | None:
    try:
        backups = sorted(BACKUP_DIR.glob("crm-*.db"))
        return backups[-1] if backups else None
    except Exception:
        return None


def list_backups() -> list:
    try:
        out = []
        for f in sorted(BACKUP_DIR.glob("crm-*.db"), reverse=True):
            st = f.stat()
            out.append({"name": f.name, "size_kb": round(st.st_size / 1024), "mtime": st.st_mtime})
        return out
    except Exception:
        return []


def start_backup_scheduler(interval_hours: int = 24):
    """Backup automatico in background: uno poco dopo l'avvio, poi ogni `interval_hours`.
    Protegge l'unico archivio donatori locale senza che l'utente debba ricordarsene."""
    import threading

    def _run():
        backup_db()
        t = threading.Timer(interval_hours * 3600, _run)
        t.daemon = True
        t.start()

    t0 = threading.Timer(8, _run)  # leggero ritardo per non rallentare l'avvio
    t0.daemon = True
    t0.start()


def get_org() -> dict | None:
    with cursor() as conn:
        row = conn.execute("SELECT * FROM organization WHERE id=1").fetchone()
    return dict_from_row(row)


def set_language(code: str):
    """Salva la lingua scelta in organization.language (riga singleton id=1).
    Usata anche dai job AI in background per scrivere nella lingua giusta."""
    if code not in ("it", "en"):
        code = "it"
    with cursor() as conn:
        conn.execute(
            "INSERT INTO organization(id, language) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET language=excluded.language",
            (code,),
        )


def save_org(data: dict):
    cols = [
        "name","legal_form","founding_year","website","hq_city","country","size",
        "annual_budget","annual_budget_eur","mission","vision","value_proposition",
        "unique_positioning","cause_areas","programs","target_beneficiaries",
        "key_achievements","recent_campaigns","partnerships_history",
        "ideal_donor_profile","typical_ask_individual_eur","typical_ask_corporate_eur",
        "giving_levels","exclusion_criteria","tone_of_voice",
        "fundraiser_name","fundraiser_email","fundraiser_phone","extra_notes",
    ]
    placeholders = ",".join("?" for _ in cols)
    set_clause = ",".join(f"{c}=excluded.{c}" for c in cols)
    vals = [data.get(c) for c in cols]
    with cursor() as conn:
        conn.execute(
            f"""INSERT INTO organization(id,{','.join(cols)}) VALUES (1,{placeholders})
                ON CONFLICT(id) DO UPDATE SET {set_clause}, updated_at=CURRENT_TIMESTAMP""",
            vals,
        )
