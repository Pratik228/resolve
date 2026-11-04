import pytest

from resolve.db.seed import seed
from resolve.retrieval.ingest import ingest


@pytest.fixture(scope="session", autouse=True)
def northwind():
    seed()
    ingest()
