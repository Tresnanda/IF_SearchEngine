from pathlib import Path
import sys
import os

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def env_defaults():
    os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")


@pytest.fixture
def admin_headers():
    return {"X-Internal-Admin-Token": os.environ["ADMIN_INTERNAL_TOKEN"]}
