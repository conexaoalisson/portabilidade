#!/bin/bash
set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        VERIFICAÇÃO E IMPORTAÇÃO AUTOMÁTICA                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Variáveis
SQL_DIR="/app/sql_postgres"
DATA_DIR="/app/data"
BASE_URL="https://techsuper.com.br/baseportabilidade"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER}"
DB_PASS="${POSTGRES_PASSWORD}"
DB_NAME="${POSTGRES_DB}"

# Função para executar comandos SQL
exec_sql() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$1" 2>&1
}

# Função para verificar se tabela existe e tem dados
check_table() {
    local table=$1
    local result=$(exec_sql "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '$table') AND EXISTS (SELECT 1 FROM $table LIMIT 1);" | grep -E "(t|f)" | tr -d ' ')
    if [ "$result" = "t" ]; then
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
        echo "• Baixando $file..."
        mkdir -p "$SQL_DIR"
        wget -q --show-progress "$url" -O "$SQL_DIR/$file.gz"
        gunzip "$SQL_DIR/$file.gz"
        echo "  ✓ Download concluído"
    else
        echo "  ✓ Arquivo $file já existe"
    fi
}

# Iniciar PostgreSQL temporário se não estiver rodando
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo "Iniciando PostgreSQL temporário para importação..."
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start"

    # Aguardar PostgreSQL estar pronto
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; do
        sleep 1
    done
    TEMP_PG=1
fi

echo ""
echo "1. Verificando estrutura do banco de dados..."

# Criar tabelas usando SQLAlchemy/Alembic se não existirem
if ! check_table "operadoras_rn1" && ! check_table "operadoras_stfc" && ! check_table "faixa_operadora"; then
    echo "• Criando estrutura das tabelas..."
    cd /app
    python3 -c "
from app.database import engine, Base
from app.models import FaixaOperadora, OperadoraRN1, OperadoraSTFC, PortabilidadeHistorico

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)
print('  ✓ Tabelas criadas com sucesso')
"
else
    echo "  ✓ Estrutura do banco já existe"
fi

echo ""
echo "2. Verificando arquivos de dados..."

# Baixar arquivos se não existirem
download_if_missing "operadoras_rn1.sql" "${BASE_URL}/operadoras_rn1.sql.gz"
download_if_missing "operadoras_stfc.sql" "${BASE_URL}/operadoras_stfc.sql.gz"
download_if_missing "faixa_operadora.sql" "${BASE_URL}/faixa_operadora.sql.gz"

echo ""
echo "3. Verificando dados nas tabelas..."

# Importar dados se necessário
if ! check_table "operadoras_rn1"; then
    echo "• Importando operadoras_rn1..."

    # Criar estrutura da tabela temporária para o INSERT
    exec_sql "CREATE TABLE IF NOT EXISTS operadoras_rn1 (
        id SERIAL PRIMARY KEY,
        nome_operadora VARCHAR(150),
        cnpj VARCHAR(20),
        rn1_prefixo VARCHAR(10) UNIQUE
    );"

    # Importar dados
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_rn1.sql" > /dev/null 2>&1

    # Verificar quantidade importada
    count=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" | grep -E "[0-9]+" | head -1 | tr -d ' ')
    echo "  ✓ Importados $count registros em operadoras_rn1"
else
    echo "  ✓ operadoras_rn1 já contém dados"
fi

if ! check_table "operadoras_stfc"; then
    echo "• Importando operadoras_stfc..."

    # Criar estrutura da tabela temporária para o INSERT
    exec_sql "CREATE TABLE IF NOT EXISTS operadoras_stfc (
        id SERIAL PRIMARY KEY,
        eot VARCHAR(10),
        nome_fantasia VARCHAR(150),
        razao_social VARCHAR(200),
        csp VARCHAR(10),
        tipo_servico VARCHAR(50),
        modalidade_banda VARCHAR(50),
        area_prestacao VARCHAR(100),
        holding VARCHAR(150),
        cnpj VARCHAR(25),
        inscricao_estadual VARCHAR(50),
        contato VARCHAR(100),
        email VARCHAR(150),
        fone VARCHAR(100),
        endereco_nf TEXT,
        endereco_correspondencia TEXT,
        uf VARCHAR(2),
        regiao VARCHAR(10),
        concessao VARCHAR(5),
        rn1 VARCHAR(10),
        spid VARCHAR(10)
    );"

    # Importar dados
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_stfc.sql" > /dev/null 2>&1

    # Verificar quantidade importada
    count=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" | grep -E "[0-9]+" | head -1 | tr -d ' ')
    echo "  ✓ Importados $count registros em operadoras_stfc"
else
    echo "  ✓ operadoras_stfc já contém dados"
fi

if ! check_table "faixa_operadora"; then
    echo "• Importando faixa_operadora (pode demorar)..."

    # Criar estrutura da tabela temporária para o INSERT
    exec_sql "CREATE TABLE IF NOT EXISTS faixa_operadora (
        id SERIAL PRIMARY KEY,
        nome_operadora VARCHAR(100),
        tipo_numero VARCHAR(1),
        ddi_ddd VARCHAR(10),
        ddd VARCHAR(5),
        prefixo VARCHAR(10),
        faixa_inicio INTEGER,
        faixa_fim INTEGER,
        sigla_operadora VARCHAR(10),
        estado VARCHAR(2),
        codigo_regiao VARCHAR(10)
    );"

    # Importar dados
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/faixa_operadora.sql" > /dev/null 2>&1

    # Verificar quantidade importada
    count=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" | grep -E "[0-9]+" | head -1 | tr -d ' ')
    echo "  ✓ Importados $count registros em faixa_operadora"
else
    echo "  ✓ faixa_operadora já contém dados"
fi

echo ""
echo "4. Criando índices otimizados..."

# Criar índices se não existirem
exec_sql "CREATE INDEX IF NOT EXISTS idx_rn1_prefixo ON operadoras_rn1(rn1_prefixo);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_spid ON operadoras_stfc(spid);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_eot ON operadoras_stfc(eot);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_faixa_ddd_prefixo ON faixa_operadora(ddd, prefixo);" > /dev/null 2>&1

echo "  ✓ Índices verificados/criados"

# Parar PostgreSQL temporário se iniciamos
if [ "$TEMP_PG" = "1" ]; then
    echo ""
    echo "Parando PostgreSQL temporário..."
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop"
    sleep 2
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║        IMPORTAÇÃO AUTOMÁTICA CONCLUÍDA                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""