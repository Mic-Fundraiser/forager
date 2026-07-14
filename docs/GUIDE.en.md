# Forager — Complete Guide

The same guide available in-app (**Guide** menu), browsable on GitHub.

🇮🇹 [Versione italiana](GUIDA.md) · ← [Back to README](../README.md)

## Table of contents

1. [Getting started](#getting-started)
2. [Key concepts](#key-concepts)
3. [Managing prospects](#managing-prospects)
4. [AI prospect research](#ai-prospect-research)
5. [Pipeline and dashboard](#pipeline-and-dashboard)
6. [Gifts and stewardship](#gifts-and-stewardship)
7. [AI email writing](#ai-email-writing)
8. [Multi-email sequences](#multi-email-sequences)
9. [AI chat and “Ask your data”](#ai-chat-and-ask-your-data)
10. [Tasks and cadences](#tasks-and-cadences)
11. [Goals, forecast and campaigns](#goals-forecast-and-campaigns)
12. [Network map and duplicates](#network-map-and-duplicates)
13. [Finding emails (Hunter.io)](#finding-emails-hunterio)
14. [Import, export, tags and backups](#import-export-tags-and-backups)
15. [Shortcuts and productivity](#shortcuts-and-productivity)
16. [Costs and Usage](#costs-and-usage)
17. [Troubleshooting (FAQ)](#troubleshooting-faq)

## Getting started

Forager is a CRM for fundraisers that runs entirely on your computer: data stays local, AI helps with prospect research and communication.

### What you need to run Forager

Forager works out-of-the-box for records, pipeline, gifts and tasks. **AI** features (research, email, chat) require **Claude Code CLI** installed and authenticated on your computer: a yellow banner appears at the top if it's missing. **Hunter.io** is optional and only needed to find email addresses.

### Starting and managing the app

From the terminal, in the Forager folder: `./forager start` starts the server and opens the browser (on Windows: `forager.bat`). Other useful commands: `./forager init` (first setup), `./forager doctor` (diagnostics), `./forager backup` and `./forager restore`, `./forager update`.

### Fill in your organization profile

Go to **Organization** and enter name, legal form, mission, projects and tone of voice. The AI uses this profile to personalize emails, research and suggestions: the more complete it is, the better the results. An amber dot shows in the sidebar until the name is set.

### Changing language

The interface is available in Italian and English: switch language at the bottom of the sidebar (IT / EN) or from the account menu in the top right.

> 💡 **Tip** — Start with 3–5 real prospects: run AI research on each, set the stage and a contact cadence. In 15 minutes you'll have a working pipeline.

## Key concepts

Four ideas are enough to find your way around: prospects, stages, asks and activities.

### Prospects and types

A **prospect** is a potential donor. Three types: **Major donor** (individual), **Corporate** (company), **Foundation** (grantmaker). The type changes the record sections and the angle of AI research. Sidebar segments filter the list by type.

### The stage pipeline

Each prospect moves through the classic major giving pipeline: **Identified** (you found them) → **Qualified** (verified capacity and affinity) → **Cultivation** (building the relationship) → **Solicited** (you made the ask) → **Stewardship** (they gave, you nurture the relationship). **Declined** = they said no: removed from forecast but kept on file.

### Ask and score

The **ask** is the amount you plan to request: it feeds the forecast. The AI can suggest an amount (**Suggest ask** on the record) based on capacity and giving history, saved with one click. The **score** on the record estimates how promising the prospect is: recalculate it after major updates.

### Activities

Every interaction — call, email, meeting, note, task — is logged as an **activity** on the record and shows in the timeline and the global feed (**Activity** in the sidebar). It's the memory of the relationship: the AI reads it when drafting emails or answering in chat.

## Managing prospects

Three ways to create prospects, an instantly filterable list and a detail record that gathers everything.

### Creating a prospect

Three ways: **manually** (All prospects → New), **with AI** (Prospect Research: type the name and the AI fills the record by searching the web), **in bulk** (CSV import). For AI research, the name plus a bit of context (city, company) helps avoid namesakes.

### List, filters and bulk actions

The list filters instantly by type, stage and tag; the top search (<kbd>/</kbd> key) searches the whole database. Select multiple rows with checkboxes for **bulk actions**: change stage, assign tags or campaign, delete. On mobile the list becomes cards.

### The detail record

The record gathers everything: AI summary, research data with sources, gifts, activities, contacts, affiliations and connections. The sub-nav at the top jumps between sections. **Edit** opens a side panel without losing context. Every action starts here: compose email, chat, briefing, sequence, network, PDF.

### Trash

Deleting a prospect moves it to the **Trash**, it doesn't erase it: from there you can **restore** it or delete it permanently. A safety net against wrong clicks.

## AI prospect research

The heart of Forager: the AI searches the web and builds the prospect profile — bio, capacity, philanthropy, relationships — with cited sources.

### Running research

From **Prospect Research** type name and context, pick the type and start. Research runs **in the background**: keep working and come back when it's ready (the record shows job status). The result fills in bio, capacity estimate, giving history, affiliations, connections and sources.

### Updating and redoing

**Update research** merges new findings while keeping what's there; **Force refresh** rebuilds the record from scratch (use it if research went wrong, e.g. a namesake). **Deep-dive** digs into a single section — say, philanthropy only — with a targeted search, faster and cheaper than full research.

### Source verification and grounding

Two anti-hallucination checks: **Verify links** checks that cited sources exist and are reachable; **Verify content** (grounding) re-reads the sources and checks they *actually support* the record's claims, flagging unconfirmed ones. Run them before basing an ask on a data point.

### News and signals

**Search news** finds recent news about the prospect and saves it on the record, highlighting **signals** relevant to fundraising (company sale, public donation, new role). Great to run before a meeting.

> 💡 **Tip** — AI can be wrong, especially with namesakes. Treat the record as a draft to verify: check sources, fix things manually where needed — the AI will use the corrected data from then on.

## Pipeline and dashboard

The dashboard is your operations center: pipeline by stage, overdue contacts and next actions.

### Moving prospects between stages

Change stage from the prospect record (selector at the top) or via bulk actions from the list. The dashboard shows the pipeline as clickable columns with counts and value: each column opens the list filtered by that stage.

### What to check every morning

Three dashboard blocks drive your day: **overdue contacts** (lapsed cadences), **due tasks** and **recent activity**. Work them top-down: it's the fastest way to keep relationships warm.

### When to mark "Declined"

If a prospect says no, set the stage to **Declined** instead of deleting: they leave the forecast but keep history and contacts. A no today can become a yes in two years.

## Gifts and stewardship

The registry of actual gifts: what turns a research CRM into a fundraising CRM.

### Recording a gift

From the prospect record → **Record gift**: amount, date, source campaign and whether it's **tax-deductible**. Gifts feed goal progress and campaign statistics.

### Thank-you and receipt

On each gift you can mark **thanked** and **receipt sent**: Forager highlights gifts missing a receipt, so you never miss the follow-through (and the donor never misses the deduction).

### History and export

The record shows the prospect's full giving history. All gifts export to **gifts.csv** (Export menu) for accounting or external analysis.

> 💡 **Tip** — Golden rule: thank within 48 hours. Filter recent gifts not yet thanked and make them the first activity of your day.

## AI email writing

The AI drafts tailored emails using the prospect's research, the relationship history and your organization profile.

### Composing an email

From the record → **Compose**: pick a goal (first contact, follow-up, ask, thank-you…), tone and length. Text streams in and the draft **auto-saves** as you write. You can also start from a saved template.

### Refining with AI

In the editor: select a passage and ask the AI to **rewrite it** (shorter, warmer, more formal); get alternative **subject lines**; use **continue** to have it pick up where you left off.

### Drafts and sending

Forager doesn't send email: copy the text into your mail client, then click **Mark as sent**. This logs the activity on the record and updates the last-contact date (resets the cadence). Drafts stay on the record until you delete them.

### Templates and snippets

**Email templates**: reusable blueprints (structure, placeholders) the AI can start from. **Snippets**: fixed blocks — signature, bank details, tax info — to drop into any draft. Both have a dedicated page in the sidebar.

## Multi-email sequences

A coordinated series of emails — e.g. introduction → deep-dive → invitation — generated in one go.

### Creating a sequence

From the record → **Sequence**: describe the goal and the steps (how many emails, how far apart, what escalation). The AI generates all steps **in the background**; you'll find them ready on the sequence page.

### Managing steps

Each step can be **edited** individually (with AI help too) and **marked as sent** when you send it: each send is tracked as an activity. You can delete the whole sequence if strategy changes.

> 💡 **Tip** — Sequences shine in cultivation: 3 touches over 4–6 weeks, each with valuable content, before getting to the ask.

## AI chat and “Ask your data”

Two ways to query Forager in natural language: about a single prospect or across the whole database.

### Prospect chat

From the record → **AI Chat**: a conversation with an assistant that knows that prospect's research, gifts and activities. Use it to prep a meeting, rehearse objections, think through strategy. The chat can also **perform actions** when asked (e.g. “create a task for Friday”, “update the ask to €5,000”). You can clear the conversation anytime.

### Pre-meeting briefing

**Briefing** generates a one-page summary — who they are, what we know, what to talk about, what to avoid — perfect to skim five minutes before the meeting or to print.

### Ask your data

**Ask your data** (in the sidebar) answers questions across the whole database: “who haven't I contacted in 3+ months?”, “how much did I raise from foundations this year?”, “which corporates have an ask above 10k?”. It streams answers using your real data, not made-up numbers.

## Tasks and cadences

The system that keeps you from forgetting people: timely reminders and contact rhythms.

### Tasks

Tasks are created from the **Tasks** page, from a prospect record or by asking the AI chat. They have due dates and are checked off with one click; the open-task count is always visible in the sidebar.

### Contact cadences

On the record you set **how often** you want to touch base with that prospect (e.g. every 30 days for a major donor in cultivation). Forager computes the next contact; overdue ones surface on the dashboard. The **Contacted today** button (or “Mark as sent” on an email) resets the timer.

### Export to calendar (.ics)

From the record you can download an **.ics** file with the prospect's deadlines (next contact, tasks) to import into Google Calendar, Apple Calendar or Outlook.

## Goals, forecast and campaigns

How much you want to raise, how much you're actually raising, and what the pipeline promises.

### Fundraising goals

In **Goals & forecast** you create a target with amount and period (e.g. “€200,000 in 2026”). Progress updates automatically from recorded gifts. Finished goals can be **archived** and stay available.

### How the forecast works

The forecast weights each prospect's **ask** by the probability of their **stage** (further along the pipeline = more likely). It tells you what the current pipeline can realistically yield — and whether you need to identify new prospects or push existing ones.

### Campaigns

**Campaigns** group initiatives (“Christmas 2026”, “Capital for the new HQ”): assign prospects and gifts to a campaign and measure its results. Campaigns open and close by changing status.

## Network map and duplicates

Relationships are a fundraiser's capital: Forager draws them as a navigable graph.

### Global graph

**Network map** shows prospects, people and organizations linked through AI research: shared boards, common companies, personal ties. Use it to find **who can introduce you to whom**: the shortest path to a new prospect almost always goes through someone you already know.

### Single prospect network

From the record → **Network**: the local view of that prospect's connections, useful for meeting prep or choosing the warmest path in.

### Relink entities

If the graph looks fragmented (the same person mentioned in different ways), **Relink** has the AI re-read the records and rebuild links between entities.

### Duplicates

**Duplicates** detects records likely referring to the same person/org (similar names, same email) and **merges** them: you choose field by field what to keep; activities and gifts merge without loss.

## Finding emails (Hunter.io)

Optional integration to find verified email addresses of decision makers and contacts.

### Enabling Hunter

Sign up free at **hunter.io** (25 searches/month on the free plan), copy the API key and put it in the `.env` file as `HUNTER_API_KEY`. Restart Forager: the “Find email” buttons light up.

### Company emails and decision makers

On corporates and foundations, **Find email** queries the organization's domain and returns contacts with role and seniority (configurable in `.env`: default *executive*). Results are saved among the record's contacts.

### Personal contacts

On major donors, **Find personal contacts** looks up the person's email from their name and known company. Your remaining Hunter quota shows on the **Usage** page; results are cached for 30 days to avoid wasting searches.

## Import, export, tags and backups

Your data is yours: it comes in via CSV, goes out as CSV/JSON/PDF, and lives in a local database with automatic backups.

### CSV import

**Import** accepts CSVs from other CRMs or spreadsheets: upload the file, **map the columns** to Forager fields (name, type, email, stage, tags…), preview and confirm. Ideal for migrating an existing list in minutes.

### Export

From the **Export** menu: `prospects.csv` (full records), `gifts.csv` (gifts), `full.json` (the whole database, for migration or archiving). Each record also exports as **PDF** or a **print** version — handy for board meetings.

### Tags

**Tags** are free-form colored labels (“board member”, “alumni”, “event 2026”) to combine with types and stages. Create them on the Tags page, assign from the record or in bulk, and use them as list filters.

### Backup and restore

Forager makes **automatic backups** in the background into the `backups/` folder. From **Settings** you can run a manual backup or **download** the database. To restore: `./forager restore` from the terminal. To move to another computer: backup → copy → restore.

### Privacy and GDPR

Everything lives in a **local SQLite** database (the `data/` folder): no cloud, no accounts. AI features send Claude only the prospect data needed for the request. Fonts are self-hosted (no calls to Google Fonts). You are the data controller: use export and trash to honor data-subject requests.

## Shortcuts and productivity

A few keys to move anywhere without the mouse.

### Keyboard

<kbd>/</kbd> focuses the search. <kbd>⌘K</kbd> (or <kbd>Ctrl K</kbd>) opens the **command palette**: search prospects by name or jump to any page; <kbd>↑</kbd><kbd>↓</kbd> to move, <kbd>↵</kbd> to open, <kbd>esc</kbd> to close.

### Global search

The top bar searches all prospects (name, organization, email). The same search is available in the palette, with avatar and stage preview.

### Activity feed

**Activity** in the sidebar is the logbook: everything you did (and the AI did for you) in chronological order, clickable through to the records.

## Costs and Usage

Every AI call is tracked: you always know how much you're spending and on what.

### The Usage page

**Usage** shows call counts, tokens, estimated cost and duration — totals, last 7/30 days, by **operation type** (research, compose, chat…) and by **prospect**. You also see errors and the remaining Hunter quota.

### Keeping costs down

Full research is the most expensive operation: prefer a targeted **deep-dive** when you only need one section, and an **update** over a force refresh. Chat and email editing are cheap. Check Usage weekly to see where spend goes.

## Troubleshooting (FAQ)

The most frequent situations and how to get out of them.

### “Claude not configured” banner

AI features can't find the Claude CLI. Install **Claude Code**, make sure the `claude` command is on your PATH (or set the full path in `.env` → `CLAUDE_BIN`) and restart. `./forager doctor` checks the whole configuration.

### Research stuck “in progress”

Research runs in the background and deep ones take a few minutes: the record refreshes by itself. If the app was closed mid-job, on restart Forager **automatically resumes** interrupted jobs. If a job failed, it's flagged on the record (and in Usage).

### Port already in use

On Mac, port 5000 is often taken by AirPlay. Set `FORAGER_PORT=5001` (or any free port) in the `.env` file and restart.

### Where is my data?

In the SQLite database inside the installation's `data/` folder; backups in `backups/`. To move to another computer: `./forager backup`, copy the file, then `./forager restore` on the new machine.

### The AI wrote something wrong

It happens, especially with namesakes or people with little online presence. Use **Verify links** and **Verify content** to catch unsupported claims, fix the record manually (Edit) or redo the research with more context (“Mario Rossi, CEO of Acme, Milan”). From then on the AI works with the corrected data.

### I deleted a prospect by mistake

Go to the **Trash** (bottom of the sidebar) and click **Restore**: the record comes back intact with activities and gifts.

---

🇮🇹 [Versione italiana](GUIDA.md) · ← [Back to README](../README.md)
