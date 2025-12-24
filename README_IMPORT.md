# 📊 Sistema de Importação Automática - Portabilidade

## 🚀 Como Ativar Importação Automática

### Opção 1: Via Docker Compose
```yaml
services:
  portabilidade:
    image: portabilidade:latest
    environment:
      - AUTO_IMPORT_HISTORICO=true  # Ativa importação automática
    ports:
      - "8000:8000"
      - "2027:5432"
      - "32:2222"
```

### Opção 2: Via Docker Run
```bash
docker run -d \
  -e AUTO_IMPORT_HISTORICO=true \
  -p 8000:8000 \
  -p 2027:5432 \
  -p 32:2222 \
  portabilidade:latest
```

### Opção 3: Executar Manualmente
```bash
# SSH no container
ssh -p 32 root@portabilidade.i.vsip.com.br

# Executar importação
/app/import_historico_auto.sh
```

## 📋 Variáveis de Ambiente

| Variável | Valores | Padrão | Descrição |
|----------|---------|---------|-----------|
| `AUTO_IMPORT_HISTORICO` | `true`, `false`, `1`, `0` | `false` | Ativa importação automática dos 51M registros |

## ⚙️ O que acontece na importação?

1. **Verifica se já foi importado**: Se já tem 50M+ registros, pula
2. **Baixa arquivo CSV**: 51.6M registros (~11GB descompactado)
3. **Divide em chunks**: 1M registros por chunk (~52 chunks)
4. **Importa cada chunk**:
   - Tenta COPY (rápido)
   - Se falhar, usa INSERT linha por linha
5. **Monitor visual**: Mostra progresso em tempo real

## 📊 Tempo Estimado

- **Download**: ~10-30 minutos (depende da conexão)
- **Importação**: ~2-4 horas (depende do hardware)
- **Total**: ~3-5 horas

## 🔍 Monitorar Progresso

```bash
# Em outro terminal SSH
ssh -p 32 root@portabilidade.i.vsip.com.br
python3 /app/monitor_import.py
```

Você verá:
- Barra de progresso visual
- Velocidade em registros/segundo
- Tempo restante estimado
- Tamanho do banco em tempo real

## 🛠️ Troubleshooting

### Importação travou?
```bash
# Ver logs
tail -f /app/logs/import.log

# Verificar quantos registros foram importados
psql -U portabilidade -d portabilidade -c "SELECT COUNT(*) FROM portabilidade_historico"
```

### Quer recomeçar?
```bash
# Limpar tabela
psql -U portabilidade -d portabilidade -c "TRUNCATE portabilidade_historico"

# Executar novamente
/app/import_historico_auto.sh
```

### Sem espaço em disco?
O arquivo CSV descompactado ocupa ~11GB. Certifique-se de ter pelo menos 25GB livres.

## 📈 Performance Tips

1. **SSD é melhor**: Importação em SSD é 3x mais rápida
2. **Mais RAM ajuda**: PostgreSQL usa RAM para cache
3. **CPU múltiplos cores**: Chunks são processados em paralelo

## 🔐 Credenciais

As credenciais são geradas automaticamente na primeira execução:

```bash
cat /app/.credentials
```

Exemplo:
```
SSH_PASSWORD=Ab3Cd4Ef5Gh6Ij7K
POSTGRES_PASSWORD=Lm8No9Pq0Rs1Tu2V
```