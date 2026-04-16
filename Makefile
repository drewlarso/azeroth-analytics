.PHONY: default fetch

default: main

fetch:
	uv run python -m scripts.fetch_auctions

main:
	uv run python main.py
