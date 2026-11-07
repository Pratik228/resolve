import pytest

from resolve.db.seed import seed
from resolve.retrieval.ingest import ingest


@pytest.fixture(scope="session", autouse=True)
def northwind():
    seed()
    ingest()


@pytest.fixture(autouse=True)
def clean_ledger():
    from resolve.db.seed import reset_ledger

    reset_ledger()
    yield
