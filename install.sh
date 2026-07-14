#!/usr/bin/env bash
# Forager — installer one-shot per macOS / Linux
# Uso:
#   ./install.sh               (locale, dalla directory del repo)
#   curl -fsSL https://raw.githubusercontent.com/Mic-Fundraiser/forager/main/install.sh | bash
#
# Cosa fa:
#   1. Clona/aggiorna il repo (se invocato via curl|bash)
#   2. Crea venv + installa dipendenze
#   3. Crea .env da .env.example
#   4. Inizializza database
#   5. Stampa istruzioni per partire

set -e

REPO_URL="${FORAGER_REPO:-https://github.com/Mic-Fundraiser/forager.git}"
TARGET_DIR="${FORAGER_DIR:-$HOME/forager}"

C_OK="\033[32m✓\033[0m"
C_ERR="\033[31m✗\033[0m"
C_INFO="\033[36m→\033[0m"
C_WARN="\033[33m⚠\033[0m"
C_BOLD="\033[1m"
C_END="\033[0m"

echo ""
echo -e "${C_BOLD}  Forager · OSINT CRM per Major Donor & Corporate Fundraising${C_END}"
echo ""

# 1. Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${C_ERR} Python 3 non trovato."
  echo "   Installa da https://www.python.org/downloads/  (versione 3.10 o superiore)"
  exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${C_OK} Python ${PY_VER}"

# 2. Check git
if ! command -v git >/dev/null 2>&1; then
  echo -e "${C_WARN} git non trovato — scarica manualmente il codice."
  HAS_GIT=0
else
  HAS_GIT=1
fi

# 3. Clone / pull se chiamato da curl
if [ ! -f "./forager" ] && [ ! -f "./app.py" ]; then
  if [ $HAS_GIT -eq 1 ]; then
    if [ -d "$TARGET_DIR" ]; then
      echo -e "${C_INFO} Aggiorno installazione in ${TARGET_DIR} …"
      cd "$TARGET_DIR"
      git pull -q
    else
      echo -e "${C_INFO} Clono repository in ${TARGET_DIR} …"
      git clone -q "$REPO_URL" "$TARGET_DIR"
      cd "$TARGET_DIR"
    fi
    echo -e "${C_OK} Codice scaricato"
  else
    echo -e "${C_ERR} Niente git e nessun file locale. Scarica lo zip manualmente."
    exit 1
  fi
fi

# 4. venv + deps
if [ ! -d ".venv" ]; then
  echo -e "${C_INFO} Creo virtual environment …"
  python3 -m venv .venv
fi
echo -e "${C_INFO} Installo dipendenze …"
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt
echo -e "${C_OK} Dipendenze installate"

# 5. .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${C_OK} File .env creato"
fi

# 6. DB
./.venv/bin/python -c "import db; db.init_db()"
echo -e "${C_OK} Database inizializzato"

# 7. Claude CLI check
if command -v claude >/dev/null 2>&1; then
  echo -e "${C_OK} Claude CLI trovato"
else
  echo -e "${C_WARN} Claude CLI non installato"
  echo "   Forager usa Claude Code per la ricerca AI. Installa da:"
  echo "   ${C_BOLD}https://docs.claude.com/claude-code${C_END}"
fi

chmod +x ./forager

echo ""
echo -e "${C_BOLD}  Installazione completata. Avvia ora:${C_END}"
echo ""
echo "    cd $(pwd)"
echo "    ./forager start"
echo ""
echo -e "${C_INFO} Il browser si aprirà automaticamente su http://127.0.0.1:5000"
echo ""
