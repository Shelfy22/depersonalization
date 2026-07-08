.PHONY: install test lint run docker-build docker-up

install:
	python -m pip install -r requirements.txt

test:
	MODEL_ENABLED=false pytest -q

lint:
	ruff check .

run:
	uvicorn app.main:app --host 127.0.0.1 --port 8088

docker-build:
	docker build -t pii-filter-service .

docker-up:
	docker compose up --build
