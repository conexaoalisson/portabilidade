#!/bin/bash
set -e

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

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

# Função para desenhar barra de progresso
draw_progress_bar() {
    local progress=$1
    local total=$2
    local width=50

    # Calcular porcentagem
    local percent=$((progress * 100 / total))
    local filled=$((width * progress / total))

    # Desenhar barra
    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%$((width - filled))s" | tr ' ' '░'
    printf "] ${BOLD}%3d%%${NC}" $percent
}

# Função para executar SQL com feedback
exec_sql() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$1" 2>/dev/null
}

# Função para executar SQL verboso
exec_sql_verbose() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$1"
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

# Função para contar linhas em arquivo SQL
count_sql_lines() {
    local file=$1
    grep -c "INSERT INTO\|VALUES" "$file" 2>/dev/null || echo "0"
}

# Função para baixar com progresso
download_with_progress() {
    local file=$1
    local url=$2

    echo -e "${YELLOW}📥 Baixando $file...${NC}"
    mkdir -p "$SQL_DIR"

    # Download com wget mostrando progresso
    wget --progress=bar:force:noscroll "$url" -O "$SQL_DIR/$file.gz" 2>&1 | \
        grep --line-buffered "%" | \
        sed -u -e "s/.* \([0-9]\+\)%.*/\1/" | \
        while read percent; do
            draw_progress_bar $percent 100
        done

    echo -e "\n${GREEN}✓ Download concluído${NC}"

    echo -e "${YELLOW}📦 Descompactando...${NC}"
    gunzip -f "$SQL_DIR/$file.gz"
    echo -e "${GREEN}✓ Arquivo pronto${NC}\n"
}

# Banner inicial
clear
echo -e "${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         IMPORTAÇÃO DE DADOS COM MONITORAMENTO              ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Iniciar PostgreSQL se necessário
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo -e "${YELLOW}🔄 Iniciando PostgreSQL...${NC}"
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start" > /dev/null 2>&1

    # Mostrar progresso de inicialização
    for i in {1..10}; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo -e "\r${GREEN}✓ PostgreSQL iniciado${NC}                    "
            break
        fi
        printf "\r${YELLOW}⏳ Aguardando PostgreSQL... %d/10${NC}" $i
        sleep 0.5
    done
    echo ""
    TEMP_PG=1
fi

# ETAPA 1: Verificar/Criar Estrutura
echo -e "\n${BOLD}1. ESTRUTURA DO BANCO DE DADOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ! exec_sql "SELECT 1 FROM information_schema.tables WHERE table_name = 'operadoras_rn1';" | grep -q 1 2>/dev/null; then
    echo -e "${BLUE}🔨 Criando tabelas...${NC}\n"

    cd /app
    python3 << 'EOF'
import sys
from app.database import engine, Base
from app.models import FaixaOperadora, OperadoraRN1, OperadoraSTFC, PortabilidadeHistorico

print("  → Criando operadoras_rn1...", end='', flush=True)
OperadoraRN1.__table__.create(engine, checkfirst=True)
print(" ✓")

print("  → Criando operadoras_stfc...", end='', flush=True)
OperadoraSTFC.__table__.create(engine, checkfirst=True)
print(" ✓")

print("  → Criando faixa_operadora...", end='', flush=True)
FaixaOperadora.__table__.create(engine, checkfirst=True)
print(" ✓")

print("  → Criando portabilidade_historico...", end='', flush=True)
PortabilidadeHistorico.__table__.create(engine, checkfirst=True)
print(" ✓")
EOF

    echo -e "\n${GREEN}✓ Estrutura criada com sucesso${NC}"
else
    echo -e "${GREEN}✓ Estrutura já existe${NC}"
fi

# ETAPA 2: Download dos Arquivos
echo -e "\n${BOLD}2. DOWNLOAD DOS ARQUIVOS DE DADOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

FILES_TO_DOWNLOAD=()

if [ ! -f "$SQL_DIR/operadoras_rn1.sql" ]; then
    FILES_TO_DOWNLOAD+=("operadoras_rn1.sql")
fi

if [ ! -f "$SQL_DIR/operadoras_stfc.sql" ]; then
    FILES_TO_DOWNLOAD+=("operadoras_stfc.sql")
fi

if [ ! -f "$SQL_DIR/faixa_operadora.sql" ]; then
    FILES_TO_DOWNLOAD+=("faixa_operadora.sql")
fi

if [ ${#FILES_TO_DOWNLOAD[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ Todos os arquivos já existem${NC}"
else
    for file in "${FILES_TO_DOWNLOAD[@]}"; do
        download_with_progress "$file" "${BASE_URL}/${file}.gz"
    done
fi

# ETAPA 3: Importação dos Dados
echo -e "\n${BOLD}3. IMPORTAÇÃO DOS DADOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Importar operadoras_rn1
if ! check_table "operadoras_rn1"; then
    echo -e "${BLUE}📊 Importando operadoras_rn1${NC}"

    # Contar registros
    TOTAL_LINES=$(grep -c "^(" "$SQL_DIR/operadoras_rn1.sql" || echo "0")
    echo -e "   Total de registros: ${BOLD}$TOTAL_LINES${NC}\n"

    # Criar tabela temporária para monitoramento
    exec_sql "CREATE TABLE IF NOT EXISTS import_progress (id serial, table_name text, processed int);" > /dev/null 2>&1
    exec_sql "INSERT INTO import_progress (table_name, processed) VALUES ('operadoras_rn1', 0);" > /dev/null 2>&1

    # Importar com progresso
    (PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_rn1.sql" 2>&1 | \
        while IFS= read -r line; do
            if [[ $line == INSERT* ]]; then
                CURRENT=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" | tr -d ' ')
                draw_progress_bar $CURRENT $TOTAL_LINES
            fi
        done) &

    # Monitorar progresso
    while true; do
        CURRENT=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" 2>/dev/null | tr -d ' ' || echo "0")
        if [ "$CURRENT" -ge "$TOTAL_LINES" ] || [ "$CURRENT" = "$TOTAL_LINES" ]; then
            draw_progress_bar $TOTAL_LINES $TOTAL_LINES
            break
        fi
        draw_progress_bar $CURRENT $TOTAL_LINES
        sleep 0.5
    done

    echo -e "\n${GREEN}✓ Importados $CURRENT registros${NC}\n"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" | tr -d ' ')
    echo -e "${GREEN}✓ operadoras_rn1 já contém $COUNT registros${NC}"
fi

# Importar operadoras_stfc
if ! check_table "operadoras_stfc"; then
    echo -e "${BLUE}📊 Importando operadoras_stfc${NC}"

    TOTAL_LINES=$(grep -c "^(" "$SQL_DIR/operadoras_stfc.sql" || echo "0")
    echo -e "   Total de registros: ${BOLD}$TOTAL_LINES${NC}\n"

    # Importar em background
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/operadoras_stfc.sql" > /dev/null 2>&1 &
    PID=$!

    # Monitorar progresso
    while kill -0 $PID 2>/dev/null; do
        CURRENT=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" 2>/dev/null | tr -d ' ' || echo "0")
        draw_progress_bar $CURRENT $TOTAL_LINES
        sleep 0.5
    done

    FINAL=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" | tr -d ' ')
    draw_progress_bar $FINAL $FINAL
    echo -e "\n${GREEN}✓ Importados $FINAL registros${NC}\n"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" | tr -d ' ')
    echo -e "${GREEN}✓ operadoras_stfc já contém $COUNT registros${NC}"
fi

# Importar faixa_operadora (arquivo grande)
if ! check_table "faixa_operadora"; then
    echo -e "${BLUE}📊 Importando faixa_operadora${NC}"
    echo -e "${YELLOW}   ⚠️  Arquivo grande - pode levar alguns minutos${NC}"

    # Estimar total (arquivo muito grande para contar)
    FILE_SIZE=$(stat -c%s "$SQL_DIR/faixa_operadora.sql" 2>/dev/null || echo "0")
    ESTIMATED_LINES=$((FILE_SIZE / 150)) # Estimativa baseada no tamanho médio de linha
    echo -e "   Registros estimados: ${BOLD}~$ESTIMATED_LINES${NC}\n"

    # Importar em background
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_DIR/faixa_operadora.sql" > /dev/null 2>&1 &
    PID=$!

    # Monitorar progresso
    LAST_COUNT=0
    SPEED_COUNTER=0
    while kill -0 $PID 2>/dev/null; do
        CURRENT=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" 2>/dev/null | tr -d ' ' || echo "0")

        # Calcular velocidade
        SPEED=$((CURRENT - LAST_COUNT))
        LAST_COUNT=$CURRENT

        # Mostrar progresso com velocidade
        printf "\r["
        printf "%50s" | tr ' ' '█'
        printf "] ${BOLD}%s${NC} registros | ${GREEN}+%s/seg${NC}  " "$CURRENT" "$SPEED"

        sleep 1
    done

    FINAL=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" | tr -d ' ')
    echo -e "\r${GREEN}✓ Importados $FINAL registros${NC}                              \n"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" | tr -d ' ')
    echo -e "${GREEN}✓ faixa_operadora já contém $COUNT registros${NC}"
fi

# ETAPA 4: Criação de Índices
echo -e "${BOLD}4. OTIMIZAÇÃO DO BANCO${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

INDICES=(
    "idx_rn1_prefixo ON operadoras_rn1(rn1_prefixo)"
    "idx_stfc_spid ON operadoras_stfc(spid)"
    "idx_stfc_eot ON operadoras_stfc(eot)"
    "idx_faixa_ddd_prefixo ON faixa_operadora(ddd, prefixo)"
    "idx_faixa_operadora_completo ON faixa_operadora(ddd, prefixo, faixa_inicio, faixa_fim)"
)

TOTAL_INDICES=${#INDICES[@]}
CURRENT_INDEX=0

for index in "${INDICES[@]}"; do
    CURRENT_INDEX=$((CURRENT_INDEX + 1))
    INDEX_NAME=$(echo $index | cut -d' ' -f1)

    echo -ne "${BLUE}🔧 Criando índice $CURRENT_INDEX/$TOTAL_INDICES: $INDEX_NAME...${NC}"

    if exec_sql "CREATE INDEX IF NOT EXISTS $index;" 2>/dev/null; then
        echo -e "\r${GREEN}✓ Índice $CURRENT_INDEX/$TOTAL_INDICES: $INDEX_NAME criado${NC}                    "
    else
        echo -e "\r${YELLOW}⚠️  Índice $CURRENT_INDEX/$TOTAL_INDICES: $INDEX_NAME já existe${NC}                  "
    fi
done

# Limpar tabela temporária
exec_sql "DROP TABLE IF EXISTS import_progress;" > /dev/null 2>&1

# ETAPA 5: Resumo Final
echo -e "\n${BOLD}5. RESUMO DA IMPORTAÇÃO${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Estatísticas
RN1_COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" | tr -d ' ')
STFC_COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" | tr -d ' ')
FAIXA_COUNT=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" | tr -d ' ')
TOTAL_COUNT=$((RN1_COUNT + STFC_COUNT + FAIXA_COUNT))

echo -e "  ${BOLD}Tabela${NC}                    ${BOLD}Registros${NC}"
echo -e "  ────────────────────────  ─────────"
printf "  %-24s ${GREEN}%'9d${NC}\n" "operadoras_rn1" $RN1_COUNT
printf "  %-24s ${GREEN}%'9d${NC}\n" "operadoras_stfc" $STFC_COUNT
printf "  %-24s ${GREEN}%'9d${NC}\n" "faixa_operadora" $FAIXA_COUNT
echo -e "  ────────────────────────  ─────────"
printf "  ${BOLD}%-24s %'9d${NC}\n" "TOTAL" $TOTAL_COUNT

# Parar PostgreSQL temporário se iniciamos
if [ "$TEMP_PG" = "1" ]; then
    echo -e "\n${YELLOW}🔄 Finalizando PostgreSQL temporário...${NC}"
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop" > /dev/null 2>&1
    echo -e "${GREEN}✓ PostgreSQL finalizado${NC}"
fi

echo -e "\n${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              ${GREEN}IMPORTAÇÃO CONCLUÍDA COM SUCESSO${NC}${BOLD}             ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""