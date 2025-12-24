#!/bin/bash
set -e

# Carregar credenciais
source /app/.credentials 2>/dev/null || true

# Variáveis
SQL_DIR="/app/sql_postgres"
BASE_URL="https://techsuper.com.br/baseportabilidade"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER}"
DB_PASS="${POSTGRES_PASSWORD}"
DB_NAME="${POSTGRES_DB}"

# Função para executar comandos SQL silenciosamente
exec_sql() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$1" 2>/dev/null
}

# Função para verificar se tabela existe e tem dados
check_table() {
    local table=$1
    local count=$(exec_sql "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$count" -gt "0" ]; then
        return 0
    else
        return 1
    fi
}

# Função para baixar arquivo se não existir
download_if_missing() {
    local file=$1
    local url=$2

    if [ ! -f "$SQL_DIR/$file" ]; then
        echo "  ✓ Baixando $file..."
        mkdir -p "$SQL_DIR"
        wget -q "$url" -O "$SQL_DIR/$file.gz" 2>/dev/null
        gunzip -q "$SQL_DIR/$file.gz" 2>/dev/null
    fi
}

# Iniciar PostgreSQL se necessário
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start" > /dev/null 2>&1
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; do
        sleep 0.5
    done
    TEMP_PG=1
fi

# Criar tabelas se não existirem
if ! exec_sql "SELECT 1 FROM information_schema.tables WHERE table_name = 'operadoras_rn1';" | grep -q 1 2>/dev/null; then
    echo "  ✓ Criando estrutura do banco..."
    cd /app
    python3 -c "
from app.database import engine, Base
from app.models import FaixaOperadora, OperadoraRN1, OperadoraSTFC, PortabilidadeHistorico
Base.metadata.create_all(bind=engine)
" 2>/dev/null
fi

# Baixar arquivos necessários
download_if_missing "operadoras_rn1.sql" "${BASE_URL}/operadoras_rn1.sql.gz"
download_if_missing "operadoras_stfc.sql" "${BASE_URL}/operadoras_stfc.sql.gz"
download_if_missing "faixa_operadora.sql" "${BASE_URL}/faixa_operadora.sql.gz"

# Importar dados se necessário
IMPORTED=0

if ! check_table "operadoras_rn1"; then
    echo "  ✓ Importando operadoras_rn1..."

    # Adicionar colunas faltantes se necessário
    exec_sql "ALTER TABLE operadoras_rn1 ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;" || true
    exec_sql "ALTER TABLE operadoras_rn1 ADD COLUMN IF NOT EXISTS nome_operadora VARCHAR(150);" || true
    exec_sql "ALTER TABLE operadoras_rn1 ADD COLUMN IF NOT EXISTS cnpj VARCHAR(20);" || true
    exec_sql "ALTER TABLE operadoras_rn1 ADD COLUMN IF NOT EXISTS rn1_prefixo VARCHAR(10);" || true

    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_rn1.sql" > /dev/null 2>&1
    IMPORTED=1
fi

if ! check_table "operadoras_stfc"; then
    echo "  ✓ Importando operadoras_stfc..."

    # Adicionar todas as colunas necessárias
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS eot VARCHAR(10);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS nome_fantasia VARCHAR(150);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS razao_social VARCHAR(200);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS csp VARCHAR(10);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS tipo_servico VARCHAR(50);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS modalidade_banda VARCHAR(50);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS area_prestacao VARCHAR(100);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS holding VARCHAR(150);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS cnpj VARCHAR(25);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(50);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS contato VARCHAR(100);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS email VARCHAR(150);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS fone VARCHAR(100);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS endereco_nf TEXT;" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS endereco_correspondencia TEXT;" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS uf VARCHAR(2);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS regiao VARCHAR(10);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS concessao VARCHAR(5);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS rn1 VARCHAR(10);" || true
    exec_sql "ALTER TABLE operadoras_stfc ADD COLUMN IF NOT EXISTS spid VARCHAR(10);" || true

    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_stfc.sql" > /dev/null 2>&1
    IMPORTED=1
fi

if ! check_table "faixa_operadora"; then
    echo "  ✓ Importando faixa_operadora (aguarde)..."

    # Adicionar colunas necessárias
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS nome_operadora VARCHAR(100);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS tipo_numero VARCHAR(1);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS ddi_ddd VARCHAR(10);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS ddd VARCHAR(5);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS prefixo VARCHAR(10);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS faixa_inicio INTEGER;" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS faixa_fim INTEGER;" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS sigla_operadora VARCHAR(10);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS estado VARCHAR(2);" || true
    exec_sql "ALTER TABLE faixa_operadora ADD COLUMN IF NOT EXISTS codigo_regiao VARCHAR(10);" || true

    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/faixa_operadora.sql" > /dev/null 2>&1
    IMPORTED=1
fi

# Criar índices
if [ "$IMPORTED" = "1" ]; then
    echo "  ✓ Otimizando banco de dados..."
    exec_sql "CREATE INDEX IF NOT EXISTS idx_rn1_prefixo ON operadoras_rn1(rn1_prefixo);" || true
    exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_spid ON operadoras_stfc(spid);" || true
    exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_eot ON operadoras_stfc(eot);" || true
    exec_sql "CREATE INDEX IF NOT EXISTS idx_faixa_ddd_prefixo ON faixa_operadora(ddd, prefixo);" || true
fi

# Parar PostgreSQL temporário se iniciamos
if [ "$TEMP_PG" = "1" ]; then
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop" > /dev/null 2>&1
    sleep 2
fi

if [ "$IMPORTED" = "1" ]; then
    echo "  ✓ Importação concluída!"
else
    echo "  ✓ Dados já importados"
fi