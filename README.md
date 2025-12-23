# API Portabilidade

Sistema de consulta de portabilidade de operadora telefônica.

## 🚀 Características

- **FastAPI** - API moderna e rápida
- **PostgreSQL** - Banco de dados robusto
- **Docker** - Containerizado e pronto para deploy
- **SSH** - Acesso remoto habilitado (porta 22)
- **EasyPanel** - Deploy automático via webhook

## 📋 Requisitos

- Docker
- Docker Compose
- Git

## 🔧 Instalação

### 1. Clonar repositório

```bash
git clone git@github.com:conexaoalisson/portabilidade.git
cd portabilidade
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

### 3. Iniciar containers

```bash
docker-compose up -d
```

## 🌐 Endpoints

### GET `/`
Informações básicas da API

### GET `/health`
Status de saúde da aplicação e banco de dados

### POST `/consulta`
Consulta portabilidade de um telefone

**Body:**
```json
{
  "telefone": "11987654321"
}
```

**Response:**
```json
{
  "telefone": "11987654321",
  "operadora": "TIM",
  "operadora_original": "VIVO",
  "portado": true,
  "ddd": "11",
  "prefixo": "9876"
}
```

### GET `/info`
Informações de configuração

## 🔐 Acesso SSH

- **Porta:** 2222 (mapeada para 22 no container)
- **Usuário:** root
- **Senha:** portabilidade2025

```bash
ssh root@localhost -p 2222
```

## 🗄️ Banco de Dados

- **Host:** localhost
- **Porta:** 5432
- **Database:** portabilidade
- **Usuário:** portabilidade
- **Senha:** portabilidade123

### 📊 Bases de Dados de Portabilidade

As bases de dados de portabilidade estão disponíveis em:

**URL Pública:** `https://techsuper.com.br/baseportabilidade/`

#### Arquivos Disponíveis

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `export_full_mysql.csv.gz` | 852 MB | Base completa de portabilidade (CSV compactado) |
| `faixa_operadora.sql` | 10 MB | Faixas de numeração por operadora |
| `operadoras_rn1.sql` | 36 KB | Cadastro de operadoras RN1 |
| `operadoras_stfc.sql` | 1.8 MB | Cadastro de operadoras STFC |

#### Estrutura das Tabelas

**Tabela: `faixa_operadora`**
```sql
CREATE TABLE `faixa_operadora` (
  `nome_operadora` varchar(100),
  `tipo_numero` char(1),
  `ddi_ddd` varchar(10),
  `ddd` varchar(5),
  `prefixo` varchar(10),
  `faixa_inicio` int,
  `faixa_fim` int,
  `sigla_operadora` varchar(10),
  `estado` varchar(2),
  `codigo_regiao` varchar(10)
);
```

**Tabela: `operadoras_rn1`**
```sql
CREATE TABLE `operadoras_rn1` (
  `nome_operadora` varchar(150),
  `cnpj` varchar(20),
  `rn1_prefixo` varchar(10)
);
```

**Tabela: `operadoras_stfc`**
```sql
CREATE TABLE `operadoras_stfc` (
  `eot` varchar(10),
  `nome_fantasia` varchar(150),
  `razao_social` varchar(200),
  `csp` varchar(10),
  `tipo_servico` varchar(50),
  `modalidade_banda` varchar(50),
  `area_prestacao` varchar(100),
  `holding` varchar(150),
  `cnpj` varchar(25),
  `inscricao_estadual` varchar(50),
  `contato` varchar(100),
  `email` varchar(150),
  `fone` varchar(100),
  `endereco_nf` text,
  `endereco_correspondencia` text,
  `uf` varchar(2),
  `regiao` varchar(10),
  `concessao` varchar(5),
  `rn1` varchar(10),
  `spid` varchar(10)
);
```

#### Importar Dados

**Via Docker SSH:**
```bash
ssh root@easypanel.i.vsip.com.br -p 2222
# Senha: portabilidade2025

# Download dos arquivos
wget https://techsuper.com.br/baseportabilidade/operadoras_rn1.sql
wget https://techsuper.com.br/baseportabilidade/operadoras_stfc.sql
wget https://techsuper.com.br/baseportabilidade/faixa_operadora.sql

# Importar no PostgreSQL
psql -h localhost -p 5432 -U portabilidade -d portabilidade -f operadoras_rn1.sql
psql -h localhost -p 5432 -U portabilidade -d portabilidade -f operadoras_stfc.sql
psql -h localhost -p 5432 -U portabilidade -d portabilidade -f faixa_operadora.sql
```

## 📦 Estrutura do Projeto

```
portabilidade/
├── app/
│   ├── __init__.py
│   ├── main.py          # API principal
│   └── database.py      # Configuração do banco
├── data/                # Dados e imports
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── start.sh
└── README.md
```

## 🚀 Deploy EasyPanel

O projeto está configurado com webhook automático:
- Push para `main` → Deploy automático
- URL Webhook: Configurada no GitHub

## 📝 TODO

- [ ] Implementar consulta real no banco de dados
- [ ] Importar base de dados de portabilidade
- [ ] Adicionar cache Redis
- [ ] Implementar autenticação JWT
- [ ] Adicionar rate limiting
- [ ] Documentação Swagger completa

## 👨‍💻 Desenvolvimento

### Acessar logs

```bash
docker-compose logs -f app
```

### Reiniciar containers

```bash
docker-compose restart
```

### Parar containers

```bash
docker-compose down
```

## 📄 Licença

Privado - Uso interno
