FROM python:3.11-slim

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Variáveis de ambiente
ENV POSTGRES_USER=portabilidade \
    POSTGRES_PASSWORD=portabilidade123 \
    POSTGRES_DB=portabilidade \
    PGDATA=/var/lib/postgresql/data \
    TERM=xterm

# Instalar PostgreSQL, SSH e dependências
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    supervisor \
    openssh-server \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Configurar PostgreSQL
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql && \
    chmod 700 /var/lib/postgresql/data

# Inicializar banco de dados PostgreSQL
USER postgres
RUN /usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data && \
    echo "host all all 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf && \
    echo "listen_addresses='*'" >> /var/lib/postgresql/data/postgresql.conf && \
    echo "timezone='America/Sao_Paulo'" >> /var/lib/postgresql/data/postgresql.conf

USER root

# Configurar SSH
RUN mkdir -p /var/run/sshd && \
    mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    ssh-keygen -A && \
    sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "root:portabilidade2025" | chpasswd

# Diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app/ ./app/

# Criar diretórios
RUN mkdir -p /app/data /app/logs

# Copiar scripts de inicialização
COPY start.sh /start.sh
COPY auto_import.sh /app/auto_import.sh
COPY generate_credentials.sh /app/generate_credentials.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN chmod +x /start.sh /app/auto_import.sh /app/generate_credentials.sh

# Expor portas
EXPOSE 8000 5432 2222

# Comando de inicialização
CMD ["/start.sh"]
