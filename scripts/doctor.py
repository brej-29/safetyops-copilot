from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import Optional

from safetyops.core import get_logger, settings

logger = get_logger(__name__)


def _check_python() -> bool:
    major, minor = sys.version_info[:2]
    print(f"[python] Detected Python {major}.{minor} ({sys.executable})")
    if major < 3 or (major == 3 and minor < 10):
        print("  ! Python 3.10+ is required. Please upgrade your Python interpreter.")
        return False
    return True


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        return proc.returncode, proc.stdout.strip()
    except Exception as exc:
        return 1, f"error: {exc}"


def _check_docker() -> None:
    print("[docker] Checking Docker CLI availability...")
    if shutil.which("docker") is None:
        print(
            "  ! Docker CLI not found on PATH. Local infra (`postgres`, `redis`, etc.) "
            "will not start until Docker Desktop (or Docker Engine) is installed."
        )
        return

    code, out = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    if code != 0:
        print(
            "  ! Docker is installed but the daemon may not be running "
            "(or current user lacks permissions)."
        )
        print(f"    Output: {out}")
    else:
        print(f"  ✓ Docker server version: {out}")


def _print_settings() -> None:
    print("[config] Effective SafetyOps settings:")
    print(f"  ENV:              {settings.env}")
    print(f"  DEPLOY_MODE:      {settings.deploy_mode}")
    print(f"  REDIS_URL:        {settings.redis_url}")
    print(f"  DATABASE_URL:     {settings.database_url}")
    print(f"  ARTIFACTS_DIR:    {settings.artifacts_dir}")
    print(f"  NLP_MODEL_DIR:    {settings.nlp_model_dir}")
    print(f"  VISION_MODEL:     {settings.vision_model_path}")
    print(f"  METRICS_NAMESPACE:{settings.metrics_namespace}")

    if settings.database_url.startswith("postgresql"):
        print(
            "  note: Using Postgres. For quick local demos without Docker/Postgres, "
            "you can instead set SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db"
        )
    elif settings.database_url.startswith("sqlite"):
        print("  note: Using SQLite; this is suitable for local demos but not production.")


def _check_redis() -> None:
    print("[redis] Checking Redis connectivity...")
    try:
        import redis  # type: ignore[import]
    except Exception:
        print("  ! redis Python package not installed. Run `pip install -r requirements.txt`.")
        return

    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        print(f"  ✓ Connected to Redis at {settings.redis_url}")
    except Exception as exc:
        print(
            "  ! Could not connect to Redis. Ensure Docker is running and "
            "the `redis` service from infra/docker-compose.local.yml is up."
        )
        print(f"    Details: {exc}")


def _check_database() -> None:
    print("[database] Checking database connectivity...")
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    from safetyops.db.session import get_engine

    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"  ✓ Connected to database at {settings.database_url}")
    except SQLAlchemyError as exc:
        print(
            "  ! Could not connect to the database. If you are running locally with "
            "Docker, ensure the `postgres` service is up. For a Docker-free demo, "
            "consider setting SAFETYOPS_DATABASE_URL=sqlite:///./safetyops.db."
        )
        print(f"    Details: {exc}")


def main() -> None:
    print("SafetyOps Copilot - environment doctor")
    print(f"Platform: {platform.system()} {platform.release()}")
    print("-" * 60)

    ok_python = _check_python()
    print("-" * 60)
    _print_settings()
    print("-" * 60)
    _check_docker()
    print("-" * 60)
    _check_redis()
    print("-" * 60)
    _check_database()
    print("-" * 60)

    if not ok_python:
        print("One or more critical checks failed. Please address the items marked with '!'.")
    else:
        print("Doctor completed. Review any warnings above before running the system.")


if __name__ == "__main__":
    main()