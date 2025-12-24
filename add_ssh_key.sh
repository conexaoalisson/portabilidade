#!/bin/bash
#
# Script para adicionar chave SSH ao servidor
#
# Executar no servidor via Console do Easypanel ou SSH
#

echo "Adicionando chave SSH..."

# Criar diretório .ssh se não existir
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Adicionar chave ao authorized_keys
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAWbON7TW8gwrNaPmnYTjQ8NiTlhvPTUC7LtT3cxqKLr root@68ad4c48a62d
EOF

# Configurar permissões corretas
chmod 600 ~/.ssh/authorized_keys

echo "Chave SSH adicionada com sucesso!"
echo "Arquivo: ~/.ssh/authorized_keys"

# Verificar
echo ""
echo "Chaves cadastradas:"
cat ~/.ssh/authorized_keys
