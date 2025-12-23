# 🔄 Guia de Redeploy

O código foi atualizado no GitHub mas o container ainda está rodando a versão antiga.

## ✅ Status Atual

- **GitHub:** v2.0.0 (atualizado) ✅
- **Produção:** v1.0.0 (antiga) ❌
- **Container:** Precisa rebuild

## 📋 Opções de Redeploy

### Opção 1: Via EasyPanel (Recomendado)

1. Acesse o painel do EasyPanel
2. Localize o projeto "portabilidade"
3. Clique em **"Rebuild"** ou **"Redeploy"**
4. Aguarde o build completar (2-5 minutos)
5. Verifique a versão: `curl https://portabilidade.i.vsip.com.br/`

### Opção 2: Via Webhook GitHub

Se o webhook estiver configurado:

1. Qualquer `git push` para `main` deve disparar deploy automático
2. Já fizemos 3 pushes recentes:
   - `5398468` - Sistema de importação
   - `62fc081` - Scripts de monitoramento
   - `5fd542a` - Endpoint de reboot

Se o webhook não disparou automaticamente, verifique:
- GitHub → Settings → Webhooks
- Verificar URL do webhook do EasyPanel
- Verificar logs de entrega

### Opção 3: Rebuild Manual via Docker

Se você tem acesso ao servidor onde roda o EasyPanel:

```bash
# Encontrar o container
docker ps | grep portabilidade

# Rebuild via docker-compose (se aplicável)
cd /caminho/do/projeto
docker-compose pull
docker-compose up -d --build

# OU via comandos docker diretos
docker stop portabilidade_app
docker rm portabilidade_app
docker build -t portabilidade .
docker run -d --name portabilidade_app portabilidade
```

### Opção 4: Reboot do Sistema via API

⚠️ **Quando o endpoint /reboot estiver disponível:**

```bash
curl -X POST https://portabilidade.i.vsip.com.br/reboot \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "delay": 10}'
```

Isto reiniciará o container, que pode puxar a imagem atualizada (depende da configuração do EasyPanel).

## 🔍 Verificar se Redeploy foi Concluído

```bash
# Verificar versão
curl -s https://portabilidade.i.vsip.com.br/ | python3 -m json.tool

# Deve retornar:
# "version": "2.0.0"

# Verificar novos endpoints
curl -s https://portabilidade.i.vsip.com.br/ | python3 -c "import sys, json; print('\n'.join(json.load(sys.stdin)['endpoints'].keys()))"

# Deve listar:
# health
# consulta
# stats
# import
# import_status
# reboot (NOVO)
```

## 🧪 Testar Após Redeploy

```bash
# 1. Verificar versão
curl https://portabilidade.i.vsip.com.br/

# 2. Testar health
curl https://portabilidade.i.vsip.com.br/health

# 3. Testar stats
curl https://portabilidade.i.vsip.com.br/stats

# 4. Testar endpoint de reboot (validação)
./test_reboot.sh https://portabilidade.i.vsip.com.br

# 5. Iniciar importação de teste
curl -X POST https://portabilidade.i.vsip.com.br/import \
  -H "Content-Type: application/json" \
  -d '{"test_mode": true}'

# 6. Monitorar importação
./monitor_import.sh https://portabilidade.i.vsip.com.br
```

## 📊 Commits Pendentes de Deploy

| Commit | Descrição | Status |
|--------|-----------|--------|
| `014ac88` | Documentação bases de dados | ⏳ Pendente |
| `5398468` | Sistema de importação completo | ⏳ Pendente |
| `62fc081` | Scripts de monitoramento | ⏳ Pendente |
| `5fd542a` | Endpoint de reboot | ⏳ Pendente |

## ❓ Troubleshooting

### Container não atualiza após rebuild

```bash
# Verificar se está usando cache antigo
# No EasyPanel, procure opção "No cache" ou "Clean build"

# Ou via SSH no servidor:
docker system prune -a
```

### Webhook não está funcionando

```bash
# Verificar configuração no GitHub
# Settings → Webhooks → Recent Deliveries
# Verificar se há erros 404, 500, etc.
```

### EasyPanel não responde

```bash
# Acessar via SSH e reiniciar manualmente
ssh root@easypanel.i.vsip.com.br -p 2222
# Senha: portabilidade2025

cd /app
ps aux | grep uvicorn
kill -9 <PID>
# O supervisor deve reiniciar automaticamente
```

## 🎯 Próximos Passos Após Redeploy

1. ✅ Verificar versão 2.0.0
2. ✅ Executar testes de validação
3. ✅ Importar base de dados (modo teste)
4. ✅ Validar importação
5. ✅ Importar base completa
6. ✅ Testar consultas de portabilidade

---

**Última atualização:** 2025-12-23
**Versão alvo:** 2.0.0
