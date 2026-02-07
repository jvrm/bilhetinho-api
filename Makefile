# Bilhetinho API - Complete Deployment Makefile
# Usage: make <command>

# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Variables
AWS_REGION := us-east-1
AWS_ACCOUNT_ID := 728528177598
ECR_REPO := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/bilhetinho-api-dev
IMAGE_TAG := dev-latest
ECS_CLUSTER := bilhetinho-dev-cluster
ECS_SERVICE := bilhetinho-dev-bilhetinho-api
LOG_GROUP := /ecs/bilhetinho-dev/bilhetinho-api

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: help local build push deploy restart logs status url clean rollback health tasks info wait

# Default target
help:
	@echo "$(BLUE)Bilhetinho API - Deployment Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  make local       - Run API locally with uvicorn"
	@echo "  make test        - Run tests (if configured)"
	@echo ""
	@echo "$(YELLOW)Production Deployment:$(NC)"
	@echo "  make build       - Build Docker image"
	@echo "  make push        - Build + Push to ECR"
	@echo "  make deploy      - Push + Update ECS service (full deploy)"
	@echo "  make restart     - Restart ECS service (reload env vars from Secrets Manager)"
	@echo "  make rollback    - Rollback to previous task definition"
	@echo "  make wait        - Wait for deployment to complete"
	@echo ""
	@echo "$(YELLOW)Monitoring:$(NC)"
	@echo "  make logs        - View ECS logs (live)"
	@echo "  make status      - Check ECS service status (simple)"
	@echo "  make info        - Detailed service info"
	@echo "  make tasks       - List running tasks"
	@echo "  make url         - Get application URL"
	@echo "  make health      - Check application health"
	@echo ""
	@echo "$(YELLOW)Cleanup:$(NC)"
	@echo "  make clean       - Remove local Docker images"

# ====================
# Local Development
# ====================

local:
	@echo "$(GREEN)🚀 Starting local development server...$(NC)"
	@if [ ! -d ".venv" ]; then \
		echo "$(YELLOW)⚠️  Virtual environment not found. Creating...$(NC)"; \
		python -m venv .venv; \
		. .venv/bin/activate && pip install -r requirements.txt; \
	fi
	@. .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@if [ ! -d ".venv" ]; then \
		echo "$(RED)❌ Virtual environment not found. Run 'make local' first$(NC)"; \
		exit 1; \
	fi
	@. .venv/bin/activate && pytest -v || echo "$(YELLOW)⚠️  No tests configured yet$(NC)"

# ====================
# Build & Deploy
# ====================

build:
	@echo "$(BLUE)🔨 Building Docker image for linux/amd64...$(NC)"
	@docker build --platform linux/amd64 -t $(ECR_REPO):$(IMAGE_TAG) .
	@echo "$(GREEN)✅ Build complete!$(NC)"

push: build
	@echo "$(BLUE)🔐 Logging into ECR...$(NC)"
	@aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO)
	@echo "$(BLUE)⬆️  Pushing image to ECR...$(NC)"
	@docker push $(ECR_REPO):$(IMAGE_TAG)
	@echo "$(GREEN)✅ Push complete!$(NC)"

deploy: push
	@echo "$(BLUE)🚀 Deploying to ECS...$(NC)"
	@aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--no-cli-pager > /dev/null
	@echo "$(GREEN)✅ Deployment initiated!$(NC)"
	@echo ""
	@echo "$(YELLOW)⏳ Run 'make wait' to wait for deployment or 'make logs' to watch progress$(NC)"

restart:
	@echo "$(BLUE)🔄 Restarting ECS service (reloading env vars from Secrets Manager)...$(NC)"
	@aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--no-cli-pager > /dev/null
	@echo "$(GREEN)✅ Service restart initiated!$(NC)"
	@echo ""
	@echo "$(YELLOW)💡 This will:$(NC)"
	@echo "  - Stop current tasks"
	@echo "  - Start new tasks with latest env vars from Secrets Manager"
	@echo "  - Keep same Docker image (no rebuild needed)"
	@echo ""
	@echo "$(YELLOW)⏳ Run 'make wait' to wait for restart or 'make logs' to watch progress$(NC)"

wait:
	@echo "$(BLUE)⏳ Waiting for deployment to stabilize...$(NC)"
	@aws ecs wait services-stable \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION) && \
	echo "$(GREEN)✅ Deployment complete!$(NC)" || \
	echo "$(RED)❌ Deployment failed or timed out$(NC)"

rollback:
	@echo "$(YELLOW)🔄 Rolling back to previous version...$(NC)"
	@CURRENT_TASK=$$(aws ecs describe-services \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION) \
		--query 'services[0].taskDefinition' \
		--output text); \
	CURRENT_VERSION=$$(echo $$CURRENT_TASK | grep -oE '[0-9]+$$'); \
	PREVIOUS_VERSION=$$(($$CURRENT_VERSION - 1)); \
	if [ $$PREVIOUS_VERSION -lt 1 ]; then \
		echo "$(RED)❌ No previous version to rollback to$(NC)"; \
		exit 1; \
	fi; \
	TASK_FAMILY=$$(echo $$CURRENT_TASK | sed "s/:$$CURRENT_VERSION$$//"); \
	PREVIOUS_TASK="$$TASK_FAMILY:$$PREVIOUS_VERSION"; \
	echo "$(BLUE)  From: $$CURRENT_TASK$(NC)"; \
	echo "$(BLUE)  To:   $$PREVIOUS_TASK$(NC)"; \
	read -p "Continue with rollback? (yes/no): " CONFIRM; \
	if [ "$$CONFIRM" != "yes" ]; then \
		echo "$(YELLOW)Rollback cancelled$(NC)"; \
		exit 0; \
	fi; \
	aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--task-definition $$PREVIOUS_TASK \
		--region $(AWS_REGION) \
		--no-cli-pager > /dev/null && \
	echo "$(GREEN)✅ Rollback initiated!$(NC)" || \
	echo "$(RED)❌ Rollback failed$(NC)"

# ====================
# Monitoring
# ====================

logs:
	@echo "$(BLUE)📋 Streaming ECS logs (Ctrl+C to stop)...$(NC)"
	@aws logs tail $(LOG_GROUP) --follow --region $(AWS_REGION)

status:
	@echo "$(BLUE)📊 ECS Service Status:$(NC)"
	@aws ecs describe-services \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION) \
		--query 'services[0].[serviceName,status,runningCount,desiredCount,deployments[0].rolloutState]' \
		--output table

info:
	@echo "$(BLUE)=========================================="
	@echo "ECS Service Detailed Info"
	@echo "==========================================$(NC)"
	@SERVICE_INFO=$$(aws ecs describe-services \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION) \
		--query 'services[0]' \
		--output json); \
	DESIRED=$$(echo "$$SERVICE_INFO" | jq -r '.desiredCount'); \
	RUNNING=$$(echo "$$SERVICE_INFO" | jq -r '.runningCount'); \
	PENDING=$$(echo "$$SERVICE_INFO" | jq -r '.pendingCount'); \
	STATUS=$$(echo "$$SERVICE_INFO" | jq -r '.status'); \
	TASK_DEF=$$(echo "$$SERVICE_INFO" | jq -r '.taskDefinition'); \
	echo ""; \
	echo "$(YELLOW)Service:$(NC)"; \
	echo "  Cluster: $(ECS_CLUSTER)"; \
	echo "  Service: $(ECS_SERVICE)"; \
	echo "  Status: $$STATUS"; \
	echo "  Task Definition: $$TASK_DEF"; \
	echo ""; \
	echo "$(YELLOW)Tasks:$(NC)"; \
	echo "  Desired: $$DESIRED"; \
	echo "  Running: $$RUNNING"; \
	echo "  Pending: $$PENDING"; \
	echo ""; \
	echo "$(YELLOW)Recent Events:$(NC)"; \
	echo "$$SERVICE_INFO" | jq -r '.events[0:5][] | "  [\(.createdAt)] \(.message)"'; \
	echo ""

tasks:
	@echo "$(BLUE)📋 Running Tasks:$(NC)"
	@TASK_ARNS=$$(aws ecs list-tasks \
		--cluster $(ECS_CLUSTER) \
		--service-name $(ECS_SERVICE) \
		--desired-status RUNNING \
		--region $(AWS_REGION) \
		--query 'taskArns' \
		--output json); \
	TASK_COUNT=$$(echo "$$TASK_ARNS" | jq '. | length'); \
	if [ $$TASK_COUNT -eq 0 ]; then \
		echo "$(RED)  No running tasks$(NC)"; \
	else \
		TASKS=$$(aws ecs describe-tasks \
			--cluster $(ECS_CLUSTER) \
			--tasks $$(echo "$$TASK_ARNS" | jq -r '.[]') \
			--region $(AWS_REGION) \
			--query 'tasks' \
			--output json); \
		echo "$$TASKS" | jq -r '.[] | "  Task: \(.taskArn | split("/") | last)\n  Status: \(.lastStatus)\n  Health: \(.healthStatus // "N/A")\n  Started: \(.startedAt)\n"'; \
	fi

url:
	@echo "$(BLUE)🌐 Getting application URL...$(NC)"
	@TASK_ARNS=$$(aws ecs list-tasks \
		--cluster $(ECS_CLUSTER) \
		--service-name $(ECS_SERVICE) \
		--desired-status RUNNING \
		--region $(AWS_REGION) \
		--query 'taskArns[0]' \
		--output text); \
	if [ -z "$$TASK_ARNS" ] || [ "$$TASK_ARNS" = "None" ]; then \
		echo "$(RED)❌ No running tasks$(NC)"; \
		exit 1; \
	fi; \
	TASK_INFO=$$(aws ecs describe-tasks \
		--cluster $(ECS_CLUSTER) \
		--tasks $$TASK_ARNS \
		--region $(AWS_REGION) \
		--query 'tasks[0]' \
		--output json); \
	PORT=$$(echo "$$TASK_INFO" | jq -r '.containers[0].networkBindings[0].hostPort'); \
	CONTAINER_INSTANCE=$$(echo "$$TASK_INFO" | jq -r '.containerInstanceArn'); \
	INSTANCE_ID=$$(aws ecs describe-container-instances \
		--cluster $(ECS_CLUSTER) \
		--container-instances $$CONTAINER_INSTANCE \
		--region $(AWS_REGION) \
		--query 'containerInstances[0].ec2InstanceId' \
		--output text); \
	PUBLIC_IP=$$(aws ec2 describe-instances \
		--instance-ids $$INSTANCE_ID \
		--region $(AWS_REGION) \
		--query 'Reservations[0].Instances[0].PublicIpAddress' \
		--output text); \
	HEALTH=$$(echo "$$TASK_INFO" | jq -r '.healthStatus // "UNKNOWN"'); \
	echo ""; \
	echo "$(GREEN)✅ Application Info:$(NC)"; \
	echo "  Status: $$HEALTH"; \
	echo "  Instance: $$INSTANCE_ID"; \
	echo "  Port: $$PORT"; \
	echo ""; \
	echo "$(YELLOW)🌐 URLs:$(NC)"; \
	echo "  Base URL:    http://$$PUBLIC_IP:$$PORT"; \
	echo "  Health:      http://$$PUBLIC_IP:$$PORT/health"; \
	echo "  API Docs:    http://$$PUBLIC_IP:$$PORT/docs"; \
	echo "  Room Active: http://$$PUBLIC_IP:$$PORT/api/room/active"; \
	echo ""; \
	echo "$(BLUE)💡 Test:$(NC)"; \
	echo "  curl http://$$PUBLIC_IP:$$PORT/health"

health:
	@echo "$(BLUE)🏥 Checking application health...$(NC)"
	@TASK_ARNS=$$(aws ecs list-tasks \
		--cluster $(ECS_CLUSTER) \
		--service-name $(ECS_SERVICE) \
		--desired-status RUNNING \
		--region $(AWS_REGION) \
		--query 'taskArns[0]' \
		--output text); \
	if [ -z "$$TASK_ARNS" ] || [ "$$TASK_ARNS" = "None" ]; then \
		echo "$(RED)❌ No running tasks$(NC)"; \
		exit 1; \
	fi; \
	TASK_INFO=$$(aws ecs describe-tasks \
		--cluster $(ECS_CLUSTER) \
		--tasks $$TASK_ARNS \
		--region $(AWS_REGION) \
		--query 'tasks[0]' \
		--output json); \
	PORT=$$(echo "$$TASK_INFO" | jq -r '.containers[0].networkBindings[0].hostPort'); \
	CONTAINER_INSTANCE=$$(echo "$$TASK_INFO" | jq -r '.containerInstanceArn'); \
	INSTANCE_ID=$$(aws ecs describe-container-instances \
		--cluster $(ECS_CLUSTER) \
		--container-instances $$CONTAINER_INSTANCE \
		--region $(AWS_REGION) \
		--query 'containerInstances[0].ec2InstanceId' \
		--output text); \
	PUBLIC_IP=$$(aws ec2 describe-instances \
		--instance-ids $$INSTANCE_ID \
		--region $(AWS_REGION) \
		--query 'Reservations[0].Instances[0].PublicIpAddress' \
		--output text); \
	RESPONSE=$$(curl -s -o /dev/null -w "%{http_code}" http://$$PUBLIC_IP:$$PORT/health 2>/dev/null); \
	if [ "$$RESPONSE" = "200" ]; then \
		echo "$(GREEN)✅ Application is healthy (HTTP $$RESPONSE)$(NC)"; \
		curl -s http://$$PUBLIC_IP:$$PORT/health | jq '.'; \
	else \
		echo "$(RED)❌ Application is unhealthy (HTTP $$RESPONSE)$(NC)"; \
		exit 1; \
	fi

# ====================
# Cleanup
# ====================

clean:
	@echo "$(YELLOW)🧹 Removing local Docker images...$(NC)"
	@docker rmi $(ECR_REPO):$(IMAGE_TAG) 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete!$(NC)"
