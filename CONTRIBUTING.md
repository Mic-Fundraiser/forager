# Contributing a Forager

Grazie per voler contribuire. Forager nasce per la community fundraising italiana ma vuole crescere oltre.

## Setup dev

```bash
git clone https://github.com/USERNAME/forager.git
cd forager
./forager init
./forager start
```

## Struttura

```
forager/
├── app.py             Flask routes
├── db.py              Schema SQLite + helpers
├── ai_engine.py       Wrapper claude CLI per ricerca AI + compose
├── hunter.py          Integrazione Hunter.io (email decision maker)
├── prompts.py         Template prompt per Claude (Prospect Research + email)
├── config.py          Config (legge .env)
├── forager            CLI launcher
├── templates/         Jinja2 templates
├── static/styles.css  Custom CSS (oltre Tailwind CDN)
├── data/crm.db        DB locale (gitignored)
└── backups/           Backup database (gitignored)
```

## Convenzioni

- **Python**: stile PEP 8, type hints dove utile
- **Frontend**: Tailwind utility-first, custom CSS solo per cose Tailwind non copre
- **DB migrations**: usa pattern `_add_col` in `db.py` per ALTER TABLE idempotenti
- **Prompt**: tutti in `prompts.py`, in italiano se il target è il fundraiser italiano
- **No build step**: tutto via CDN (Tailwind, Lucide, HTMX, Alpine)

## Cosa NON aggiungere

- ❌ Dipendenze JS pesanti (React, Vue, build pipelines)
- ❌ Database server (Postgres, MySQL) — SQLite basta e avanza per il caso d'uso
- ❌ Hard dependency su cloud o API a pagamento — tutto deve avere fallback locale
- ❌ Tracking, telemetria, analytics esterni
- ❌ Roba che obbliga l'utente a creare account terzi (oltre Claude e Hunter, opzionali)

## Aree dove serve aiuto

- 🧪 **Test automatici** (pytest)
- 🌐 **i18n** — sistema traduzioni e versioni EN/FR/ES
- 📱 **Mobile** — refinement touch
- 🔌 **Integrazioni**: Pipedrive, HubSpot, Salesforce NPSP, NationBuilder
- 📊 **Visualizzazioni**: charts pipeline, funnel conversion
- 🗃️ **Dataset open** per stress test (donor pubblici da bilanci)
- 📝 **Docs** screenshots, tutorial video
- 🐛 **Bug fix**

## Workflow PR

1. Fork
2. Branch: `git checkout -b feat/nome-feature`
3. Commit con messaggi chiari in italiano o inglese
4. PR verso `main` con descrizione e screenshot se UI

## Code of Conduct

Sii gentile. Forager è uno strumento per persone che fanno raccolta fondi per cause sociali —
manteniamo la community sullo stesso spirito.

## Licenza dei contributi

Contribuendo accetti che il tuo codice sia rilasciato sotto MIT.
