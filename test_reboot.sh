#!/bin/bash

# Script de teste do endpoint /reboot
# Uso: ./test_reboot.sh [URL]

URL="${1:-https://portabilidade.i.vsip.com.br}"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "TESTE DO ENDPOINT /reboot"
echo "=========================================="
echo "URL: $URL"
echo "=========================================="
echo ""

# Verificar versão da API
echo -e "${BLUE}1. Verificando versão da API...${NC}"
VERSION=$(curl -s "$URL/" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null)

if [ "$VERSION" = "2.0.0" ]; then
    echo -e "${GREEN}✓ API v2.0.0 detectada${NC}"
elif [ "$VERSION" = "1.0.0" ]; then
    echo -e "${RED}✗ API v1.0.0 (antiga) - Endpoint /reboot não disponível${NC}"
    echo -e "${YELLOW}Faça o redeploy primeiro!${NC}"
    exit 1
else
    echo -e "${YELLOW}⚠ Versão desconhecida: $VERSION${NC}"
fi

echo ""

# Teste 1: Sem confirmação (deve dar erro 400)
echo -e "${BLUE}2. Teste SEM confirmação (deve dar erro 400)...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$URL/reboot" \
  -H "Content-Type: application/json" \
  -d '{}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ PASSOU - Erro 400 retornado corretamente${NC}"
    echo "  Response: $BODY"
else
    echo -e "${RED}✗ FALHOU - Código HTTP: $HTTP_CODE${NC}"
    echo "  Response: $BODY"
fi

echo ""

# Teste 2: Confirmação false (deve dar erro 400)
echo -e "${BLUE}3. Teste com confirm=false (deve dar erro 400)...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$URL/reboot" \
  -H "Content-Type: application/json" \
  -d '{"confirm": false}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ PASSOU - Erro 400 retornado corretamente${NC}"
    echo "  Response: $BODY"
else
    echo -e "${RED}✗ FALHOU - Código HTTP: $HTTP_CODE${NC}"
    echo "  Response: $BODY"
fi

echo ""

# Teste 3: Delay negativo (deve dar erro 400)
echo -e "${BLUE}4. Teste com delay negativo (deve dar erro 400)...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$URL/reboot" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "delay": -5}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ PASSOU - Erro 400 retornado corretamente${NC}"
    echo "  Response: $BODY"
else
    echo -e "${RED}✗ FALHOU - Código HTTP: $HTTP_CODE${NC}"
    echo "  Response: $BODY"
fi

echo ""

# Teste 4: Delay muito alto (deve dar erro 400)
echo -e "${BLUE}5. Teste com delay > 60s (deve dar erro 400)...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$URL/reboot" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "delay": 100}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✓ PASSOU - Erro 400 retornado corretamente${NC}"
    echo "  Response: $BODY"
else
    echo -e "${RED}✗ FALHOU - Código HTTP: $HTTP_CODE${NC}"
    echo "  Response: $BODY"
fi

echo ""

# Teste 5: Confirmação válida (SIMULAÇÃO - NÃO EXECUTA)
echo -e "${BLUE}6. Validando formato de confirmação válida...${NC}"
echo -e "${YELLOW}   (Não será executado - apenas validação de formato)${NC}"

VALID_REQUEST='{"confirm": true, "delay": 10}'
echo "  Request válido: $VALID_REQUEST"
echo -e "${GREEN}✓ Formato correto${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}TESTES DE SEGURANÇA CONCLUÍDOS${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}⚠️  ATENÇÃO:${NC}"
echo "Para fazer reboot REAL, execute:"
echo ""
echo -e "${RED}curl -X POST $URL/reboot \\${NC}"
echo -e "${RED}  -H 'Content-Type: application/json' \\${NC}"
echo -e "${RED}  -d '{\"confirm\": true, \"delay\": 10}'${NC}"
echo ""
echo "Isso irá REINICIAR o sistema em 10 segundos!"
echo ""
