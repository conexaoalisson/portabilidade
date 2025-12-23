#!/bin/bash

# Consulta rápida do status de importação
# Uso: ./check_import.sh [URL]

URL="${1:-https://portabilidade.i.vsip.com.br}"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "Consultando status da importação..."
echo ""

# Obter status
RESPONSE=$(curl -s "$URL/import/status" 2>/dev/null)

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ ERRO: Não foi possível conectar ao servidor${NC}"
    echo "URL: $URL/import/status"
    exit 1
fi

# Exibir JSON formatado se python disponível
if command -v python3 &> /dev/null; then
    echo "$RESPONSE" | python3 -m json.tool

    # Extrair status
    RUNNING=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('running', False))" 2>/dev/null)
    LAST_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('last_status', 'unknown'))" 2>/dev/null)

    echo ""
    echo "=============================="

    if [ "$RUNNING" = "True" ]; then
        echo -e "${YELLOW}⏳ IMPORTAÇÃO EM ANDAMENTO${NC}"
        echo ""
        echo "Use ./monitor_import.sh para acompanhar em tempo real"
    elif [ "$LAST_STATUS" = "success" ]; then
        echo -e "${GREEN}✓ IMPORTAÇÃO CONCLUÍDA${NC}"
        echo ""
        echo "Verificando estatísticas..."
        curl -s "$URL/stats" | python3 -m json.tool 2>/dev/null
    elif [ "$LAST_STATUS" = "error" ]; then
        echo -e "${RED}✗ IMPORTAÇÃO FALHOU${NC}"
    else
        echo -e "${YELLOW}⚪ IMPORTAÇÃO NÃO INICIADA${NC}"
        echo ""
        echo "Para iniciar importação:"
        echo ""
        echo "# Teste (amostra):"
        echo "curl -X POST $URL/import -H 'Content-Type: application/json' -d '{\"test_mode\": true}'"
        echo ""
        echo "# Completa:"
        echo "curl -X POST $URL/import -H 'Content-Type: application/json' -d '{\"test_mode\": false}'"
    fi
else
    echo "$RESPONSE"
fi

echo ""
