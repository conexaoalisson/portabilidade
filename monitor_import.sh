#!/bin/bash

# Script de monitoramento da importação
# Uso: ./monitor_import.sh [URL]

URL="${1:-https://portabilidade.i.vsip.com.br}"
INTERVAL=5  # segundos entre verificações

echo "=========================================="
echo "MONITORAMENTO DE IMPORTAÇÃO"
echo "=========================================="
echo "URL: $URL"
echo "Intervalo: ${INTERVAL}s"
echo "=========================================="
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

while true; do
    # Limpar tela
    clear

    echo "=========================================="
    echo "MONITORAMENTO DE IMPORTAÇÃO"
    echo "=========================================="
    echo "URL: $URL"
    echo "Atualizado: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    # Obter status
    RESPONSE=$(curl -s "$URL/import/status" 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ ERRO: Não foi possível conectar ao servidor${NC}"
        echo ""
        echo "Tentando novamente em ${INTERVAL}s..."
        sleep $INTERVAL
        continue
    fi

    # Parsear JSON (usando python se disponível, senão grep)
    if command -v python3 &> /dev/null; then
        RUNNING=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('running', 'null'))" 2>/dev/null)
        LAST_RUN=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('last_run', 'null'))" 2>/dev/null)
        LAST_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('last_status', 'null'))" 2>/dev/null)
        MESSAGE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', 'null'))" 2>/dev/null)
    else
        RUNNING=$(echo "$RESPONSE" | grep -o '"running":[^,}]*' | cut -d':' -f2 | tr -d ' ')
        LAST_RUN=$(echo "$RESPONSE" | grep -o '"last_run":"[^"]*"' | cut -d'"' -f4)
        LAST_STATUS=$(echo "$RESPONSE" | grep -o '"last_status":"[^"]*"' | cut -d'"' -f4)
        MESSAGE=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    fi

    # Status da importação
    echo "STATUS DA IMPORTAÇÃO:"
    echo "===================="

    if [ "$RUNNING" = "true" ] || [ "$RUNNING" = "True" ]; then
        echo -e "${YELLOW}⏳ IMPORTAÇÃO EM ANDAMENTO${NC}"
        echo ""
        echo -e "${BLUE}Progresso:${NC}"

        # Tentar extrair progresso da mensagem
        if echo "$MESSAGE" | grep -q "Baixando"; then
            echo "  • Download de arquivos..."
        elif echo "$MESSAGE" | grep -q "Importando"; then
            echo "  • Importando dados..."
        elif echo "$MESSAGE" | grep -q "Validando"; then
            echo "  • Validando dados..."
        else
            echo "  • Processando..."
        fi

    elif [ "$RUNNING" = "false" ] || [ "$RUNNING" = "False" ]; then
        if [ "$LAST_STATUS" = "success" ]; then
            echo -e "${GREEN}✓ IMPORTAÇÃO CONCLUÍDA COM SUCESSO${NC}"
        elif [ "$LAST_STATUS" = "error" ]; then
            echo -e "${RED}✗ IMPORTAÇÃO FALHOU${NC}"
        else
            echo -e "${YELLOW}⚪ IMPORTAÇÃO NÃO INICIADA${NC}"
        fi
    else
        echo -e "${YELLOW}⚪ STATUS DESCONHECIDO${NC}"
    fi

    echo ""

    # Última execução
    if [ "$LAST_RUN" != "null" ] && [ "$LAST_RUN" != "None" ] && [ -n "$LAST_RUN" ]; then
        echo "Última Execução: $LAST_RUN"
    fi

    if [ "$LAST_STATUS" != "null" ] && [ "$LAST_STATUS" != "None" ] && [ -n "$LAST_STATUS" ]; then
        echo "Status: $LAST_STATUS"
    fi

    echo ""

    # Mensagem detalhada
    if [ "$MESSAGE" != "null" ] && [ "$MESSAGE" != "None" ] && [ -n "$MESSAGE" ]; then
        echo "MENSAGEM:"
        echo "=========="
        # Limitar a 10 primeiras linhas da mensagem
        echo "$MESSAGE" | head -n 10

        # Se mensagem tem mais de 10 linhas, indicar
        LINE_COUNT=$(echo "$MESSAGE" | wc -l)
        if [ "$LINE_COUNT" -gt 10 ]; then
            echo "..."
            echo "(+ $((LINE_COUNT - 10)) linhas)"
        fi
    fi

    echo ""
    echo "=========================================="

    # Se não está rodando e última execução foi sucesso, verificar stats
    if [ "$RUNNING" = "false" ] && [ "$LAST_STATUS" = "success" ]; then
        echo ""
        echo "ESTATÍSTICAS:"
        echo "============="

        STATS=$(curl -s "$URL/stats" 2>/dev/null)

        if [ $? -eq 0 ]; then
            if command -v python3 &> /dev/null; then
                echo "$STATS" | python3 -m json.tool 2>/dev/null | grep -E '"(operadoras_|faixa_|total_)' | sed 's/^/  /'
            else
                echo "$STATS"
            fi
        fi

        echo ""
        echo -e "${GREEN}✓ Importação completa! Pressione Ctrl+C para sair.${NC}"
        echo ""
    fi

    # Se importação em andamento, atualizar mais rápido
    if [ "$RUNNING" = "true" ]; then
        echo "Próxima atualização em ${INTERVAL}s... (Ctrl+C para sair)"
        sleep $INTERVAL
    else
        echo "Atualização pausada. Pressione Ctrl+C para sair."
        sleep 30  # Se não está rodando, verificar a cada 30s
    fi

done
