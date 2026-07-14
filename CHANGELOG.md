# Changelog

## v1.0.0 — 2026-06-09

Prima release pubblica.

### Added
- Cadenze di ricontatto: ultimo/prossimo contatto per prospect + coda "Da ricontattare" in dashboard
- Campagne come entità: tabella dedicata, raccolto per campagna, collegamento donazioni
- Cestino: i prospect eliminati finiscono nel cestino (ripristino o eliminazione definitiva)
- Compliance Italia sui gift: flag deducibilità, ricevuta emessa
- Export completo: gifts.csv e dump JSON di tutti i dati
- Protezione CSRF su tutte le richieste POST
- SECRET_KEY generata automaticamente al primo avvio (persistita in `data/.secret_key`)
- Asset frontend in locale (`static/vendor/`): l'app funziona offline
- Banner in dashboard se il CLI `claude` non è installato
- Smoke test (`tests/`) + GitHub Actions CI
- Numero di versione (`config.__version__`) mostrato nel footer

### Changed
- Docker: bind solo su 127.0.0.1, container non-root
- Route AI sincrone protette da lock per-prospect (no doppia esecuzione)
- Import CSV con limiti di dimensione/righe; export CSV con escape anti formula-injection
- Streaming SSE: heartbeat periodico + terminazione affidabile del processo claude
- Messaggi di errore Hunter tradotti in indicazioni operative

## v0.2

### Added
- First-run wizard `/welcome` per onboarding rapido
- CLI `forager` con sub-commands: start, init, doctor, backup, restore, update
- Installer one-liner `install.sh` per macOS/Linux
- Launcher Windows `forager.bat`
- Dockerfile + docker-compose.yml
- `.env.example` con tutte le variabili
- LICENSE MIT
- CONTRIBUTING.md

### Changed
- `config.py` ora legge da env vars / .env (niente più hardcoded)
- Hunter.io API key opzionale (con messaggio chiaro se mancante)
- README completamente riscritto per audience non-tech

## v0.1 — base CRM
- CRM SQLite con pipeline 6 stage
- ricerca AI research via Claude Code CLI subprocess
- Hunter.io integration (decision maker email)
- Tasks, tags, goals, activity feed, network mapping
- AI compose email contestualizzato
- Bulk operations + CSV import
- UI light theme (Tailwind + Lucide)
