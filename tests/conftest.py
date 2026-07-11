"""Shared test configuration.

Environment variables must be set BEFORE any safetyops import: the SQLAlchemy
engine is created at import time from `settings.database_url`, so this module
redirects it to a temporary SQLite database instead of Postgres.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="safetyops-tests-"))
os.environ["SAFETYOPS_DATABASE_URL"] = f"sqlite:///{(_TEST_DB_DIR / 'test.db').as_posix()}"
