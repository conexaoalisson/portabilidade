#!/bin/bash
set -e

# Gerar ou carregar credenciais
source /app/generate_credentials.sh

# Função para log simplificado
log() {
    echo "$(date '+%H:%M:%S') $1"
}

# Banner inicial
clear
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         API PORTABILIDADE - INICIALIZANDO                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Preparar diretórios
log "Preparando ambiente..."
mkdir -p /var/run/sshd /var/lib/postgresql/data /app/logs
chown -R postgres:postgres /var/lib/postgresql
chmod 700 /var/lib/postgresql/data

# Configurar SSH com nova senha
echo "root:$SSH_PASSWORD" | chpasswd 2>/dev/null

# Inicializar PostgreSQL se necessário
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    log "Inicializando banco de dados..."
    su - postgres -c "/usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data" > /dev/null 2>&1
    su - postgres -c "echo \"host all all 0.0.0.0/0 md5\" >> /var/lib/postgresql/data/pg_hba.conf"
    su - postgres -c "echo \"listen_addresses='*'\" >> /var/lib/postgresql/data/postgresql.conf"
fi

# Iniciar PostgreSQL temporário
log "Configurando PostgreSQL..."
su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start" > /dev/null 2>&1

# Aguardar PostgreSQL
until su - postgres -c "pg_isready -h localhost -p 5432" > /dev/null 2>&1; do
  sleep 0.5
done

# Configurar banco com nova senha
su - postgres -c "psql -h localhost -p 5432 -c \"CREATE DATABASE ${POSTGRES_DB};\"" 2>/dev/null || true
su - postgres -c "psql -h localhost -p 5432 -c \"CREATE USER ${POSTGRES_USER} WITH ENCRYPTED PASSWORD '${POSTGRES_PASSWORD}';\"" 2>/dev/null || true
su - postgres -c "psql -h localhost -p 5432 -c \"GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};\"" 2>/dev/null || true
su - postgres -c "psql -h localhost -p 5432 -d ${POSTGRES_DB} -c \"GRANT ALL PRIVILEGES ON SCHEMA public TO ${POSTGRES_USER};\"" 2>/dev/null || true
su - postgres -c "psql -h localhost -p 5432 -c \"ALTER DATABASE ${POSTGRES_DB} OWNER TO ${POSTGRES_USER};\"" 2>/dev/null || true

# Parar PostgreSQL temporário
su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop" > /dev/null 2>&1
sleep 2

# Executar importação automática (output reduzido)
if [ -f /app/auto_import.sh ]; then
    log "Verificando dados..."
    /app/auto_import.sh 2>&1 | grep -E "(✓|Importando|concluíd)" || true
fi

# Exibir credenciais
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    CREDENCIAIS DE ACESSO                   ║"
echo "╠════════════════════════════════════════════════════════════╣"
printf "║  SSH:                                                      ║\n"
printf "║    Usuário: %-46s ║\n" "$SSH_USER"
printf "║    Senha:   %-46s ║\n" "$SSH_PASSWORD"
printf "║    Porta:   %-46s ║\n" "$SSH_PORT"
echo "║                                                            ║"
printf "║  PostgreSQL:                                               ║\n"
printf "║    Usuário: %-46s ║\n" "$POSTGRES_USER"
printf "║    Senha:   %-46s ║\n" "$POSTGRES_PASSWORD"
printf "║    Porta:   %-46s ║\n" "$POSTGRES_PORT"
printf "║    Database: %-45s ║\n" "$POSTGRES_DB"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Salvar credenciais em arquivo para consulta posterior
cat > /app/credentials.txt << EOF
=== CREDENCIAIS API PORTABILIDADE ===

SSH:
  Host: portabilidade.i.vsip.com.br
  Porta: 32
  Usuário: $SSH_USER
  Senha: $SSH_PASSWORD

PostgreSQL:
  Host: portabilidade.i.vsip.com.br
  Porta: 2027
  Usuário: $POSTGRES_USER
  Senha: $POSTGRES_PASSWORD
  Database: $POSTGRES_DB

API:
  URL: https://portabilidade.i.vsip.com.br
  Docs: https://portabilidade.i.vsip.com.br/docs
EOF

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   SERVIÇOS INICIANDO                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Iniciar serviços
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf