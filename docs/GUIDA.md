# Guida completa a Forager

La stessa guida che trovi in-app (menu **Guida**), in versione consultabile su GitHub.

🇬🇧 [English version](GUIDE.en.md) · ← [Torna al README](../README.md)

## Indice

1. [Primi passi](#primi-passi)
2. [Concetti chiave](#concetti-chiave)
3. [Gestire i prospect](#gestire-i-prospect)
4. [Prospect Research con l'AI](#prospect-research-con-lai)
5. [Pipeline e dashboard](#pipeline-e-dashboard)
6. [Donazioni e stewardship](#donazioni-e-stewardship)
7. [Email con l'AI](#email-con-lai)
8. [Sequenze multi-email](#sequenze-multi-email)
9. [Chat AI e «Chiedi ai dati»](#chat-ai-e-chiedi-ai-dati)
10. [Task e cadenze](#task-e-cadenze)
11. [Goals, forecast e campagne](#goals-forecast-e-campagne)
12. [Mappa del network e duplicati](#mappa-del-network-e-duplicati)
13. [Trovare email (Hunter.io)](#trovare-email-hunterio)
14. [Import, export, tag e backup](#import-export-tag-e-backup)
15. [Scorciatoie e produttività](#scorciatoie-e-produttività)
16. [Costi e Usage](#costi-e-usage)
17. [Problemi comuni (FAQ)](#problemi-comuni-faq)

## Primi passi

Forager è un CRM per fundraiser che gira interamente sul tuo computer: i dati restano in locale, l'AI ti aiuta nella ricerca prospect e nella comunicazione.

### Cosa serve per usare Forager

Forager funziona out-of-the-box per anagrafica, pipeline, donazioni e task. Le funzioni **AI** (ricerca, email, chat) richiedono **Claude Code CLI** installato e autenticato sul computer: se manca vedi un banner giallo in alto. **Hunter.io** è opzionale e serve solo per trovare indirizzi email.

### Avviare e gestire l'app

Dal terminale, nella cartella di Forager: `./forager start` avvia il server e apre il browser (su Windows: `forager.bat`). Altri comandi utili: `./forager init` (primo setup), `./forager doctor` (diagnostica), `./forager backup` e `./forager restore`, `./forager update`.

### Compila il profilo organizzazione

Vai in **Organizzazione** e inserisci nome, forma giuridica, missione, progetti e tono di voce. L'AI usa questo profilo per personalizzare email, ricerche e suggerimenti: più è completo, migliori sono i risultati. Finché manca il nome vedi un pallino ambra in sidebar.

### Cambiare lingua

L'interfaccia è disponibile in italiano e inglese: cambia lingua dal fondo della sidebar (IT / EN) o dal menu account in alto a destra.

> 💡 **Suggerimento** — Inizia con 3–5 prospect reali: fai una ricerca AI su ciascuno, imposta lo stage e una cadenza di contatto. In 15 minuti hai una pipeline funzionante.

## Concetti chiave

Quattro idee bastano per orientarsi: prospect, stage, ask e attività.

### Prospect e tipi

Un **prospect** è un potenziale donatore. Tre tipi: **Major donor** (persona fisica), **Corporate** (azienda), **Fondazione** (ente erogatore). Il tipo cambia le sezioni della scheda e il taglio della ricerca AI. I segmenti in sidebar filtrano la lista per tipo.

### La pipeline a stage

Ogni prospect attraversa la pipeline classica del major giving: **Identificato** (l'hai trovato) → **Qualificato** (ha capacità e affinità verificate) → **Cultivation** (stai costruendo la relazione) → **Sollecitato** (hai fatto la richiesta) → **Steward** (ha donato, curi la relazione). **Declinato** = ha detto no: esce dal forecast ma resta in archivio.

### Ask e score

L'**ask** è l'importo che intendi chiedere: lo usi nel forecast. Puoi farti suggerire un importo dall'AI (**Suggerisci ask** nella scheda) sulla base di capacità e storia filantropica, e salvarlo con un clic. Lo **score** nella scheda stima quanto il prospect è promettente: ricalcolalo dopo aggiornamenti importanti.

### Attività

Ogni interazione — chiamata, email, incontro, nota, task — si registra come **attività** sulla scheda e finisce nella timeline e nel feed globale (**Attività** in sidebar). È la memoria della relazione: l'AI la legge quando scrive email o risponde in chat.

## Gestire i prospect

Tre modi per creare prospect, una lista filtrabile all'istante e una scheda dettaglio che raccoglie tutto.

### Creare un prospect

Tre strade: **a mano** (Tutti i prospect → Nuovo), **con l'AI** (Prospect Research: scrivi il nome e l'AI compila la scheda cercando sul web), **in blocco** (Importa da CSV). Per la ricerca AI bastano nome e qualche indizio di contesto (città, azienda) per evitare omonimi.

### Lista, filtri e azioni in blocco

La lista filtra all'istante per tipo, stage e tag; la ricerca in alto (tasto <kbd>/</kbd>) cerca su tutta la base. Seleziona più righe con le checkbox per le **azioni bulk**: cambiare stage, assegnare tag o campagna, eliminare. Su mobile la lista diventa card.

### La scheda dettaglio

La scheda raccoglie tutto: sintesi AI, dati di ricerca con fonti, donazioni, attività, contatti, affiliazioni e connessioni. La sub-nav in alto salta alle sezioni. **Modifica** apre un pannello laterale senza perdere il contesto. Da qui parti per ogni azione: componi email, chat, briefing, sequenza, network, PDF.

### Cestino

Eliminare un prospect lo sposta nel **Cestino**, non lo cancella: da lì puoi **ripristinarlo** o eliminarlo definitivamente. Utile contro i clic sbagliati.

## Prospect Research con l'AI

Il cuore di Forager: l'AI cerca sul web e costruisce il profilo del prospect — bio, capacità, filantropia, relazioni — con le fonti citate.

### Avviare una ricerca

Da **Prospect Research** scrivi nome e contesto, scegli il tipo e avvia. La ricerca gira **in background**: puoi continuare a lavorare e tornare quando è pronta (la scheda mostra lo stato del job). Il risultato compila bio, stima di capacità, storia filantropica, affiliazioni, connessioni e fonti.

### Aggiornare e rifare

**Aggiorna ricerca** integra le novità mantenendo ciò che c'è; **Refresh forzato** ricostruisce la scheda da zero (usalo se la ricerca è partita male, es. omonimo). **Deep-dive** approfondisce una singola sezione — ad esempio solo la filantropia — con una ricerca mirata, più rapida ed economica di una ricerca completa.

### Verifica fonti e grounding

Due controlli anti-allucinazione: **Verifica link** controlla che le fonti citate esistano e siano raggiungibili; **Verifica contenuti** (grounding) rilegge le fonti e controlla che *supportino davvero* le affermazioni della scheda, segnalando quelle non confermate. Usali prima di basare un ask su un dato.

### News e segnali

**Cerca news** trova notizie recenti sul prospect e le salva sulla scheda, evidenziando i **segnali** utili al fundraising (vendita di un'azienda, donazione pubblica, nuovo incarico). Ottimo da lanciare prima di un incontro.

> 💡 **Suggerimento** — L'AI può sbagliare, soprattutto con gli omonimi. Tratta la scheda come una bozza da verificare: controlla le fonti, correggi a mano dove serve — l'AI userà i dati corretti da lì in poi.

## Pipeline e dashboard

La dashboard è il centro operativo: pipeline per stage, contatti in ritardo e prossime azioni.

### Muovere i prospect tra gli stage

Cambia stage dalla scheda del prospect (selettore in alto) o con le azioni bulk dalla lista. La dashboard mostra la pipeline come colonne cliccabili con conteggi e valore: ogni colonna porta alla lista filtrata per quello stage.

### Cosa guardare ogni mattina

Tre blocchi della dashboard guidano la giornata: **contatti in ritardo** (cadenze scadute), **task in scadenza** e **ultime attività**. Lavorali dall'alto: è il modo più rapido per non far raffreddare le relazioni.

### Quando segnare "Declinato"

Se un prospect dice no, segna lo stage **Declinato** invece di eliminarlo: esce dal forecast ma conserva storia e contatti. Un no oggi può diventare un sì tra due anni.

## Donazioni e stewardship

Il registro delle donazioni reali: quello che trasforma un CRM di ricerca in un CRM di raccolta.

### Registrare una donazione

Dalla scheda del prospect → **Registra donazione**: importo, data, campagna di provenienza e se è **deducibile**. Le donazioni alimentano l'avanzamento dei goal e le statistiche di campagna.

### Ringraziamento e ricevuta

Su ogni donazione puoi segnare **ringraziato** e **ricevuta inviata**: Forager evidenzia le donazioni senza ricevuta, così non perdi gli adempimenti (e il donatore non perde la deduzione).

### Storico ed export

La scheda mostra lo storico completo delle donazioni del prospect. Tutte le donazioni si esportano in **gifts.csv** (menu Esporta) per contabilità o analisi esterne.

> 💡 **Suggerimento** — Regola d'oro: ringrazia entro 48 ore. Filtra le donazioni recenti senza ringraziamento e fanne la prima attività della giornata.

## Email con l'AI

L'AI scrive bozze su misura usando la ricerca del prospect, lo storico della relazione e il profilo della tua organizzazione.

### Comporre un'email

Dalla scheda → **Componi**: scegli obiettivo (primo contatto, follow-up, richiesta, ringraziamento…), tono e lunghezza. Il testo arriva **in streaming** e la bozza si **salva da sola** mentre scrivi. Puoi partire anche da un template salvato.

### Rifinire con l'AI

Nell'editor: seleziona un passaggio e chiedi all'AI di **riscriverlo** (più breve, più caldo, più formale); fatti proporre **oggetti** alternativi; usa **continua** per farle completare il testo da dove sei arrivato.

### Bozze e invio

Forager non invia email: copi il testo nel tuo client e poi clicchi **Segna inviata**. Questo registra l'attività sulla scheda e aggiorna la data di ultimo contatto (azzera la cadenza). Le bozze restano nella scheda finché non le elimini.

### Template e snippet

**Template email**: schemi riusabili (struttura, placeholder) da cui far partire l'AI. **Snippet**: blocchi fissi — firma, IBAN, dati fiscali — da inserire al volo in qualsiasi bozza. Entrambi hanno una pagina dedicata in sidebar.

## Sequenze multi-email

Una serie coordinata di email — ad esempio presentazione → approfondimento → invito — generata in un colpo solo.

### Creare una sequenza

Dalla scheda → **Sequenza**: descrivi l'obiettivo e i passi (quante email, a che distanza, con quale escalation). L'AI genera tutti gli step **in background**; li trovi pronti nella pagina della sequenza.

### Gestire gli step

Ogni step si **modifica** singolarmente (anche con l'aiuto dell'AI) e si **segna inviato** quando lo spedisci: l'invio viene tracciato come attività. Puoi eliminare l'intera sequenza se cambia la strategia.

> 💡 **Suggerimento** — Le sequenze rendono al meglio in cultivation: 3 tocchi in 4–6 settimane, ciascuno con un contenuto di valore, prima di arrivare alla richiesta.

## Chat AI e «Chiedi ai dati»

Due modi di interrogare Forager in linguaggio naturale: sul singolo prospect o su tutta la base dati.

### Chat sul prospect

Dalla scheda → **Chat AI**: una conversazione con un assistente che conosce ricerca, donazioni e attività di quel prospect. Usala per preparare un incontro, simulare obiezioni, ragionare sulla strategia. La chat può anche **eseguire azioni** quando gliele chiedi (es. «crea un task per venerdì», «aggiorna l'ask a 5.000€»). Puoi azzerare la conversazione quando vuoi.

### Briefing pre-incontro

**Briefing** genera una sintesi da una pagina — chi è, cosa sappiamo, di cosa parlare, cosa evitare — perfetta da rileggere cinque minuti prima dell'incontro o da stampare.

### Chiedi ai dati

**Chiedi ai dati** (in sidebar) risponde a domande su tutto il database: «chi non contatto da più di 3 mesi?», «quanto ho raccolto quest'anno dalle fondazioni?», «quali corporate hanno un ask sopra i 10k?». Risponde in streaming usando i tuoi dati reali, non inventati.

## Task e cadenze

Il sistema che ti impedisce di dimenticare le persone: promemoria puntuali e ritmi di contatto.

### Task

I task si creano dalla pagina **Tasks**, dalla scheda prospect o chiedendolo alla chat AI. Hanno scadenza e si spuntano con un clic; il numero dei task aperti è sempre visibile in sidebar.

### Cadenze di contatto

Sulla scheda imposti **ogni quanti giorni** vuoi sentire quel prospect (es. 30 per un major in cultivation). Forager calcola il prossimo contatto; chi è in ritardo emerge in dashboard. Il bottone **Contattato oggi** (o «Segna inviata» su un'email) azzera il timer.

### Esporta in calendario (.ics)

Dalla scheda scarichi un file **.ics** con le scadenze del prospect (prossimo contatto, task) da importare in Google Calendar, Apple Calendar o Outlook.

## Goals, forecast e campagne

Quanto vuoi raccogliere, quanto stai raccogliendo davvero e quanto promette la pipeline.

### Goal di raccolta

In **Goals & forecast** crei un obiettivo con importo e periodo (es. «200.000€ nel 2026»). L'avanzamento si aggiorna da solo con le donazioni registrate. I goal conclusi si **archiviano** e restano consultabili.

### Come si calcola il forecast

Il forecast pesa l'**ask** di ogni prospect per la probabilità del suo **stage** (più avanti nella pipeline = più probabile). Ti dice quanto la pipeline attuale può realisticamente fruttare — e quindi se devi identificare nuovi prospect o spingere quelli che hai.

### Campagne

Le **campagne** raggruppano iniziative («Natale 2026», «Capitale per la nuova sede»): assegni prospect e donazioni a una campagna e ne misuri i risultati. Le campagne si aprono e chiudono cambiando stato.

## Mappa del network e duplicati

Le relazioni sono il capitale del fundraiser: Forager le disegna come un grafo navigabile.

### Grafo globale

**Network mappa** mostra prospect, persone e organizzazioni collegate emerse dalle ricerche AI: board condivisi, aziende in comune, relazioni personali. Usalo per trovare **chi può presentarti a chi**: il percorso più corto verso un nuovo prospect passa quasi sempre da qualcuno che conosci già.

### Network del singolo prospect

Dalla scheda → **Network**: la vista locale delle connessioni di quel prospect, utile per preparare un incontro o scegliere il canale di avvicinamento.

### Ricollega entità

Se il grafo sembra frammentato (stessa persona citata in modi diversi), **Ricollega** fa rileggere le schede all'AI e ricostruisce i collegamenti tra entità.

### Duplicati

**Duplicati** rileva schede probabilmente riferite alla stessa persona/ente (nomi simili, stessa email) e le **fonde**: scegli campo per campo cosa tenere; attività e donazioni si uniscono senza perdite.

## Trovare email (Hunter.io)

Integrazione opzionale per trovare indirizzi email verificati di decision maker e contatti.

### Attivare Hunter

Registrati gratis su **hunter.io** (25 ricerche/mese nel piano free), copia la API key e mettila nel file `.env` come `HUNTER_API_KEY`. Riavvia Forager: i bottoni «Trova email» si attivano.

### Email aziendali e decision maker

Su corporate e fondazioni, **Trova email** interroga il dominio dell'organizzazione e restituisce i contatti con ruolo e seniority (configurabile in `.env`: default *executive*). I risultati si salvano tra i contatti della scheda.

### Contatti personali

Sui major donor, **Trova contatti personali** cerca l'email della persona a partire da nome e azienda nota. La quota Hunter rimasta è visibile nella pagina **Usage**; i risultati sono in cache 30 giorni per non sprecare ricerche.

## Import, export, tag e backup

I tuoi dati sono tuoi: entrano da CSV, escono in CSV/JSON/PDF, e vivono in un database locale con backup automatici.

### Import da CSV

**Importa** accetta CSV da altri CRM o fogli di calcolo: carichi il file, **mappi le colonne** sui campi di Forager (nome, tipo, email, stage, tag…), vedi l'anteprima e confermi. Ideale per migrare una lista esistente in pochi minuti.

### Export

Dal menu **Esporta**: `prospects.csv` (anagrafica completa), `gifts.csv` (donazioni), `full.json` (tutto il database, per migrare o archiviare). Ogni scheda si esporta anche in **PDF** o in versione **stampabile** — utile per board meeting.

### Tag

I **tag** sono etichette libere con colore («board member», «alumni», «evento 2026») da combinare con tipi e stage. Si creano nella pagina Tag, si assegnano dalla scheda o in bulk, e diventano filtri nella lista.

### Backup e ripristino

Forager fa **backup automatici** in background nella cartella `backups/`. Da **Impostazioni** puoi lanciare un backup manuale o **scaricare** il database. Per ripristinare: `./forager restore` dal terminale. Per spostarti su un altro computer: backup → copia → restore.

### Privacy e GDPR

Tutto vive in un database **SQLite locale** (cartella `data/`): niente cloud, niente account. Le funzioni AI inviano a Claude solo i dati del prospect necessari alla richiesta. I font sono self-hosted (nessuna chiamata a Google Fonts). Sei tu il titolare del trattamento: usa export e cestino per esercitare i diritti degli interessati.

## Scorciatoie e produttività

Pochi tasti per muoverti ovunque senza mouse.

### Tastiera

<kbd>/</kbd> porta il cursore nella ricerca. <kbd>⌘K</kbd> (o <kbd>Ctrl K</kbd>) apre la **command palette**: cerca prospect per nome o salta a qualsiasi pagina; <kbd>↑</kbd><kbd>↓</kbd> per muoverti, <kbd>↵</kbd> per aprire, <kbd>esc</kbd> per chiudere.

### Ricerca globale

La barra in alto cerca su tutti i prospect (nome, organizzazione, email). La stessa ricerca è disponibile nella palette, con anteprima di avatar e stage.

### Feed attività

**Attività** in sidebar è il diario di bordo: tutto quello che hai fatto (e che l'AI ha fatto per te) in ordine cronologico, cliccabile verso le schede.

## Costi e Usage

Ogni chiamata AI è tracciata: sai sempre quanto stai spendendo e per cosa.

### La pagina Usage

**Usage** mostra numero di chiamate, token, costo stimato e durata — totali, ultimi 7/30 giorni, per **tipo di operazione** (ricerca, compose, chat…) e per **prospect**. Vedi anche gli errori e la quota Hunter residua.

### Tenere bassi i costi

Le ricerche complete sono l'operazione più costosa: preferisci il **deep-dive** mirato quando ti serve solo una sezione, e l'**aggiornamento** al refresh forzato. Chat e editing email costano poco. Controlla Usage una volta a settimana per capire dove va la spesa.

## Problemi comuni (FAQ)

Le situazioni più frequenti e come uscirne.

### Banner «Claude non configurato»

Le funzioni AI non trovano la CLI di Claude. Installa **Claude Code**, assicurati che il comando `claude` sia nel PATH (oppure indica il percorso completo in `.env` → `CLAUDE_BIN`) e riavvia. `./forager doctor` verifica tutta la configurazione.

### Una ricerca resta «in corso»

Le ricerche girano in background e le più profonde richiedono qualche minuto: la scheda si aggiorna da sola. Se l'app è stata chiusa a metà job, al riavvio Forager **riprende automaticamente** i job interrotti. Se il job è andato in errore lo vedi segnalato sulla scheda (e in Usage).

### La porta è occupata

Su Mac la porta 5000 è spesso presa da AirPlay. Imposta `FORAGER_PORT=5001` (o altra porta libera) nel file `.env` e riavvia.

### Dove sono i miei dati?

Nel database SQLite dentro la cartella `data/` dell'installazione; i backup in `backups/`. Per spostarti su un altro computer: `./forager backup`, copia il file, poi `./forager restore` sul nuovo computer.

### L'AI ha scritto cose sbagliate

Succede, soprattutto con omonimi o persone poco presenti online. Usa **Verifica link** e **Verifica contenuti** per scovare le affermazioni non supportate, correggi la scheda a mano (Modifica) o rifai la ricerca con più contesto («Mario Rossi, CEO di Acme, Milano»). Da quel momento l'AI lavora sui dati corretti.

### Ho eliminato un prospect per errore

Vai nel **Cestino** (in fondo alla sidebar) e clicca **Ripristina**: la scheda torna intatta con attività e donazioni.

---

🇬🇧 [English version](GUIDE.en.md) · ← [Torna al README](../README.md)
