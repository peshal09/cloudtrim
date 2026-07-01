# CloudTrim — developer tasks
# Packages are imported via PYTHONPATH (scaffold; no editable install yet).
PYTHONPATH := apps/api:apps/worker:packages/engine:packages/ai
export PYTHONPATH

.PHONY: install lint format test run eval web-install web-dev

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

test:
	pytest

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

eval:
	python eval/run_eval.py

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev
