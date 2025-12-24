# SOLUÇÃO RÁPIDA - PostgreSQL Loop Infinito

## PROBLEMA
Container PostgreSQL em loop infinito de recovery há 30+ minutos.
SSH inacessível (Connection refused).

## CAUSA
Checkpoint final precisa de 5-10 minutos mas `pg_ctl` tem timeout de apenas 60 segundos.

## SOLUÇÃO IMEDIATA

### 1. Acesse o Console do Container
- Abra: https://easypanel.i.vsip.com.br
- Vá no serviço PostgreSQL
- Clique em "Console" ou "Terminal"

### 2. Cole este comando (TUDO DE UMA VEZ):

```bash
pkill -9 postgres && sleep 3 && rm -rf /var/lib/postgresql/data/pg_wal/* && mkdir -p /var/lib/postgresql/data/pg_wal && chown -R postgres:postgres /var/lib/postgresql/data/pg_wal && chmod 700 /var/lib/postgresql/data/pg_wal && echo "checkpoint_timeout=30min" >> /var/lib/postgresql/data/postgresql.auto.conf && echo "max_wal_size=2GB" >> /var/lib/postgresql/data/postgresql.auto.conf && su - postgres -c "pg_ctl start -D /var/lib/postgresql/data -w -t 600 -l /tmp/pg_start.log" && echo "===== SUCESSO =====" && su - postgres -c "psql -U portabilidade -d portabilidade -c 'SELECT COUNT(*) FROM portabilidade_historico;'" || (echo "===== ERRO - LOGS =====" && cat /tmp/pg_start.log)
```

### 3. Aguarde até 10 minutos

O comando vai:
- Matar PostgreSQL
- Limpar WAL corrompidos
- Reconfigurar checkpoints (30 min timeout)
- Iniciar com timeout de 600 segundos
- Mostrar quantos registros foram preservados

### 4. Resultado Esperado

```
===== SUCESSO =====
  count
----------
 38000000
(1 row)
```

## ALTERNATIVA: Sem Acesso ao Console

### Opção A: Desabilitar Restart Automático
1. Painel Easypanel → Settings do serviço
2. "Restart Policy" → Mude de "always" para "no"
3. Aguarde 10 minutos
4. PostgreSQL deve completar checkpoint

### Opção B: Variável de Ambiente
1. Painel Easypanel → Environment
2. Adicione: `PGCTL_START_TIMEOUT=600`
3. Reinicie container
4. Aguarde 10 minutos

### Opção C: Editar docker-compose.yml
```yaml
command: >
  bash -c "
  /usr/sbin/sshd &&
  rm -rf /var/lib/postgresql/data/pg_wal/* &&
  echo 'checkpoint_timeout=30min' >> /var/lib/postgresql/data/postgresql.auto.conf &&
  echo 'max_wal_size=2GB' >> /var/lib/postgresql/data/postgresql.auto.conf &&
  su - postgres -c 'pg_ctl start -D /var/lib/postgresql/data -w -t 600' &&
  tail -f /dev/null
  "
```

## DEPOIS QUE FUNCIONAR

### 1. Testar SSH
```bash
ssh -p 2222 root@easypanel.i.vsip.com.br
# Senha: portabilidade2025
```

### 2. Contar Registros
```bash
cd /app
python3 -c "from app.database import SessionLocal; from app.models import PortabilidadeHistorico; session = SessionLocal(); print(f'Registros: {session.query(PortabilidadeHistorico).count():,}'); session.close()"
```

### 3. Retomar Importação
```bash
cd /app
nohup python3 import_csv_copy_chunks.py > import_resume.log 2>&1 &
tail -f import_resume.log
```

## DADOS PRESERVADOS
- Estimativa: ~38M registros (73.6%)
- Faltam: ~14M registros
- Tempo restante: ~2-3 horas

## ARQUIVOS DE SUPORTE
- `recovery_postgresql.sh` - Script automático completo
- `RECOVERY_POSTGRESQL.md` - Documentação detalhada
- `import_csv_copy_chunks.py` - Retomar importação

## LOGS DO PROBLEMA

```
2025-12-24 09:42:50.101 [22] LOG:  redo starts at 3F/100F52D0
2025-12-24 09:43:02.234 [22] LOG:  redo done at 3F/64072018
2025-12-24 09:43:02.753 [20] LOG:  checkpoint starting: end-of-recovery immediate wait
pg_ctl: server did not start in time  ← AQUI TRAVA
```

**Recovery completa OK, mas checkpoint timeout em 60s**

## CONTATO
GitHub: https://github.com/conexaoalisson/portabilidade
Commit: b916b2e
