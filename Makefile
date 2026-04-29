.PHONY: fetch-auctions fetch-static pull database tui

default: tui

fetch-auctions:
	uv run python -m scripts.fetch_auctions

fetch-static:
	uv run python -m scripts.fetch_static

pull:
	uv run python -m scripts.pull_to_local_db

database:
	uv run python -m scripts.create_database
	duckdb azeroth.db

tui:
	uv run python main.py
