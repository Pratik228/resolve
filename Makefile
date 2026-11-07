.PHONY: up down seed ingest eval eval-fast ablate api web test policy install snapshot report

up:
	docker compose up -d postgres qdrant redis
	@echo "waiting for healthchecks..."
	@sleep 3
	@docker compose ps

down:
	docker compose down

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"

seed:
	python -m resolve.db.seed

ingest:
	python -m resolve.retrieval.ingest

eval:
	PYTHONHASHSEED=0 pytest evals/ -q

eval-fast:
	PYTHONHASHSEED=0 pytest evals/ -m fast -q

ablate:
	PYTHONHASHSEED=0 python -m evals.ablation

snapshot:
	PYTHONHASHSEED=0 python -m evals.snapshot

report:
	python scripts/make_report.py

test:
	PYTHONHASHSEED=0 pytest tests/ -q

api:
	PYTHONPATH=. uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm install && npm run dev -- --hostname 127.0.0.1 --port 3000

policy:
	pytest tests/test_policy_engine.py -q

cli:
	python -m resolve.cli "I was charged twice this month and the API keeps throwing NW-4031. Refund me." --customer cus_014
