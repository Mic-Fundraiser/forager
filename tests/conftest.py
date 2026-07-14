"""Fixtures: DB temporaneo isolato (mai il crm.db reale) + test client Flask."""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db as dbmod  # noqa: E402

# Patch del path DB PRIMA di importare app (che chiama init_db all'avvio del server,
# ma il test client non esegue __main__: init esplicito qui sotto).
_tmpdir = tempfile.mkdtemp(prefix="forager-test-")
dbmod.DB_PATH = Path(_tmpdir) / "crm.db"
dbmod.BACKUP_DIR = Path(_tmpdir) / "backups"

import app as appmod  # noqa: E402


@pytest.fixture(scope="session")
def flask_app():
    appmod.init_db()
    appmod.app.testing = True
    return appmod.app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()
