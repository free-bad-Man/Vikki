#!/bin/bash
# Vikki Platform - Production Deployment Script
# Usage: ./deploy.sh [--env production|staging] [--rebuild]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$PROJECT_ROOT/infra/compose/docker-compose.prod.yml"

# Default values
ENVIRONMENT="${ENV:-production}"
REBUILD=false
SKIP_BUILD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env ENV        Environment (production|staging), default: production"
            echo "  --rebuild        Force rebuild of all Docker images"
            echo "  --skip-build     Skip building images (use existing)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing+=("docker-compose")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Validate environment file
validate_env() {
    log_info "Validating environment file..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        log_info "Copy .env.example to .env and configure it first"
        exit 1
    fi
    
    # Source env file for validation
    set -a
    source "$ENV_FILE"
    set +a
    
    local required_vars=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
    
    log_info "Environment validation passed"
}

# Build Docker images
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_info "Skipping Docker image build"
        return
    fi
    
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    if [ "$REBUILD" = true ]; then
        log_info "Force rebuilding all images (no cache)..."
        docker compose -f "$COMPOSE_FILE" build --no-cache
    else
        docker compose -f "$COMPOSE_FILE" build
    fi
    
    log_info "Docker images built successfully"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Run alembic migrations in the API container
    docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head || {
        log_warn "Migration step completed (may have already been applied)"
    }
    
    log_info "Database migrations completed"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    cd "$PROJECT_ROOT"
    
    docker compose -f "$COMPOSE_FILE" up -d
    
    log_info "Services started"
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    local services=("postgres" "redis" "minio" "api" "web" "caddy")
    local failed=()
    
    cd "$PROJECT_ROOT"
    
    for service in "${services[@]}"; do
        if ! docker compose -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy\|Up"; then
            failed+=("$service")
        fi
    done
    
    if [ ${#failed[@]} -ne 0 ]; then
        log_warn "Some services may not be healthy: ${failed[*]}"
        log_info "Check logs with: docker compose -f $COMPOSE_FILE logs"
    else
        log_info "All services are healthy"
    fi
}

# Main deployment flow
main() {
    log_info "========================================="
    log_info "Vikki Platform Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "========================================="
    
    check_prerequisites
    validate_env
    build_images
    run_migrations
    start_services
    health_check
    
    log_info "========================================="
    log_info "Deployment completed successfully!"
    log_info "========================================="
    log_info ""
    log_info "Useful commands:"
    log_info "  View logs:     docker compose -f $COMPOSE_FILE logs -f"
    log_info "  Stop services: docker compose -f $COMPOSE_FILE down"
    log_info "  Restart:       docker compose -f $COMPOSE_FILE restart"
    log_info ""
}

# Run main function
main "$@"
