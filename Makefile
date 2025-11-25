.PHONY: help install run test test-cov docker-test docker-test-cov lint format clean docker-build docker-up docker-down migrate-up migrate-down migrate-create migrate-status migrate-history

# Default target
help:
	@echo "QnA Agent API - Available Commands"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start application"
	@echo "  make docker-test      Run tests"
	@echo "  make docker-test-cov  Run tests with coverage"
	@echo ""
	@echo "Database:"
	@echo "  make docker-migrate   Run database migrations"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start services with docker-compose"
	@echo "  make docker-down      Stop services"
	@echo "  make docker-logs      View docker logs"
	@echo "  make docker-migrate   Run migrations in Docker container"
	@echo ""
	@echo "Kubernetes (Docker Desktop):"
	@echo "  make k8s-full-deploy  Complete setup: check k8s, build, deploy"
	@echo "  make k8s-start        Check Kubernetes status"
	@echo "  make k8s-build        Build Docker image"
	@echo "  make k8s-deploy       Deploy to Kubernetes"
	@echo "  make k8s-port-forward Forward service to localhost:8000"
	@echo "  make k8s-migrate      Run migrations in Kubernetes"
	@echo "  make k8s-logs         View pod logs"
	@echo "  make k8s-status       Show Kubernetes resources"
	@echo "  make k8s-delete       Delete all resources"
	@echo "  make k8s-stop         Info about stopping Kubernetes"
	@echo "  make k8s-clean        Delete all resources"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove cache and temporary files"

# Setup & Development
install:
	poetry install

run:
	poetry run python src/main.py

test:
	poetry run pytest

test-cov:
	poetry run pytest --cov=src --cov-report=html --cov-report=term

docker-test:
	@echo "Building Docker image if needed..."
	@docker build -t qna-agent-api . > /dev/null 2>&1 || docker build -t qna-agent-api .
	@echo "Running tests in Docker..."
	docker-compose run --rm qna-agent-api sh -c "cd /app && poetry install --no-interaction --no-root --with dev && poetry run pytest"

docker-test-cov:
	@echo "Building Docker image if needed..."
	@docker build -t qna-agent-api . > /dev/null 2>&1 || docker build -t qna-agent-api .
	@echo "Running tests with coverage in Docker..."
	docker-compose run --rm qna-agent-api sh -c "cd /app && poetry install --no-interaction --no-root --with dev && poetry run pytest --cov=src --cov-report=html --cov-report=term"

# Code Quality
lint:
	poetry run ruff check src/
	poetry run mypy src/

format:
	poetry run black src/ tests/
	poetry run ruff check --fix src/

type-check:
	poetry run mypy src/

# Database Migrations
migrate-up:
	@echo "Applying database migrations..."
	poetry run alembic upgrade head
	@echo "✓ Migrations applied successfully"

migrate-down:
	@echo "Rolling back last migration..."
	poetry run alembic downgrade -1
	@echo "✓ Rollback completed"

migrate-status:
	@echo "Current migration status:"
	poetry run alembic current

migrate-history:
	@echo "Migration history:"
	poetry run alembic history --verbose

migrate-create:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG parameter required"; \
		echo "Usage: make migrate-create MSG=\"description of changes\""; \
		exit 1; \
	fi
	@echo "Creating new migration: $(MSG)"
	poetry run alembic revision --autogenerate -m "$(MSG)"
	@echo "✓ Migration created successfully"

# Docker
docker-build:
	docker build -t qna-agent-api .

docker-up:
	docker-compose up -d
	@echo "✓ Services started. View logs with: make docker-logs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-migrate:
	@echo "Running migrations in Docker container..."
	docker-compose exec qna-agent-api poetry run alembic upgrade head
	@echo "✓ Migrations applied successfully"

docker-migrate-status:
	docker-compose exec qna-agent-api poetry run alembic current

# Kubernetes (Docker Desktop)
k8s-setup:
	@echo "Checking Kubernetes setup..."
	@command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl not installed. Run: brew install kubectl"; exit 1; }
	@kubectl cluster-info >/dev/null 2>&1 || { echo "Error: Kubernetes not running. Enable it in Docker Desktop settings"; exit 1; }
	@echo "✓ Kubernetes is ready"

k8s-start:
	@echo "Checking Kubernetes status..."
	@kubectl cluster-info
	@echo "✓ Using Docker Desktop Kubernetes"

k8s-build:
	@echo "Building Docker image..."
	docker build -t qna-agent-api:latest .
	@echo "✓ Image built"

k8s-secret:
	@echo "Creating Kubernetes secret from .env file..."
	@if [ ! -f .env ]; then echo "Error: .env file not found"; exit 1; fi
	@. ./.env && kubectl create secret generic qna-agent-secrets \
		--from-literal=openai-api-key="$$OPENAI_API_KEY" \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "✓ Secret created"

k8s-deploy:
	@echo "Deploying to Minikube..."
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/pvc.yaml
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	@echo "✓ Deployed successfully"
	@echo "Waiting for deployment to be ready..."
	kubectl wait --for=condition=available --timeout=120s deployment/qna-agent-api
	@echo "✓ Deployment ready"

k8s-status:
	@echo "Kubernetes Resources:"
	@kubectl get all -l app=qna-agent-api
	@echo ""
	@echo "PVCs:"
	@kubectl get pvc -l app=qna-agent-api

k8s-logs:
	kubectl logs -l app=qna-agent-api --tail=100 -f

k8s-port-forward:
	@echo "Port forwarding to localhost:8000..."
	@echo "Access the API at: http://localhost:8000"
	@echo "Press Ctrl+C to stop"
	kubectl port-forward service/qna-agent-api 8000:80

k8s-migrate:
	@echo "Running database migrations in Kubernetes..."
	kubectl exec -it deployment/qna-agent-api -- poetry run alembic upgrade head
	@echo "✓ Migrations applied"

k8s-shell:
	kubectl exec -it deployment/qna-agent-api -- /bin/bash

k8s-delete:
	@echo "Deleting Kubernetes resources..."
	kubectl delete -f k8s/service.yaml --ignore-not-found=true
	kubectl delete -f k8s/deployment.yaml --ignore-not-found=true
	kubectl delete -f k8s/pvc.yaml --ignore-not-found=true
	kubectl delete -f k8s/configmap.yaml --ignore-not-found=true
	kubectl delete secret qna-agent-secrets --ignore-not-found=true
	@echo "✓ Resources deleted"

k8s-stop:
	@echo "Note: To stop Kubernetes, disable it in Docker Desktop settings"
	@echo "Resources will be deleted but cluster stays running"

k8s-clean: k8s-delete
	@echo "✓ All resources deleted"
	@echo "Note: To reset Kubernetes cluster, use Docker Desktop settings"

k8s-full-deploy: k8s-setup k8s-start k8s-build k8s-secret k8s-deploy
	@echo ""
	@echo "=========================================="
	@echo "✓ Full deployment completed!"
	@echo "=========================================="
	@echo ""
	@echo "Access your application:"
	@echo "  API: http://localhost:30080"
	@echo "  Swagger: http://localhost:30080/docs"
	@echo ""
	@echo "View logs:"
	@echo "  make k8s-logs"
	@echo ""
	@echo "Run migrations:"
	@echo "  make k8s-migrate"
	@echo ""
	@echo "Check status:"
	@echo "  make k8s-status"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
	@echo "✓ Cleanup completed"
