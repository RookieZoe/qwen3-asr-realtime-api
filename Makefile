.PHONY: help install start stop test docker-build docker-run docker-stop clean

# Default target
help:
	@echo "Qwen3-ASR-Realtime Server - Available Commands:"
	@echo ""
	@echo "  make install       - Install Python dependencies"
	@echo "  make start         - Start the server"
	@echo "  make stop          - Stop the server (if running in background)"
	@echo "  make test          - Run all tests"
	@echo "  make test-basic    - Run basic WebSocket test"
	@echo "  make test-sdk      - Run SDK compatibility test"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run with Docker Compose"
	@echo "  make docker-stop   - Stop Docker containers"
	@echo "  make docker-logs   - View Docker logs"
	@echo "  make clean         - Clean up cache files"
	@echo ""

# Installation
install:
	pip install -r requirements.txt

# Server management
start:
	python main.py

stop:
	-pkill -f "python main.py" 2>/dev/null || true

# Testing
test: test-basic test-sdk

test-basic:
	@echo "Running basic WebSocket test..."
	python tests/test_websocket.py

test-sdk:
	@echo "Running SDK compatibility test..."
	python tests/test_sdk_compatibility.py

test-vad:
	@echo "Running VAD test..."
	python tests/test_vad_asr.py

# Docker
docker-build:
	docker build -t qwen3-asr-realtime:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker rmi qwen3-asr-realtime:latest 2>/dev/null || true

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ 2>/dev/null || true

# Development
dev-setup:
	cp .env.example .env
	@echo "Please edit .env with your configuration"

format:
	@echo "Code formatting not configured. Add black/isort if needed."

lint:
	@echo "Linting not configured. Add flake8/pylint if needed."
