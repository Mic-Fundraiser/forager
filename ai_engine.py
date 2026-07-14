"""Wrapper around the local `claude` CLI to run ricerca AI research via the user's
Claude Code subscription. No external API keys required."""
import json
import re
import shutil
import subprocess
import threading
import time
from typing import Optional

import prompts
import config
from datetime import date
from db import cursor, get_org, rows_to_dicts, dict_from_row

CLAUDE_BIN = config.CLAUDE_BIN or shutil.which("claude") or "claude"


def build_context() -> str:
    """Contesto comune prependuto a ogni prompt AI: lingua di output + ancoraggio
    temporale (la data odierna) + briefing organizzazione. Usato sia qui sia dalle
    route streaming in app.py. La lingua è letta da org.language → funziona anche nei
    job in background (senza request)."""
    org = get_org()
    lang = (org or {}).get("language") if org else None
    if lang == "en":
        lang_line = ("# OUTPUT LANGUAGE: ENGLISH\nWrite ALL generated content (summaries, "
                     "emails, answers, next actions, notes) in ENGLISH, regardless of the "
                     "language of the sources.\n\n")
    else:
        lang_line = ("# LINGUA DI OUTPUT: ITALIANO\nScrivi TUTTI i contenuti generati "
                     "(sintesi, email, risposte, next action, note) in ITALIANO.\n\n")
    today = date.today().isoformat()
    anchor = (
        f"# DATA ODIERNA / TODAY: {today}\n"
        f"Riferisci 'recente'/'ultimi 12 mesi' a questa data ({today}); esplicita l'anno per i fatti datati.\n\n"
    )
    return lang_line + anchor + prompts.org_context_block(org)


def enrich_prospect_context(prospect: dict) -> dict:
    """Aggiunge al profilo i record figli già nel DB (giving, wealth, affiliazioni,
    connessioni, news recenti). Così la chat AI risponde con i dati reali invece di
    dire 'non lo so' o inventare quando l'informazione c'è."""
    pid = (prospect or {}).get("id")
    if not pid:
        return prospect or {}
    out = dict(prospect)
    try:
        with cursor() as conn:
            out["giving_history"] = [dict(r) for r in conn.execute(
                "SELECT organization,year,amount_eur,cause,source FROM giving_history WHERE prospect_id=? ORDER BY year DESC", (pid,)).fetchall()]
            out["wealth_indicators"] = [dict(r) for r in conn.execute(
                "SELECT category,label,detail,value_eur,confidence,source FROM wealth_indicators WHERE prospect_id=? ORDER BY value_eur DESC", (pid,)).fetchall()]
            out["affiliations"] = [dict(r) for r in conn.execute(
                "SELECT organization,role,period,type FROM affiliations WHERE prospect_id=?", (pid,)).fetchall()]
            out["connections"] = [dict(r) for r in conn.execute(
                "SELECT name,relationship,context,strength FROM connections WHERE prospect_id=?", (pid,)).fetchall()]
            out["recent_news"] = [dict(r) for r in conn.execute(
                "SELECT title,publisher,published_at,signal,signal_note FROM news_items WHERE prospect_id=? ORDER BY COALESCE(published_at,fetched_at) DESC LIMIT 8", (pid,)).fetchall()]
    except Exception:
        pass
    return out


DEFAULT_TIMEOUT = 600  # 10 min per ricerca

# Pool a concorrenza limitata: evita che un import CSV grosso lanci centinaia di
# processi `claude` in parallelo (rate-limit / esaurimento risorse garantito).
from concurrent.futures import ThreadPoolExecutor

_JOB_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="forager-job")


def _job_guard(fn, job_id, *args):
    """Esegue un job e, se solleva, marca il job come 'error' invece di lasciarlo appeso."""
    try:
        fn(job_id, *args)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            with cursor() as conn:
                conn.execute(
                    "UPDATE research_jobs SET status='error', finished_at=CURRENT_TIMESTAMP, error=? "
                    "WHERE id=? AND status NOT IN ('done')",
                    (f"Errore interno: {e}", job_id),
                )
        except Exception:
            pass


def recover_orphan_jobs():
    """All'avvio RIPRENDE i job rimasti 'pending'/'running' da un riavvio/crash precedente
    (prima venivano persi e marcati 'error'). Così un import notturno di 200 nomi non si
    perde se il Mac va in sleep: i job vengono ri-accodati e completati."""
    try:
        with cursor() as conn:
            jobs = rows_to_dicts(conn.execute(
                "SELECT * FROM research_jobs WHERE status IN ('pending','running')"
            ).fetchall())
    except Exception:
        return
    resumed = 0
    for j in jobs:
        try:
            q = json.loads(j.get("query") or "{}")
        except Exception:
            q = {}
        pid = j.get("prospect_id")
        with cursor() as conn:
            conn.execute("UPDATE research_jobs SET status='pending', error=NULL WHERE id=?", (j["id"],))
        if q.get("kind") == "sequence":
            _JOB_POOL.submit(_job_guard, _run_sequence_job, j["id"], pid,
                             q.get("goal") or "cultivation", int(q.get("n_steps") or 4))
        else:
            ptype = "individual"
            if pid:
                try:
                    with cursor() as conn:
                        row = conn.execute("SELECT type FROM prospects WHERE id=?", (pid,)).fetchone()
                    if row:
                        ptype = row["type"]
                except Exception:
                    pass
            _JOB_POOL.submit(_job_guard, _run_job, j["id"], pid, ptype,
                             q.get("full_name") or "", q.get("context") or "",
                             q.get("country") or "", q.get("notes") or "")
        resumed += 1
    if resumed:
        print(f"  Ripresi {resumed} job AI interrotti")


def _extract_json(text: str) -> Optional[dict]:
    """Robust JSON extraction from model output."""
    if not text:
        return None
    text = text.strip()
    # try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip code fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = text[start : end + 1]
        try:
            return json.loads(chunk)
        except Exception:
            return None
    return None


def run_claude_stream(prompt: str, allowed_tools: list[str] | None = None,
                      usage_kind: str | None = None, prospect_id: int | None = None,
                      timeout: int = DEFAULT_TIMEOUT):
    """Generator che yielda eventi dal CLI claude in modalità stream-json.

    Eventi yieldati (dict):
      {"type": "chunk", "text": "<delta>"}
      {"type": "done",  "text": "<full>", "usage": {...}}
      {"type": "error", "error": "..."}
    """
    cmd = [
        CLAUDE_BIN,
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
    ]
    if allowed_tools is not None:
        cmd += ["--allowed-tools", ",".join(allowed_tools) if allowed_tools else ""]

    t0 = time.time()
    accumulated = ""
    in_tok = out_tok = None
    cost_usd = None
    done_emitted = False
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )
    except FileNotFoundError:
        if usage_kind:
            _log_usage(usage_kind, prospect_id, 0, None, None, None, False, "claude CLI non trovato")
        yield {"type": "error", "error": "Motore AI non disponibile: Claude Code non risulta installato o autenticato."}
        return

    # Watchdog: se il processo non produce un risultato entro `timeout`, lo termina.
    # Senza questo, un blocco lato CLI lascerebbe lo spinner infinito e un processo orfano.
    timed_out = {"v": False}

    def _kill_on_timeout():
        timed_out["v"] = True
        try:
            proc.kill()
        except Exception:
            pass

    watchdog = threading.Timer(timeout, _kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()

    # Reader su thread separato + coda: il loop principale può così emettere un
    # heartbeat quando il CLI resta in silenzio a lungo (tool use di minuti),
    # tenendo viva la connessione SSE attraverso proxy/browser con idle timeout.
    import queue as _queue
    _lines: "_queue.Queue[object]" = _queue.Queue()
    _EOF = object()

    def _reader():
        try:
            for raw in proc.stdout:
                _lines.put(raw)
        except Exception:
            pass
        finally:
            _lines.put(_EOF)

    reader_t = threading.Thread(target=_reader, daemon=True)
    reader_t.start()

    def _iter_lines():
        while True:
            try:
                item = _lines.get(timeout=25)
            except _queue.Empty:
                yield None  # silenzio prolungato → heartbeat
                continue
            if item is _EOF:
                return
            yield item

    try:
        for line in _iter_lines():
            if line is None:
                yield {"type": "heartbeat"}
                continue
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except Exception:
                continue
            etype = evt.get("type")
            if etype == "assistant":
                msg = evt.get("message") or {}
                contents = msg.get("content") or []
                # accumula il text di tutte le parts type==text
                full_text = "".join(c.get("text", "") for c in contents if c.get("type") == "text")
                if len(full_text) > len(accumulated):
                    delta = full_text[len(accumulated):]
                    accumulated = full_text
                    yield {"type": "chunk", "text": delta}
            elif etype == "result":
                final = evt.get("result") or accumulated
                # se result più lungo di accumulated (caso non-stream), emetti delta
                if len(final) > len(accumulated):
                    yield {"type": "chunk", "text": final[len(accumulated):]}
                    accumulated = final
                usage = evt.get("usage") or {}
                in_tok = usage.get("input_tokens") or usage.get("input_tokens_total")
                out_tok = usage.get("output_tokens") or usage.get("output_tokens_total")
                cost_usd = evt.get("total_cost_usd") or evt.get("cost_usd")
                done_emitted = True
                yield {"type": "done", "text": accumulated,
                       "usage": {"input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": cost_usd}}
                break
        # timeout scattato: avvisa il client invece di chiudere in silenzio
        if timed_out["v"] and not done_emitted:
            yield {"type": "error", "error": _friendly_error("timeout")}
        # loop terminato senza evento `result` (es. CLI chiusa a metà): done di fallback
        elif not done_emitted:
            done_emitted = True
            yield {"type": "done", "text": accumulated,
                   "usage": {"input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": cost_usd}}
    except GeneratorExit:
        # il client ha chiuso la connessione SSE: termina subito il processo claude
        # (evita processi orfani che continuano a consumare la subscription)
        try:
            proc.kill()
        except Exception:
            pass
        raise
    finally:
        watchdog.cancel()
        if proc.poll() is None:
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        duration_ms = int((time.time() - t0) * 1000)
        if usage_kind:
            _log_usage(usage_kind, prospect_id, duration_ms, in_tok, out_tok, cost_usd, done_emitted,
                       error=None if done_emitted else ("timeout" if timed_out["v"] else "stream interrotto"))


def _log_usage(kind: str, prospect_id: int | None, duration_ms: int,
               input_tokens: int | None, output_tokens: int | None,
               cost_usd: float | None, ok: bool, error: str | None = None, notes: str | None = None):
    """Persisti riga in usage_log. Mai fail-loud: se errore, ingoia."""
    try:
        with cursor() as conn:
            conn.execute(
                """INSERT INTO usage_log(kind, prospect_id, duration_ms, input_tokens, output_tokens, cost_usd, ok, error, notes)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (kind, prospect_id, duration_ms, input_tokens, output_tokens, cost_usd, 1 if ok else 0, error, notes),
            )
    except Exception:
        pass


def _friendly_error(raw: str | None) -> str:
    """Traduce gli errori tecnici della CLI in messaggi azionabili per un fundraiser non-tech.
    Il messaggio tecnico originale resta comunque salvato in usage_log."""
    e = (raw or "").lower()
    if not e:
        return "Errore sconosciuto. Riprova; se persiste riavvia Forager."
    if "non trovat" in e or "not found" in e or "no such file" in e:
        return "Motore AI non disponibile: Claude Code non risulta installato o autenticato. Apri il terminale e verifica con « claude ». "
    if "timeout" in e:
        return "La ricerca ha impiegato troppo tempo e si è interrotta. Riprova: spesso al secondo tentativo va a buon fine."
    if "json" in e:
        return "Claude ha risposto in un formato non leggibile. Riprova la ricerca."
    if "overloaded" in e or "rate" in e or "429" in e or "limit" in e:
        return "Il servizio AI è momentaneamente sovraccarico o hai raggiunto un limite d'uso. Attendi qualche minuto e riprova."
    if "auth" in e or "401" in e or "403" in e or "login" in e:
        return "Sessione Claude scaduta. Riautenticati con « claude » nel terminale, poi riprova."
    # default: messaggio generico + traccia breve
    return "Si è verificato un errore con il motore AI. Riprova; se persiste, controlla che Claude Code sia attivo."


def _repair_json(raw_text: str, timeout: int = 90) -> Optional[dict]:
    """Tenta di recuperare un JSON valido da output malformato con un passaggio
    economico SENZA tool web (non ri-esegue la ricerca da capo)."""
    if not raw_text:
        return None
    prompt = (
        "Dal testo seguente estrai ESCLUSIVAMENTE l'oggetto JSON valido che contiene. "
        "Correggi virgole finali, virgolette e parentesi non chiuse. "
        "Restituisci SOLO il JSON, niente altro, niente markdown.\n\n---\n" + raw_text[:20000]
    )
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--output-format", "json", "--allowed-tools", ""],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception:
        return None
    out = proc.stdout or ""
    try:
        wrapper = json.loads(out)
        out = wrapper.get("result", out) if isinstance(wrapper, dict) else out
    except Exception:
        pass
    return _extract_json(out)


def run_claude(prompt: str, timeout: int = DEFAULT_TIMEOUT,
               usage_kind: str | None = None, prospect_id: int | None = None,
               allowed_tools: list[str] | None = None, repair_json: bool = False) -> dict:
    """Invoke claude CLI in headless mode.

    allowed_tools: lista di tool consentiti. None → default WebSearch/WebFetch
      (per le funzioni che cercano sul web). [] → nessun tool (più veloce/economico,
      per compose/edit/chat/briefing/ask che lavorano sul profilo già in mano).
    repair_json: se True e il parsing fallisce, tenta un recupero economico del JSON
      senza ri-eseguire la ricerca.

    Returns a dict with keys: ok, text, json (parsed), raw, error.
    Se usage_kind è valorizzato, logga una riga in usage_log.
    """
    if allowed_tools is None:
        allowed_tools = ["WebSearch", "WebFetch"]
    cmd = [
        CLAUDE_BIN,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--allowed-tools",
        ",".join(allowed_tools),
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        if usage_kind:
            _log_usage(usage_kind, prospect_id, int((time.time()-t0)*1000), None, None, None, False, "timeout")
        return {"ok": False, "error": _friendly_error("timeout"), "error_tech": "timeout", "raw": ""}
    except FileNotFoundError:
        if usage_kind:
            _log_usage(usage_kind, prospect_id, int((time.time()-t0)*1000), None, None, None, False, "claude CLI non trovato")
        return {"ok": False, "error": _friendly_error("non trovato"), "error_tech": "claude CLI non trovato", "raw": ""}

    duration_ms = int((time.time() - t0) * 1000)
    raw = proc.stdout or ""
    err = proc.stderr or ""

    if proc.returncode != 0 and not raw:
        tech = err.strip() or f"exit {proc.returncode}"
        if usage_kind:
            _log_usage(usage_kind, prospect_id, duration_ms, None, None, None, False, tech)
        return {"ok": False, "error": _friendly_error(tech), "error_tech": tech, "raw": raw}

    # CLI returns wrapper JSON: {"type":"result","subtype":"success","result":"...assistant text...", ...}
    text = raw
    in_tok = out_tok = None
    cost_usd = None
    try:
        wrapper = json.loads(raw)
        if isinstance(wrapper, dict):
            if "result" in wrapper:
                text = wrapper.get("result", "") or ""
            usage = wrapper.get("usage") or {}
            in_tok = usage.get("input_tokens") or usage.get("input_tokens_total")
            out_tok = usage.get("output_tokens") or usage.get("output_tokens_total")
            # cost wrapper può essere total_cost_usd o cost_usd
            cost_usd = wrapper.get("total_cost_usd") or wrapper.get("cost_usd")
    except Exception:
        # not the wrapper, treat as text
        pass

    parsed = _extract_json(text)
    # Recupero: se ci aspettavamo JSON ma il parsing fallisce, tenta un fix economico
    # (senza ri-eseguire la ricerca) prima di considerare perso il lavoro.
    if parsed is None and repair_json and text.strip():
        parsed = _repair_json(text)
    if usage_kind:
        _log_usage(usage_kind, prospect_id, duration_ms, in_tok, out_tok, cost_usd, True)
    return {"ok": True, "text": text, "json": parsed, "raw": raw, "error": None,
            "input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": cost_usd,
            "duration_ms": duration_ms}


# ------------- Persistence helpers -------------


def _norm_str(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v if x)
    return str(v)


def _norm_int(v):
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except Exception:
        return None


def persist_profile(prospect_id: int, profile: dict, ptype: str = "individual"):
    """Update a prospect row + child tables from a profile JSON."""
    if not profile:
        return
    sectors = profile.get("sectors")
    with cursor() as conn:
        conn.execute(
            """
            UPDATE prospects SET
                type = COALESCE(?, type),
                headline = COALESCE(?, headline),
                company = COALESCE(?, company),
                role = COALESCE(?, role),
                email = COALESCE(?, email),
                phone = COALESCE(?, phone),
                location = COALESCE(?, location),
                country = COALESCE(?, country),
                linkedin = COALESCE(?, linkedin),
                website = COALESCE(?, website),
                twitter = COALESCE(?, twitter),
                photo_url = COALESCE(?, photo_url),
                estimated_net_worth = COALESCE(?, estimated_net_worth),
                capacity_rating = COALESCE(?, capacity_rating),
                propensity_score = COALESCE(?, propensity_score),
                affinity_score = COALESCE(?, affinity_score),
                ai_summary = COALESCE(?, ai_summary),
                ai_red_flags = COALESCE(?, ai_red_flags),
                ai_next_action = COALESCE(?, ai_next_action),
                ask_amount = COALESCE(?, ask_amount),
                sectors = COALESCE(?, sectors),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                ptype,
                _norm_str(profile.get("headline")),
                _norm_str(profile.get("company")),
                _norm_str(profile.get("role")),
                _norm_str(profile.get("email")),
                _norm_str(profile.get("phone")),
                _norm_str(profile.get("location")),
                _norm_str(profile.get("country")),
                _norm_str(profile.get("linkedin")),
                _norm_str(profile.get("website")),
                _norm_str(profile.get("twitter")),
                _norm_str(profile.get("photo_url")),
                _norm_str(profile.get("estimated_net_worth")),
                _norm_int(profile.get("capacity_rating")),
                _norm_int(profile.get("propensity_score")),
                _norm_int(profile.get("affinity_score")),
                _norm_str(profile.get("ai_summary")),
                _norm_str(profile.get("ai_red_flags")),
                _norm_str(profile.get("ai_next_action")),
                _norm_int(profile.get("ask_amount")),
                _norm_str(sectors),
                prospect_id,
            ),
        )

        # Sostituisci SOLO i record prodotti da una ricerca completa precedente.
        # I deep-dive (origin='deep_dive') e gli inserimenti manuali (origin='manual')
        # vengono preservati: una nuova "Aggiorna ricerca" non distrugge più quel lavoro.
        for tbl in ("wealth_indicators", "affiliations", "giving_history", "connections", "sources"):
            conn.execute(f"DELETE FROM {tbl} WHERE prospect_id = ? AND origin = 'research'", (prospect_id,))

        for w in profile.get("wealth_indicators") or []:
            conn.execute(
                "INSERT INTO wealth_indicators(prospect_id,category,label,detail,value_eur,source,confidence,origin) VALUES (?,?,?,?,?,?,?,'research')",
                (
                    prospect_id,
                    _norm_str(w.get("category")),
                    _norm_str(w.get("label")) or "—",
                    _norm_str(w.get("detail")),
                    _norm_int(w.get("value_eur")),
                    _norm_str(w.get("source")),
                    _norm_str(w.get("confidence")) or "medium",
                ),
            )
        for a in profile.get("affiliations") or []:
            conn.execute(
                "INSERT INTO affiliations(prospect_id,organization,role,period,type,source,origin) VALUES (?,?,?,?,?,?,'research')",
                (
                    prospect_id,
                    _norm_str(a.get("organization")) or "—",
                    _norm_str(a.get("role")),
                    _norm_str(a.get("period")),
                    _norm_str(a.get("type")),
                    _norm_str(a.get("source")),
                ),
            )
        for g in profile.get("giving_history") or []:
            conn.execute(
                "INSERT INTO giving_history(prospect_id,organization,year,amount_eur,cause,source,notes,origin) VALUES (?,?,?,?,?,?,?,'research')",
                (
                    prospect_id,
                    _norm_str(g.get("organization")),
                    _norm_int(g.get("year")),
                    _norm_int(g.get("amount_eur")),
                    _norm_str(g.get("cause")),
                    _norm_str(g.get("source")),
                    _norm_str(g.get("notes")),
                ),
            )
        for c in profile.get("connections") or []:
            conn.execute(
                "INSERT INTO connections(prospect_id,name,relationship,context,strength,origin) VALUES (?,?,?,?,?,'research')",
                (
                    prospect_id,
                    _norm_str(c.get("name")) or "—",
                    _norm_str(c.get("relationship")),
                    _norm_str(c.get("context")),
                    _norm_str(c.get("strength")) or "medium",
                ),
            )
        for s in profile.get("sources") or []:
            conn.execute(
                "INSERT INTO sources(prospect_id,url,title,snippet,origin) VALUES (?,?,?,?,'research')",
                (
                    prospect_id,
                    _norm_str(s.get("url")) or "—",
                    _norm_str(s.get("title")),
                    _norm_str(s.get("snippet")),
                ),
            )

        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (
                prospect_id,
                "ai_research",
                "Ricerca AI completata",
                profile.get("ai_summary") or "",
            ),
        )


# ------------- Async job runner -------------


def _run_job(job_id: int, prospect_id: int, ptype: str, full_name: str, context: str, country: str, notes: str):
    template = {
        "corporate": prompts.CORPORATE_RESEARCH_PROMPT,
        "foundation": prompts.FOUNDATION_RESEARCH_PROMPT,
    }.get(ptype, prompts.INDIVIDUAL_RESEARCH_PROMPT)
    org_ctx = build_context()
    prompt = template.format(
        org_context=org_ctx,
        full_name=full_name or "",
        context=context or "",
        country=country or "",
        notes=notes or "",
    )

    with cursor() as conn:
        conn.execute("UPDATE research_jobs SET status='running' WHERE id=?", (job_id,))

    result = run_claude(prompt, usage_kind="research", prospect_id=prospect_id, repair_json=True)

    if not result["ok"]:
        with cursor() as conn:
            conn.execute(
                "UPDATE research_jobs SET status='error', finished_at=CURRENT_TIMESTAMP, error=?, raw_output=? WHERE id=?",
                (result.get("error"), result.get("raw"), job_id),
            )
        return

    profile = result.get("json")
    if not profile:
        with cursor() as conn:
            conn.execute(
                "UPDATE research_jobs SET status='error', finished_at=CURRENT_TIMESTAMP, error=?, raw_output=? WHERE id=?",
                ("Claude ha risposto in un formato non leggibile. Riprova la ricerca (di solito al secondo tentativo va a buon fine).",
                 result.get("text") or result.get("raw"), job_id),
            )
        return

    persist_profile(prospect_id, profile, ptype=ptype)
    auto_link_connections(prospect_id)        # le SUE connection → prospect esistenti
    link_connections_to(prospect_id)          # le connection ALTRUI → questa scheda nuova

    with cursor() as conn:
        conn.execute(
            "UPDATE research_jobs SET status='done', finished_at=CURRENT_TIMESTAMP, raw_output=? WHERE id=?",
            (json.dumps(profile, ensure_ascii=False), job_id),
        )


def start_research_job(prospect_id: int, ptype: str, full_name: str, context: str, country: str, notes: str) -> int:
    with cursor() as conn:
        # Un solo job attivo per prospect: due ricerche parallele sullo stesso profilo
        # si sovrascriverebbero a vicenda (persist_profile cancella e ricrea i figli).
        if prospect_id:
            existing = conn.execute(
                "SELECT id FROM research_jobs WHERE prospect_id=? AND status IN ('pending','running') LIMIT 1",
                (prospect_id,),
            ).fetchone()
            if existing:
                return existing["id"]
        cur = conn.execute(
            "INSERT INTO research_jobs(prospect_id, query, status) VALUES (?,?, 'pending')",
            (prospect_id, json.dumps({"full_name": full_name, "context": context, "country": country, "notes": notes})),
        )
        job_id = cur.lastrowid

    _JOB_POOL.submit(_job_guard, _run_job, job_id, prospect_id, ptype, full_name, context, country, notes)
    return job_id


def compose_email(prospect_id: int, profile: dict, purpose: str, tone: str, word_target: int,
                  contact_name: str, contact_email: str, key_points: str) -> dict:
    """Genera bozza email via Claude. Salva in email_drafts. Returns {ok, draft_id, subject, body, error}."""
    import json as _json
    org_ctx = build_context()
    profile_json = _json.dumps(profile, ensure_ascii=False, default=str)
    prompt = prompts.COMPOSE_EMAIL_PROMPT.format(
        org_context=org_ctx,
        profile_json=profile_json,
        purpose=purpose or "first cold approach",
        tone=tone or "warm",
        word_target=word_target or 180,
        contact_name=contact_name or profile.get("full_name") or "—",
        contact_email=contact_email or profile.get("email") or "—",
        key_points=key_points or "(autonomo)",
    )
    result = run_claude(prompt, timeout=180, usage_kind="compose", prospect_id=prospect_id,
                        allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not subject or not body:
        return {"ok": False, "error": "Claude non ha restituito subject/body."}

    with cursor() as conn:
        cur = conn.execute(
            """INSERT INTO email_drafts(prospect_id, contact_email, contact_name, subject, body, purpose, tone, word_target, key_points)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                prospect_id,
                contact_email or None,
                contact_name or None,
                subject,
                body,
                purpose,
                tone,
                word_target,
                key_points or None,
            ),
        )
        draft_id = cur.lastrowid
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "email", f"Bozza email AI: {subject}", f"Generata draft email · purpose: {purpose} · tone: {tone}"),
        )

    return {"ok": True, "draft_id": draft_id, "subject": subject, "body": body}


import unicodedata

# titoli/onorifici da ignorare nel match dei nomi
_NAME_TITLES = {
    "dott", "dr", "dssa", "sig", "sigra", "ing", "prof", "avv", "arch", "rag",
    "mr", "mrs", "ms", "on", "sen", "the", "di", "de", "del", "della", "san",
}


def _name_tokens(s: str) -> list[str]:
    """Normalizza un nome → lista di token (lowercase, senza accenti, punteggiatura, titoli)."""
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return [t for t in s.split() if len(t) >= 2 and t not in _NAME_TITLES]


def _names_match(a_toks: list[str], b_toks: list[str]) -> bool:
    """True se due nomi indicano (con buona probabilità) la stessa persona/ente.
    Evita i falsi positivi del vecchio match a sottostringa (es. tutti i 'Marco')."""
    if not a_toks or not b_toks:
        return False
    sa, sb = set(a_toks), set(b_toks)
    if sa == sb:
        return True
    # nome a token singolo: solo match esatto, niente euristiche
    if len(sa) == 1 or len(sb) == 1:
        return sa == sb
    # almeno 2 token "forti" (len>=3) in comune → tipicamente nome + cognome
    strong_common = [t for t in (sa & sb) if len(t) >= 3]
    if len(strong_common) < 2:
        return False
    # ...e l'ultimo token (cognome) deve coincidere: evita falsi positivi tipo
    # "Anna Maria Rossi" vs "Anna Maria Bianchi" (condividono Anna+Maria ma non il cognome).
    return a_toks[-1] == b_toks[-1]


def auto_link_connections(prospect_id: int):
    """Se una connection di un prospect corrisponde a un altro prospect nel DB, linka.
    Match per token di nome normalizzati (vedi _names_match) per ridurre i falsi positivi."""
    with cursor() as conn:
        conns = conn.execute(
            "SELECT id, name FROM connections WHERE prospect_id=? AND matched_prospect_id IS NULL",
            (prospect_id,),
        ).fetchall()
        if not conns:
            return
        all_p = conn.execute(
            "SELECT id, full_name FROM prospects WHERE id != ?",
            (prospect_id,),
        ).fetchall()
        # pre-tokenizza i prospect una volta sola
        p_toks = [(p["id"], _name_tokens(p["full_name"])) for p in all_p]
        for c in conns:
            ctoks = _name_tokens(c["name"])
            if not ctoks:
                continue
            for pid, ptoks in p_toks:
                if pid != prospect_id and _names_match(ctoks, ptoks):
                    conn.execute(
                        "UPDATE connections SET matched_prospect_id=? WHERE id=?",
                        (pid, c["id"]),
                    )
                    break


def link_connections_to(prospect_id: int) -> int:
    """Direzione INVERSA di auto_link_connections: quando nasce una scheda nuova,
    aggancia a lei le connection non abbinate degli ALTRI prospect che la citavano
    per nome (prima restavano scollegate finché non premevi "Ricollega")."""
    with cursor() as conn:
        row = conn.execute("SELECT full_name FROM prospects WHERE id=?", (prospect_id,)).fetchone()
        if not row:
            return 0
        ptoks = _name_tokens(row["full_name"])
        if not ptoks:
            return 0
        conns = conn.execute(
            "SELECT id, name FROM connections WHERE matched_prospect_id IS NULL AND prospect_id != ?",
            (prospect_id,),
        ).fetchall()
        linked = 0
        for c in conns:
            ctoks = _name_tokens(c["name"])
            if ctoks and _names_match(ctoks, ptoks):
                conn.execute(
                    "UPDATE connections SET matched_prospect_id=? WHERE id=? AND matched_prospect_id IS NULL",
                    (prospect_id, c["id"]),
                )
                linked += 1
        return linked


def relink_all_connections() -> int:
    """Ricollega TUTTE le connection in un colpo solo: tokenizza ogni prospect una
    volta, confronta in memoria, scrive in un'unica transazione. Sostituisce il vecchio
    loop che riapriva la connessione e ri-tokenizzava tutti i prospect per ogni prospect
    (O(n²) di tokenizzazioni + tanti open/close). Ritorna il numero di link creati."""
    with cursor() as conn:
        prospects = conn.execute("SELECT id, full_name FROM prospects").fetchall()
        conns = conn.execute(
            "SELECT id, prospect_id, name FROM connections WHERE matched_prospect_id IS NULL"
        ).fetchall()
        p_toks = [(p["id"], _name_tokens(p["full_name"])) for p in prospects]
        linked = 0
        for c in conns:
            ctoks = _name_tokens(c["name"])
            if not ctoks:
                continue
            for pid, ptoks in p_toks:
                if pid != c["prospect_id"] and _names_match(ctoks, ptoks):
                    conn.execute("UPDATE connections SET matched_prospect_id=? WHERE id=?", (pid, c["id"]))
                    linked += 1
                    break
    return linked


def refresh_insights(prospect_id: int, profile_json: str) -> dict:
    org_ctx = build_context()
    prompt = prompts.REFRESH_INSIGHTS_PROMPT.format(org_context=org_ctx, profile_json=profile_json)
    result = run_claude(prompt, timeout=180, usage_kind="refresh", prospect_id=prospect_id,
                        allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}

    with cursor() as conn:
        conn.execute(
            """UPDATE prospects SET
                ai_summary = COALESCE(?, ai_summary),
                ai_red_flags = COALESCE(?, ai_red_flags),
                ai_next_action = COALESCE(?, ai_next_action),
                capacity_rating = COALESCE(?, capacity_rating),
                propensity_score = COALESCE(?, propensity_score),
                affinity_score = COALESCE(?, affinity_score),
                ask_amount = COALESCE(?, ask_amount),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?""",
            (
                _norm_str(data.get("ai_summary")),
                _norm_str(data.get("ai_red_flags")),
                _norm_str(data.get("ai_next_action")),
                _norm_int(data.get("capacity_rating")),
                _norm_int(data.get("propensity_score")),
                _norm_int(data.get("affinity_score")),
                _norm_int(data.get("ask_amount")),
                prospect_id,
            ),
        )
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "ai_research", "Insights aggiornati", data.get("ai_next_action") or ""),
        )
    return {"ok": True, "data": data}


# ===================================================================
#                  EDITOR EMAIL helpers
# ===================================================================

EDIT_ACTIONS = {
    "rephrase":      "Riformula mantenendo significato e lunghezza, ma migliora flow e rimuovi banalità.",
    "shorten":       "Accorcia del 40-50% mantenendo i punti chiave.",
    "expand":        "Espandi del 30-50%, aggiungi sostanza e dettaglio. Non riempire di banalità.",
    "formal":        "Rendi più formale, istituzionale, registro alto. Evita colloquialismi.",
    "warm":          "Rendi più caloroso, personale, umano. Aggiungi empatia e prossimità.",
    "direct":        "Rendi più diretto, asciutto. Vai al sodo, taglia il preambolo.",
    "soft":          "Rendi più morbido, meno assertivo. Aggiungi cautele linguistiche.",
    "intimate":      "Rendi più confidenziale e intimo. Tono da relazione personale.",
    "visionary":     "Rendi più visionario, narrativo. Costruisci immagini.",
    "translate_en":  "Traduci in inglese mantenendo registro e tono.",
    "translate_fr":  "Traduci in francese mantenendo registro e tono.",
    "fix_grammar":   "Correggi grammatica, ortografia, punteggiatura. NIENTE altre modifiche.",
    "simplify":      "Semplifica linguaggio: rendi accessibile a un lettore non esperto.",
    "fundraiser":    ("Riscrivi nello stile di un fundraiser senior: gancio specifico sul destinatario (un fatto concreto), "
                      "ponte verso la causa, UNA richiesta chiara, chiusura breve e umana. "
                      "Vietate le formule da mailing automatico: 'Mi permetto di scriverLe', 'Spero che questa email La trovi bene', "
                      "'Siamo un'associazione che…', superlativi vuoti e burocratese. Specifico e mai banale."),
}


def _short_summary(prospect: dict) -> str:
    parts = [prospect.get("full_name", "")]
    if prospect.get("role"): parts.append(prospect["role"])
    if prospect.get("company"): parts.append(prospect["company"])
    if prospect.get("headline"): parts.append(prospect["headline"])
    if prospect.get("ai_summary"): parts.append(prospect["ai_summary"][:300])
    return " · ".join(p for p in parts if p)


def edit_text(text: str, action: str, prospect: dict | None = None) -> dict:
    org_ctx = build_context()
    action_desc = EDIT_ACTIONS.get(action, action)
    prompt = prompts.EDIT_ACTION_PROMPT.format(
        org_context=org_ctx,
        prospect_summary=_short_summary(prospect or {}),
        text=text or "",
        action_desc=action_desc,
    )
    result = run_claude(prompt, timeout=120, usage_kind="edit", allowed_tools=[])
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    out = (result.get("text") or "").strip()
    # strip code fences if present
    if out.startswith("```"):
        out = out.split("\n", 1)[-1]
        if out.endswith("```"):
            out = out.rsplit("```", 1)[0]
        out = out.strip()
    return {"ok": True, "text": out}


def generate_subjects(body: str, prospect: dict | None = None, n: int = 5) -> dict:
    org_ctx = build_context()
    prompt = prompts.GENERATE_SUBJECTS_PROMPT.format(
        org_context=org_ctx,
        body=body or "",
        prospect_summary=_short_summary(prospect or {}),
        n=n,
    )
    result = run_claude(prompt, timeout=90, usage_kind="subjects", allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    return {"ok": True, "subjects": data.get("subjects") or []}


def continue_writing(text: str, prospect: dict | None = None) -> dict:
    org_ctx = build_context()
    prompt = prompts.CONTINUE_WRITING_PROMPT.format(
        org_context=org_ctx,
        prospect_summary=_short_summary(prospect or {}),
        text=text or "",
    )
    result = run_claude(prompt, timeout=60, usage_kind="continue", allowed_tools=[])
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    return {"ok": True, "text": (result.get("text") or "").strip()}


# ===================================================================
#                  BRIEFING
# ===================================================================

def briefing(prospect: dict) -> dict:
    import json as _json
    org_ctx = build_context()
    prompt = prompts.BRIEFING_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(prospect, ensure_ascii=False, default=str),
    )
    result = run_claude(prompt, timeout=180, usage_kind="briefing", prospect_id=prospect.get("id"),
                        allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    if not data:
        return {"ok": False, "error": "JSON non parsabile"}
    return {"ok": True, "data": data}


# ===================================================================
#                  ASK suggerito con motivazione
# ===================================================================

def suggest_ask(prospect: dict) -> dict:
    """Propone importo ask + range + motivazione. Salva su prospects. Returns {ok, ...}."""
    import json as _json
    org_ctx = build_context()
    prompt = prompts.SUGGEST_ASK_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(prospect, ensure_ascii=False, default=str),
    )
    result = run_claude(prompt, timeout=150, usage_kind="suggest_ask", prospect_id=prospect.get("id"),
                        allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    ask = _norm_int(data.get("ask_eur"))
    if not ask:
        return {"ok": False, "error": "Claude non ha restituito un importo valido."}
    low = _norm_int(data.get("ask_low_eur"))
    high = _norm_int(data.get("ask_high_eur"))
    rationale = _norm_str(data.get("rationale"))
    pid = prospect.get("id")
    if pid:
        with cursor() as conn:
            conn.execute(
                "UPDATE prospects SET suggested_ask_eur=?, suggested_ask_low_eur=?, suggested_ask_high_eur=?, "
                "ask_rationale=?, ask_suggested_at=CURRENT_TIMESTAMP WHERE id=?",
                (ask, low, high, rationale, pid),
            )
            conn.execute(
                "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
                (pid, "ai_research", f"Ask suggerito: € {ask:,}".replace(",", "."), rationale or ""),
            )
    return {"ok": True, "ask_eur": ask, "ask_low_eur": low, "ask_high_eur": high,
            "rationale": rationale, "confidence": _norm_str(data.get("confidence"))}


# ===================================================================
#                  CHAT
# ===================================================================

def chat_message(prospect: dict, message: str, history: list[dict]) -> dict:
    import json as _json
    org_ctx = build_context()
    hist_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in (history or [])[-10:])
    prompt = prompts.CHAT_PROSPECT_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(enrich_prospect_context(prospect), ensure_ascii=False, default=str),
        history=hist_text or "(nessuna)",
        message=message,
    )
    result = run_claude(prompt, timeout=120, usage_kind="chat", prospect_id=prospect.get("id"),
                        allowed_tools=[])
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    return {"ok": True, "text": (result.get("text") or "").strip()}


# ===================================================================
#                  SEQUENCE
# ===================================================================

def _run_sequence_job(job_id: int, prospect_id: int, goal: str, n_steps: int):
    """Async runner: genera la sequence, persiste, marca il job done.

    Schema research_jobs riusato. Quando finito, raw_output contiene JSON con seq_id.
    """
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (prospect_id,)).fetchone()
    if not row:
        with cursor() as conn:
            conn.execute("UPDATE research_jobs SET status='error', error='Prospect non trovato', finished_at=CURRENT_TIMESTAMP WHERE id=?", (job_id,))
        return
    prospect = dict(row)

    with cursor() as conn:
        conn.execute("UPDATE research_jobs SET status='running' WHERE id=?", (job_id,))

    result = generate_sequence(prospect, goal, n_steps=n_steps)
    if not result.get("ok"):
        with cursor() as conn:
            conn.execute(
                "UPDATE research_jobs SET status='error', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
                (result.get("error") or "errore", job_id),
            )
        return

    with cursor() as conn:
        cur = conn.execute(
            "INSERT INTO sequences(prospect_id, name, goal, status) VALUES (?,?,?, 'draft')",
            (prospect_id, result.get("name") or "Sequence", goal),
        )
        seq_id = cur.lastrowid
        for s in result["steps"]:
            conn.execute(
                """INSERT INTO sequence_steps(sequence_id, step_index, delay_days, purpose, subject, body)
                   VALUES (?,?,?,?,?,?)""",
                (
                    seq_id,
                    int(s.get("step_index") or 0),
                    int(s.get("delay_days") or 0),
                    s.get("purpose"),
                    s.get("subject"),
                    s.get("body"),
                ),
            )
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "ai_research", f"Sequence creata: {result.get('name')}", f"{len(result['steps'])} step · goal: {goal}"),
        )
        conn.execute(
            "UPDATE research_jobs SET status='done', finished_at=CURRENT_TIMESTAMP, raw_output=? WHERE id=?",
            (json.dumps({"seq_id": seq_id, "name": result.get("name"), "steps_count": len(result["steps"])}, ensure_ascii=False), job_id),
        )


def start_sequence_job(prospect_id: int, goal: str, n_steps: int) -> int:
    """Lancia generate_sequence in background. Ritorna research_jobs.id da pollare."""
    with cursor() as conn:
        cur = conn.execute(
            "INSERT INTO research_jobs(prospect_id, query, status) VALUES (?,?, 'pending')",
            (prospect_id, json.dumps({"kind": "sequence", "goal": goal, "n_steps": n_steps})),
        )
        job_id = cur.lastrowid
    _JOB_POOL.submit(_job_guard, _run_sequence_job, job_id, prospect_id, goal, n_steps)
    return job_id


def generate_sequence(prospect: dict, goal: str, n_steps: int = 4) -> dict:
    import json as _json
    org_ctx = build_context()
    prompt = prompts.SEQUENCE_GENERATE_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(prospect, ensure_ascii=False, default=str),
        goal=goal,
        n_steps=n_steps,
    )
    result = run_claude(prompt, timeout=240, usage_kind="sequence", prospect_id=prospect.get("id"),
                        allowed_tools=[], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    steps = data.get("steps") or []
    if not steps:
        return {"ok": False, "error": "Nessuno step generato"}
    return {"ok": True, "name": data.get("name") or "Sequence", "steps": steps}


# ===================================================================
#                  DEEP DIVE — ricerca mirata per sezione
# ===================================================================

DEEP_DIVE_SECTIONS = ("wealth", "network", "giving", "affiliations")


def deep_dive_section(prospect_id: int, section: str) -> dict:
    """Esegue ricerca AI mirata su una singola sezione e merge dei risultati nel CRM.
    NON tocca il resto del profilo.
    """
    if section not in DEEP_DIVE_SECTIONS:
        return {"ok": False, "error": f"Sezione non valida: {section}"}

    import json as _json
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (prospect_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "Prospect non trovato"}
    p = dict(row)

    org_ctx = build_context()
    prompt = prompts.DEEP_DIVE_PROMPT.format(
        org_context=org_ctx,
        profile_json=_json.dumps(p, ensure_ascii=False, default=str),
        section=section,
        instructions=prompts.DEEP_DIVE_INSTRUCTIONS[section],
    )
    result = run_claude(prompt, timeout=400, usage_kind="deep_dive", prospect_id=prospect_id, repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    if not data:
        return {"ok": False, "error": "JSON non parsabile"}

    items = data.get("items") or []
    new_sources = data.get("sources") or []

    with cursor() as conn:
        added = 0
        if section == "wealth":
            for w in items:
                conn.execute(
                    "INSERT INTO wealth_indicators(prospect_id,category,label,detail,value_eur,source,confidence,origin) VALUES (?,?,?,?,?,?,?,'deep_dive')",
                    (
                        prospect_id,
                        _norm_str(w.get("category")),
                        _norm_str(w.get("label")) or "—",
                        _norm_str(w.get("detail")),
                        _norm_int(w.get("value_eur")),
                        _norm_str(w.get("source")),
                        _norm_str(w.get("confidence")) or "medium",
                    ),
                )
                added += 1
            net = _norm_str(data.get("estimated_net_worth"))
            cap = _norm_int(data.get("capacity_rating"))
            if net or cap is not None:
                conn.execute(
                    "UPDATE prospects SET estimated_net_worth=COALESCE(?, estimated_net_worth), capacity_rating=COALESCE(?, capacity_rating), updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (net, cap, prospect_id),
                )
        elif section == "network":
            for c in items:
                conn.execute(
                    "INSERT INTO connections(prospect_id,name,relationship,context,strength,origin) VALUES (?,?,?,?,?,'deep_dive')",
                    (
                        prospect_id,
                        _norm_str(c.get("name")) or "—",
                        _norm_str(c.get("relationship")),
                        _norm_str(c.get("context")),
                        _norm_str(c.get("strength")) or "medium",
                    ),
                )
                added += 1
        elif section == "giving":
            for g in items:
                conn.execute(
                    "INSERT INTO giving_history(prospect_id,organization,year,amount_eur,cause,source,notes,origin) VALUES (?,?,?,?,?,?,?,'deep_dive')",
                    (
                        prospect_id,
                        _norm_str(g.get("organization")),
                        _norm_int(g.get("year")),
                        _norm_int(g.get("amount_eur")),
                        _norm_str(g.get("cause")),
                        _norm_str(g.get("source")),
                        _norm_str(g.get("notes")),
                    ),
                )
                added += 1
            prop = _norm_int(data.get("propensity_score"))
            if prop is not None:
                conn.execute("UPDATE prospects SET propensity_score=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (prop, prospect_id))
        elif section == "affiliations":
            for a in items:
                conn.execute(
                    "INSERT INTO affiliations(prospect_id,organization,role,period,type,source,origin) VALUES (?,?,?,?,?,?,'deep_dive')",
                    (
                        prospect_id,
                        _norm_str(a.get("organization")) or "—",
                        _norm_str(a.get("role")),
                        _norm_str(a.get("period")),
                        _norm_str(a.get("type")),
                        _norm_str(a.get("source")),
                    ),
                )
                added += 1

        # append nuove fonti
        for s in new_sources:
            url = _norm_str(s.get("url"))
            if not url:
                continue
            existing = conn.execute("SELECT id FROM sources WHERE prospect_id=? AND url=?", (prospect_id, url)).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO sources(prospect_id,url,title,snippet,origin) VALUES (?,?,?,?,'deep_dive')",
                (prospect_id, url, _norm_str(s.get("title")), _norm_str(s.get("snippet"))),
            )

        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "ai_research", f"Deep dive: {section}", data.get("note") or f"{added} nuovi record"),
        )

    if section in ("network",):
        auto_link_connections(prospect_id)

    return {"ok": True, "section": section, "added": added, "note": data.get("note"), "sources_added": len(new_sources)}


# ===================================================================
#                  NEWS — ricerca menzioni recenti
# ===================================================================

def fetch_news(prospect_id: int) -> dict:
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (prospect_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "Prospect non trovato"}
    p = dict(row)

    org_ctx = build_context()
    prompt = prompts.NEWS_SEARCH_PROMPT.format(
        org_context=org_ctx,
        full_name=p.get("full_name") or "",
        ptype=p.get("type") or "individual",
        company=p.get("company") or p.get("website") or "",
        country=p.get("country") or "",
    )
    result = run_claude(prompt, timeout=240, usage_kind="news", prospect_id=prospect_id, repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    items = data.get("items") or []

    added = 0
    with cursor() as conn:
        for it in items:
            url = _norm_str(it.get("url"))
            if not url:
                continue
            exists = conn.execute("SELECT id FROM news_items WHERE prospect_id=? AND url=?", (prospect_id, url)).fetchone()
            if exists:
                continue
            signal = (_norm_str(it.get("signal")) or "neutral").lower()
            if signal not in ("opportunity", "neutral", "risk"):
                signal = "neutral"
            conn.execute(
                """INSERT INTO news_items(prospect_id,title,url,publisher,snippet,published_at,relevance,sentiment,signal,signal_note)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    prospect_id,
                    _norm_str(it.get("title")),
                    url,
                    _norm_str(it.get("publisher")),
                    _norm_str(it.get("snippet")),
                    _norm_str(it.get("published_at")),
                    _norm_str(it.get("relevance")) or "medium",
                    _norm_str(it.get("sentiment")) or "neutral",
                    signal,
                    _norm_str(it.get("signal_note")),
                ),
            )
            added += 1
        conn.execute(
            "INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
            (prospect_id, "ai_research", f"News fetch: {added} nuove menzioni", ""),
        )
    return {"ok": True, "added": added, "total_items": len(items)}


# ===================================================================
#                  VERIFICA FONTI — HTTP HEAD/GET
# ===================================================================

# Codici "la pagina esiste ma accesso limitato" (paywall, anti-bot, rate-limit):
# NON sono fonti rotte → verified=2 (giallo), non -1 (rosso).
_VERIFY_RESTRICTED = {401, 403, 429, 451, 999}


def _check_source_url(url: str) -> tuple:
    """Ritorna (state, http_status, note). state: 1 OK, 2 ristretto, -1 KO. Nessun accesso DB."""
    import requests
    if not url or not url.startswith(("http://", "https://")):
        return (-1, None, "URL non valido")
    headers = {"User-Agent": "Mozilla/5.0 (Forager CRM source verifier)", "Accept": "*/*"}
    status = None
    try:
        resp = requests.head(url, allow_redirects=True, timeout=8, headers=headers)
        status = resp.status_code
        if status == 405 or status >= 400:
            resp = requests.get(url, allow_redirects=True, timeout=10, headers=headers, stream=True)
            status = resp.status_code
            resp.close()
        if 200 <= status < 400:
            return (1, status, None)
        if status in _VERIFY_RESTRICTED:
            return (2, status, f"accesso con restrizioni (HTTP {status}) — la pagina esiste")
        return (-1, status, f"HTTP {status}")
    except requests.exceptions.Timeout:
        return (-1, status, "timeout")
    except requests.exceptions.SSLError:
        return (-1, status, "SSL error")
    except requests.exceptions.ConnectionError:
        return (-1, status, "connessione fallita")
    except Exception as e:
        return (-1, status, str(e)[:200])


def verify_sources(prospect_id: int, force: bool = False) -> dict:
    """Controlla raggiungibilità HTTP delle fonti. Salta quelle già verificate OK negli
    ultimi 7 giorni (force=True le ricontrolla tutte). Controlli in parallelo, scrittura
    in un'unica transazione."""
    from datetime import datetime, timedelta
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    with cursor() as conn:
        rows = rows_to_dicts(conn.execute(
            "SELECT id, url, verified, verified_at FROM sources WHERE prospect_id=?",
            (prospect_id,),
        ).fetchall())
    if not rows:
        _log_usage("verify", prospect_id, int((time.time()-t0)*1000), None, None, None, True, notes="0 fonti")
        return {"ok": True, "checked": 0, "ok_count": 0, "ko_count": 0, "restricted_count": 0, "skipped": 0}

    fresh_cutoff = datetime.utcnow() - timedelta(days=7)

    def _is_fresh_ok(r):
        if force or r.get("verified") != 1 or not r.get("verified_at"):
            return False
        try:
            ts = datetime.fromisoformat(str(r["verified_at"]).replace(" ", "T"))
        except Exception:
            return False
        return ts > fresh_cutoff

    to_check = [r for r in rows if not _is_fresh_ok(r)]
    skipped = len(rows) - len(to_check)

    results = {}
    if to_check:
        with ThreadPoolExecutor(max_workers=min(8, len(to_check))) as ex:
            futs = {ex.submit(_check_source_url, r["url"]): r["id"] for r in to_check}
            for fut in futs:
                rid = futs[fut]
                try:
                    results[rid] = fut.result()
                except Exception as e:
                    results[rid] = (-1, None, str(e)[:200])

    ok_n = ko_n = restricted_n = 0
    with cursor() as conn:
        for rid, (state, status, note) in results.items():
            conn.execute(
                "UPDATE sources SET verified=?, verified_at=CURRENT_TIMESTAMP, http_status=?, verification_note=? WHERE id=?",
                (state, status, note, rid),
            )
            if state == 1:
                ok_n += 1
            elif state == 2:
                restricted_n += 1
            else:
                ko_n += 1
    # le fonti saltate erano già OK: contiamole tra gli OK per il messaggio
    ok_n += skipped

    _log_usage("verify", prospect_id, int((time.time()-t0)*1000), None, None, None, True,
               notes=f"{ok_n} ok ({skipped} saltate), {restricted_n} restricted, {ko_n} ko")
    return {"ok": True, "checked": len(to_check), "ok_count": ok_n, "ko_count": ko_n,
            "restricted_count": restricted_n, "skipped": skipped}


# ===================================================================
#                  GROUNDING — verifica del DATO nel contenuto
# ===================================================================

def ground_sources(prospect_id: int, max_sources: int = 8) -> dict:
    """Apre le fonti con WebFetch e verifica se SUPPORTANO davvero le affermazioni chiave
    del profilo (non solo se l'URL risponde). Aggiorna sources.grounded/grounding_note.
    È il guardrail che separa un dossier difendibile da un generatore di numeri plausibili."""
    import json as _json
    with cursor() as conn:
        row = conn.execute("SELECT * FROM prospects WHERE id=?", (prospect_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "Prospect non trovato"}
        p = dict(row)
        srcs = rows_to_dicts(conn.execute(
            "SELECT id, url, title FROM sources WHERE prospect_id=? AND url LIKE 'http%' ORDER BY id LIMIT ?",
            (prospect_id, max_sources),
        ).fetchall())
        wealth = rows_to_dicts(conn.execute(
            "SELECT label, detail, value_eur FROM wealth_indicators WHERE prospect_id=? ORDER BY value_eur DESC NULLS LAST LIMIT 6",
            (prospect_id,),
        ).fetchall())
        giving = rows_to_dicts(conn.execute(
            "SELECT organization, amount_eur, year FROM giving_history WHERE prospect_id=? LIMIT 6",
            (prospect_id,),
        ).fetchall())
    if not srcs:
        return {"ok": False, "error": "Nessuna fonte con URL da verificare."}

    claims = []
    if p.get("ai_summary"):
        claims.append("Sintesi: " + p["ai_summary"])
    if p.get("estimated_net_worth"):
        claims.append("Patrimonio stimato: " + str(p["estimated_net_worth"]))
    for w in wealth:
        claims.append("Wealth: " + " ".join(str(x) for x in [w.get("label"), w.get("detail"), w.get("value_eur")] if x))
    for g in giving:
        claims.append("Donazione: " + " ".join(str(x) for x in [g.get("organization"), g.get("amount_eur"), g.get("year")] if x))
    claims_block = "\n".join(f"- {c}" for c in claims) or "- (nessuna affermazione strutturata)"
    sources_block = "\n".join(f"- {s['url']}" + (f"  ({s['title']})" if s.get("title") else "") for s in srcs)

    org_ctx = build_context()
    prompt = prompts.GROUND_SOURCES_PROMPT.format(org_context=org_ctx, claims=claims_block, sources_list=sources_block)
    result = run_claude(prompt, timeout=400, usage_kind="ground", prospect_id=prospect_id,
                        allowed_tools=["WebFetch", "WebSearch"], repair_json=True)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error")}
    data = result.get("json") or {}
    items = data.get("sources") or []
    by_url = {(_norm_str(it.get("url")) or "").strip().rstrip("/"): it for it in items}

    sup = con = nf = 0
    with cursor() as conn:
        for s in srcs:
            it = by_url.get((s["url"] or "").strip().rstrip("/"))
            if not it:
                continue
            status = (_norm_str(it.get("status")) or "not_found").lower()
            if status not in ("supported", "not_found", "contradicted"):
                status = "not_found"
            conn.execute("UPDATE sources SET grounded=?, grounding_note=? WHERE id=?",
                         (status, _norm_str(it.get("note")), s["id"]))
            if status == "supported":
                sup += 1
            elif status == "contradicted":
                con += 1
            else:
                nf += 1
        conn.execute("INSERT INTO activities(prospect_id,type,title,body) VALUES (?,?,?,?)",
                     (prospect_id, "ai_research", "Grounding fonti",
                      data.get("summary") or f"{sup} confermano, {con} contraddicono, {nf} non trovano"))
    return {"ok": True, "checked": len(srcs), "supported": sup, "contradicted": con,
            "not_found": nf, "summary": data.get("summary")}
