"""Test del motore AI intercambiabile (claude / codex)."""
import json
import os

import ai_engine
import config as cfg


def test_parse_codex_jsonl():
    events = [
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "item.completed", "item": {"id": "i1", "type": "reasoning", "text": "penso..."}},
        {"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": '{"ok": true}'}},
        {"type": "turn.completed", "usage": {"input_tokens": 120, "cached_input_tokens": 10, "output_tokens": 34}},
    ]
    raw = "\n".join(json.dumps(e) for e in events) + "\nriga non json\n"
    text, in_tok, out_tok, err = ai_engine._parse_codex_jsonl(raw)
    assert text == '{"ok": true}'
    assert (in_tok, out_tok) == (120, 34)
    assert err is None


def test_parse_codex_jsonl_error():
    raw = json.dumps({"type": "turn.failed", "error": {"message": "stream disconnected"}})
    text, _, _, err = ai_engine._parse_codex_jsonl(raw)
    assert text == ""
    assert "stream disconnected" in err


def test_engine_default_and_switch():
    assert ai_engine.engine() == "claude"
    old = cfg.AI_ENGINE
    try:
        cfg.AI_ENGINE = "codex"
        assert ai_engine.engine() == "codex"
        assert "Codex" in ai_engine.engine_label()
    finally:
        cfg.AI_ENGINE = old


def test_codex_cmd_web_toggle():
    cmd_web = ai_engine._codex_cmd("ciao", None)
    cmd_noweb = ai_engine._codex_cmd("ciao", [])
    assert "exec" in cmd_web and "--json" in cmd_web and cmd_web[-1] == "ciao"
    assert "--search" in cmd_web
    assert "--search" not in cmd_noweb
    assert "--sandbox" in cmd_noweb and "read-only" in cmd_noweb


def test_run_claude_codex_missing_binary():
    """Con engine=codex e binario inesistente: errore amichevole, niente eccezioni."""
    old_engine, old_bin = cfg.AI_ENGINE, ai_engine.CODEX_BIN
    try:
        cfg.AI_ENGINE = "codex"
        ai_engine.CODEX_BIN = "/nonexistent/codex-binary"
        res = ai_engine.run_claude("test", timeout=5)
        assert res["ok"] is False
        assert "Codex" in res["error"]
    finally:
        cfg.AI_ENGINE, ai_engine.CODEX_BIN = old_engine, old_bin


def test_settings_save_engine(flask_app, client, tmp_path, monkeypatch):
    """POST /settings/save con ai_engine=codex scrive FORAGER_AI_ENGINE e aggiorna cfg a caldo."""
    monkeypatch.setenv("FORAGER_DATA_DIR", str(tmp_path))
    old = cfg.AI_ENGINE
    try:
        resp = client.post("/settings/save", data={"ai_engine": "codex"}, follow_redirects=False)
        assert resp.status_code in (302, 303)
        env_text = (tmp_path / ".env").read_text(encoding="utf-8")
        assert "FORAGER_AI_ENGINE=codex" in env_text
        assert cfg.AI_ENGINE == "codex"
        # valore non valido: ignorato
        client.post("/settings/save", data={"ai_engine": "gemini"}, follow_redirects=False)
        assert cfg.AI_ENGINE == "codex"
        # torna a claude
        client.post("/settings/save", data={"ai_engine": "claude"}, follow_redirects=False)
        assert cfg.AI_ENGINE == "claude"
    finally:
        cfg.AI_ENGINE = old
        os.environ.pop("FORAGER_AI_ENGINE", None)
