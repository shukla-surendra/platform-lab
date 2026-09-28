# Developer entry points. `make help` lists them.

DATABASE_URL      ?= postgres://taskapi:taskapi@localhost:55432/taskapi?sslmode=disable
TEST_DATABASE_URL ?= postgres://taskapi:taskapi@localhost:55432/taskapi_test?sslmode=disable
PORT              ?= 8081
VERSION           ?= $(shell git describe --always --dirty 2>/dev/null || echo dev)

export DATABASE_URL PORT

.PHONY: help run build test test-integration cover fmt vet check db-up db-down db-reset db-shell up down logs smoke docker-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

run: ## Run the API locally against the compose Postgres (make db-up first)
	go run ./cmd/api

build: ## Build bin/api with the version stamped in
	go build -ldflags "-X main.version=$(VERSION)" -o bin/api ./cmd/api

test: ## Unit tests (no database needed)
	go test -race ./...

test-integration: db-up ## Unit + integration tests against real Postgres
	TEST_DATABASE_URL="$(TEST_DATABASE_URL)" go test -race -count=1 ./...

cover: ## Coverage report in the browser
	TEST_DATABASE_URL="$(TEST_DATABASE_URL)" go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out

fmt: ## Format code
	gofmt -w .

vet: ## Static checks
	go vet ./...

check: vet test ## What CI would run
	@test -z "$$(gofmt -l .)" || (echo "gofmt needed:"; gofmt -l .; exit 1)

db-up: ## Start Postgres (waits until healthy)
	docker compose up -d --wait db

db-down: ## Stop Postgres (keeps data)
	docker compose down

db-reset: ## Stop Postgres and DELETE its data volume
	docker compose down -v

db-shell: ## psql into the dev database
	docker compose exec db psql -U taskapi -d taskapi

up: ## Build and run Postgres + API in containers (API on :8081)
	docker compose --profile app up -d --build --wait

down: ## Stop everything
	docker compose --profile app down

logs: ## Tail API container logs
	docker compose --profile app logs -f api

smoke: ## Exercise every endpoint against a running API
	./scripts/smoke.sh http://localhost:$(PORT)

docker-build: ## Build the production image
	docker build --build-arg VERSION=$(VERSION) -t taskapi:$(VERSION) .
