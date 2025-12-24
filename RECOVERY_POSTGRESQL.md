# Recuperação PostgreSQL - Loop Infinito de Recovery

## Problema Identificado

Durante a importação de 51.6M registros (7.1 GB CSV), o PostgreSQL travou em um loop infinito de recovery após crash do container.

### Sintomas

```
2025-12-24 09:42:50.101 -03 [22] LOG:  database system was not properly shut down; automatic recovery in progress
2025-12-24 09:42:50.101 -03 [22] LOG:  redo starts at 3F/100F52D0
2025-12-24 09:43:02.234 -03 [22] LOG:  successfully skipped missing contrecord at 3F/64071030
2025-12-24 09:43:02.234 -03 [22] LOG:  invalid record length at 3F/64072048: expected at least 24, got 0
2025-12-24 09:43:02.234 -03 [22] LOG:  redo done at 3F/64072018
2025-12-24 09:43:02.753 -03 [20] LOG:  checkpoint starting: end-of-recovery immediate wait
```

Container reinicia infinitamente sem conseguir completar o checkpoint final do recovery.

### Causa Raiz

1. **Checkpoint muito grande**: ~38M registros pendentes de checkpoint quando o PostgreSQL crashou
2. **Timeout insuficiente**: `pg_ctl` aguarda apenas 60 segundos por padrão
3. **WAL corrupto**: Arquivos WAL com registros incompletos após crash abrupto
4. **Configurações default**: Checkpoint a cada 5 minutos não é suficiente para carga massiva

## Dados Importados

Antes do crash, foram importados com sucesso:
- **38,000,000 registros** (73.6% do total)
- **Chunks 1-38** completados
- **Chunks 40-52** faltantes (13M registros)

## Solução

### 1. Script de Recuperação

Execute o script `recovery_postgresql.sh` quando o servidor estiver acessível:

```bash
chmod +x recovery_postgresql.sh
./recovery_postgresql.sh
```

### 2. O que o script faz

1. **Para PostgreSQL forçadamente** (SIGKILL se necessário)
2. **Backup dos WAL files** antes de remover
3. **Limpa WAL corrompidos** para forçar recovery limpo
4. **Reconfigura PostgreSQL** com:
   - Checkpoint timeout: 30 minutos
   - Max WAL size: 2GB
   - Logs verbosos para debug
5. **Reinicia com timeout de 600 segundos**
6. **Verifica integridade** dos dados

### 3. Próximos Passos Após Recovery

```bash
# 1. Contar registros preservados
cd /app
python3 -c "from app.database import SessionLocal; from app.models import PortabilidadeHistorico; session = SessionLocal(); print(f'Registros: {session.query(PortabilidadeHistorico).count():,}'); session.close()"

# 2. Retomar importação dos registros faltantes
nohup python3 import_csv_copy_chunks.py > import_resume.log 2>&1 &

# 3. Monitorar progresso
tail -f import_resume.log
```

## Configurações Aplicadas

O script adiciona automaticamente em `postgresql.auto.conf`:

```ini
# Configurações para recovery robusto
checkpoint_timeout = 30min
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 2GB
min_wal_size = 80MB

# Commits mais frequentes
commit_delay = 0
commit_siblings = 5

# Logs para debug
log_checkpoints = on
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p] %u@%d '
```

## Histórico do Problema

### Tentativa 1: ALTER TABLE
- Importados 38M registros com INTEGER
- Chunks 40-52 falharam (integer overflow)
- Tentativa de ALTER TABLE para BIGINT - demorou 50+ minutos

### Tentativa 2: Drop e Recriar (Decisão do usuário)
- Drop da tabela com 38M registros
- Recriar com BIGINT desde o início
- Reimportar todos os 51.6M registros do zero
- **PostgreSQL crashou aos 38M registros** - loop de recovery

## Status Atual

- ✅ Script de recovery criado
- ⏳ Aguardando acesso SSH ao servidor
- ⏳ Executar recovery_postgresql.sh
- ⏳ Verificar quantos registros foram preservados
- ⏳ Retomar importação dos ~14M registros faltantes

## Prevenção Futura

Para evitar este problema em importações massivas:

1. **Configurar checkpoints antes** da importação:
```sql
ALTER SYSTEM SET checkpoint_timeout = '30min';
ALTER SYSTEM SET max_wal_size = '2GB';
SELECT pg_reload_conf();
```

2. **Desabilitar autovacuum** durante importação:
```sql
ALTER TABLE portabilidade_historico SET (autovacuum_enabled = false);
```

3. **Aumentar timeout do pg_ctl** no docker-entrypoint:
```bash
pg_ctl start -D /var/lib/postgresql/data -w -t 600
```

4. **Monitorar WAL usage**:
```sql
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0') / 1024 / 1024 AS wal_mb;
```

## Referências

- [PostgreSQL WAL Configuration](https://www.postgresql.org/docs/current/wal-configuration.html)
- [Checkpoint Tuning](https://www.postgresql.org/docs/current/runtime-config-wal.html)
- [Recovery Process](https://www.postgresql.org/docs/current/continuous-archiving.html)
