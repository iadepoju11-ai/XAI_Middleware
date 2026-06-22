"""
Shared pytest fixtures and environment bootstrap.

IMPORTANT: DATABASE_URL and KAFKA_ENABLED must be set before any backend
module is imported, because audit_logger.py creates the SQLAlchemy engine at
module level (when the module is first imported).  This file is loaded by
pytest before any test modules, so the os.environ assignments below run first.
"""
import os
import sys
import tempfile

# Point at a separate SQLite file so tests never touch the production audit.db
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix="_test_audit.db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["KAFKA_ENABLED"] = "false"

# Add backend/ to sys.path so `import app`, `import audit_logger`, etc. work
_BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import pytest


@pytest.fixture(scope="session")
def flask_client():
    """Session-scoped Flask test client — models loaded once per test run."""
    import app as flask_app_module
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        yield client


@pytest.fixture(scope="session")
def sample_payload():
    """Canonical valid scoring request used across multiple tests."""
    return {
        "credit_amount": 5000,
        "duration": 12,
        "age": 30,
        "purpose": "car",
        "employment": "2",
        "installment_commitment": 3,
        "existing_credits": 1,
        "sex": 0,
    }


def _make_decision(decision="accept", sex=0):
    """Helper: build a minimal decision dict for compliance tests."""
    return {
        "decision": decision,
        "probability": 0.75 if decision == "accept" else 0.25,
        "input_features": {"sex": sex},
    }


@pytest.fixture
def balanced_decisions():
    """20 decisions: equal accept rates for sex=0 and sex=1."""
    decisions = []
    for i in range(20):
        decisions.append(_make_decision("accept", sex=i % 2))
    return decisions


@pytest.fixture
def biased_decisions():
    """20 decisions: all sex=0 (female) denied, all sex=1 (male) accepted."""
    decisions = []
    for _ in range(10):
        decisions.append(_make_decision("deny", sex=0))
    for _ in range(10):
        decisions.append(_make_decision("accept", sex=1))
    return decisions
