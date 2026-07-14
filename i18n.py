"""i18n leggero, zero dipendenze: catalogo it/en + funzione t().

La lingua corrente è in flask.g.lang (impostata da app.before_request).
Le stringhe mancanti ricadono su italiano, poi sulla chiave (così si notano).
"""
try:
    from flask import g
except Exception:  # uso fuori da Flask (test)
    g = None

LANGS = ("it", "en")
LANG_LABELS = {"it": "Italiano", "en": "English"}
DEFAULT_LANG = "it"


def current_lang() -> str:
    lang = getattr(g, "lang", None) if g is not None else None
    return lang if lang in LANGS else DEFAULT_LANG


def t(key: str, **kw) -> str:
    """Traduce una chiave nella lingua corrente. Supporta interpolazione {nome}."""
    entry = CAT.get(key)
    if entry is None:
        s = key
    else:
        lang = current_lang()
        s = entry.get(lang) or entry.get("it") or key
    if kw:
        try:
            s = s.format(**kw)
        except Exception:
            pass
    return s


def add(catalog: dict):
    """Unisce un frammento di catalogo {chiave: {it, en}} in CAT."""
    CAT.update(catalog or {})


# ===================================================================
#  CATALOGO  —  CAT[chiave] = {"it": "...", "en": "..."}
#  Nucleo (chrome, navigazione, etichette di dominio). Le schermate
#  aggiungono le loro chiavi più sotto via add({...}).
# ===================================================================
CAT = {
    # --- generici / azioni ---
    "common.save": {"it": "Salva", "en": "Save"},
    "common.cancel": {"it": "Annulla", "en": "Cancel"},
    "common.delete": {"it": "Elimina", "en": "Delete"},
    "common.edit": {"it": "Modifica", "en": "Edit"},
    "common.create": {"it": "Crea", "en": "Create"},
    "common.open": {"it": "Apri", "en": "Open"},
    "common.all": {"it": "Tutti", "en": "All"},
    "common.none": {"it": "Nessuno", "en": "None"},
    "common.search": {"it": "Cerca", "en": "Search"},
    "common.loading": {"it": "Attendo…", "en": "Working…"},
    "common.back": {"it": "Indietro", "en": "Back"},

    # --- sidebar / navigazione ---
    "nav.tagline": {"it": "Fundraising · CRM", "en": "Fundraising · CRM"},
    "nav.dashboard": {"it": "Dashboard", "en": "Dashboard"},
    "nav.all_prospects": {"it": "Tutti i prospect", "en": "All prospects"},
    "nav.research": {"it": "Prospect Research", "en": "Prospect Research"},
    "nav.ask": {"it": "Chiedi ai dati", "en": "Ask your data"},
    "nav.tasks": {"it": "Tasks", "en": "Tasks"},
    "nav.activity": {"it": "Attività", "en": "Activity"},
    "nav.section_segments": {"it": "Segmenti", "en": "Segments"},
    "nav.major_donor": {"it": "Major donor", "en": "Major donors"},
    "nav.corporate": {"it": "Corporate", "en": "Corporate"},
    "nav.foundations": {"it": "Fondazioni", "en": "Foundations"},
    "nav.section_pipeline": {"it": "Pipeline", "en": "Pipeline"},
    "nav.qualified": {"it": "Qualificati", "en": "Qualified"},
    "nav.cultivation": {"it": "Cultivation", "en": "Cultivation"},
    "nav.solicited": {"it": "Solicitati", "en": "Solicited"},
    "nav.steward": {"it": "Steward", "en": "Stewardship"},
    "nav.section_tools": {"it": "Strumenti", "en": "Tools"},
    "nav.goals": {"it": "Goals & forecast", "en": "Goals & forecast"},
    "nav.network": {"it": "Network mappa", "en": "Network map"},
    "nav.duplicates": {"it": "Duplicati", "en": "Duplicates"},
    "nav.tags": {"it": "Tag", "en": "Tags"},
    "nav.import": {"it": "Import CSV", "en": "Import CSV"},
    "nav.email_templates": {"it": "Esempi email", "en": "Email examples"},
    "nav.snippets": {"it": "Snippets", "en": "Snippets"},
    "nav.org": {"it": "La mia org", "en": "My org"},
    "nav.export": {"it": "Export CSV", "en": "Export CSV"},
    "nav.usage": {"it": "Consumo AI", "en": "AI usage"},
    "nav.settings": {"it": "Settings", "en": "Settings"},
    "nav.guide": {"it": "Guida", "en": "Guide"},

    # --- guida in-app ---
    "guide.eyebrow": {"it": "Manuale", "en": "Manual"},
    "guide.title": {"it": "Guida a Forager", "en": "Forager guide"},
    "guide.subtitle": {
        "it": "Tutto quello che Forager sa fare, spiegato dall'inizio: ricerca AI, pipeline, donazioni, email e molto altro.",
        "en": "Everything Forager can do, explained from the start: AI research, pipeline, gifts, email and much more.",
    },
    "guide.search_ph": {"it": "Cerca nella guida…", "en": "Search the guide…"},
    "guide.toc": {"it": "In questa pagina", "en": "On this page"},
    "guide.tip_label": {"it": "Suggerimento", "en": "Tip"},
    "guide.no_results": {"it": "Nessun risultato nella guida", "en": "No results in the guide"},
    "guide.no_results_hint": {"it": "Prova con una parola diversa, ad esempio “email” o “backup”.", "en": "Try a different word, e.g. “email” or “backup”."},
    "guide.footer": {"it": "Scorciatoia: apri la palette da qualsiasi pagina con", "en": "Shortcut: open the palette from any page with"},

    # --- header ---
    "header.search_ph": {"it": "Cerca per nome, azienda, settore…", "en": "Search by name, company, sector…"},
    "header.new_research": {"it": "Nuova ricerca", "en": "New research"},
    "header.open_palette": {"it": "Vai a… (cerca persone e sezioni)", "en": "Go to… (search people and sections)"},
    "header.account": {"it": "Account e impostazioni", "en": "Account & settings"},

    # --- accessibilità ---
    "a11y.skip_to_content": {"it": "Vai al contenuto", "en": "Skip to content"},
    "a11y.main_nav": {"it": "Navigazione principale", "en": "Main navigation"},
    "a11y.open_menu": {"it": "Apri menu", "en": "Open menu"},
    "a11y.dismiss": {"it": "Chiudi", "en": "Dismiss"},

    # --- conferme (modale non nativa) ---
    "confirm.title": {"it": "Confermi?", "en": "Are you sure?"},
    "confirm.confirm": {"it": "Conferma", "en": "Confirm"},

    # --- sezioni sidebar ---
    "nav.section_main": {"it": "Principale", "en": "Main"},
    "nav.org_setup_hint": {"it": "Completa il profilo della tua organizzazione", "en": "Complete your organization profile"},

    # --- command palette / overlay ---
    "palette.ph": {"it": "Cerca un prospect o salta a una sezione…", "en": "Search a prospect or jump to a section…"},
    "palette.navigate": {"it": "naviga", "en": "navigate"},
    "palette.open": {"it": "apri", "en": "open"},
    "palette.a_new": {"it": "Nuova ricerca prospect", "en": "New prospect research"},
    "palette.searching": {"it": "Cerco…", "en": "Searching…"},
    "palette.no_results": {"it": "Nessun risultato per", "en": "No results for"},
    "busy.title": {"it": "Claude sta lavorando…", "en": "Claude is working…"},
    "busy.sub": {"it": "Di solito 15–60 secondi. Non chiudere la pagina.", "en": "Usually 15–60 seconds. Don't close the page."},

    # --- selettore lingua ---
    "lang.label": {"it": "Lingua", "en": "Language"},

    # --- etichette di dominio: stage ---
    "stage.identified": {"it": "Identificato", "en": "Identified"},
    "stage.qualified": {"it": "Qualificato", "en": "Qualified"},
    "stage.cultivated": {"it": "In cultivation", "en": "In cultivation"},
    "stage.solicited": {"it": "Sollecitato", "en": "Solicited"},
    "stage.stewarded": {"it": "Steward", "en": "Stewardship"},
    "stage.declined": {"it": "Declinato", "en": "Declined"},
    # priorità
    "priority.low": {"it": "Bassa", "en": "Low"},
    "priority.medium": {"it": "Media", "en": "Medium"},
    "priority.high": {"it": "Alta", "en": "High"},
    # tipi prospect
    "type.individual": {"it": "Major donor", "en": "Major donor"},
    "type.corporate": {"it": "Corporate", "en": "Corporate"},
    "type.foundation": {"it": "Fondazione", "en": "Foundation"},
    # gift
    "gift.kind.one_off": {"it": "Una tantum", "en": "One-off"},
    "gift.kind.pledge": {"it": "Pledge / impegno", "en": "Pledge"},
    "gift.kind.recurring": {"it": "Ricorrente", "en": "Recurring"},
    "gift.status.received": {"it": "Incassato", "en": "Received"},
    "gift.status.promised": {"it": "Promesso", "en": "Promised"},
    # livello di confidenza / forza (dati AI: wealth, connessioni, contatti)
    "level.high": {"it": "Alta", "en": "High"},
    "level.medium": {"it": "Media", "en": "Medium"},
    "level.low": {"it": "Bassa", "en": "Low"},

    # --- dettaglio prospect: sub-nav, azioni, glossario (aggiunte UX) ---
    "pdetail.sections_nav": {"it": "Sezioni della scheda", "en": "Profile sections"},
    "pdetail.nav_overview": {"it": "Panoramica", "en": "Overview"},
    "pdetail.nav_summary": {"it": "Riassunto AI", "en": "AI summary"},
    "pdetail.nav_ask": {"it": "Ask consigliato", "en": "Suggested ask"},
    "pdetail.nav_gifts": {"it": "Donazioni", "en": "Gifts"},
    "pdetail.nav_wealth": {"it": "Ricchezza", "en": "Wealth"},
    "pdetail.nav_contacts": {"it": "Contatti", "en": "Contacts"},
    "pdetail.nav_activity": {"it": "Attività", "en": "Activity"},
    "pdetail.nav_news": {"it": "News", "en": "News"},
    "pdetail.nav_sources": {"it": "Fonti", "en": "Sources"},
    "pdetail.more_actions": {"it": "Altre azioni", "en": "More actions"},
    "pdetail.stage_updated": {"it": "Stage aggiornato", "en": "Stage updated"},
    "pdetail.score_propensity_help": {"it": "Propensione a donare: quanto è probabile che questa persona/ente sostenga la tua causa (0–100).", "en": "Propensity to give: how likely this person/entity is to support your cause (0–100)."},
    "pdetail.score_affinity_help": {"it": "Affinità con la tua missione: vicinanza tra i suoi interessi e le tue cause (0–100).", "en": "Affinity with your mission: closeness between their interests and your causes (0–100)."},
    "pdetail.score_capacity_help": {"it": "Capacità economica stimata di donare (1–5 stelle).", "en": "Estimated financial capacity to give (1–5 stars)."},

    # --- lista prospect: filtri rapidi / contatore (aggiunte UX) ---
    "plist.filtered": {"it": "filtrati", "en": "filtered"},
    "plist.qf_all": {"it": "Tutti", "en": "All"},
    "plist.qf_top": {"it": "Top priorità", "en": "Top priority"},
    "plist.filters_label": {"it": "Filtri attivi", "en": "Active filters"},
    "plist.clear_filters": {"it": "Azzera", "en": "Clear"},
    "plist.compose_quick": {"it": "Componi email", "en": "Compose email"},

    # --- onboarding / primo avvio (aggiunte UX) ---
    "onb.title": {"it": "Inizia da qui", "en": "Start here"},
    "onb.subtitle": {"it": "Tre passi per far funzionare Forager al massimo.", "en": "Three steps to get the most out of Forager."},
    "onb.step1": {"it": "Completa il profilo della tua organizzazione", "en": "Complete your organization profile"},
    "onb.step1_desc": {"it": "Missione e cause: guidano l'AI in ogni ricerca.", "en": "Mission and causes guide the AI in every search."},
    "onb.step2": {"it": "Avvia la prima ricerca prospect", "en": "Run your first prospect research"},
    "onb.step2_desc": {"it": "L'AI costruisce un profilo completo del donatore.", "en": "The AI builds a complete donor profile."},
    "onb.step3": {"it": "Imposta un obiettivo di raccolta", "en": "Set a fundraising goal"},
    "onb.step3_desc": {"it": "Misura il forecast verso il tuo target.", "en": "Track the forecast toward your target."},
    "onb.done": {"it": "Fatto", "en": "Done"},
    "onb.go": {"it": "Vai", "en": "Go"},
    "welcome.steps_hint": {"it": "3 passi · meno di 2 minuti", "en": "3 steps · under 2 minutes"},

    # --- settings ---
    "settings.breadcrumb": {"it": "Workspace · Sistema", "en": "Workspace · System"},
    "settings.title": {"it": "Settings", "en": "Settings"},
    "settings.engine_title": {"it": "Motore AI", "en": "AI engine"},
    "settings.connected": {"it": "Connesso", "en": "Connected"},
    "settings.not_found": {"it": "Non trovato", "en": "Not found"},
    "settings.engine_installed": {"it": "installato", "en": "installed"},
    "settings.engine_info": {
        "it": "Forager usa come motore AI un CLI agentico installato sul tuo computer, con il tuo abbonamento: <b>Claude Code</b> (Anthropic, consigliato) oppure <b>Codex CLI</b> (OpenAI). Nessuna API key da inserire: l'autenticazione la fa il CLI stesso.",
        "en": "Forager's AI engine is an agent CLI installed on your computer, using your own subscription: <b>Claude Code</b> (Anthropic, recommended) or <b>Codex CLI</b> (OpenAI). No API key to paste: the CLI handles authentication.",
    },
    "settings.engine_claude_sub": {"it": "Abbonamento Claude · consigliato", "en": "Claude subscription · recommended"},
    "settings.engine_codex_sub": {"it": "Abbonamento ChatGPT (Plus/Pro)", "en": "ChatGPT subscription (Plus/Pro)"},
    "settings.codex_install_hint": {
        "it": "Il CLI codex non è installato (o non è nel PATH). Installalo e riavvia Forager:",
        "en": "The codex CLI is not installed (or not in PATH). Install it and restart Forager:",
    },
    "settings.codex_install_link": {"it": "Guida all'installazione di Codex CLI", "en": "Codex CLI install guide"},
    "settings.codex_binary": {"it": "Codex binary", "en": "Codex binary"},
    "settings.claude_install_hint": {
        "it": "Il CLI claude non è installato (o non è nel PATH). Installalo e riavvia Forager:",
        "en": "The claude CLI is not installed (or not in PATH). Install it and restart Forager:",
    },
    "settings.claude_install_link": {"it": "Guida all'installazione di Claude Code", "en": "Claude Code install guide"},
    "settings.claude_binary": {"it": "Claude binary", "en": "Claude binary"},
    "settings.database": {"it": "Database", "en": "Database"},
    "settings.backup_title": {"it": "Dati & backup", "en": "Data & backup"},
    "settings.backup_auto": {"it": "auto ogni 24h", "en": "auto every 24h"},
    "settings.backup_info": {
        "it": "Backup automatico e coerente del database (snapshot transazionale, anche con WAL attivo), in <code>backups/</code>, con rotazione (ultimi 14). Per ripristinare: <code>./forager restore</code> da terminale.",
        "en": "Automatic, consistent database backup (transactional snapshot, WAL-safe) into <code>backups/</code>, rotated (last 14). To restore: <code>./forager restore</code> from the terminal.",
    },
    "settings.backup_now": {"it": "Backup ora", "en": "Back up now"},
    "settings.backup_busy": {"it": "Backup…", "en": "Backing up…"},
    "settings.backup_download": {"it": "Scarica ultimo backup", "en": "Download latest backup"},
    "settings.backup_none": {"it": "Nessun backup ancora — clicca “Backup ora”.", "en": "No backups yet — click “Back up now”."},
    "settings.backup_file": {"it": "File", "en": "File"},
    "settings.backup_size": {"it": "Dimensione", "en": "Size"},
    "settings.export_title": {"it": "Esporta i tuoi dati", "en": "Export your data"},
    "settings.export_info": {
        "it": "I dati sono tuoi: esportali quando vuoi, senza lock-in.",
        "en": "Your data is yours: export it anytime, no lock-in.",
    },
    "settings.export_prospects": {"it": "Prospect (CSV)", "en": "Prospects (CSV)"},
    "settings.export_gifts": {"it": "Donazioni (CSV)", "en": "Gifts (CSV)"},
    "settings.export_full": {"it": "Tutto (JSON)", "en": "Everything (JSON)"},
    "settings.hunter_title": {"it": "Hunter.io · email decision maker", "en": "Hunter.io · decision-maker email"},
    "settings.hunter_error": {"it": "Errore", "en": "Error"},
    "settings.hunter_info": {
        "it": "Hunter viene chiamato <strong>solo quando glielo chiedi esplicitamente</strong> dal profilo di un prospect. Filtro <code>seniority=executive</code>, limite {max} email/dominio, cache {days} giorni.",
        "en": "Hunter is called <strong>only when you explicitly ask</strong> from a prospect profile. <code>seniority=executive</code> filter, {max} emails/domain limit, {days}-day cache.",
    },
    "settings.hunter_plan": {"it": "Piano", "en": "Plan"},
    "settings.hunter_searches": {"it": "Ricerche", "en": "Searches"},
    "settings.hunter_verifications": {"it": "Verifiche", "en": "Verifications"},
    "settings.hunter_available": {"it": "{n} disponibili", "en": "{n} available"},
    "settings.hunter_reset": {"it": "Reset {d}", "en": "Resets {d}"},
    "settings.hunter_unreachable": {"it": "Hunter non disponibile", "en": "Hunter unavailable"},
    "settings.hunter_err_missing": {
        "it": "API key non configurata. Hunter è opzionale: serve solo per trovare le email dei decision maker. Crea un account gratuito su hunter.io e aggiungi HUNTER_API_KEY nel file .env.",
        "en": "API key not configured. Hunter is optional: it's only used to find decision-maker emails. Create a free account on hunter.io and add HUNTER_API_KEY to your .env file.",
    },
    "settings.hunter_err_key": {
        "it": "API key non valida o scaduta. Controlla la chiave su hunter.io → API e aggiornala nel file .env.",
        "en": "Invalid or expired API key. Check your key on hunter.io → API and update it in the .env file.",
    },
    "settings.hunter_err_quota": {
        "it": "Quota Hunter esaurita per questo mese. Le ricerche email riprenderanno al reset del piano.",
        "en": "Hunter quota exhausted for this month. Email searches will resume when your plan resets.",
    },
    "settings.hunter_err_network": {
        "it": "Hunter non raggiungibile: controlla la connessione internet e riprova.",
        "en": "Hunter unreachable: check your internet connection and try again.",
    },
    "settings.anti_waste_title": {"it": "Anti-spreco crediti", "en": "Credit-saving rules"},
    "settings.anti_waste_1": {"it": "Nessuna chiamata automatica.", "en": "No automatic calls."},
    "settings.anti_waste_2": {"it": "Filtro <code>seniority=executive</code> — solo decision maker.", "en": "<code>seniority=executive</code> filter — decision makers only."},
    "settings.anti_waste_3": {"it": "Domain search cachato {days} giorni — stesso dominio = 1 sola chiamata.", "en": "Domain search cached {days} days — same domain = 1 call only."},
    "settings.anti_waste_4": {"it": "Email finder usa 1 credito anche se non trova: usa solo nomi sicuri.", "en": "Email finder spends 1 credit even on a miss: use it only on confident names."},
    "settings.privacy_title": {"it": "Privacy & sicurezza", "en": "Privacy & security"},
    "settings.privacy_1": {"it": "Tutti i dati sono in locale (<code>data/crm.db</code>).", "en": "All data stays local (<code>data/crm.db</code>)."},
    "settings.privacy_2": {"it": "Le query di ricerca AI passano dal CLI Claude Code (il tuo account Anthropic).", "en": "AI research queries go through the Claude Code CLI (your Anthropic account)."},
    "settings.privacy_3": {"it": "Hunter.io riceve solo il dominio aziendale.", "en": "Hunter.io only receives the company domain."},
    "settings.privacy_4": {"it": "Avatar e loghi generati in locale (SVG): nessun dato inviato a servizi terzi.", "en": "Avatars and logos generated locally (SVG): nothing sent to third-party services."},
    "settings.shortcuts_title": {"it": "Shortcut", "en": "Shortcuts"},
    "settings.shortcut_search": {"it": "Focus ricerca", "en": "Focus search"},
    "settings.shortcut_new": {"it": "Nuovo prospect", "en": "New prospect"},
    "settings.shortcut_research": {"it": "Nuova ricerca AI", "en": "New AI research"},
    "settings.env_title": {"it": "Override via env", "en": "Env overrides"},
    "settings.diag_title": {"it": "Diagnostica", "en": "Diagnostics"},
    "settings.diag_claude": {"it": "Test CLI Claude", "en": "Test Claude CLI"},
    "settings.diag_codex": {"it": "Test CLI Codex", "en": "Test Codex CLI"},
    "settings.diag_hunter": {"it": "Test Hunter", "en": "Test Hunter"},

    # --- cadenze di ricontatto ---
    "cadence.title": {"it": "Ricontatto", "en": "Follow-up"},
    "cadence.last_contact": {"it": "Ultimo contatto", "en": "Last contact"},
    "cadence.next_contact": {"it": "Prossimo contatto", "en": "Next contact"},
    "cadence.cadence_days": {"it": "Cadenza (giorni)", "en": "Cadence (days)"},
    "cadence.cadence_hint": {"it": "Es. 30 = ricontattare ogni 30 giorni dopo ogni contatto registrato.", "en": "E.g. 30 = follow up every 30 days after each logged contact."},
    "cadence.saved": {"it": "Cadenza di ricontatto salvata.", "en": "Follow-up cadence saved."},
    "cadence.contacted_today": {"it": "Contattato oggi", "en": "Contacted today"},
    "cadence.contacted_ok": {"it": "Contatto registrato.", "en": "Contact logged."},
    "cadence.contacted_log": {"it": "Contatto registrato (coda ricontatti)", "en": "Contact logged (follow-up queue)"},
    "cadence.never": {"it": "mai", "en": "never"},
    "cadence.queue_title": {"it": "Da ricontattare", "en": "To follow up"},
    "cadence.queue_empty": {"it": "Nessuno da ricontattare. Imposta una data di prossimo contatto sulle schede prospect.", "en": "No one to follow up. Set a next-contact date on prospect profiles."},
    "cadence.overdue": {"it": "in ritardo", "en": "overdue"},
    "cadence.save": {"it": "Salva", "en": "Save"},

    # --- cestino (soft-delete) ---
    "trash.title": {"it": "Cestino", "en": "Trash"},
    "trash.moved": {"it": "Prospect spostato nel cestino. Puoi ripristinarlo dal Cestino.", "en": "Prospect moved to trash. You can restore it from Trash."},
    "trash.restored": {"it": "Prospect ripristinato.", "en": "Prospect restored."},
    "trash.purged": {"it": "Prospect eliminato definitivamente.", "en": "Prospect permanently deleted."},
    "trash.in_trash_hint": {"it": "Questo prospect è nel cestino: ripristinalo per aprire la scheda.", "en": "This prospect is in the trash: restore it to open the profile."},
    "trash.empty": {"it": "Il cestino è vuoto.", "en": "Trash is empty."},
    "trash.restore": {"it": "Ripristina", "en": "Restore"},
    "trash.purge": {"it": "Elimina per sempre", "en": "Delete forever"},
    "trash.purge_confirm": {"it": "Eliminazione DEFINITIVA: cancella anche donazioni, attività e tutto lo storico. Non si può annullare.", "en": "PERMANENT deletion: also removes gifts, activities and all history. Cannot be undone."},
    "trash.deleted_on": {"it": "Eliminato il", "en": "Deleted on"},
    "trash.gifts_warn": {"it": "donazioni registrate", "en": "recorded gifts"},
    "trash.subtitle": {"it": "I prospect eliminati restano qui finché non li ripristini o li elimini per sempre.", "en": "Deleted prospects stay here until you restore them or delete them forever."},

    # --- campagne ---
    "camp.title": {"it": "Campagne", "en": "Campaigns"},
    "camp.subtitle": {"it": "Appelli e campagne con obiettivo: ogni donazione collegata risponde a “quale campagna ha reso di più?”", "en": "Appeals and campaigns with a goal: each linked gift answers “which campaign performed best?”"},
    "camp.new": {"it": "Nuova campagna", "en": "New campaign"},
    "camp.name": {"it": "Nome", "en": "Name"},
    "camp.name_required": {"it": "Il nome della campagna è obbligatorio.", "en": "Campaign name is required."},
    "camp.description": {"it": "Descrizione", "en": "Description"},
    "camp.start": {"it": "Inizio", "en": "Start"},
    "camp.end": {"it": "Fine", "en": "End"},
    "camp.target": {"it": "Obiettivo €", "en": "Target €"},
    "camp.created": {"it": "Campagna creata.", "en": "Campaign created."},
    "camp.deleted": {"it": "Campagna eliminata (le donazioni restano, senza campagna).", "en": "Campaign deleted (gifts remain, unlinked)."},
    "camp.delete_confirm": {"it": "Eliminare la campagna? Le donazioni collegate NON vengono cancellate.", "en": "Delete this campaign? Linked gifts will NOT be removed."},
    "camp.raised": {"it": "Raccolto", "en": "Raised"},
    "camp.promised": {"it": "Promesso", "en": "Promised"},
    "camp.donors": {"it": "donatori", "en": "donors"},
    "camp.gifts": {"it": "donazioni", "en": "gifts"},
    "camp.status_active": {"it": "Attiva", "en": "Active"},
    "camp.status_closed": {"it": "Chiusa", "en": "Closed"},
    "camp.close": {"it": "Chiudi", "en": "Close"},
    "camp.reopen": {"it": "Riapri", "en": "Reopen"},
    "camp.empty": {"it": "Nessuna campagna ancora. Creane una e collega le donazioni dal profilo prospect.", "en": "No campaigns yet. Create one and link gifts from prospect profiles."},
    "camp.none_select": {"it": "— nessuna campagna —", "en": "— no campaign —"},
    "nav.campaigns": {"it": "Campagne", "en": "Campaigns"},
    "nav.trash": {"it": "Cestino", "en": "Trash"},

    # --- gift compliance Italia ---
    "gift.deductible": {"it": "Erogazione liberale (deducibile)", "en": "Tax-deductible gift"},
    "gift.deductible_short": {"it": "Deducibile", "en": "Deductible"},
    "gift.receipt_sent": {"it": "Ricevuta emessa", "en": "Receipt issued"},
    "gift.receipt_missing": {"it": "Ricevuta da emettere", "en": "Receipt pending"},
    "gift.mark_receipt": {"it": "Segna ricevuta emessa", "en": "Mark receipt issued"},

    # --- polish grafico v1 ---
    "pdetail.red_flags_show": {"it": "dettagli", "en": "details"},
    "pdetail.red_flags_hide": {"it": "nascondi", "en": "hide"},
    "dash.kpi_no_forecast_hint": {"it": "Imposta gli ask sui prospect per vedere il forecast →", "en": "Set asks on prospects to see the forecast →"},
    "goals.no_forecast_hint": {"it": "Nessun ask in pipeline: impostali sui prospect qualificati →", "en": "No asks in pipeline: set them on qualified prospects →"},
    "camp.empty_step1": {"it": "Crea la campagna (es. “5x1000 2026”) con un obiettivo", "en": "Create the campaign (e.g. “Year-end appeal”) with a target"},
    "camp.empty_step2": {"it": "Registra le donazioni dal profilo prospect scegliendo la campagna", "en": "Log gifts from the prospect profile choosing the campaign"},
    "camp.empty_step3": {"it": "Qui vedi raccolto, promesso e donatori per ogni campagna", "en": "Here you'll see raised, promised and donors per campaign"},
    "goals.empty_step1": {"it": "Definisci l'obiettivo dell'anno (o della campagna)", "en": "Define the goal for the year (or campaign)"},
    "goals.empty_step2": {"it": "Registra donazioni e imposta gli ask sui prospect", "en": "Log gifts and set asks on prospects"},
    "goals.empty_step3": {"it": "La barra ti dice quanto manca al target", "en": "The bar shows how far you are from target"},

    # --- network: pannello laterale (redesign v1) ---
    "netg.panel_hint": {"it": "Clicca un nodo per dettagli e percorsi di accesso. Doppio click: apri la scheda.", "en": "Click a node for details and access paths. Double-click: open the profile."},
    "netg.top_connectors": {"it": "Top connettori", "en": "Top connectors"},
    "netg.top_connectors_desc": {"it": "Chi apre più porte nel tuo network.", "en": "Who opens the most doors in your network."},
    "netg.links_count": {"it": "collegamenti", "en": "links"},
    "netg.open_profile": {"it": "Apri scheda", "en": "Open profile"},
    "netg.compose_email": {"it": "Scrivi email", "en": "Write email"},
    "netg.doors": {"it": "Porte d'accesso", "en": "Access doors"},
    "netg.doors_desc": {"it": "Collegamenti diretti nel tuo CRM.", "en": "Direct links in your CRM."},
    "netg.doors_none": {"it": "Nessun collegamento diretto nel CRM.", "en": "No direct links in the CRM yet."},
    "netg.path_title": {"it": "Come arrivarci", "en": "How to get there"},
    "netg.path_none": {"it": "Nessun percorso da una relazione calda: serve un'introduzione esterna.", "en": "No path from a warm relationship yet: you'll need an outside introduction."},
    "netg.path_self": {"it": "Relazione già avviata: contattalo direttamente.", "en": "Relationship already warm: reach out directly."},
    "netg.entity_panel_hint": {"it": "Entità citata nelle ricerche — non ancora una scheda nel CRM. Creala per arricchire il grafo.", "en": "Entity mentioned in research — not a CRM profile yet. Create one to enrich the graph."},
    "netg.entity_create": {"it": "Crea scheda", "en": "Create profile"},
    "netg.you_know": {"it": "tu conosci", "en": "you know"},
    "netg.capacity": {"it": "Capacità", "en": "Capacity"},
    "netg.propensity": {"it": "Propensione", "en": "Propensity"},
    "netg.ask_lbl": {"it": "Ask", "en": "Ask"},

    # --- banner motore AI mancante ---
    "claude.missing_banner": {
        "it": "Il motore AI non è disponibile: il CLI “claude” (Claude Code) non risulta installato. Le funzioni di ricerca e scrittura AI non funzioneranno.",
        "en": "The AI engine is unavailable: the “claude” CLI (Claude Code) is not installed. AI research and writing features won't work.",
    },
    "codex.missing_banner": {
        "it": "Il motore AI non è disponibile: il CLI “codex” (OpenAI) non risulta installato. Le funzioni di ricerca e scrittura AI non funzioneranno. Puoi cambiare motore in Settings.",
        "en": "The AI engine is unavailable: the “codex” CLI (OpenAI) is not installed. AI research and writing features won't work. You can switch engine in Settings.",
    },
    "claude.missing_link": {"it": "Guida all'installazione", "en": "Install guide"},
}

# Catalogo generato per-schermata (translations_auto.py): unito qui se presente.
try:
    from translations_auto import EXTRA as _EXTRA
    CAT.update(_EXTRA)
except Exception:
    pass
