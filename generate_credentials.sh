#!/bin/bash
# Script para gerar credenciais aleatórias

# Função para gerar senha segura
generate_password() {
    # 16 caracteres com letras maiúsculas, minúsculas e números
    tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 16
}

# Gerar credenciais se não existirem
if [ ! -f /app/.credentials ]; then
    # Gerar senhas aleatórias
    export SSH_PASSWORD=$(generate_password)
    export POSTGRES_PASSWORD=$(generate_password)

    # Salvar credenciais
    cat > /app/.credentials << EOF
SSH_USER=root
SSH_PASSWORD=$SSH_PASSWORD
SSH_PORT=2222
POSTGRES_USER=portabilidade
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_PORT=5432
POSTGRES_DB=portabilidade
EOF

    # Proteger arquivo
    chmod 600 /app/.credentials
else
    # Carregar credenciais existentes
    source /app/.credentials
fi

# Exportar variáveis
export SSH_USER
export SSH_PASSWORD
export SSH_PORT
export POSTGRES_USER
export POSTGRES_PASSWORD
export POSTGRES_PORT
export POSTGRES_DB