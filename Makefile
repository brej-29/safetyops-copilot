.PHONY: install lint test up down format

install:
\tpython -m pip install --upgrade pip
\tpip install -r requirements-dev.txt

lint:
\truff .

test:
\tpytest

up:
\tdocker compose -f infra/docker-compose.local.yml up -d

down:
\tdocker compose -f infra/docker-compose.local.yml down

format:
\truff --fix .