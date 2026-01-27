.PHONY: install lint test up down format

install:
\tpython -m pip install --upgrade pip
\tpip install -r requirements-dev.txt

lint:
	ruff check .

test:
\tpytest

up:
\tdocker compose -f infra/docker-compose.local.yml up -d

down:
\tdocker compose -f infra/docker-compose.local.yml down

format:
	ruff check --fix .