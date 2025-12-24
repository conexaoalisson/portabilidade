#!/bin/bash
# Script para executar importação com limite de memória

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== IMPORTAÇÃO COM LIMITE DE MEMÓRIA ===${NC}"
echo ""

# Configurar limites
ulimit -v 2097152  # 2GB de memória virtual máxima
ulimit -m 1572864  # 1.5GB de memória residente máxima

echo -e "${GREEN}Limites configurados:${NC}"
echo "  Memória virtual máxima: 2GB"
echo "  Memória residente máxima: 1.5GB"
echo ""

# Configurar nice para baixa prioridade
echo -e "${YELLOW}Executando com baixa prioridade...${NC}"
nice -n 10 python3 /app/import_low_memory.py

echo -e "${GREEN}Processo finalizado${NC}"