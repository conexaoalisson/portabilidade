#!/bin/bash
#
# Script de Recuperação do PostgreSQL
# Resolve problema de loop infinito durante recovery
#
# Problema identificado:
# - PostgreSQL travou em loop de recovery após crash durante importação
# - Checkpoint muito grande (38M+ registros) excede timeout
# - Container reinicia infinitamente sem conseguir completar recovery
#
# Logs do erro:
# "database system was not properly shut down; automatic recovery in progress"
# "checkpoint starting: end-of-recovery immediate wait"
# "pg_ctl: server did not start in time"
#

echo "=============================================="
echo "SCRIPT DE RECUPERAÇÃO DO POSTGRESQL"
echo "=============================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função de log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Parar PostgreSQL se estiver rodando
log_info "Parando PostgreSQL..."
pg_ctl stop -D /var/lib/postgresql/data -m immediate 2>/dev/null || true
pkill -9 postgres 2>/dev/null || true
sleep 5

# 2. Backup dos arquivos WAL problemáticos
log_info "Fazendo backup dos WAL files..."
WAL_DIR="/var/lib/postgresql/data/pg_wal"
BACKUP_DIR="/var/lib/postgresql/wal_backup_$(date +%Y%m%d_%H%M%S)"

if [ -d "$WAL_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    cp -r "$WAL_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
    log_info "Backup salvo em: $BACKUP_DIR"
fi

# 3. Limpar arquivos WAL para forçar recovery limpo
log_warn "Removendo arquivos WAL corrompidos/pendentes..."
rm -rf "$WAL_DIR"/* 2>/dev/null || true

# 4. Criar novo diretório WAL
mkdir -p "$WAL_DIR"
chown -R postgres:postgres "$WAL_DIR"
chmod 700 "$WAL_DIR"

# 5. Configurar PostgreSQL para recovery mais robusto
log_info "Ajustando configurações do PostgreSQL..."
PGDATA="/var/lib/postgresql/data"

cat >> "$PGDATA/postgresql.auto.conf" << EOF

# Configurações para recovery robusto
# Adicionadas automaticamente pelo script de recovery
checkpoint_timeout = 30min
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 2GB
min_wal_size = 80MB

# Commits mais frequentes para evitar checkpoints enormes
commit_delay = 0
commit_siblings = 5

# Logs mais verbosos para debug
log_checkpoints = on
log_connections = on
log_disconnections = on
log_duration = off
log_line_prefix = '%t [%p] %u@%d '

EOF

log_info "Configurações aplicadas"

# 6. Iniciar PostgreSQL com recovery forçado
log_info "Iniciando PostgreSQL..."
log_warn "Isso pode demorar alguns minutos se houver muitos dados para recuperar..."

# Iniciar em modo standalone para recovery
su - postgres -c "pg_ctl start -D $PGDATA -w -t 600 -l $PGDATA/startup.log"

if [ $? -eq 0 ]; then
    log_info "✅ PostgreSQL iniciado com sucesso!"

    # Verificar conexão
    sleep 5
    if su - postgres -c "psql -c 'SELECT version();'" > /dev/null 2>&1; then
        log_info "✅ Conexão com banco OK"
    else
        log_error "❌ PostgreSQL iniciou mas não aceita conexões"
        exit 1
    fi
else
    log_error "❌ Falha ao iniciar PostgreSQL"
    log_error "Verifique os logs em: $PGDATA/startup.log"
    exit 1
fi

# 7. Verificar quantos registros foram salvos
log_info "Verificando dados importados..."
COUNT=$(su - postgres -c "psql -U portabilidade -d portabilidade -t -c 'SELECT COUNT(*) FROM portabilidade_historico;'" 2>/dev/null | tr -d ' ')

if [ ! -z "$COUNT" ]; then
    log_info "✅ Registros encontrados: $(echo $COUNT | sed ':a;s/\B[0-9]\{3\}\>/,&/;ta')"
else
    log_warn "⚠️  Não foi possível contar registros"
fi

# 8. Executar VACUUM FULL para otimizar
log_info "Otimizando banco de dados..."
su - postgres -c "psql -U portabilidade -d portabilidade -c 'VACUUM FULL ANALYZE portabilidade_historico;'" > /dev/null 2>&1 &
VACUUM_PID=$!

echo ""
log_info "✅ RECOVERY CONCLUÍDO!"
echo ""
echo "Próximos passos:"
echo "1. Verificar quantos registros foram preservados"
echo "2. Retomar importação dos registros faltantes"
echo "3. Configurar checkpoints automáticos mais frequentes"
echo ""
echo "Para retomar a importação:"
echo "  cd /app && nohup python3 import_csv_copy_chunks.py > import_resume.log 2>&1 &"
echo ""
echo "=============================================="
