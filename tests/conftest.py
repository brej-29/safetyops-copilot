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

# Keep tests deterministic and fast regardless of locally trained/downloaded
# models: point model paths at nonexistent locations so inference always uses
# the rule-based classifier and stub PPE predictions.
os.environ["SAFETYOPS_NLP_MODEL_DIR"] = str(_TEST_DB_DIR / "no-nlp-model")
os.environ["SAFETYOPS_VISION_MODEL_PATH"] = str(_TEST_DB_DIR / "no-vision-model.pt")

# Never let tests call a real LLM endpoint, even if the developer's .env
# configures one (nondeterministic output, external quota, network).
os.environ["SAFETYOPS_LLM_BASE_URL"] = ""
os.environ["SAFETYOPS_LLM_API_KEY"] = ""
os.environ["SAFETYOPS_LLM_MODEL"] = ""
os.environ["SAFETYOPS_OLLAMA_BASE_URL"] = ""
os.environ["SAFETYOPS_OLLAMA_MODEL"] = ""
