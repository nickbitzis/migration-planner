PORT ?= 8821

.PHONY: install test lint format run plan estate screenshot docker-build clean

install:
	uv sync --python 3.12

test:
	uv run --python 3.12 --group dev pytest -q

lint:
	uvx ruff check .

format:
	uvx ruff format .
	uvx ruff check . --fix

run:
	PORT=$(PORT) MIGPLAN_OVERRIDES=data/overrides.json uv run migplan serve

plan:  ## full plan on the sample estate: reports/waves.csv, reports/migration-plan.md, reports/plan.json
	uv run migplan plan --out reports --gate

estate:  ## write the synthetic inventory, servers, and flows as CSV to data/
	uv run migplan estate --out data

screenshot:  ## needs the server running on $(PORT) and Google Chrome installed (macOS path)
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
		--virtual-time-budget=10000 --window-size=1440,1100 --screenshot=docs/screenshot.png http://127.0.0.1:$(PORT)/

docker-build:
	docker build -t migration-planner .

clean:
	rm -rf .pytest_cache .ruff_cache
