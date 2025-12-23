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
