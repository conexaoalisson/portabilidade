# Como Adicionar Deploy Key no GitHub

## Sua Chave SSH Pública
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAWbON7TW8gwrNaPmnYTjQ8NiTlhvPTUC7LtT3cxqKLr root@68ad4c48a62d
```

## Passo a Passo para Adicionar no GitHub

### 1. Acesse o Repositório
https://github.com/conexaoalisson/portabilidade

### 2. Vá em Settings
- Clique em **Settings** (engrenagem) no menu do repositório

### 3. Acesse Deploy Keys
- No menu lateral esquerdo, clique em **Deploy keys**
- Ou acesse direto: https://github.com/conexaoalisson/portabilidade/settings/keys

### 4. Adicione a Nova Chave
1. Clique no botão **"Add deploy key"**
2. Preencha os campos:

**Title:**
```
Easypanel Server - 68ad4c48a62d
```

**Key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAWbON7TW8gwrNaPmnYTjQ8NiTlhvPTUC7LtT3cxqKLr root@68ad4c48a62d
```

**Permissões:**
- ✅ **Allow write access** (marcar se quiser fazer push do Easypanel)
- ⬜ Deixe desmarcado se só vai fazer pull/clone

3. Clique em **"Add key"**

### 5. Confirme
Você verá a chave listada em Deploy keys:
- Nome: Easypanel Server - 68ad4c48a62d
- Fingerprint: será gerado automaticamente
- Status: ativo

## Testando no Easypanel

Depois de adicionar a deploy key no GitHub, teste no Easypanel:

```bash
# Teste de conexão SSH com GitHub
ssh -T git@github.com

# Clone do repositório
git clone git@github.com:conexaoalisson/portabilidade.git

# Ou pull se já existe
cd /app
git pull origin main
```

## Resposta Esperada

```
Hi conexaoalisson/portabilidade! You've successfully authenticated, but GitHub does not provide shell access.
```

## URL do Repositório

### HTTPS (não precisa de chave SSH):
```
https://github.com/conexaoalisson/portabilidade.git
```

### SSH (precisa da deploy key):
```
git@github.com:conexaoalisson/portabilidade.git
```

## Comandos no Easypanel

### Clone inicial:
```bash
cd /app
git clone git@github.com:conexaoalisson/portabilidade.git .
```

### Pull das atualizações:
```bash
cd /app
git pull origin main
```

### Ver arquivos baixados:
```bash
ls -la /app
```

## Arquivos que Serão Baixados

Após o clone, você terá acesso a:
- `add_ssh_key.sh` - Script para adicionar chaves SSH
- `recovery_postgresql.sh` - Script de recovery do PostgreSQL
- `QUICK_FIX.md` - Guia rápido de solução
- `RECOVERY_POSTGRESQL.md` - Documentação completa
- `import_csv_copy_chunks.py` - Script de importação
- `import_missing_chunks.py` - Reimportar chunks faltantes
- `app/` - Código da aplicação
- E todos os outros arquivos do projeto

## Troubleshooting

### Erro: Permission denied (publickey)
**Causa:** Deploy key não foi adicionada no GitHub
**Solução:** Siga os passos acima para adicionar a chave

### Erro: Repository not found
**Causa:** URL incorreta ou falta permissão
**Solução:** Verifique se a URL está correta e se a deploy key foi adicionada

### Erro: Host key verification failed
**Causa:** GitHub não está nos known_hosts
**Solução:**
```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

## Links Úteis

- Repositório: https://github.com/conexaoalisson/portabilidade
- Deploy Keys: https://github.com/conexaoalisson/portabilidade/settings/keys
- Documentação GitHub: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account
