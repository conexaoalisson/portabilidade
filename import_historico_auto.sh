#!/bin/bash
# Script automático para importar arquivo de 51M de registros
# Com chunks, COPY/INSERT e progresso visual

export TERM=${TERM:-xterm}

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Arquivo de entrada
CSV_FILE="/tmp/export_full_mysql.csv"
CSV_GZ="${CSV_FILE}.gz"
CSV_URL="http://techsuper.com.br/baseportabilidade/export_full_mysql.csv.gz"

# Função de log com timestamp
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

# Verificar se já foi importado
check_imported() {
    local count=$(psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM portabilidade_historico" 2>/dev/null || echo "0")
    count=$(echo $count | tr -d ' ')

    if [ "$count" -gt "50000000" ]; then
        echo -e "${GREEN}✓ Base já importada: ${count} registros${NC}"
        return 0
    fi
    return 1
}

# Download do arquivo se necessário
download_csv() {
    if [ -f "$CSV_FILE" ]; then
        local size=$(stat -f%z "$CSV_FILE" 2>/dev/null || stat -c%s "$CSV_FILE" 2>/dev/null || echo "0")
        if [ "$size" -gt "1000000000" ]; then # > 1GB
            echo -e "${GREEN}✓ Arquivo já existe: $(du -h $CSV_FILE | cut -f1)${NC}"
            return 0
        fi
    fi

    echo -e "${YELLOW}📥 Baixando arquivo de 51M de registros...${NC}"

    # Baixar com Axel (50 conexões)
    if command -v axel &> /dev/null; then
        axel -n 50 -a "$CSV_URL" -o "$CSV_GZ" 2>&1
    else
        wget --progress=bar:force "$CSV_URL" -O "$CSV_GZ"
    fi

    if [ $? -eq 0 ]; then
        echo -e "${YELLOW}📦 Descompactando...${NC}"
        gunzip -f "$CSV_GZ"
        echo -e "${GREEN}✓ Download concluído${NC}"
        return 0
    else
        echo -e "${RED}✗ Erro no download${NC}"
        return 1
    fi
}

# Executar importação
run_import() {
    echo -e "\n${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         INICIANDO IMPORTAÇÃO DE 51M DE REGISTROS           ║${NC}"
    echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}\n"

    # Executar script Python de importação
    if [ -f "/app/import_chunks_smart.py" ]; then
        python3 /app/import_chunks_smart.py
    else
        echo -e "${RED}✗ Script de importação não encontrado${NC}"
        return 1
    fi
}

# Monitoramento em segundo plano
start_monitor() {
    if [ -f "/app/monitor_import.py" ]; then
        # Iniciar monitor em background
        python3 /app/monitor_import.py &
        MONITOR_PID=$!
        echo -e "${BLUE}🔍 Monitor iniciado (PID: $MONITOR_PID)${NC}"

        # Parar monitor quando script terminar
        trap "kill $MONITOR_PID 2>/dev/null" EXIT
    fi
}

# Main
main() {
    echo -e "\n${BOLD}=== VERIFICAÇÃO DE IMPORTAÇÃO HISTÓRICA ===${NC}\n"

    # Verificar se já foi importado
    if check_imported; then
        echo -e "${GREEN}✓ Importação histórica já realizada${NC}"
        return 0
    fi

    echo -e "${YELLOW}⚠ Base histórica não encontrada${NC}"
    echo -e "${BLUE}ℹ Total esperado: 51.618.684 registros${NC}\n"

    # Verificar se deve importar automaticamente
    if [ "${AUTO_IMPORT_HISTORICO}" = "true" ] || [ "${AUTO_IMPORT_HISTORICO}" = "1" ]; then
        # Modo automático - iniciar importação direto
        echo -e "${YELLOW}🚀 Iniciando importação automática...${NC}"
        echo -e "${BLUE}ℹ Isso pode levar várias horas${NC}\n"

        # Dar 5 segundos para cancelar se necessário
        echo -e "${YELLOW}Iniciando em 5 segundos... (Ctrl+C para cancelar)${NC}"
        for i in {5..1}; do
            echo -ne "\r${YELLOW}Iniciando em $i segundos...${NC}"
            sleep 1
        done
        echo -e "\n"
    else
        # Modo interativo - perguntar
        if [ -t 0 ]; then
            read -p "Deseja iniciar importação agora? [s/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Ss]$ ]]; then
                echo -e "${YELLOW}⏭ Importação pulada${NC}"
                echo -e "${BLUE}ℹ Para importar automaticamente, defina AUTO_IMPORT_HISTORICO=true${NC}"
                return 0
            fi
        else
            echo -e "${YELLOW}⏭ Modo não interativo - pulando importação${NC}"
            echo -e "${BLUE}ℹ Para importar automaticamente, defina AUTO_IMPORT_HISTORICO=true${NC}"
            echo -e "${BLUE}ℹ Para importar manualmente: /app/import_historico_auto.sh${NC}"
            return 0
        fi
    fi

    # Download se necessário
    if ! [ -f "$CSV_FILE" ]; then
        if ! download_csv; then
            return 1
        fi
    fi

    # Iniciar monitor em paralelo
    start_monitor

    # Executar importação
    run_import

    echo -e "\n${GREEN}✓ Processo finalizado${NC}"
}

# Executar apenas se não for sourced
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main
fi