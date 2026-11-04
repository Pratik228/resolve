.PHONY: up down seed ingest eval eval-fast ablate api web test policy install

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
	pytest evals/ -q

eval-fast:
	pytest evals/ -m fast -q

ablate:
	python -m evals.ablation

api:
	PYTHONPATH=. uvicorn apps.api.main:app --reload --port 8000

web:
	cd apps/web && npm install && npm run dev -- --port 3001

test:
	pytest tests/ evals/test_policy.py -q

policy:
	pytest tests/test_policy_engine.py -q

cli:
	python -m resolve.cli "I was charged twice this month and the API keeps throwing NW-4031. Refund me." --customer cus_014
