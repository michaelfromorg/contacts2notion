.PHONY: help run auth sync sync-google sync-notion init-schema status check format typecheck test clean

help:
	@echo "Available commands:"
	@echo "  make run            - Show CLI help"
	@echo "  make auth           - Authorize with Google (get refresh token)"
	@echo "  make sync           - 2-way sync (Google ↔ Notion)"
	@echo "  make sync-google    - One-way sync (Google → Notion only)"
	@echo "  make sync-notion    - One-way sync (Notion → Google only)"
	@echo "  make init-schema    - Initialize Notion database schema"
	@echo "  make status         - Show database status"
	@echo "  make check          - Run linter (ruff)"
	@echo "  make format         - Format code (ruff)"
	@echo "  make typecheck      - Run type checker (ty)"
	@echo "  make test           - Run tests"

# CLI commands
run:
	@uv run contacts2notion --help

auth:
	@uv run contacts2notion auth

sync:
	@uv run contacts2notion sync

sync-google:
	@uv run contacts2notion sync --google-only

sync-notion:
	@uv run contacts2notion sync --notion-only

init-schema:
	@uv run contacts2notion init-schema

status:
	@uv run contacts2notion status

# Development commands
check:
	@uv run ruff check src tests

format:
	@uv run ruff format src tests

typecheck:
	@uvx ty check src

test:
	@uv run pytest

clean:
	rm -rf .ruff_cache .pytest_cache __pycache__ dist build *.egg-info .venv
