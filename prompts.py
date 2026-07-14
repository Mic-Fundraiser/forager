"""Prompt templates passed to claude CLI for ricerca AI research.
Org context viene iniettato dinamicamente da ai_engine.build_prompt()."""


def org_context_block(org: dict | None) -> str:
    """Costruisce il blocco di contesto organizzativo da prependere ai prompt ricerca AI.
    Solo i campi compilati vengono inclusi: l'utente può lasciare vuoto cosa non vuole esporre."""
    if not org or not org.get("name"):
        return ""

    lines = ["# CONTESTO DEL FUNDRAISER", ""]
    lines.append(f"Stai facendo ricerca prospect per conto di **{org['name']}**.")

    if org.get("legal_form"):
        lines.append(f"Forma giuridica: {org['legal_form']}.")
    if org.get("founding_year"):
        lines.append(f"Fondata nel {org['founding_year']}.")
    if org.get("hq_city") or org.get("country"):
        loc = ", ".join(x for x in [org.get("hq_city"), org.get("country")] if x)
        lines.append(f"Sede: {loc}.")
    if org.get("size"):
        size_map = {"micro": "micro (<5 persone)", "small": "small (5–20)", "medium": "medium (20–100)", "large": "large (>100)"}
        lines.append(f"Dimensione: {size_map.get(org['size'], org['size'])}.")
    if org.get("annual_budget"):
        lines.append(f"Budget annuo: {org['annual_budget']}.")
    if org.get("website"):
        lines.append(f"Sito: {org['website']}.")

    if org.get("mission"):
        lines.append(f"\n**Mission**: {org['mission']}")
    if org.get("vision"):
        lines.append(f"\n**Vision**: {org['vision']}")
    if org.get("value_proposition"):
        lines.append(f"\n**Value proposition**: {org['value_proposition']}")
    if org.get("unique_positioning"):
        lines.append(f"\n**Posizionamento distintivo**: {org['unique_positioning']}")

    if org.get("cause_areas"):
        lines.append(f"\n**Cause / temi**: {org['cause_areas']}")
    if org.get("programs"):
        lines.append(f"\n**Programmi attivi**: {org['programs']}")
    if org.get("target_beneficiaries"):
        lines.append(f"\n**Beneficiari**: {org['target_beneficiaries']}")
    if org.get("key_achievements"):
        lines.append(f"\n**Risultati chiave**: {org['key_achievements']}")
    if org.get("recent_campaigns"):
        lines.append(f"\n**Campagne recenti**: {org['recent_campaigns']}")
    if org.get("partnerships_history"):
        lines.append(f"\n**Partnership storiche**: {org['partnerships_history']}")

    if org.get("ideal_donor_profile"):
        lines.append(f"\n**Profilo donor ideale**: {org['ideal_donor_profile']}")

    asks = []
    if org.get("typical_ask_individual_eur"):
        asks.append(f"individual ~ €{org['typical_ask_individual_eur']:,}")
    if org.get("typical_ask_corporate_eur"):
        asks.append(f"corporate ~ €{org['typical_ask_corporate_eur']:,}")
    if asks:
        lines.append(f"\n**Ask amount tipici**: {' · '.join(asks)}")
    if org.get("giving_levels"):
        lines.append(f"**Tier di donazione**: {org['giving_levels']}")

    if org.get("exclusion_criteria"):
        lines.append(f"\n**Red flag / criteri di esclusione donatori**: {org['exclusion_criteria']}")
    if org.get("tone_of_voice"):
        lines.append(f"**Tono comunicazione**: {org['tone_of_voice']}")

    lines.append("")
    lines.append("**ISTRUZIONI CONTESTUALI**")
    lines.append("- Quando valuti propensity e affinity, considera l'allineamento tra le cause/valori del prospect e quelle del fundraiser sopra.")
    lines.append("- Quando calcoli `ask_amount` consigliato, allinealo ai tier tipici del fundraiser.")
    lines.append("- Quando suggerisci `ai_next_action`, sii operativo e contestualizzato (es. citare campagna pertinente, partnership esistente, evento, programma specifico).")
    if org.get("exclusion_criteria"):
        lines.append("- Se il prospect cade nei criteri di esclusione sopra, segnalalo chiaramente in `ai_red_flags`.")
    lines.append("- Nel `headline` puoi citare il match esplicito con le cause del fundraiser (es. 'ex board fondazione X — match diretto con causa Y').")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ===================================================================
#   BLOCCHI CONDIVISI — concatenati nei prompt (niente graffe: safe per .format)
# ===================================================================

SCORING_RUBRIC = """
RUBRICA DI SCORING — usa queste ancore, non punteggi a sentimento (così i prospect sono confrontabili tra loro e nel tempo):
- capacity_rating (0-5): 0 = nessuna evidenza di capacità; 1 = reddito medio, nessun asset noto; 2 = manager/imprenditore PMI, asset modesti; 3 = executive/proprietario, patrimonio stimato 6-7 cifre; 4 = multi-milionario o C-level di grande azienda; 5 = UHNWI / lista Forbes / patrimonio oltre 50M.
- propensity_score (0-100): 0-20 nessun segnale filantropico; 21-50 valori/cause affini ma nessuna donazione nota; 51-80 storico filantropico documentato; 81-100 donatore attivo nel settore di questo fundraiser.
- affinity_score (0-100): quanto le cause e i valori del prospect si allineano a quelle del fundraiser (0 nessun legame, 100 sovrapposizione piena e dichiarata).
Non assegnare capacity 4-5 o propensity superiore a 70 senza almeno una fonte a supporto. In ai_summary spiega brevemente su quali evidenze poggiano capacity e propensity.
"""

SOURCING_RULES = """
REGOLE DI ONESTÀ E FONTI — un dossier serve a chiedere soldi, un dato inventato fa fare brutta figura o sbagliare l'ask:
- Ogni numero (patrimonio, importi, fatturati) e ogni nome proprio nel summary deve essere rintracciabile in `sources`, OPPURE marcato esplicitamente come "(stima)".
- Distingui sempre fatto verificato da inferenza: se deduci senza fonte diretta, prefissa con "stima:" e usa confidence "low".
- estimated_net_worth e ogni wealth_indicator con value_eur devono avere source + confidence.
- Email, foto e url: includili solo se li hai realmente verificati, altrimenti null. Mai inventare un indirizzo email.
"""

ITALIAN_SOURCES = """
FONTI ITALIANE PRIORITARIE — se il prospect è italiano, controlla queste prima delle generiche estere:
- Registro Imprese / Camera di Commercio (cariche, quote societarie, bilanci depositati)
- RUNTS e registri delle fondazioni (ruoli in ETS, fondazioni, ODV/APS)
- Elenchi 5x1000 dell'Agenzia delle Entrate (enti già sostenuti dal prospect)
- ACRI e fondazioni di origine bancaria (erogazioni, board)
- Bilanci e relazioni di sostenibilità, comunicati, rassegna stampa (Il Sole 24 Ore, Corriere, MF/Milano Finanza)
- Visure, Gazzetta Ufficiale, atti di nomina; LinkedIn pubblico.
Quando proponi l'ask o la next action, considera le leve fiscali italiane: 5x1000, Art bonus, deducibilità delle erogazioni liberali a ETS.
"""

CLICHE_BLACKLIST = """
DA EVITARE (formule che fanno suonare la mail come un mailing automatico):
- aperture tipo "Mi permetto di scriverLe", "Spero che questa email La trovi bene", "Siamo un'associazione che si occupa di…"
- frasi generiche su mission/valori senza un aggancio specifico al destinatario
- superlativi vuoti ("straordinario", "eccezionale") e burocratese.
STRUTTURA consigliata (adattala, non renderla rigida): 1) gancio specifico sul destinatario (un fatto reale dal profilo); 2) ponte verso la causa del fundraiser; 3) richiesta UNA e chiara (ask o passo successivo); 4) chiusura breve e umana.
"""


INDIVIDUAL_RESEARCH_PROMPT = """{org_context}Sei un analista ricerca AI senior specializzato in prospect research per major donor fundraising.
Devi profilare la persona target usando ESCLUSIVAMENTE fonti pubbliche e verificabili sul web (LinkedIn pubblico, stampa, registri imprese, atti di fondazioni, comunicati ufficiali, newsroom aziendali, dichiarazioni patrimoniali pubbliche, biografie istituzionali).

TARGET:
- Nome: {full_name}
- Contesto/Azienda noto: {context}
- Paese ipotizzato: {country}
- Note utente: {notes}

ISTRUZIONI:
1. Usa WebSearch e WebFetch per raccogliere informazioni pubbliche.
2. Cerca: ruolo attuale, carriera, board memberships, azionariati noti, partecipazioni in fondazioni, attivismo filantropico, donazioni note, beni immobiliari pubblicamente noti, interviste rilevanti, possibili interessi/cause supportate, network di relazioni.
3. NON inventare. Se un'informazione non è verificabile, non includerla. Distingui chiaramente "verificato" da "ipotesi".
4. Stima capacity (capacità di donare) e propensity (propensione a donare) su base evidenze.
5. Restituisci SOLO JSON valido secondo lo schema sotto. Niente testo prima o dopo. Niente markdown fences.
""" + SCORING_RUBRIC + SOURCING_RULES + ITALIAN_SOURCES + """
SCHEMA JSON DI OUTPUT:
{{
  "full_name": "string",
  "headline": "string breve (es. 'CEO Acme Spa, ex Goldman, board Telethon')",
  "company": "string o null",
  "role": "string o null",
  "email": "string o null",
  "phone": "string o null",
  "location": "string o null",
  "country": "string o null",
  "linkedin": "url o null",
  "website": "url o null",
  "twitter": "url o null",
  "photo_url": "url immagine pubblica o null",
  "estimated_net_worth": "string es. '5-10M EUR (stima)' o null",
  "capacity_rating": 0-5,
  "propensity_score": 0-100,
  "affinity_score": 0-100,
  "ask_amount": numero EUR consigliato per il primo ask (allineato ai tier del fundraiser, null se non stimabile),
  "sectors": ["string", ...],
  "ai_summary": "3-5 frasi che sintetizzano chi è e perché è rilevante per il fundraising di QUESTO fundraiser",
  "ai_red_flags": "string o null — controversie, reputazione, conflitti, match con criteri esclusione del fundraiser",
  "ai_next_action": "1-2 frasi concrete e contestualizzate al fundraiser (cita campagna/programma/partnership esistente se rilevante)",
  "wealth_indicators": [
    {{"category":"real_estate|salary|equity|board|foundation|giving_history|art|other","label":"string","detail":"string","value_eur": numero o null,"source":"url","confidence":"low|medium|high"}}
  ],
  "affiliations": [
    {{"organization":"string","role":"string","period":"string","type":"corporate|nonprofit|political|academic|other","source":"url"}}
  ],
  "giving_history": [
    {{"organization":"string","year": numero o null,"amount_eur": numero o null,"cause":"string","source":"url","notes":"string"}}
  ],
  "connections": [
    {{"name":"string","relationship":"string","context":"string","strength":"low|medium|high"}}
  ],
  "sources": [
    {{"url":"string","title":"string","snippet":"string breve"}}
  ]
}}

VINCOLI CRITICI:
- Output deve essere PARSABILE come JSON. Nessun testo extra.
- Tutte le url devono essere reali e raggiunte da te durante la ricerca.
- Se non trovi nulla di affidabile, restituisci comunque lo schema con i campi a null/array vuoti e ai_summary che spiega l'assenza di dati.
"""


CORPORATE_RESEARCH_PROMPT = """{org_context}Sei un analista senior di corporate fundraising e CSR research.
Profila l'azienda target raccogliendo SOLO informazioni pubbliche e verificabili.

TARGET:
- Azienda: {full_name}
- Dominio/sito noto: {context}
- Paese: {country}
- Note utente: {notes}

ISTRUZIONI:
1. Usa WebSearch e WebFetch.
2. Cerca: settore, fatturato, dipendenti, HQ, executive team, board, programma CSR/sostenibilità, fondazione corporate, partnership nonprofit storiche, cause supportate, budget filantropico noto, decisori per donazioni/sponsorship.
3. NON inventare.
4. Restituisci SOLO JSON valido. No markdown fences.
""" + SCORING_RUBRIC + SOURCING_RULES + ITALIAN_SOURCES + """
SCHEMA JSON:
{{
  "full_name": "string (nome azienda)",
  "headline": "string breve (settore + dimensione + posizionamento CSR + match con cause del fundraiser)",
  "company": "string (uguale a full_name)",
  "role": "Corporate",
  "website": "url o null",
  "linkedin": "url o null",
  "location": "string HQ o null",
  "country": "string o null",
  "photo_url": "url logo o null",
  "estimated_net_worth": "fatturato annuo es. '120M EUR (2023)' o null",
  "capacity_rating": 0-5,
  "propensity_score": 0-100,
  "affinity_score": 0-100,
  "ask_amount": numero EUR consigliato per primo ask corporate (allineato ai tier del fundraiser),
  "sectors": ["string"],
  "ai_summary": "3-5 frasi: chi sono, dimensione, perché potrebbero finanziare QUESTO fundraiser",
  "ai_red_flags": "string o null (incluso match con criteri esclusione del fundraiser)",
  "ai_next_action": "1-2 frasi su come avvicinarli con angolo specifico per il fundraiser",
  "wealth_indicators": [
    {{"category":"revenue|csr_budget|foundation|sponsorship|giving_history|other","label":"string","detail":"string","value_eur": numero o null,"source":"url","confidence":"low|medium|high"}}
  ],
  "affiliations": [
    {{"organization":"string (es. nome fondazione o partner)","role":"string","period":"string","type":"corporate|nonprofit|political|academic|other","source":"url"}}
  ],
  "giving_history": [
    {{"organization":"string","year": numero o null,"amount_eur": numero o null,"cause":"string","source":"url","notes":"string"}}
  ],
  "connections": [
    {{"name":"string (decisore/contatto)","relationship":"string ruolo","context":"string","strength":"low|medium|high"}}
  ],
  "sources": [
    {{"url":"string","title":"string","snippet":"string"}}
  ]
}}
"""


FOUNDATION_RESEARCH_PROMPT = """{org_context}Sei un analista senior di institutional fundraising, specializzato in fondazioni erogative ed enti finanziatori.
Profila la FONDAZIONE target raccogliendo SOLO informazioni pubbliche e verificabili, con l'ottica di chi deve ottenere un GRANT/erogazione (non di chi vende).

TARGET:
- Fondazione: {full_name}
- Dominio/sito noto: {context}
- Paese: {country}
- Note utente: {notes}

ISTRUZIONI:
1. Usa WebSearch e WebFetch. Per le fondazioni italiane parti da: sito ufficiale (sezioni "bandi"/"cosa finanziamo"/"erogazioni"), ACRI (se fondazione di origine bancaria), RUNTS/registro persone giuridiche, bilanci di missione, comunicati.
2. Identifica: tipo di fondazione (bancaria | d'impresa | familiare | comunitaria | erogativa/operativa); patrimonio e ammontare erogato all'anno; SETTORI e CAUSE finanziati; aree geografiche ammissibili; modalità (a BANDO vs erogazioni dirette/su invito); importi tipici di grant; bandi attualmente aperti e relative SCADENZE; criteri di ammissibilità (chi può candidarsi).
3. Mappa il processo decisionale e i referenti: organi (CdA, comitato erogazioni/di indirizzo), Segretario Generale, responsabili di area/programma.
4. Cerca erogazioni recenti note (a chi, quanto, per cosa) → utili come precedenti e per capire l'allineamento.
5. NON inventare. Distingui sempre dato verificato da stima.
6. Restituisci SOLO JSON valido. No markdown fences.

NOTE DI MAPPING sullo schema (il CRM riusa i campi corporate):
- `estimated_net_worth`: usalo per patrimonio e/o erogato annuo (es. "erogato ~12M EUR/anno (2024)").
- `wealth_indicators`: capacità erogativa → categorie tipiche: "csr_budget" per il budget erogativo annuo, "foundation"/"giving_history" per programmi e bandi, "other" per patrimonio. In `label`/`detail` indica importi tipici di grant, bandi aperti e SCADENZE quando note.
- `giving_history`: erogazioni/grant CONCESSI dalla fondazione (organization = ente beneficiario, cause, anno, importo, source).
- `affiliations`: organi e governance (es. "Comitato erogazioni", "CdA").
- `connections`: referenti utili (Segretario Generale, responsabili di programma) con ruolo in `relationship`.
- `capacity_rating`: dimensione erogativa della fondazione; `propensity_score`: quanto finanzia cause come quelle del fundraiser; `affinity_score`: allineamento causa/area/ammissibilità.
- `ai_next_action`: come accedere CONCRETAMENTE (bando X aperto fino a YYYY-MM-DD → candidarsi; oppure lettera di intenti / contatto al referente; verifica ammissibilità).
""" + SCORING_RUBRIC + SOURCING_RULES + ITALIAN_SOURCES + """
SCHEMA JSON:
{{
  "full_name": "string (nome fondazione)",
  "headline": "string breve (tipo fondazione + settori finanziati + match con cause del fundraiser)",
  "company": "string (uguale a full_name)",
  "role": "Fondazione",
  "website": "url o null",
  "linkedin": "url o null",
  "location": "string sede o null",
  "country": "string o null",
  "photo_url": "url logo o null",
  "estimated_net_worth": "patrimonio e/o erogato annuo, es. 'erogato 12M EUR/anno (2024)' o null",
  "capacity_rating": 0-5,
  "propensity_score": 0-100,
  "affinity_score": 0-100,
  "ask_amount": numero EUR plausibile per un primo grant (coerente con gli importi tipici della fondazione e i tier del fundraiser),
  "sectors": ["settori/cause finanziati"],
  "ai_summary": "3-5 frasi: che fondazione è, cosa finanzia, perché può finanziare QUESTO fundraiser e con quale modalità",
  "ai_red_flags": "string o null (es. non finanzia la tua area/regione, bandi chiusi, conflitti, criteri esclusione del fundraiser)",
  "ai_next_action": "1-2 frasi operative su come accedere (bando+scadenza, lettera intenti, referente)",
  "wealth_indicators": [
    {{"category":"csr_budget|foundation|giving_history|other","label":"string","detail":"string (importi tipici grant, bando aperto, scadenza)","value_eur": numero o null,"source":"url","confidence":"low|medium|high"}}
  ],
  "affiliations": [
    {{"organization":"string (organo/comitato)","role":"string","period":"string","type":"nonprofit|other","source":"url"}}
  ],
  "giving_history": [
    {{"organization":"string (ente beneficiario)","year": numero o null,"amount_eur": numero o null,"cause":"string","source":"url","notes":"string"}}
  ],
  "connections": [
    {{"name":"string (referente)","relationship":"string (es. Segretario Generale)","context":"string","strength":"low|medium|high"}}
  ],
  "sources": [
    {{"url":"string","title":"string","snippet":"string"}}
  ]
}}
"""


REFRESH_INSIGHTS_PROMPT = """{org_context}Sei un analista di major gift fundraising.
Hai questo profilo prospect dal CRM (JSON):

{profile_json}

Genera un aggiornamento strategico in JSON, contestualizzato al fundraiser sopra. Non fare nuova ricerca web a meno che non sia esplicitamente utile.

IMPORTANTE sugli score: NON modificare capacity/propensity/affinity rispetto ai valori già presenti nel profilo se non hai una NUOVA evidenza concreta. In assenza di nuovi elementi, riporta gli stessi valori. Evita oscillazioni arbitrarie.
""" + SCORING_RUBRIC + """
{{
  "ai_summary": "3-5 frasi aggiornate e contestualizzate al fundraiser",
  "ai_red_flags": "string o null",
  "ai_next_action": "next best action concreta, specifica, che cita programma/campagna/partnership pertinente del fundraiser",
  "capacity_rating": 0-5,
  "propensity_score": 0-100,
  "affinity_score": 0-100,
  "ask_amount": numero EUR consigliato per il primo ask (allineato ai tier del fundraiser)
}}

Solo JSON. No markdown fences.
"""


ASK_DB_PROMPT = """{org_context}Sei l'analista del CRM di questo fundraiser. Hai l'elenco dei prospect nel CRM (una riga per prospect: id, tipo, stage, score capacity/propensity/affinity, azienda, location, settori, ask, raccolto reale, tag).

DATI CRM:
{snapshot}

DOMANDA DEL FUNDRAISER: {question}

ISTRUZIONI:
- Rispondi in italiano, concreto e operativo, basandoti SOLO sui dati sopra. NON inventare prospect che non sono in lista.
- Quando citi o elenchi un prospect usa SEMPRE un link markdown [Nome](/prospects/ID) con l'id esatto della riga.
- Costruisci liste ordinate/raggruppate quando ha senso e, per ciascuno, proponi la prossima mossa concreta (allineata al briefing dell'org).
- Se i dati non bastano, dillo e indica quale ricerca/azione colmerebbe il vuoto.
- Usa **grassetto**, liste con `-`, tabelle markdown se utile. Sintetico ma completo. Verrà renderizzato in HTML.

Risposta:"""


GROUND_SOURCES_PROMPT = """{org_context}Sei un fact-checker. Devi verificare se le FONTI di un dossier prospect supportano davvero le affermazioni chiave (non solo se l'URL esiste).

AFFERMAZIONI CHIAVE SUL PROSPECT (dal CRM):
{claims}

FONTI DA CONTROLLARE (apri ciascun URL con WebFetch):
{sources_list}

ISTRUZIONI:
1. Per OGNI fonte, aprila con WebFetch e valuta se il suo contenuto SUPPORTA le affermazioni chiave sopra (patrimonio, donazioni, ruoli/board, dati citati).
2. Stato per fonte: "supported" (conferma almeno un'affermazione), "not_found" (pagina non pertinente / dato non trovato / non accessibile), "contradicted" (contraddice un'affermazione).
3. In `note` spiega in 1 frase COSA conferma o smentisce, citando il dato.
4. NON inventare: se non riesci ad aprire o non trovi il dato, usa "not_found".
5. Restituisci SOLO JSON valido. No markdown fences.

SCHEMA:
{{
  "sources": [
    {{"url": "string (identica a quella data)", "status": "supported|not_found|contradicted", "note": "1 frase"}}
  ],
  "summary": "1-2 frasi: quanto è solido il dossier alla luce delle fonti"
}}
"""


CHAT_SYSTEM = """Sei l'assistente AI del Prospect Research CRM del fundraiser. Rispondi in italiano, conciso e operativo.
Quando ti chiedono di un prospect ne ricevi il profilo come contesto. Suggerisci azioni di cultivation, draft email, possibili ask, domini da approfondire. Sii pratico, non generico."""


COMPOSE_EMAIL_STREAM_PROMPT = """{org_context}Sei un fundraiser esperto. Scrivi una bozza email di cultivation per un prospect specifico, contestualizzata al fundraiser sopra.

PROSPECT (JSON profilo dal CRM):
{profile_json}

PARAMETRI:
- Scopo: {purpose}
- Tono: {tone}
- Lunghezza target: ~{word_target} parole
- Destinatario nome: {contact_name}
- Email destinatario: {contact_email}
- Punti chiave: {key_points}
{style_example_block}
ISTRUZIONI:
1. Personale e specifica — cita 1-2 elementi del profilo (board, donazioni, interessi, carriera) per credibilità.
2. Allinea ask/proposta alle cause e ai tier del fundraiser sopra.
3. Evita banalità ("siamo un'associazione che…"). Vai al sodo.
4. Firma con il fundraiser di riferimento se presente nel briefing.
5. Se sopra è fornito un ESEMPIO DI STILE, **imita il registro, il ritmo e la struttura** di quell'esempio (NON copiare il contenuto: adattalo al prospect e ai parametri di QUESTA email).
""" + CLICHE_BLACKLIST + """
FORMATO OUTPUT (plain text, senza markdown):
Riga 1: "Oggetto: <oggetto breve e specifico, max 65 char>"
Riga 2: vuota
Resto: corpo email. Usa a-capo naturali. Niente HTML, niente asterischi, niente JSON.
"""


def style_example_block(template: dict | None) -> str:
    """Costruisce il blocco di few-shot da un template email scelto dall'utente."""
    if not template or not template.get("body"):
        return ""
    name = template.get("name") or "Esempio"
    desc = template.get("description") or ""
    lines = ["", "ESEMPIO DI STILE (imita registro, ritmo, struttura — adatta il contenuto al prospect):", f"— {name}" + (f": {desc}" if desc else ""), "```", template["body"].strip(), "```", ""]
    return "\n".join(lines)


COMPOSE_EMAIL_PROMPT = """{org_context}Sei un fundraiser esperto. Devi scrivere una bozza email di cultivation per un prospect specifico, contestualizzata al fundraiser sopra.

PROSPECT (JSON profilo dal CRM):
{profile_json}

PARAMETRI DELLA EMAIL:
- Scopo: {purpose}
- Tono: {tone}
- Lunghezza target: ~{word_target} parole
- Destinatario nome: {contact_name}
- Email destinatario: {contact_email}
- Punti chiave da includere: {key_points}

ISTRUZIONI:
1. Scrivi un'email professionale ma personale che dimostri di aver studiato il prospect.
2. Cita 1-2 elementi specifici del suo profilo (board, donazioni, interessi, carriera) per costruire credibilità.
3. Allinea l'ask/proposta alle cause e ai programmi del fundraiser, e ai tier ask tipici.
4. Evita banalità ("siamo un'associazione che…"). Vai al sodo.
5. Firma con il fundraiser di riferimento se presente.
6. Restituisci SOLO JSON con due campi: subject e body. No markdown fences.
""" + CLICHE_BLACKLIST + """
OUTPUT JSON:
{{
  "subject": "string oggetto email (breve, specifico, no clickbait)",
  "body": "corpo email con \\n per a-capo, formattato per essere copincollabile in un client email. Niente HTML."
}}
"""


# ===================================================================
#                  EDITOR EMAIL — AI ACTIONS
# ===================================================================

EDIT_ACTION_PROMPT = """{org_context}Sei un editor email senior per fundraising.

PROSPECT (sintesi):
{prospect_summary}

TESTO ORIGINALE:
---
{text}
---

AZIONE RICHIESTA: {action_desc}

ISTRUZIONI:
- Mantieni i fatti e il contesto presenti nel testo (non inventare).
- Allinea al briefing del fundraiser quando rilevante.
- Restituisci SOLO il testo modificato.
- Nessun preambolo, commento, JSON, markdown. Solo plain text.
"""


GENERATE_SUBJECTS_PROMPT = """{org_context}Genera {n} oggetti email alternativi per la bozza qui sotto.

CORPO EMAIL:
---
{body}
---

PROSPECT (sintesi):
{prospect_summary}

VINCOLI:
- Ogni oggetto: max 65 caratteri, no clickbait, no emoji.
- Variazioni in: angolo, registro (formale/caloroso/diretto/curioso), lunghezza.
- Specifici per il prospect quando possibile.

Restituisci SOLO JSON valido:
{{"subjects": ["...", "...", ...]}}
"""


CONTINUE_WRITING_PROMPT = """{org_context}Continua questa email per fundraising mantenendo tono e stile.

PROSPECT (sintesi):
{prospect_summary}

TESTO FINORA:
---
{text}
---

ISTRUZIONI:
- Aggiungi 1-3 frasi che continuano naturalmente.
- Non rifare il saluto, non chiudere se non è il punto naturale.
- Restituisci SOLO il pezzo nuovo. No preambolo.
"""


# ===================================================================
#                  BRIEFING ONE-PAGER
# ===================================================================

BRIEFING_PROMPT = """{org_context}Genera briefing one-pager per una call/meeting di 30 minuti con questo prospect.

PROFILO PROSPECT (JSON):
{profile_json}

Output SOLO JSON:
{{
  "headline": "1 frase su chi è e perché è strategico",
  "opening": "1-2 frasi per aprire la conversazione, citando qualcosa specifico e recente",
  "talking_points": [
    {{"topic": "argomento", "why": "perché conta per noi", "question": "domanda aperta"}}
  ],
  "ask_suggestion": "importo EUR + razionale (allineato ai tier del fundraiser)",
  "match_with_org": ["intersezione 1", "intersezione 2", "intersezione 3"],
  "topics_to_avoid": ["argomento sensibile 1", "..."],
  "next_steps_if_yes": "se va bene: prossima azione concreta",
  "next_steps_if_no": "se va male: come riposizionare"
}}

Minimo 5 talking_points. Basa `opening` e i talking_points SOLO su fatti presenti nel profilo: non inventare dettagli "recenti" o aneddoti non verificabili (in una call si nota subito). Se un dato è una stima, trattalo come tale. Solo JSON, no markdown fences.
"""


# ===================================================================
#                  CHAT AI sul prospect
# ===================================================================

CHAT_PROSPECT_PROMPT = """{org_context}Sei l'assistente AI del CRM. Hai questo profilo prospect:

{profile_json}

CONVERSAZIONE PRECEDENTE:
{history}

DOMANDA UTENTE: {message}

ISTRUZIONI:
- Rispondi conciso, operativo, in italiano.
- Il profilo JSON include i dati reali del CRM: giving_history (donazioni), wealth_indicators, affiliations, connections, recent_news. USA questi dati per rispondere (es. "quanto ha donato e a chi") e cita la fonte quando c'è; NON inventare e non dire "non lo so" se il dato è presente nel JSON.
- Basa le risposte sul profilo del prospect e sul briefing del fundraiser.
- Se un dato non è nel profilo, dillo chiaramente invece di inventarlo.
- Suggerisci azioni concrete quando possibile.
- Puoi usare **grassetto**, *corsivo*, liste con `-` e link `[testo](url)`. Verrà renderizzato in HTML.

Risposta:"""


# ===================================================================
#                  SEQUENCE BUILDER
# ===================================================================

# ===================================================================
#                  DEEP DIVE — ricerca mirata per sezione
# ===================================================================

DEEP_DIVE_INSTRUCTIONS = {
    "wealth": (
        "Concentrati ESCLUSIVAMENTE sulla capacità economica del prospect. "
        "Cerca: salary stimato, equity in aziende, partecipazioni societarie, immobili pubblicamente noti, "
        "patrimonio dichiarato (es. lista Forbes/Top 500/registri pubblici), foundation di famiglia, fatturati aziende controllate."
    ),
    "network": (
        "Concentrati ESCLUSIVAMENTE sul network di relazioni. "
        "Cerca: board members con cui condivide CDA, co-founder, colleghi senior, mentori, partner business, "
        "altri prospect potenziali nella sua orbita (familiari rilevanti, soci, peer giving)."
    ),
    "giving": (
        "Concentrati ESCLUSIVAMENTE sullo storico filantropico. "
        "Cerca: donazioni note (importi, anni, organizzazioni), foundation memberships, sponsorizzazioni personali, "
        "presenza in donor list pubbliche, dichiarazioni filantropiche, cause supportate dichiarate."
    ),
    "affiliations": (
        "Concentrati ESCLUSIVAMENTE su ruoli, board, affiliazioni. "
        "Cerca: posizioni CDA attuali e passate, ruoli accademici, ruoli politici, advisory board, "
        "associazioni di categoria, fondazioni in cui siede, partiti, club esclusivi."
    ),
}

DEEP_DIVE_PROMPT = """{org_context}Sei un analista ricerca AI senior. Esegui un APPROFONDIMENTO MIRATO su un prospect già nel CRM.

PROSPECT (profilo attuale):
{profile_json}

SEZIONE DA APPROFONDIRE: **{section}**

ISTRUZIONI MIRATE:
{instructions}

REGOLE GENERALI:
1. Usa WebSearch + WebFetch. Per prospect italiani parti dalle fonti italiane (Registro Imprese, RUNTS, elenchi 5x1000, ACRI, stampa economica IT).
2. NON tornare a riprofilare tutto. NON toccare campi fuori dalla sezione richiesta.
3. NON inventare. Se non trovi nulla di nuovo, restituisci array vuoto e dillo in `note`. Ogni item deve avere una `source` reale; senza fonte, marca confidence "low".
4. Aggiorna capacity_rating/propensity_score SOLO se trovi nuova evidenza concreta; altrimenti OMETTI quel campo (non re-stimare al buio).
5. Restituisci SOLO JSON valido. No markdown fences.

SCHEMA OUTPUT (in base alla sezione):

Per "wealth":
{{
  "section": "wealth",
  "note": "1-2 frasi su cosa hai scoperto di nuovo",
  "estimated_net_worth": "string es. '10-20M EUR (stima)' o null",
  "capacity_rating": 0-5,
  "items": [
    {{"category":"real_estate|salary|equity|board|foundation|giving_history|art|other","label":"string","detail":"string","value_eur": numero o null,"source":"url","confidence":"low|medium|high"}}
  ],
  "sources": [{{"url":"...","title":"...","snippet":"..."}}]
}}

Per "network":
{{
  "section": "network",
  "note": "1-2 frasi",
  "items": [
    {{"name":"string","relationship":"string","context":"string","strength":"low|medium|high"}}
  ],
  "sources": [{{"url":"...","title":"...","snippet":"..."}}]
}}

Per "giving":
{{
  "section": "giving",
  "note": "1-2 frasi",
  "propensity_score": 0-100,
  "items": [
    {{"organization":"string","year": numero o null,"amount_eur": numero o null,"cause":"string","source":"url","notes":"string"}}
  ],
  "sources": [{{"url":"...","title":"...","snippet":"..."}}]
}}

Per "affiliations":
{{
  "section": "affiliations",
  "note": "1-2 frasi",
  "items": [
    {{"organization":"string","role":"string","period":"string","type":"corporate|nonprofit|political|academic|other","source":"url"}}
  ],
  "sources": [{{"url":"...","title":"...","snippet":"..."}}]
}}
"""


# ===================================================================
#                  NEWS ALERT
# ===================================================================

NEWS_SEARCH_PROMPT = """{org_context}Sei un analista press research. Cerca news e menzioni recenti del prospect.

PROSPECT:
- Nome: {full_name}
- Tipo: {ptype}
- Azienda/contesto: {company}
- Paese: {country}

ISTRUZIONI:
1. Usa WebSearch per trovare articoli/menzioni degli ultimi 12 mesi RISPETTO ALLA DATA ODIERNA indicata sopra.
2. Prediligi fonti credibili: stampa nazionale, riviste di settore, comunicati ufficiali, atti pubblici.
3. Escludi contenuto fluff/SEO senza valore.
4. Includi SEMPRE `published_at`: se non riesci a datare un articolo almeno all'anno-mese, scartalo. Ordina i risultati dal più recente al più vecchio.
5. Massimo 12 risultati.
6. Per ogni news valuta il SEGNALE per il fundraising IN RELAZIONE SPECIFICA alle cause/programmi del fundraiser indicati nel contesto sopra (non in astratto):
   - "opportunity" = momento favorevole per avvicinare/chiedere (es. exit/vendita azienda, utili record, nuovo ruolo prestigioso, premio, donazione pubblica, anniversario, lancio fondazione) — meglio ancora se tocca una causa del fundraiser.
   - "risk" = momento da evitare o da gestire con cautela (es. crisi, inchiesta, layoff, lutto, contenzioso, calo risultati).
   - "neutral" = nessuna implicazione operativa.
   In `signal_note` spiega in 1 frase PERCHÉ conta per QUESTO fundraiser e cosa fare.
7. Restituisci SOLO JSON valido. No markdown fences.

SCHEMA:
{{
  "items": [
    {{
      "title": "string",
      "url": "string",
      "publisher": "string (es. Il Sole 24 Ore)",
      "snippet": "1-2 frasi che spiegano il contenuto",
      "published_at": "YYYY-MM-DD o YYYY-MM o null",
      "relevance": "high|medium|low",
      "sentiment": "positive|neutral|negative",
      "signal": "opportunity|neutral|risk",
      "signal_note": "1 frase: perché conta per il fundraising e cosa fare (o null)"
    }}
  ]
}}
"""


SUGGEST_ASK_PROMPT = """{org_context}Sei un consulente senior di major gift fundraising. Devi proporre l'IMPORTO DA CHIEDERE (ask) a questo prospect, con una motivazione difendibile.

PROFILO PROSPECT (JSON):
{profile_json}

ISTRUZIONI:
- Proponi una cifra realistica e specifica, NON un numero tondo a caso: ancorala a capacity, propensity, affinity, storico donazioni, ruolo e ai tier tipici del fundraiser (vedi contesto sopra).
- Dai un range (minimo prudente, target, massimo ambizioso).
- La motivazione deve spiegare il PERCHÉ in modo concreto (su cosa ti basi) e come presentare l'ask. 3-5 frasi, in italiano, operative.
- Se i dati sono troppo scarsi per una stima seria, dillo onestamente in `rationale` e proponi comunque un ordine di grandezza prudente.
- `confidence` deve riflettere la QUALITÀ delle evidenze: se capacity/giving sono stime deboli o senza fonte, NON usare "high". Niente falsa precisione.

Output SOLO JSON, no markdown fences:
{{
  "ask_eur": numero intero (target consigliato),
  "ask_low_eur": numero intero (minimo prudente),
  "ask_high_eur": numero intero (massimo ambizioso),
  "rationale": "3-5 frasi sul perché di questa cifra e come proporla",
  "confidence": "low|medium|high"
}}
"""


SEQUENCE_GENERATE_PROMPT = """{org_context}Genera una sequence email di fundraising — {n_steps} step distribuiti nel tempo.

PROSPECT (JSON):
{profile_json}

GOAL: {goal}

LINEE GUIDA:
- Step 1 (giorno 0): primo contatto/intro
- Step 2 (giorno 7): follow-up morbido o riferimento a contenuto
- Step 3 (giorno 14-21): soft ask o richiesta meeting
- Step 4+ (giorno 30+): hard ask o thank-you steward
- Adatta spaziature al goal e profilo.
- Ogni email coerente con la precedente (riferimenti, escalation).
- Lunghezza email: 120-200 parole.

Output SOLO JSON:
{{
  "name": "nome breve descrittivo",
  "steps": [
    {{"step_index": 1, "delay_days": 0, "purpose": "cold_intro|warm_followup|soft_ask|hard_ask|thank_steward", "subject": "...", "body": "..."}}
  ]
}}
No markdown fences."""
