#!/bin/bash
set -e

echo "=== Iniciando API Portabilidade ==="
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          CREDENCIAIS DO POSTGRESQL                        ║"
echo "╠════════════════════════════════════════════════════════════╣"
printf "║  Usuário:  %-47s ║\n" "${POSTGRES_USER}"
printf "║  Senha:    %-47s ║\n" "${POSTGRES_PASSWORD}"
printf "║  Database: %-47s ║\n" "${POSTGRES_DB}"
echo "║  Porta:    5432                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Garantir que diretórios SSH existem
echo "Preparando SSH..."
mkdir -p /var/run/sshd
chmod 755 /var/run/sshd

# Corrigir permissões do diretório PostgreSQL
echo "Corrigindo permissões do PostgreSQL..."
mkdir -p /var/lib/postgresql/data
chown -R postgres:postgres /var/lib/postgresql
chmod 700 /var/lib/postgresql/data

# Verificar se o diretório de dados está vazio (primeira execução)
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    echo "Primeira execução - Inicializando banco de dados PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data"
    su - postgres -c "echo \"host all all 0.0.0.0/0 md5\" >> /var/lib/postgresql/data/pg_hba.conf"
    su - postgres -c "echo \"listen_addresses='*'\" >> /var/lib/postgresql/data/postgresql.conf"
fi

# Iniciar PostgreSQL temporariamente para configuração inicial
echo "Iniciando PostgreSQL para configuração..."
su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data start"

# Aguardar PostgreSQL estar pronto
echo "Aguardando PostgreSQL..."
until su - postgres -c "pg_isready -h localhost -p 5432" > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL iniciado!"

# Criar banco de dados e usuário (sempre tentar criar)
echo "Configurando banco de dados..."
su - postgres -c "psql -h localhost -p 5432 -c \"CREATE DATABASE ${POSTGRES_DB};\" 2>/dev/null || echo 'Database already exists'"
su - postgres -c "psql -h localhost -p 5432 -c \"CREATE USER ${POSTGRES_USER} WITH ENCRYPTED PASSWORD '${POSTGRES_PASSWORD}';\" 2>/dev/null || echo 'User already exists'"
su - postgres -c "psql -h localhost -p 5432 -c \"GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};\" 2>/dev/null || true"
su - postgres -c "psql -h localhost -p 5432 -d ${POSTGRES_DB} -c \"GRANT ALL PRIVILEGES ON SCHEMA public TO ${POSTGRES_USER};\" 2>/dev/null || true"
su - postgres -c "psql -h localhost -p 5432 -c \"ALTER DATABASE ${POSTGRES_DB} OWNER TO ${POSTGRES_USER};\" 2>/dev/null || true"

echo "Banco de dados configurado!"

# Parar PostgreSQL temporário
echo "Parando PostgreSQL temporário..."
su - postgres -c "/usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/data stop"

# Aguardar PostgreSQL parar completamente
sleep 2

# Executar importação automática se necessário
if [ -f /app/auto_import.sh ]; then
    echo ""
    echo "Verificando e importando dados automaticamente..."
    /app/auto_import.sh
fi

# Verificar serviços configurados
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          SERVIÇOS CONFIGURADOS                            ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  PostgreSQL:  porta 5432                                  ║"
echo "║  Web API:     porta 8000 (http)                           ║"
echo "║  SSH:         porta 2222 (root / portabilidade2025)       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Iniciar todos os serviços via Supervisord
echo "Iniciando todos os serviços via Supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
