"""Contenuti della Guida in-app (it/en).

Struttura dati pura, renderizzata da templates/guide.html.
I campi 'a' (risposta) e 'intro' possono contenere HTML minimale
(<b>, <kbd>, <code>, <a>): sono contenuti nostri, renderizzati con |safe.
"""

GUIDE = [
    # ================================================================
    {
        "id": "start",
        "icon": "rocket",
        "title": {"it": "Primi passi", "en": "Getting started"},
        "intro": {
            "it": "Forager è un CRM per fundraiser che gira interamente sul tuo computer: i dati restano in locale, l'AI ti aiuta nella ricerca prospect e nella comunicazione.",
            "en": "Forager is a CRM for fundraisers that runs entirely on your computer: data stays local, AI helps with prospect research and communication.",
        },
        "blocks": [
            {
                "q": {"it": "Cosa serve per usare Forager", "en": "What you need to run Forager"},
                "a": {
                    "it": "Forager funziona out-of-the-box per anagrafica, pipeline, donazioni e task. Le funzioni <b>AI</b> (ricerca, email, chat) richiedono <b>Claude Code CLI</b> installato e autenticato sul computer: se manca vedi un banner giallo in alto. <b>Hunter.io</b> è opzionale e serve solo per trovare indirizzi email.",
                    "en": "Forager works out-of-the-box for records, pipeline, gifts and tasks. <b>AI</b> features (research, email, chat) require <b>Claude Code CLI</b> installed and authenticated on your computer: a yellow banner appears at the top if it's missing. <b>Hunter.io</b> is optional and only needed to find email addresses.",
                },
            },
            {
                "q": {"it": "Avviare e gestire l'app", "en": "Starting and managing the app"},
                "a": {
                    "it": "Dal terminale, nella cartella di Forager: <code>./forager start</code> avvia il server e apre il browser (su Windows: <code>forager.bat</code>). Altri comandi utili: <code>./forager init</code> (primo setup), <code>./forager doctor</code> (diagnostica), <code>./forager backup</code> e <code>./forager restore</code>, <code>./forager update</code>.",
                    "en": "From the terminal, in the Forager folder: <code>./forager start</code> starts the server and opens the browser (on Windows: <code>forager.bat</code>). Other useful commands: <code>./forager init</code> (first setup), <code>./forager doctor</code> (diagnostics), <code>./forager backup</code> and <code>./forager restore</code>, <code>./forager update</code>.",
                },
            },
            {
                "q": {"it": "Compila il profilo organizzazione", "en": "Fill in your organization profile"},
                "a": {
                    "it": "Vai in <b>Organizzazione</b> e inserisci nome, forma giuridica, missione, progetti e tono di voce. L'AI usa questo profilo per personalizzare email, ricerche e suggerimenti: più è completo, migliori sono i risultati. Finché manca il nome vedi un pallino ambra in sidebar.",
                    "en": "Go to <b>Organization</b> and enter name, legal form, mission, projects and tone of voice. The AI uses this profile to personalize emails, research and suggestions: the more complete it is, the better the results. An amber dot shows in the sidebar until the name is set.",
                },
            },
            {
                "q": {"it": "Cambiare lingua", "en": "Changing language"},
                "a": {
                    "it": "L'interfaccia è disponibile in italiano e inglese: cambia lingua dal fondo della sidebar (IT / EN) o dal menu account in alto a destra.",
                    "en": "The interface is available in Italian and English: switch language at the bottom of the sidebar (IT / EN) or from the account menu in the top right.",
                },
            },
        ],
        "tip": {
            "it": "Inizia con 3–5 prospect reali: fai una ricerca AI su ciascuno, imposta lo stage e una cadenza di contatto. In 15 minuti hai una pipeline funzionante.",
            "en": "Start with 3–5 real prospects: run AI research on each, set the stage and a contact cadence. In 15 minutes you'll have a working pipeline.",
        },
    },
    # ================================================================
    {
        "id": "concepts",
        "icon": "book-open",
        "title": {"it": "Concetti chiave", "en": "Key concepts"},
        "intro": {
            "it": "Quattro idee bastano per orientarsi: prospect, stage, ask e attività.",
            "en": "Four ideas are enough to find your way around: prospects, stages, asks and activities.",
        },
        "blocks": [
            {
                "q": {"it": "Prospect e tipi", "en": "Prospects and types"},
                "a": {
                    "it": "Un <b>prospect</b> è un potenziale donatore. Tre tipi: <b>Major donor</b> (persona fisica), <b>Corporate</b> (azienda), <b>Fondazione</b> (ente erogatore). Il tipo cambia le sezioni della scheda e il taglio della ricerca AI. I segmenti in sidebar filtrano la lista per tipo.",
                    "en": "A <b>prospect</b> is a potential donor. Three types: <b>Major donor</b> (individual), <b>Corporate</b> (company), <b>Foundation</b> (grantmaker). The type changes the record sections and the angle of AI research. Sidebar segments filter the list by type.",
                },
            },
            {
                "q": {"it": "La pipeline a stage", "en": "The stage pipeline"},
                "a": {
                    "it": "Ogni prospect attraversa la pipeline classica del major giving: <b>Identificato</b> (l'hai trovato) → <b>Qualificato</b> (ha capacità e affinità verificate) → <b>Cultivation</b> (stai costruendo la relazione) → <b>Sollecitato</b> (hai fatto la richiesta) → <b>Steward</b> (ha donato, curi la relazione). <b>Declinato</b> = ha detto no: esce dal forecast ma resta in archivio.",
                    "en": "Each prospect moves through the classic major giving pipeline: <b>Identified</b> (you found them) → <b>Qualified</b> (verified capacity and affinity) → <b>Cultivation</b> (building the relationship) → <b>Solicited</b> (you made the ask) → <b>Stewardship</b> (they gave, you nurture the relationship). <b>Declined</b> = they said no: removed from forecast but kept on file.",
                },
            },
            {
                "q": {"it": "Ask e score", "en": "Ask and score"},
                "a": {
                    "it": "L'<b>ask</b> è l'importo che intendi chiedere: lo usi nel forecast. Puoi farti suggerire un importo dall'AI (<b>Suggerisci ask</b> nella scheda) sulla base di capacità e storia filantropica, e salvarlo con un clic. Lo <b>score</b> nella scheda stima quanto il prospect è promettente: ricalcolalo dopo aggiornamenti importanti.",
                    "en": "The <b>ask</b> is the amount you plan to request: it feeds the forecast. The AI can suggest an amount (<b>Suggest ask</b> on the record) based on capacity and giving history, saved with one click. The <b>score</b> on the record estimates how promising the prospect is: recalculate it after major updates.",
                },
            },
            {
                "q": {"it": "Attività", "en": "Activities"},
                "a": {
                    "it": "Ogni interazione — chiamata, email, incontro, nota, task — si registra come <b>attività</b> sulla scheda e finisce nella timeline e nel feed globale (<b>Attività</b> in sidebar). È la memoria della relazione: l'AI la legge quando scrive email o risponde in chat.",
                    "en": "Every interaction — call, email, meeting, note, task — is logged as an <b>activity</b> on the record and shows in the timeline and the global feed (<b>Activity</b> in the sidebar). It's the memory of the relationship: the AI reads it when drafting emails or answering in chat.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "prospects",
        "icon": "users",
        "title": {"it": "Gestire i prospect", "en": "Managing prospects"},
        "intro": {
            "it": "Tre modi per creare prospect, una lista filtrabile all'istante e una scheda dettaglio che raccoglie tutto.",
            "en": "Three ways to create prospects, an instantly filterable list and a detail record that gathers everything.",
        },
        "blocks": [
            {
                "q": {"it": "Creare un prospect", "en": "Creating a prospect"},
                "a": {
                    "it": "Tre strade: <b>a mano</b> (Tutti i prospect → Nuovo), <b>con l'AI</b> (Prospect Research: scrivi il nome e l'AI compila la scheda cercando sul web), <b>in blocco</b> (Importa da CSV). Per la ricerca AI bastano nome e qualche indizio di contesto (città, azienda) per evitare omonimi.",
                    "en": "Three ways: <b>manually</b> (All prospects → New), <b>with AI</b> (Prospect Research: type the name and the AI fills the record by searching the web), <b>in bulk</b> (CSV import). For AI research, the name plus a bit of context (city, company) helps avoid namesakes.",
                },
            },
            {
                "q": {"it": "Lista, filtri e azioni in blocco", "en": "List, filters and bulk actions"},
                "a": {
                    "it": "La lista filtra all'istante per tipo, stage e tag; la ricerca in alto (tasto <kbd>/</kbd>) cerca su tutta la base. Seleziona più righe con le checkbox per le <b>azioni bulk</b>: cambiare stage, assegnare tag o campagna, eliminare. Su mobile la lista diventa card.",
                    "en": "The list filters instantly by type, stage and tag; the top search (<kbd>/</kbd> key) searches the whole database. Select multiple rows with checkboxes for <b>bulk actions</b>: change stage, assign tags or campaign, delete. On mobile the list becomes cards.",
                },
            },
            {
                "q": {"it": "La scheda dettaglio", "en": "The detail record"},
                "a": {
                    "it": "La scheda raccoglie tutto: sintesi AI, dati di ricerca con fonti, donazioni, attività, contatti, affiliazioni e connessioni. La sub-nav in alto salta alle sezioni. <b>Modifica</b> apre un pannello laterale senza perdere il contesto. Da qui parti per ogni azione: componi email, chat, briefing, sequenza, network, PDF.",
                    "en": "The record gathers everything: AI summary, research data with sources, gifts, activities, contacts, affiliations and connections. The sub-nav at the top jumps between sections. <b>Edit</b> opens a side panel without losing context. Every action starts here: compose email, chat, briefing, sequence, network, PDF.",
                },
            },
            {
                "q": {"it": "Cestino", "en": "Trash"},
                "a": {
                    "it": "Eliminare un prospect lo sposta nel <b>Cestino</b>, non lo cancella: da lì puoi <b>ripristinarlo</b> o eliminarlo definitivamente. Utile contro i clic sbagliati.",
                    "en": "Deleting a prospect moves it to the <b>Trash</b>, it doesn't erase it: from there you can <b>restore</b> it or delete it permanently. A safety net against wrong clicks.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "research",
        "icon": "scan-search",
        "title": {"it": "Prospect Research con l'AI", "en": "AI prospect research"},
        "intro": {
            "it": "Il cuore di Forager: l'AI cerca sul web e costruisce il profilo del prospect — bio, capacità, filantropia, relazioni — con le fonti citate.",
            "en": "The heart of Forager: the AI searches the web and builds the prospect profile — bio, capacity, philanthropy, relationships — with cited sources.",
        },
        "blocks": [
            {
                "q": {"it": "Avviare una ricerca", "en": "Running research"},
                "a": {
                    "it": "Da <b>Prospect Research</b> scrivi nome e contesto, scegli il tipo e avvia. La ricerca gira <b>in background</b>: puoi continuare a lavorare e tornare quando è pronta (la scheda mostra lo stato del job). Il risultato compila bio, stima di capacità, storia filantropica, affiliazioni, connessioni e fonti.",
                    "en": "From <b>Prospect Research</b> type name and context, pick the type and start. Research runs <b>in the background</b>: keep working and come back when it's ready (the record shows job status). The result fills in bio, capacity estimate, giving history, affiliations, connections and sources.",
                },
            },
            {
                "q": {"it": "Aggiornare e rifare", "en": "Updating and redoing"},
                "a": {
                    "it": "<b>Aggiorna ricerca</b> integra le novità mantenendo ciò che c'è; <b>Refresh forzato</b> ricostruisce la scheda da zero (usalo se la ricerca è partita male, es. omonimo). <b>Deep-dive</b> approfondisce una singola sezione — ad esempio solo la filantropia — con una ricerca mirata, più rapida ed economica di una ricerca completa.",
                    "en": "<b>Update research</b> merges new findings while keeping what's there; <b>Force refresh</b> rebuilds the record from scratch (use it if research went wrong, e.g. a namesake). <b>Deep-dive</b> digs into a single section — say, philanthropy only — with a targeted search, faster and cheaper than full research.",
                },
            },
            {
                "q": {"it": "Verifica fonti e grounding", "en": "Source verification and grounding"},
                "a": {
                    "it": "Due controlli anti-allucinazione: <b>Verifica link</b> controlla che le fonti citate esistano e siano raggiungibili; <b>Verifica contenuti</b> (grounding) rilegge le fonti e controlla che <i>supportino davvero</i> le affermazioni della scheda, segnalando quelle non confermate. Usali prima di basare un ask su un dato.",
                    "en": "Two anti-hallucination checks: <b>Verify links</b> checks that cited sources exist and are reachable; <b>Verify content</b> (grounding) re-reads the sources and checks they <i>actually support</i> the record's claims, flagging unconfirmed ones. Run them before basing an ask on a data point.",
                },
            },
            {
                "q": {"it": "News e segnali", "en": "News and signals"},
                "a": {
                    "it": "<b>Cerca news</b> trova notizie recenti sul prospect e le salva sulla scheda, evidenziando i <b>segnali</b> utili al fundraising (vendita di un'azienda, donazione pubblica, nuovo incarico). Ottimo da lanciare prima di un incontro.",
                    "en": "<b>Search news</b> finds recent news about the prospect and saves it on the record, highlighting <b>signals</b> relevant to fundraising (company sale, public donation, new role). Great to run before a meeting.",
                },
            },
        ],
        "tip": {
            "it": "L'AI può sbagliare, soprattutto con gli omonimi. Tratta la scheda come una bozza da verificare: controlla le fonti, correggi a mano dove serve — l'AI userà i dati corretti da lì in poi.",
            "en": "AI can be wrong, especially with namesakes. Treat the record as a draft to verify: check sources, fix things manually where needed — the AI will use the corrected data from then on.",
        },
    },
    # ================================================================
    {
        "id": "pipeline",
        "icon": "kanban",
        "title": {"it": "Pipeline e dashboard", "en": "Pipeline and dashboard"},
        "intro": {
            "it": "La dashboard è il centro operativo: pipeline per stage, contatti in ritardo e prossime azioni.",
            "en": "The dashboard is your operations center: pipeline by stage, overdue contacts and next actions.",
        },
        "blocks": [
            {
                "q": {"it": "Muovere i prospect tra gli stage", "en": "Moving prospects between stages"},
                "a": {
                    "it": "Cambia stage dalla scheda del prospect (selettore in alto) o con le azioni bulk dalla lista. La dashboard mostra la pipeline come colonne cliccabili con conteggi e valore: ogni colonna porta alla lista filtrata per quello stage.",
                    "en": "Change stage from the prospect record (selector at the top) or via bulk actions from the list. The dashboard shows the pipeline as clickable columns with counts and value: each column opens the list filtered by that stage.",
                },
            },
            {
                "q": {"it": "Cosa guardare ogni mattina", "en": "What to check every morning"},
                "a": {
                    "it": "Tre blocchi della dashboard guidano la giornata: <b>contatti in ritardo</b> (cadenze scadute), <b>task in scadenza</b> e <b>ultime attività</b>. Lavorali dall'alto: è il modo più rapido per non far raffreddare le relazioni.",
                    "en": "Three dashboard blocks drive your day: <b>overdue contacts</b> (lapsed cadences), <b>due tasks</b> and <b>recent activity</b>. Work them top-down: it's the fastest way to keep relationships warm.",
                },
            },
            {
                "q": {"it": "Quando segnare \"Declinato\"", "en": "When to mark \"Declined\""},
                "a": {
                    "it": "Se un prospect dice no, segna lo stage <b>Declinato</b> invece di eliminarlo: esce dal forecast ma conserva storia e contatti. Un no oggi può diventare un sì tra due anni.",
                    "en": "If a prospect says no, set the stage to <b>Declined</b> instead of deleting: they leave the forecast but keep history and contacts. A no today can become a yes in two years.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "gifts",
        "icon": "hand-coins",
        "title": {"it": "Donazioni e stewardship", "en": "Gifts and stewardship"},
        "intro": {
            "it": "Il registro delle donazioni reali: quello che trasforma un CRM di ricerca in un CRM di raccolta.",
            "en": "The registry of actual gifts: what turns a research CRM into a fundraising CRM.",
        },
        "blocks": [
            {
                "q": {"it": "Registrare una donazione", "en": "Recording a gift"},
                "a": {
                    "it": "Dalla scheda del prospect → <b>Registra donazione</b>: importo, data, campagna di provenienza e se è <b>deducibile</b>. Le donazioni alimentano l'avanzamento dei goal e le statistiche di campagna.",
                    "en": "From the prospect record → <b>Record gift</b>: amount, date, source campaign and whether it's <b>tax-deductible</b>. Gifts feed goal progress and campaign statistics.",
                },
            },
            {
                "q": {"it": "Ringraziamento e ricevuta", "en": "Thank-you and receipt"},
                "a": {
                    "it": "Su ogni donazione puoi segnare <b>ringraziato</b> e <b>ricevuta inviata</b>: Forager evidenzia le donazioni senza ricevuta, così non perdi gli adempimenti (e il donatore non perde la deduzione).",
                    "en": "On each gift you can mark <b>thanked</b> and <b>receipt sent</b>: Forager highlights gifts missing a receipt, so you never miss the follow-through (and the donor never misses the deduction).",
                },
            },
            {
                "q": {"it": "Storico ed export", "en": "History and export"},
                "a": {
                    "it": "La scheda mostra lo storico completo delle donazioni del prospect. Tutte le donazioni si esportano in <b>gifts.csv</b> (menu Esporta) per contabilità o analisi esterne.",
                    "en": "The record shows the prospect's full giving history. All gifts export to <b>gifts.csv</b> (Export menu) for accounting or external analysis.",
                },
            },
        ],
        "tip": {
            "it": "Regola d'oro: ringrazia entro 48 ore. Filtra le donazioni recenti senza ringraziamento e fanne la prima attività della giornata.",
            "en": "Golden rule: thank within 48 hours. Filter recent gifts not yet thanked and make them the first activity of your day.",
        },
    },
    # ================================================================
    {
        "id": "compose",
        "icon": "mail",
        "title": {"it": "Email con l'AI", "en": "AI email writing"},
        "intro": {
            "it": "L'AI scrive bozze su misura usando la ricerca del prospect, lo storico della relazione e il profilo della tua organizzazione.",
            "en": "The AI drafts tailored emails using the prospect's research, the relationship history and your organization profile.",
        },
        "blocks": [
            {
                "q": {"it": "Comporre un'email", "en": "Composing an email"},
                "a": {
                    "it": "Dalla scheda → <b>Componi</b>: scegli obiettivo (primo contatto, follow-up, richiesta, ringraziamento…), tono e lunghezza. Il testo arriva <b>in streaming</b> e la bozza si <b>salva da sola</b> mentre scrivi. Puoi partire anche da un template salvato.",
                    "en": "From the record → <b>Compose</b>: pick a goal (first contact, follow-up, ask, thank-you…), tone and length. Text streams in and the draft <b>auto-saves</b> as you write. You can also start from a saved template.",
                },
            },
            {
                "q": {"it": "Rifinire con l'AI", "en": "Refining with AI"},
                "a": {
                    "it": "Nell'editor: seleziona un passaggio e chiedi all'AI di <b>riscriverlo</b> (più breve, più caldo, più formale); fatti proporre <b>oggetti</b> alternativi; usa <b>continua</b> per farle completare il testo da dove sei arrivato.",
                    "en": "In the editor: select a passage and ask the AI to <b>rewrite it</b> (shorter, warmer, more formal); get alternative <b>subject lines</b>; use <b>continue</b> to have it pick up where you left off.",
                },
            },
            {
                "q": {"it": "Bozze e invio", "en": "Drafts and sending"},
                "a": {
                    "it": "Forager non invia email: copi il testo nel tuo client e poi clicchi <b>Segna inviata</b>. Questo registra l'attività sulla scheda e aggiorna la data di ultimo contatto (azzera la cadenza). Le bozze restano nella scheda finché non le elimini.",
                    "en": "Forager doesn't send email: copy the text into your mail client, then click <b>Mark as sent</b>. This logs the activity on the record and updates the last-contact date (resets the cadence). Drafts stay on the record until you delete them.",
                },
            },
            {
                "q": {"it": "Template e snippet", "en": "Templates and snippets"},
                "a": {
                    "it": "<b>Template email</b>: schemi riusabili (struttura, placeholder) da cui far partire l'AI. <b>Snippet</b>: blocchi fissi — firma, IBAN, dati fiscali — da inserire al volo in qualsiasi bozza. Entrambi hanno una pagina dedicata in sidebar.",
                    "en": "<b>Email templates</b>: reusable blueprints (structure, placeholders) the AI can start from. <b>Snippets</b>: fixed blocks — signature, bank details, tax info — to drop into any draft. Both have a dedicated page in the sidebar.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "sequences",
        "icon": "list-ordered",
        "title": {"it": "Sequenze multi-email", "en": "Multi-email sequences"},
        "intro": {
            "it": "Una serie coordinata di email — ad esempio presentazione → approfondimento → invito — generata in un colpo solo.",
            "en": "A coordinated series of emails — e.g. introduction → deep-dive → invitation — generated in one go.",
        },
        "blocks": [
            {
                "q": {"it": "Creare una sequenza", "en": "Creating a sequence"},
                "a": {
                    "it": "Dalla scheda → <b>Sequenza</b>: descrivi l'obiettivo e i passi (quante email, a che distanza, con quale escalation). L'AI genera tutti gli step <b>in background</b>; li trovi pronti nella pagina della sequenza.",
                    "en": "From the record → <b>Sequence</b>: describe the goal and the steps (how many emails, how far apart, what escalation). The AI generates all steps <b>in the background</b>; you'll find them ready on the sequence page.",
                },
            },
            {
                "q": {"it": "Gestire gli step", "en": "Managing steps"},
                "a": {
                    "it": "Ogni step si <b>modifica</b> singolarmente (anche con l'aiuto dell'AI) e si <b>segna inviato</b> quando lo spedisci: l'invio viene tracciato come attività. Puoi eliminare l'intera sequenza se cambia la strategia.",
                    "en": "Each step can be <b>edited</b> individually (with AI help too) and <b>marked as sent</b> when you send it: each send is tracked as an activity. You can delete the whole sequence if strategy changes.",
                },
            },
        ],
        "tip": {
            "it": "Le sequenze rendono al meglio in cultivation: 3 tocchi in 4–6 settimane, ciascuno con un contenuto di valore, prima di arrivare alla richiesta.",
            "en": "Sequences shine in cultivation: 3 touches over 4–6 weeks, each with valuable content, before getting to the ask.",
        },
    },
    # ================================================================
    {
        "id": "chat",
        "icon": "message-square-text",
        "title": {"it": "Chat AI e «Chiedi ai dati»", "en": "AI chat and “Ask your data”"},
        "intro": {
            "it": "Due modi di interrogare Forager in linguaggio naturale: sul singolo prospect o su tutta la base dati.",
            "en": "Two ways to query Forager in natural language: about a single prospect or across the whole database.",
        },
        "blocks": [
            {
                "q": {"it": "Chat sul prospect", "en": "Prospect chat"},
                "a": {
                    "it": "Dalla scheda → <b>Chat AI</b>: una conversazione con un assistente che conosce ricerca, donazioni e attività di quel prospect. Usala per preparare un incontro, simulare obiezioni, ragionare sulla strategia. La chat può anche <b>eseguire azioni</b> quando gliele chiedi (es. «crea un task per venerdì», «aggiorna l'ask a 5.000€»). Puoi azzerare la conversazione quando vuoi.",
                    "en": "From the record → <b>AI Chat</b>: a conversation with an assistant that knows that prospect's research, gifts and activities. Use it to prep a meeting, rehearse objections, think through strategy. The chat can also <b>perform actions</b> when asked (e.g. “create a task for Friday”, “update the ask to €5,000”). You can clear the conversation anytime.",
                },
            },
            {
                "q": {"it": "Briefing pre-incontro", "en": "Pre-meeting briefing"},
                "a": {
                    "it": "<b>Briefing</b> genera una sintesi da una pagina — chi è, cosa sappiamo, di cosa parlare, cosa evitare — perfetta da rileggere cinque minuti prima dell'incontro o da stampare.",
                    "en": "<b>Briefing</b> generates a one-page summary — who they are, what we know, what to talk about, what to avoid — perfect to skim five minutes before the meeting or to print.",
                },
            },
            {
                "q": {"it": "Chiedi ai dati", "en": "Ask your data"},
                "a": {
                    "it": "<b>Chiedi ai dati</b> (in sidebar) risponde a domande su tutto il database: «chi non contatto da più di 3 mesi?», «quanto ho raccolto quest'anno dalle fondazioni?», «quali corporate hanno un ask sopra i 10k?». Risponde in streaming usando i tuoi dati reali, non inventati.",
                    "en": "<b>Ask your data</b> (in the sidebar) answers questions across the whole database: “who haven't I contacted in 3+ months?”, “how much did I raise from foundations this year?”, “which corporates have an ask above 10k?”. It streams answers using your real data, not made-up numbers.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "tasks",
        "icon": "check-square",
        "title": {"it": "Task e cadenze", "en": "Tasks and cadences"},
        "intro": {
            "it": "Il sistema che ti impedisce di dimenticare le persone: promemoria puntuali e ritmi di contatto.",
            "en": "The system that keeps you from forgetting people: timely reminders and contact rhythms.",
        },
        "blocks": [
            {
                "q": {"it": "Task", "en": "Tasks"},
                "a": {
                    "it": "I task si creano dalla pagina <b>Tasks</b>, dalla scheda prospect o chiedendolo alla chat AI. Hanno scadenza e si spuntano con un clic; il numero dei task aperti è sempre visibile in sidebar.",
                    "en": "Tasks are created from the <b>Tasks</b> page, from a prospect record or by asking the AI chat. They have due dates and are checked off with one click; the open-task count is always visible in the sidebar.",
                },
            },
            {
                "q": {"it": "Cadenze di contatto", "en": "Contact cadences"},
                "a": {
                    "it": "Sulla scheda imposti <b>ogni quanti giorni</b> vuoi sentire quel prospect (es. 30 per un major in cultivation). Forager calcola il prossimo contatto; chi è in ritardo emerge in dashboard. Il bottone <b>Contattato oggi</b> (o «Segna inviata» su un'email) azzera il timer.",
                    "en": "On the record you set <b>how often</b> you want to touch base with that prospect (e.g. every 30 days for a major donor in cultivation). Forager computes the next contact; overdue ones surface on the dashboard. The <b>Contacted today</b> button (or “Mark as sent” on an email) resets the timer.",
                },
            },
            {
                "q": {"it": "Esporta in calendario (.ics)", "en": "Export to calendar (.ics)"},
                "a": {
                    "it": "Dalla scheda scarichi un file <b>.ics</b> con le scadenze del prospect (prossimo contatto, task) da importare in Google Calendar, Apple Calendar o Outlook.",
                    "en": "From the record you can download an <b>.ics</b> file with the prospect's deadlines (next contact, tasks) to import into Google Calendar, Apple Calendar or Outlook.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "goals",
        "icon": "target",
        "title": {"it": "Goals, forecast e campagne", "en": "Goals, forecast and campaigns"},
        "intro": {
            "it": "Quanto vuoi raccogliere, quanto stai raccogliendo davvero e quanto promette la pipeline.",
            "en": "How much you want to raise, how much you're actually raising, and what the pipeline promises.",
        },
        "blocks": [
            {
                "q": {"it": "Goal di raccolta", "en": "Fundraising goals"},
                "a": {
                    "it": "In <b>Goals & forecast</b> crei un obiettivo con importo e periodo (es. «200.000€ nel 2026»). L'avanzamento si aggiorna da solo con le donazioni registrate. I goal conclusi si <b>archiviano</b> e restano consultabili.",
                    "en": "In <b>Goals & forecast</b> you create a target with amount and period (e.g. “€200,000 in 2026”). Progress updates automatically from recorded gifts. Finished goals can be <b>archived</b> and stay available.",
                },
            },
            {
                "q": {"it": "Come si calcola il forecast", "en": "How the forecast works"},
                "a": {
                    "it": "Il forecast pesa l'<b>ask</b> di ogni prospect per la probabilità del suo <b>stage</b> (più avanti nella pipeline = più probabile). Ti dice quanto la pipeline attuale può realisticamente fruttare — e quindi se devi identificare nuovi prospect o spingere quelli che hai.",
                    "en": "The forecast weights each prospect's <b>ask</b> by the probability of their <b>stage</b> (further along the pipeline = more likely). It tells you what the current pipeline can realistically yield — and whether you need to identify new prospects or push existing ones.",
                },
            },
            {
                "q": {"it": "Campagne", "en": "Campaigns"},
                "a": {
                    "it": "Le <b>campagne</b> raggruppano iniziative («Natale 2026», «Capitale per la nuova sede»): assegni prospect e donazioni a una campagna e ne misuri i risultati. Le campagne si aprono e chiudono cambiando stato.",
                    "en": "<b>Campaigns</b> group initiatives (“Christmas 2026”, “Capital for the new HQ”): assign prospects and gifts to a campaign and measure its results. Campaigns open and close by changing status.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "network",
        "icon": "share-2",
        "title": {"it": "Mappa del network e duplicati", "en": "Network map and duplicates"},
        "intro": {
            "it": "Le relazioni sono il capitale del fundraiser: Forager le disegna come un grafo navigabile.",
            "en": "Relationships are a fundraiser's capital: Forager draws them as a navigable graph.",
        },
        "blocks": [
            {
                "q": {"it": "Grafo globale", "en": "Global graph"},
                "a": {
                    "it": "<b>Network mappa</b> mostra prospect, persone e organizzazioni collegate emerse dalle ricerche AI: board condivisi, aziende in comune, relazioni personali. Usalo per trovare <b>chi può presentarti a chi</b>: il percorso più corto verso un nuovo prospect passa quasi sempre da qualcuno che conosci già.",
                    "en": "<b>Network map</b> shows prospects, people and organizations linked through AI research: shared boards, common companies, personal ties. Use it to find <b>who can introduce you to whom</b>: the shortest path to a new prospect almost always goes through someone you already know.",
                },
            },
            {
                "q": {"it": "Network del singolo prospect", "en": "Single prospect network"},
                "a": {
                    "it": "Dalla scheda → <b>Network</b>: la vista locale delle connessioni di quel prospect, utile per preparare un incontro o scegliere il canale di avvicinamento.",
                    "en": "From the record → <b>Network</b>: the local view of that prospect's connections, useful for meeting prep or choosing the warmest path in.",
                },
            },
            {
                "q": {"it": "Ricollega entità", "en": "Relink entities"},
                "a": {
                    "it": "Se il grafo sembra frammentato (stessa persona citata in modi diversi), <b>Ricollega</b> fa rileggere le schede all'AI e ricostruisce i collegamenti tra entità.",
                    "en": "If the graph looks fragmented (the same person mentioned in different ways), <b>Relink</b> has the AI re-read the records and rebuild links between entities.",
                },
            },
            {
                "q": {"it": "Duplicati", "en": "Duplicates"},
                "a": {
                    "it": "<b>Duplicati</b> rileva schede probabilmente riferite alla stessa persona/ente (nomi simili, stessa email) e le <b>fonde</b>: scegli campo per campo cosa tenere; attività e donazioni si uniscono senza perdite.",
                    "en": "<b>Duplicates</b> detects records likely referring to the same person/org (similar names, same email) and <b>merges</b> them: you choose field by field what to keep; activities and gifts merge without loss.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "enrich",
        "icon": "at-sign",
        "title": {"it": "Trovare email (Hunter.io)", "en": "Finding emails (Hunter.io)"},
        "intro": {
            "it": "Integrazione opzionale per trovare indirizzi email verificati di decision maker e contatti.",
            "en": "Optional integration to find verified email addresses of decision makers and contacts.",
        },
        "blocks": [
            {
                "q": {"it": "Attivare Hunter", "en": "Enabling Hunter"},
                "a": {
                    "it": "Registrati gratis su <b>hunter.io</b> (25 ricerche/mese nel piano free), copia la API key e mettila nel file <code>.env</code> come <code>HUNTER_API_KEY</code>. Riavvia Forager: i bottoni «Trova email» si attivano.",
                    "en": "Sign up free at <b>hunter.io</b> (25 searches/month on the free plan), copy the API key and put it in the <code>.env</code> file as <code>HUNTER_API_KEY</code>. Restart Forager: the “Find email” buttons light up.",
                },
            },
            {
                "q": {"it": "Email aziendali e decision maker", "en": "Company emails and decision makers"},
                "a": {
                    "it": "Su corporate e fondazioni, <b>Trova email</b> interroga il dominio dell'organizzazione e restituisce i contatti con ruolo e seniority (configurabile in <code>.env</code>: default <i>executive</i>). I risultati si salvano tra i contatti della scheda.",
                    "en": "On corporates and foundations, <b>Find email</b> queries the organization's domain and returns contacts with role and seniority (configurable in <code>.env</code>: default <i>executive</i>). Results are saved among the record's contacts.",
                },
            },
            {
                "q": {"it": "Contatti personali", "en": "Personal contacts"},
                "a": {
                    "it": "Sui major donor, <b>Trova contatti personali</b> cerca l'email della persona a partire da nome e azienda nota. La quota Hunter rimasta è visibile nella pagina <b>Usage</b>; i risultati sono in cache 30 giorni per non sprecare ricerche.",
                    "en": "On major donors, <b>Find personal contacts</b> looks up the person's email from their name and known company. Your remaining Hunter quota shows on the <b>Usage</b> page; results are cached for 30 days to avoid wasting searches.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "data",
        "icon": "database",
        "title": {"it": "Import, export, tag e backup", "en": "Import, export, tags and backups"},
        "intro": {
            "it": "I tuoi dati sono tuoi: entrano da CSV, escono in CSV/JSON/PDF, e vivono in un database locale con backup automatici.",
            "en": "Your data is yours: it comes in via CSV, goes out as CSV/JSON/PDF, and lives in a local database with automatic backups.",
        },
        "blocks": [
            {
                "q": {"it": "Import da CSV", "en": "CSV import"},
                "a": {
                    "it": "<b>Importa</b> accetta CSV da altri CRM o fogli di calcolo: carichi il file, <b>mappi le colonne</b> sui campi di Forager (nome, tipo, email, stage, tag…), vedi l'anteprima e confermi. Ideale per migrare una lista esistente in pochi minuti.",
                    "en": "<b>Import</b> accepts CSVs from other CRMs or spreadsheets: upload the file, <b>map the columns</b> to Forager fields (name, type, email, stage, tags…), preview and confirm. Ideal for migrating an existing list in minutes.",
                },
            },
            {
                "q": {"it": "Export", "en": "Export"},
                "a": {
                    "it": "Dal menu <b>Esporta</b>: <code>prospects.csv</code> (anagrafica completa), <code>gifts.csv</code> (donazioni), <code>full.json</code> (tutto il database, per migrare o archiviare). Ogni scheda si esporta anche in <b>PDF</b> o in versione <b>stampabile</b> — utile per board meeting.",
                    "en": "From the <b>Export</b> menu: <code>prospects.csv</code> (full records), <code>gifts.csv</code> (gifts), <code>full.json</code> (the whole database, for migration or archiving). Each record also exports as <b>PDF</b> or a <b>print</b> version — handy for board meetings.",
                },
            },
            {
                "q": {"it": "Tag", "en": "Tags"},
                "a": {
                    "it": "I <b>tag</b> sono etichette libere con colore («board member», «alumni», «evento 2026») da combinare con tipi e stage. Si creano nella pagina Tag, si assegnano dalla scheda o in bulk, e diventano filtri nella lista.",
                    "en": "<b>Tags</b> are free-form colored labels (“board member”, “alumni”, “event 2026”) to combine with types and stages. Create them on the Tags page, assign from the record or in bulk, and use them as list filters.",
                },
            },
            {
                "q": {"it": "Backup e ripristino", "en": "Backup and restore"},
                "a": {
                    "it": "Forager fa <b>backup automatici</b> in background nella cartella <code>backups/</code>. Da <b>Impostazioni</b> puoi lanciare un backup manuale o <b>scaricare</b> il database. Per ripristinare: <code>./forager restore</code> dal terminale. Per spostarti su un altro computer: backup → copia → restore.",
                    "en": "Forager makes <b>automatic backups</b> in the background into the <code>backups/</code> folder. From <b>Settings</b> you can run a manual backup or <b>download</b> the database. To restore: <code>./forager restore</code> from the terminal. To move to another computer: backup → copy → restore.",
                },
            },
            {
                "q": {"it": "Privacy e GDPR", "en": "Privacy and GDPR"},
                "a": {
                    "it": "Tutto vive in un database <b>SQLite locale</b> (cartella <code>data/</code>): niente cloud, niente account. Le funzioni AI inviano a Claude solo i dati del prospect necessari alla richiesta. I font sono self-hosted (nessuna chiamata a Google Fonts). Sei tu il titolare del trattamento: usa export e cestino per esercitare i diritti degli interessati.",
                    "en": "Everything lives in a <b>local SQLite</b> database (the <code>data/</code> folder): no cloud, no accounts. AI features send Claude only the prospect data needed for the request. Fonts are self-hosted (no calls to Google Fonts). You are the data controller: use export and trash to honor data-subject requests.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "shortcuts",
        "icon": "command",
        "title": {"it": "Scorciatoie e produttività", "en": "Shortcuts and productivity"},
        "intro": {
            "it": "Pochi tasti per muoverti ovunque senza mouse.",
            "en": "A few keys to move anywhere without the mouse.",
        },
        "blocks": [
            {
                "q": {"it": "Tastiera", "en": "Keyboard"},
                "a": {
                    "it": "<kbd>/</kbd> porta il cursore nella ricerca. <kbd>⌘K</kbd> (o <kbd>Ctrl K</kbd>) apre la <b>command palette</b>: cerca prospect per nome o salta a qualsiasi pagina; <kbd>↑</kbd><kbd>↓</kbd> per muoverti, <kbd>↵</kbd> per aprire, <kbd>esc</kbd> per chiudere.",
                    "en": "<kbd>/</kbd> focuses the search. <kbd>⌘K</kbd> (or <kbd>Ctrl K</kbd>) opens the <b>command palette</b>: search prospects by name or jump to any page; <kbd>↑</kbd><kbd>↓</kbd> to move, <kbd>↵</kbd> to open, <kbd>esc</kbd> to close.",
                },
            },
            {
                "q": {"it": "Ricerca globale", "en": "Global search"},
                "a": {
                    "it": "La barra in alto cerca su tutti i prospect (nome, organizzazione, email). La stessa ricerca è disponibile nella palette, con anteprima di avatar e stage.",
                    "en": "The top bar searches all prospects (name, organization, email). The same search is available in the palette, with avatar and stage preview.",
                },
            },
            {
                "q": {"it": "Feed attività", "en": "Activity feed"},
                "a": {
                    "it": "<b>Attività</b> in sidebar è il diario di bordo: tutto quello che hai fatto (e che l'AI ha fatto per te) in ordine cronologico, cliccabile verso le schede.",
                    "en": "<b>Activity</b> in the sidebar is the logbook: everything you did (and the AI did for you) in chronological order, clickable through to the records.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "costs",
        "icon": "gauge",
        "title": {"it": "Costi e Usage", "en": "Costs and Usage"},
        "intro": {
            "it": "Ogni chiamata AI è tracciata: sai sempre quanto stai spendendo e per cosa.",
            "en": "Every AI call is tracked: you always know how much you're spending and on what.",
        },
        "blocks": [
            {
                "q": {"it": "La pagina Usage", "en": "The Usage page"},
                "a": {
                    "it": "<b>Usage</b> mostra numero di chiamate, token, costo stimato e durata — totali, ultimi 7/30 giorni, per <b>tipo di operazione</b> (ricerca, compose, chat…) e per <b>prospect</b>. Vedi anche gli errori e la quota Hunter residua.",
                    "en": "<b>Usage</b> shows call counts, tokens, estimated cost and duration — totals, last 7/30 days, by <b>operation type</b> (research, compose, chat…) and by <b>prospect</b>. You also see errors and the remaining Hunter quota.",
                },
            },
            {
                "q": {"it": "Tenere bassi i costi", "en": "Keeping costs down"},
                "a": {
                    "it": "Le ricerche complete sono l'operazione più costosa: preferisci il <b>deep-dive</b> mirato quando ti serve solo una sezione, e l'<b>aggiornamento</b> al refresh forzato. Chat e editing email costano poco. Controlla Usage una volta a settimana per capire dove va la spesa.",
                    "en": "Full research is the most expensive operation: prefer a targeted <b>deep-dive</b> when you only need one section, and an <b>update</b> over a force refresh. Chat and email editing are cheap. Check Usage weekly to see where spend goes.",
                },
            },
        ],
        "tip": None,
    },
    # ================================================================
    {
        "id": "faq",
        "icon": "help-circle",
        "title": {"it": "Problemi comuni (FAQ)", "en": "Troubleshooting (FAQ)"},
        "intro": {
            "it": "Le situazioni più frequenti e come uscirne.",
            "en": "The most frequent situations and how to get out of them.",
        },
        "blocks": [
            {
                "q": {"it": "Banner «Claude non configurato»", "en": "“Claude not configured” banner"},
                "a": {
                    "it": "Le funzioni AI non trovano la CLI di Claude. Installa <b>Claude Code</b>, assicurati che il comando <code>claude</code> sia nel PATH (oppure indica il percorso completo in <code>.env</code> → <code>CLAUDE_BIN</code>) e riavvia. <code>./forager doctor</code> verifica tutta la configurazione.",
                    "en": "AI features can't find the Claude CLI. Install <b>Claude Code</b>, make sure the <code>claude</code> command is on your PATH (or set the full path in <code>.env</code> → <code>CLAUDE_BIN</code>) and restart. <code>./forager doctor</code> checks the whole configuration.",
                },
            },
            {
                "q": {"it": "Una ricerca resta «in corso»", "en": "Research stuck “in progress”"},
                "a": {
                    "it": "Le ricerche girano in background e le più profonde richiedono qualche minuto: la scheda si aggiorna da sola. Se l'app è stata chiusa a metà job, al riavvio Forager <b>riprende automaticamente</b> i job interrotti. Se il job è andato in errore lo vedi segnalato sulla scheda (e in Usage).",
                    "en": "Research runs in the background and deep ones take a few minutes: the record refreshes by itself. If the app was closed mid-job, on restart Forager <b>automatically resumes</b> interrupted jobs. If a job failed, it's flagged on the record (and in Usage).",
                },
            },
            {
                "q": {"it": "La porta è occupata", "en": "Port already in use"},
                "a": {
                    "it": "Su Mac la porta 5000 è spesso presa da AirPlay. Imposta <code>FORAGER_PORT=5001</code> (o altra porta libera) nel file <code>.env</code> e riavvia.",
                    "en": "On Mac, port 5000 is often taken by AirPlay. Set <code>FORAGER_PORT=5001</code> (or any free port) in the <code>.env</code> file and restart.",
                },
            },
            {
                "q": {"it": "Dove sono i miei dati?", "en": "Where is my data?"},
                "a": {
                    "it": "Nel database SQLite dentro la cartella <code>data/</code> dell'installazione; i backup in <code>backups/</code>. Per spostarti su un altro computer: <code>./forager backup</code>, copia il file, poi <code>./forager restore</code> sul nuovo computer.",
                    "en": "In the SQLite database inside the installation's <code>data/</code> folder; backups in <code>backups/</code>. To move to another computer: <code>./forager backup</code>, copy the file, then <code>./forager restore</code> on the new machine.",
                },
            },
            {
                "q": {"it": "L'AI ha scritto cose sbagliate", "en": "The AI wrote something wrong"},
                "a": {
                    "it": "Succede, soprattutto con omonimi o persone poco presenti online. Usa <b>Verifica link</b> e <b>Verifica contenuti</b> per scovare le affermazioni non supportate, correggi la scheda a mano (Modifica) o rifai la ricerca con più contesto («Mario Rossi, CEO di Acme, Milano»). Da quel momento l'AI lavora sui dati corretti.",
                    "en": "It happens, especially with namesakes or people with little online presence. Use <b>Verify links</b> and <b>Verify content</b> to catch unsupported claims, fix the record manually (Edit) or redo the research with more context (“Mario Rossi, CEO of Acme, Milan”). From then on the AI works with the corrected data.",
                },
            },
            {
                "q": {"it": "Ho eliminato un prospect per errore", "en": "I deleted a prospect by mistake"},
                "a": {
                    "it": "Vai nel <b>Cestino</b> (in fondo alla sidebar) e clicca <b>Ripristina</b>: la scheda torna intatta con attività e donazioni.",
                    "en": "Go to the <b>Trash</b> (bottom of the sidebar) and click <b>Restore</b>: the record comes back intact with activities and gifts.",
                },
            },
        ],
        "tip": None,
    },
]
