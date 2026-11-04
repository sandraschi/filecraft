default:
    @just --list

test:
    uv run pytest -v

lint:
    uv run ruff check .
