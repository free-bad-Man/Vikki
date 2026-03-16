#!/bin/bash
# PostgreSQL Backup Script for Vikki Platform
# Usage: ./backup_pg.sh [--restore FILENAME]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    log_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup function
do_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/pg_backup_${timestamp}.sql.gz"
    
    log_info "Starting PostgreSQL backup..."
    log_info "Database: $POSTGRES_DB"
    log_info "Output: $backup_file"
    
    docker exec vikki-postgres pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -F c \
        -b \
        -v | gzip > "$backup_file"
    
    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Backup completed successfully ($size)"
        
        # Cleanup old backups
        log_info "Cleaning up backups older than $RETENTION_DAYS days..."
        find "$BACKUP_DIR" -name "pg_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
        
        log_info "Backup retained: $backup_file"
    else
        log_error "Backup failed or empty"
        exit 1
    fi
}

# Restore function
do_restore() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warn "WARNING: This will overwrite the current database!"
    log_warn "Backup file: $backup_file"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    log_info "Starting PostgreSQL restore..."
    
    # Drop and recreate database
    docker exec vikki-postgres psql \
        -U "$POSTGRES_USER" \
        -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_restore;"
    
    docker exec vikki-postgres psql \
        -U "$POSTGRES_USER" \
        -c "CREATE DATABASE ${POSTGRES_DB}_restore;"
    
    # Restore
    gunzip -c "$backup_file" | docker exec -i vikki-postgres pg_restore \
        -U "$POSTGRES_USER" \
        -d "${POSTGRES_DB}_restore" \
        --clean \
        --if-exists
    
    # Swap databases
    docker exec vikki-postgres psql \
        -U "$POSTGRES_USER" \
        -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
    
    docker exec vikki-postgres psql \
        -U "$POSTGRES_USER" \
        -c "ALTER DATABASE ${POSTGRES_DB}_restore RENAME TO $POSTGRES_DB;"
    
    log_info "Restore completed successfully"
}

# List backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo ""
    ls -lh "$BACKUP_DIR"/pg_backup_*.sql.gz 2>/dev/null || echo "No backups found"
}

# Main
case "${1:-backup}" in
    backup)
        do_backup
        ;;
    restore)
        if [ -z "${2:-}" ]; then
            log_error "Please specify backup file to restore"
            list_backups
            exit 1
        fi
        do_restore "$2"
        ;;
    list)
        list_backups
        ;;
    *)
        echo "Usage: $0 {backup|restore <filename>|list}"
        exit 1
        ;;
esac
