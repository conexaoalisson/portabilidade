# 📋 Documentação Completa - Sistema API Portabilidade

## 🎯 Visão Geral

O **Sistema API Portabilidade** é uma aplicação containerizada que fornece consultas de portabilidade de números telefônicos brasileiros, permitindo identificar a operadora atual de qualquer número de telefone fixo ou móvel.

### Características Principais:
- ✅ API RESTful com documentação automática (OpenAPI/Swagger)
- ✅ Importação automática de dados na inicialização
- ✅ Credenciais aleatórias geradas automaticamente
- ✅ Console limpo e organizado
- ✅ Deploy automático via webhook
- ✅ Acesso SSH e PostgreSQL remoto

## 🏗️ Arquitetura do Sistema

### Stack Tecnológica:
- **Backend**: FastAPI (Python 3.11)
- **Banco de Dados**: PostgreSQL 17
- **Servidor Web**: Uvicorn
- **Gerenciador de Processos**: Supervisord
- **Container**: Docker
- **CI/CD**: GitHub Webhook

### Estrutura de Diretórios:
```
portabilidade/
├── app/                    # Código da aplicação
│   ├── __init__.py
│   ├── main.py            # API endpoints
│   ├── models.py          # Modelos SQLAlchemy
│   ├── database.py        # Configuração do banco
│   └── import_data.py     # Script de importação
├── sql_postgres/          # Scripts SQL (baixados automaticamente)
├── Dockerfile             # Configuração do container
├── start.sh               # Script de inicialização
├── auto_import.sh         # Importação automática
├── generate_credentials.sh # Gerador de senhas
├── supervisord.conf       # Configuração dos serviços
└── requirements.txt       # Dependências Python
```

## 🚀 Fluxo de Inicialização

### 1. **Geração de Credenciais** (`generate_credentials.sh`)
```bash
# Primeira execução:
- Gera senha aleatória SSH (16 caracteres)
- Gera senha aleatória PostgreSQL (16 caracteres)
- Salva em /app/.credentials
- Arquivo protegido (chmod 600)

# Execuções seguintes:
- Carrega credenciais existentes
```

### 2. **Preparação do Ambiente** (`start.sh`)
```bash
1. Carrega credenciais
2. Prepara diretórios necessários
3. Configura SSH com nova senha
4. Inicializa PostgreSQL (se primeira vez)
5. Cria banco/usuário com credenciais geradas
6. Executa auto_import.sh
7. Exibe credenciais no console
8. Inicia supervisord
```

### 3. **Importação Automática** (`auto_import.sh`)
```bash
1. Verifica se tabelas existem
2. Cria estrutura se necessário (via SQLAlchemy)
3. Baixa arquivos SQL se não existirem:
   - operadoras_rn1.sql.gz
   - operadoras_stfc.sql.gz
   - faixa_operadora.sql.gz
4. Importa dados apenas se tabelas vazias
5. Cria índices otimizados
```

### 4. **Serviços em Execução** (`supervisord.conf`)
```ini
- PostgreSQL (porta 5432 interna)
- FastAPI (porta 8000 interna)
- SSH (porta 2222 interna)
```

## 🔌 API Endpoints

### 1. **GET /** - Status da API
```json
{
  "status": "online",
  "message": "API Portabilidade - Sistema de Consulta de Operadora",
  "version": "2.0.0",
  "endpoints": {...}
}
```

### 2. **GET /health** - Saúde do Sistema
```json
{
  "status": "healthy",
  "database": "connected",
  "tables_count": 4,
  "ssh": "enabled",
  "ssh_port": 2222,
  "api_port": 8000
}
```

### 3. **GET /stats** - Estatísticas
```json
{
  "operadoras_rn1": 312,
  "operadoras_stfc": 2439,
  "faixa_operadora": 234765,
  "total_registros": 237516
}
```

### 4. **POST /consulta** - Consultar Portabilidade
```bash
# Request:
{
  "telefone": "11987654321"
}

# Response:
{
  "telefone": "11987654321",
  "operadora": "VIVO",
  "sigla_operadora": "VIVO",
  "portado": true,
  "ddd": "11",
  "prefixo": "9876",
  "numero": "54321",
  "estado": "SP",
  "tipo_numero": "M"  # M=Móvel, F=Fixo
}
```

### 5. **POST /import** - Importar Dados
```json
{
  "test_mode": false
}
```

### 6. **GET /import/status** - Status da Importação
```json
{
  "running": false,
  "last_run": "completed",
  "last_status": "success",
  "message": "Importação concluída"
}
```

### 7. **GET /info** - Informações de Configuração
```json
{
  "database_url": "postgresql://...",
  "postgres_host": "localhost",
  "postgres_port": 5432,
  "ssh_enabled": true,
  "ssh_port": 2222,
  "api_port": 8000,
  "base_url": "https://techsuper.com.br/baseportabilidade/"
}
```

### 8. **POST /reboot** - Reiniciar Sistema
```json
# Request (CUIDADO!):
{
  "confirm": true,
  "delay": 5
}
```

## 🗄️ Estrutura do Banco de Dados

### Tabela: `operadoras_rn1`
```sql
- id: SERIAL PRIMARY KEY
- nome_operadora: VARCHAR(150)
- cnpj: VARCHAR(20) [indexed]
- rn1_prefixo: VARCHAR(10) UNIQUE [indexed]
```

### Tabela: `operadoras_stfc`
```sql
- id: SERIAL PRIMARY KEY
- eot: VARCHAR(10) [indexed]
- nome_fantasia: VARCHAR(150)
- razao_social: VARCHAR(200)
- cnpj: VARCHAR(25) [indexed]
- rn1: VARCHAR(10) [indexed]
- spid: VARCHAR(10) [indexed]
- ... (mais 14 campos)
```

### Tabela: `faixa_operadora`
```sql
- id: SERIAL PRIMARY KEY
- nome_operadora: VARCHAR(100)
- tipo_numero: VARCHAR(1)
- ddd: VARCHAR(5) [indexed]
- prefixo: VARCHAR(10) [indexed]
- faixa_inicio: INTEGER
- faixa_fim: INTEGER
- sigla_operadora: VARCHAR(10) [indexed]
- estado: VARCHAR(2) [indexed]
```

### Índices Compostos:
- `idx_ddd_prefixo_faixa` em (ddd, prefixo, faixa_inicio, faixa_fim)
- `idx_sigla_operadora` em (sigla_operadora)

## 🔐 Segurança e Credenciais

### Credenciais Geradas Automaticamente:

**SSH:**
- Usuário: `root`
- Senha: `[16 caracteres aleatórios]`
- Porta Externa: `32`

**PostgreSQL:**
- Usuário: `portabilidade`
- Senha: `[16 caracteres aleatórios]`
- Database: `portabilidade`
- Porta Externa: `2027`

### Características de Segurança:
- ✅ Senhas únicas por container
- ✅ Credenciais persistentes (não mudam após criação)
- ✅ Arquivo .credentials protegido (chmod 600)
- ✅ PostgreSQL aceita apenas conexões autenticadas
- ✅ SSH desabilitado para login sem senha

## 🌐 URLs de Acesso

**Produção:**
- API: https://portabilidade.i.vsip.com.br
- Docs: https://portabilidade.i.vsip.com.br/docs
- SSH: `ssh -p 32 root@portabilidade.i.vsip.com.br`
- PostgreSQL: `psql -h portabilidade.i.vsip.com.br -p 2027 -U portabilidade -d portabilidade`

## 📊 Processo de Consulta

1. **Cliente envia número**: `11987654321`
2. **API extrai componentes**:
   - DDD: `11`
   - Prefixo: `9876`
   - Número: `5432`
3. **Busca no banco**:
   ```sql
   SELECT * FROM faixa_operadora
   WHERE ddd = '11'
   AND prefixo = '9876'
   AND faixa_inicio <= 5432
   AND faixa_fim >= 5432
   ```
4. **Retorna operadora encontrada**

## 🔄 Deploy Automático

### GitHub Webhook Configurado:
- URL: `http://66.70.194.86:3000/api/deploy/...`
- Evento: `push`
- Branch: `main`

### Fluxo de Deploy:
1. Push para GitHub
2. Webhook acionado
3. Container reconstruído
4. Credenciais regeneradas
5. Dados reimportados (se necessário)
6. Serviços reiniciados

## 📝 Logs e Monitoramento

### Arquivos de Log:
- `/app/logs/` - Logs da aplicação
- `/app/supervisord.log` - Logs do supervisord
- `/var/log/postgresql/` - Logs do PostgreSQL

### Comandos Úteis (via SSH):
```bash
# Status dos serviços
supervisorctl status

# Logs da API
tail -f /app/logs/api.log

# Verificar importação
cat /app/credentials.txt

# Consultar banco
psql -U portabilidade -d portabilidade
```

## 🛠️ Manutenção

### Reimportar Dados:
```bash
# Via API
curl -X POST https://portabilidade.i.vsip.com.br/import \
  -H "Content-Type: application/json" \
  -d '{"test_mode": false}'
```

### Verificar Credenciais:
```bash
# Via SSH
cat /app/credentials.txt
```

### Monitorar Performance:
```sql
-- Top operadoras consultadas
SELECT sigla_operadora, COUNT(*)
FROM faixa_operadora
GROUP BY sigla_operadora
ORDER BY 2 DESC;
```

## 📈 Performance e Otimizações

- **Índices otimizados** para consultas rápidas
- **Cache de conexões** do SQLAlchemy
- **Import assíncrono** em background
- **Compressão gzip** nos downloads
- **Console limpo** para menor overhead

## 🚨 Troubleshooting

### API não responde:
1. Verificar se container está rodando
2. Checar logs via SSH
3. Reiniciar via `/reboot` endpoint

### Importação falha:
1. Verificar espaço em disco
2. Testar conectividade com fonte de dados
3. Executar importação manual via SSH

### Credenciais perdidas:
1. Acessar via console do Docker
2. Ver arquivo `/app/credentials.txt`
3. Ou reiniciar container (novas credenciais)

---

**Última atualização**: 24/12/2025
**Versão**: 2.0.0
**Mantido por**: Sistema automatizado com Claude Code