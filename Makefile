SHELL := /bin/bash
PROJECT := contenidos-inacap
PKG := contenidos_inacap

.PHONY: install run-api run-worker format lint precommit docker-up docker-down docker-logs docker-build

install:
\tpoetry install

run-api:
\tpoetry run python -m $(PKG).main_api

run-worker:
\tpoetry run python -m $(PKG).main_worker

format:
\tpoetry run ruff format .
\tpoetry run ruff check . --fix

lint:
\tpoetry run ruff check .

precommit:
\tpoetry run pre-commit install

docker-build:
\tdocker build -t $(PROJECT):latest .

docker-up:
\tdocker compose up --build

docker-down:
\tdocker compose down -v

docker-logs:
\tdocker compose logs -f
