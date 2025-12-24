#!/bin/bash
set -e

# Definir TERM se não estiver definido
export TERM=${TERM:-xterm}

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

# Função para executar SQL silenciosamente
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

# Função para download com Axel (50 conexões)
download_with_axel() {
    local filename=$1
    local max_retries=3
    local retry=0

    # URLs corretas (sem .gz)
    local url="${BASE_URL}/${filename}.sql"
    local output_file="$SQL_DIR/${filename}.sql"

    while [ $retry -lt $max_retries ]; do
        echo -e "${YELLOW}📥 Baixando ${filename}.sql com Axel (Tentativa $((retry+1))/$max_retries)${NC}"
        echo -e "${BLUE}   → 50 conexões simultâneas para máxima velocidade${NC}"

        mkdir -p "$SQL_DIR"
        rm -f "$output_file" "${output_file}.st" # Limpar arquivo e estado

        # Download com Axel
        # -n 50: 50 conexões
        # -a: Modo alternativo de progresso
        # -v: Verbose
        if axel -n 50 -a -v "$url" -o "$output_file" 2>&1; then
            # Verificar se arquivo foi baixado corretamente
            if [ -f "$output_file" ] && [ -s "$output_file" ]; then
                # Verificar conteúdo SQL válido
                if grep -q "INSERT INTO\|CREATE TABLE" "$output_file" 2>/dev/null; then
                    echo -e "${GREEN}✓ Download concluído com sucesso!${NC}"

                    # Mostrar estatísticas do arquivo
                    local size=$(ls -lh "$output_file" | awk '{print $5}')
                    local lines=$(wc -l < "$output_file")
                    echo -e "${GREEN}   → Tamanho: $size | Linhas: $lines${NC}\n"

                    return 0
                else
                    echo -e "${RED}✗ Arquivo baixado mas conteúdo inválido${NC}"
                fi
            else
                echo -e "${RED}✗ Falha no download ou arquivo vazio${NC}"
            fi
        else
            echo -e "${RED}✗ Erro no Axel${NC}"
        fi

        retry=$((retry + 1))
        if [ $retry -lt $max_retries ]; then
            echo -e "${YELLOW}⏳ Aguardando 5 segundos antes de tentar novamente...${NC}\n"
            sleep 5
        fi
    done

    echo -e "${RED}❌ Falha ao baixar $filename após $max_retries tentativas${NC}"
    return 1
}

# Banner inicial
if [ -t 1 ]; then
    clear
fi

echo -e "${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      IMPORTAÇÃO TURBO COM AXEL - 50 CONEXÕES              ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Iniciar PostgreSQL se necessário
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo -e "${YELLOW}🔄 Iniciando PostgreSQL...${NC}"
    su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start" > /dev/null 2>&1

    for i in {1..10}; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ PostgreSQL iniciado${NC}\n"
            break
        fi
        printf "\r${YELLOW}⏳ Aguardando PostgreSQL... %d/10${NC}" $i
        sleep 0.5
    done
    TEMP_PG=1
fi

# ETAPA 1: Estrutura do Banco
echo -e "${BOLD}1. ESTRUTURA DO BANCO DE DADOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if ! exec_sql "SELECT 1 FROM information_schema.tables WHERE table_name = 'operadoras_rn1';" | grep -q 1 2>/dev/null; then
    echo -e "${BLUE}🔨 Criando tabelas...${NC}\n"

    cd /app
    python3 << 'EOF'
from app.database import engine, Base
from app.models import FaixaOperadora, OperadoraRN1, OperadoraSTFC, PortabilidadeHistorico

print("  → Criando tabelas...", end='', flush=True)
Base.metadata.create_all(bind=engine)
print(" ✓")
EOF

    echo -e "\n${GREEN}✓ Estrutura criada${NC}"
else
    echo -e "${GREEN}✓ Estrutura já existe${NC}"
fi

# ETAPA 2: Download dos Arquivos com Axel
echo -e "\n${BOLD}2. DOWNLOAD TURBO DOS ARQUIVOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Lista de arquivos para baixar
FILES=("operadoras_rn1" "operadoras_stfc" "faixa_operadora")
FILES_TO_DOWNLOAD=()

for file in "${FILES[@]}"; do
    if [ ! -f "$SQL_DIR/${file}.sql" ]; then
        FILES_TO_DOWNLOAD+=("$file")
    fi
done

if [ ${#FILES_TO_DOWNLOAD[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ Todos os arquivos já existem${NC}"
else
    echo -e "${BLUE}📦 Arquivos para baixar: ${#FILES_TO_DOWNLOAD[@]}${NC}\n"

    for file in "${FILES_TO_DOWNLOAD[@]}"; do
        if ! download_with_axel "$file"; then
            echo -e "${RED}❌ Erro crítico no download${NC}"

            if [ "$TEMP_PG" = "1" ]; then
                su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop" > /dev/null 2>&1
            fi

            exit 1
        fi
    done
fi

# ETAPA 3: Importação dos Dados
echo -e "\n${BOLD}3. IMPORTAÇÃO DOS DADOS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Função para importar com feedback
import_table() {
    local table=$1
    local file=$2

    echo -e "${BLUE}📊 Importando $table${NC}"

    # Importar dados
    START_TIME=$(date +%s)

    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -f "$SQL_DIR/${file}.sql" > /dev/null 2>&1 &
    PID=$!

    # Monitorar progresso
    while kill -0 $PID 2>/dev/null; do
        COUNT=$(exec_sql "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0")
        printf "\r   ${YELLOW}→${NC} Registros importados: ${BOLD}%'d${NC}" $COUNT
        sleep 0.5
    done

    # Resultado final
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    FINAL_COUNT=$(exec_sql "SELECT COUNT(*) FROM $table;" | tr -d ' ')

    echo -e "\r   ${GREEN}✓${NC} Importados: ${BOLD}%'d${NC} registros em ${BOLD}${DURATION}s${NC}     \n" $FINAL_COUNT
}

# Importar cada tabela
if ! check_table "operadoras_rn1"; then
    import_table "operadoras_rn1" "operadoras_rn1"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_rn1;" | tr -d ' ')
    echo -e "${GREEN}✓ operadoras_rn1 já contém $COUNT registros${NC}"
fi

if ! check_table "operadoras_stfc"; then
    import_table "operadoras_stfc" "operadoras_stfc"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM operadoras_stfc;" | tr -d ' ')
    echo -e "${GREEN}✓ operadoras_stfc já contém $COUNT registros${NC}"
fi

if ! check_table "faixa_operadora"; then
    import_table "faixa_operadora" "faixa_operadora"
else
    COUNT=$(exec_sql "SELECT COUNT(*) FROM faixa_operadora;" | tr -d ' ')
    echo -e "${GREEN}✓ faixa_operadora já contém $COUNT registros${NC}"
fi

# ETAPA 4: Otimização
echo -e "${BOLD}4. OTIMIZAÇÃO DO BANCO${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${BLUE}🔧 Criando índices otimizados...${NC}"

exec_sql "CREATE INDEX IF NOT EXISTS idx_rn1_prefixo ON operadoras_rn1(rn1_prefixo);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_spid ON operadoras_stfc(spid);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_stfc_eot ON operadoras_stfc(eot);" > /dev/null 2>&1
exec_sql "CREATE INDEX IF NOT EXISTS idx_faixa_ddd_prefixo ON faixa_operadora(ddd, prefixo);" > /dev/null 2>&1

echo -e "${GREEN}✓ Índices criados${NC}"

# Estatísticas finais
echo -e "\n${BOLD}5. RESUMO DA IMPORTAÇÃO${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

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
echo -e "${BOLD}║         ${GREEN}IMPORTAÇÃO TURBO CONCLUÍDA COM SUCESSO${NC}${BOLD}            ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""