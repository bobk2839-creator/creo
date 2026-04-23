.PHONY: up down build logs test migrate seed shell-backend shell-frontend clean restart help

# Docker Compose command
DC = docker-compose

# Default target
help:
@echo "FuelProcess SaaS - Makefile Commands"
@echo ""
@echo "Usage: make [command]"
@echo ""
@echo "Commands:"
@echo "  up             Start all services in detached mode"
@echo "  down           Stop all services"
@echo "  build          Build all Docker images"
@echo "  rebuild        Force rebuild of all images"
@echo "  logs           View logs from all services"
@echo "  logs-backend   View backend logs"
@echo "  logs-db        View database logs"
@echo "  logs-frontend  View frontend logs"
@echo "  test           Run all tests"
@echo "  test-backend   Run backend tests with coverage"
@echo "  test-frontend  Run frontend tests"
@echo "  migrate        Apply database migrations"
@echo "  seed           Seed demo data"
@echo "  shell-backend  Open shell in backend container"
@echo "  shell-frontend Open shell in frontend container"
@echo "  shell-db       Open psql shell in database"
@echo "  restart        Restart all services"
@echo "  clean          Stop and remove all containers and volumes"
@echo "  dev            Start backend and frontend in development mode"
@echo ""

up:
$(DC) up -d
@echo "Services starting... Check status with: docker-compose ps"
@echo "Backend API: http://localhost:8000"
@echo "Frontend: http://localhost:3000"
@echo "Swagger Docs: http://localhost:8000/api/v1/docs"

down:
$(DC) down
@echo "All services stopped"

build:
$(DC) build

rebuild:
$(DC) build --no-cache
$(DC) up -d --force-recreate

logs:
$(DC) logs -f

logs-backend:
$(DC) logs -f backend

logs-db:
$(DC) logs -f postgres

logs-frontend:
$(DC) logs -f frontend

test: test-backend test-frontend

test-backend:
$(DC) exec backend pytest --cov=app --cov-report=term-missing

test-frontend:
$(DC) exec frontend npm test

migrate:
$(DC) exec backend alembic upgrade head
@echo "Migrations applied successfully"

seed:
$(DC) exec backend python -c "from app.services.seed_data import seed_demo_data; seed_demo_data()"
@echo "Demo data seeded successfully"

shell-backend:
$(DC) exec backend bash

shell-frontend:
$(DC) exec frontend sh

shell-db:
$(DC) exec postgres psql -U fueluser -d fuelprocess

restart:
$(DC) restart

clean:
$(DC) down -v --remove-orphans
@echo "All containers and volumes removed"

dev:
@echo "Starting development environment..."
@echo "1. Starting PostgreSQL and Redis..."
$(DC) up -d postgres redis
@echo "2. Backend will run locally on http://localhost:8000"
@echo "3. Frontend will run locally on http://localhost:3000"
@echo ""
@echo "Now run in separate terminals:"
@echo "  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
@echo "  cd frontend && npm run dev"

# Quick setup for first time users
setup:
@echo "Setting up FuelProcess SaaS..."
@echo "1. Checking Docker installation..."
@which docker || (echo "Docker not found! Please install Docker first." && exit 1)
@which docker-compose || (echo "Docker Compose not found! Please install Docker Compose first." && exit 1)
@echo "✓ Docker installed"
@echo "2. Copying .env.example to .env..."
@if [ ! -f .env ]; then cp .env.example .env && echo "✓ .env created"; else echo "✓ .env already exists"; fi
@echo "3. Building Docker images..."
$(DC) build
@echo "4. Starting services..."
$(DC) up -d
@echo "5. Waiting for database to be ready..."
@sleep 10
@echo "6. Applying migrations..."
$(DC) exec backend alembic upgrade head || true
@echo ""
@echo "✅ Setup complete!"
@echo ""
@echo "Access the application:"
@echo "  Frontend: http://localhost:3000"
@echo "  Backend API: http://localhost:8000"
@echo "  Swagger Docs: http://localhost:8000/api/v1/docs"
@echo ""
@echo "Default credentials:"
@echo "  Admin: admin / admin123"
@echo "  Tech: tech / tech123"
@echo ""
@echo "Check service status: docker-compose ps"
@echo "View logs: make logs"
