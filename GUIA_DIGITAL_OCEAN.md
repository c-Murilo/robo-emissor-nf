# 💧 GUIA COMPLETO - DEPLOY DIGITAL OCEAN

Digital Ocean é perfeito para seu caso:
- ✅ $4-5/mês (mais barato)
- ✅ Chrome funciona 100%
- ✅ Selenium funciona 100%
- ✅ Super fácil de configurar
- ✅ Excelente suporte

---

## 📋 PASSO 1: Criar Conta Digital Ocean

1. Acesse: **https://www.digitalocean.com**
2. Clique em **"Sign up"**
3. Preencha email e senha
4. Verifique email (clique link)
5. Pronto! Está logado

---

## 💳 PASSO 2: Adicionar Método de Pagamento

1. Clique no seu perfil (canto superior direito)
2. Selecione **"Billing"**
3. Clique em **"Add Payment Method"**
4. Adicione cartão de crédito
5. Confirme

⚠️ **Nota:** Digital Ocean cobra apenas pelo que você usar. Mínimo ~$4/mês.

---

## ✅ PASSO 3: Criar Droplet (Servidor)

### Opção A: Uma linha de comando (rápido)

```bash
# Instalar doctl (CLI do Digital Ocean)
brew install doctl

# Autenticar
doctl auth init

# Criar droplet Python
doctl compute droplet create game-nfse \
  --region nyc3 \
  --image python-22-04 \
  --size s-1vcpu-512mb-10gb \
  --enable-monitoring \
  --format ID,Name,PublicIPv4,Status \
  --no-header
```

### Opção B: Web interface (visual)

1. Acesse painel Digital Ocean
2. Clique em **"Create"** (canto superior azul)
3. Selecione **"Droplet"**
4. Configure:

| Campo | Valor |
|-------|-------|
| **Choose an image** | Ubuntu 22.04 x64 |
| **Choose a plan** | Basic ($4/month) |
| **Droplet type** | Regular |
| **CPU options** | Shared |
| **Datacenter region** | New York (nyc3) |
| **Authentication** | Password (mais fácil) |
| **Hostname** | game-nfse |

5. Clique **"Create Droplet"**
6. Aguarde 1-2 minutos

---

## 🔑 PASSO 4: Acessar via SSH

Você receberá um email com:
- **IP público:** ex: 123.45.67.89
- **Root password:** ex: A1b2C3d4E5f6

No terminal:

```bash
ssh root@123.45.67.89

# Será pedida senha (a que você recebeu por email)
# Digite e pressione Enter
```

Pronto! Você está dentro do servidor.

---

## ⚙️ PASSO 5: Instalar Dependências

```bash
# Atualizar sistema
apt update && apt upgrade -y

# Instalar Python 3
apt install -y python3 python3-pip python3-venv

# Instalar Chrome
apt install -y chromium-browser

# Instalar Git
apt install -y git

# Instalar ferramentas úteis
apt install -y curl wget nano
```

Aguarde (vai levar 3-5 minutos)...

---

## 📥 PASSO 6: Clonar seu Repositório

```bash
# Ir para /home
cd /home

# Clonar seu repo (mude seu-usuario)
git clone https://github.com/seu-usuario/game.git

# Entrar na pasta
cd game

# Listar arquivos
ls -la
```

Você deve ver: `app.py`, `logic.py`, `requirements.txt`, `Procfile`, etc.

---

## 🐍 PASSO 7: Instalar Dependências Python

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar
source venv/bin/activate

# Instalar requirements
pip install -r requirements.txt

# Verificar (deve aparecer packages)
pip list
```

Aguarde 2-3 minutos...

---

## 🔐 PASSO 8: Configurar Variáveis de Ambiente

```bash
# Editar .env
nano .env

# Copie e cole (Ctrl+Shift+V):
NFSE_INSCRICAO=seu_cpf_ou_cnpj
NFSE_SENHA=sua_senha
NFSE_URL=https://www.nfse.gov.br/EmissorNacional/Login?ReturnUrl=%2fEmissorNacional
NFSE_CIDADE=Curitiba
NFSE_TRIBUTACAO_BUSCA=fisioterapia
NFSE_DESCRICAO_SERVICO=SERVICOS PRESTADOS DE FISIOTERAPIA
NFSE_INTERVALO_SEGUNDOS=180
NFSE_SELENIUM_DETACH=true
FLASK_ENV=production
PORT=8000

# Salvar: Ctrl+X, depois Y, depois Enter
```

---

## 🚀 PASSO 9: Testar Rodando Localmente

```bash
# Ainda dentro do venv
python app.py

# Você verá:
# * Running on http://0.0.0.0:8000

# Pressione Ctrl+C para parar
```

✅ Funcionou!

---

## 🌐 PASSO 10: Instalar e Configurar Gunicorn

Gunicorn é um servidor profissional para produção:

```bash
# Instalar
pip install gunicorn

# Testar
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app

# Você verá:
# [INFO] Listening at: http://0.0.0.0:8000
# [INFO] Worker spawned

# Pressione Ctrl+C para parar
```

---

## 👤 PASSO 11: Criar Usuário de Serviço (Opcional, mas recomendado)

```bash
# Criar usuário 'game'
useradd -m -s /bin/bash game

# Dar permissão
chown -R game:game /home/game

# Mudar para esse usuário
su - game
```

---

## 🔄 PASSO 12: Criar Serviço Systemd (Auto-start)

```bash
# Voltar para root
exit

# Criar arquivo de serviço
nano /etc/systemd/system/game-nfse.service

# Copie e cole:
[Unit]
Description=Game NFSE Service
After=network.target

[Service]
Type=notify
User=game
WorkingDirectory=/home/game
ExecStart=/home/game/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
Restart=always

[Install]
WantedBy=multi-user.target

# Salvar: Ctrl+X, Y, Enter
```

---

## ✅ PASSO 13: Ativar Serviço

```bash
# Recarregar systemd
systemctl daemon-reload

# Ativar serviço
systemctl enable game-nfse

# Iniciar
systemctl start game-nfse

# Verificar status
systemctl status game-nfse

# Você verá: ● game-nfse.service - Game NFSE Service
#           Loaded: loaded
#           Active: active (running)
```

✅ Pronto! O app vai iniciar automaticamente se o servidor reiniciar.

---

## 🔥 PASSO 14: Abrir Porta no Firewall

```bash
# Instalar UFW (firewall)
apt install -y ufw

# Permitir SSH (IMPORTANTE!)
ufw allow 22

# Permitir porta 8000 (seu app)
ufw allow 8000

# Ativar firewall
ufw enable

# Verificar
ufw status
```

---

## 📝 PASSO 15: Verificar IP Público

```bash
# Seu IP
curl ifconfig.me

# Ou no painel Digital Ocean:
# 1. Clique em "Droplets"
# 2. Procure por "game-nfse"
# 3. Copie o "Public IPv4"
```

---

## 🧪 PASSO 16: Testar no Navegador

```
Acesse: http://SEU_IP_PUBLICO:8000

Você deve ver a página de upload!
```

---

## 📊 DOMÍNIO CUSTOMIZADO (Opcional)

Se tiver um domínio:

1. Digital Ocean → **Networking** → **Domains**
2. Adicione seu domínio
3. Crie registro **A** apontando para seu IP
4. Configure Nginx como proxy (guia separado)

---

## 🆘 MONITORAMENTO

```bash
# Ver logs
journalctl -u game-nfse -f

# Reiniciar serviço
systemctl restart game-nfse

# Parar
systemctl stop game-nfse

# Ver uso de CPU/RAM
top

# Sair: Q
```

---

## 📊 CUSTO

| Item | Preço |
|------|-------|
| Droplet (512 MB) | $4/mês |
| Transferência de dados | Incluído (1 TB/mês) |
| **TOTAL** | **$4/mês** |

Super barato! 💰

---

## 📚 RESUMO RÁPIDO

```bash
# 1. SSH
ssh root@SEU_IP

# 2. Instalar
apt update && apt install -y python3 python3-pip chromium-browser git

# 3. Clonar
cd /home && git clone https://github.com/SEU-USUARIO/game.git && cd game

# 4. Venv
python3 -m venv venv && source venv/bin/activate

# 5. Install
pip install -r requirements.txt

# 6. .env
nano .env
# (adicione variáveis NFSE_*)

# 7. Test
python app.py

# 8. Gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app

# 9. Service
nano /etc/systemd/system/game-nfse.service
# (copie conteúdo da Passo 12)

# 10. Enable
systemctl daemon-reload && systemctl enable game-nfse && systemctl start game-nfse

# 11. Firewall
ufw allow 22 && ufw allow 8000 && ufw enable

# 12. Acessar
# Vá para: http://SEU_IP:8000
```

---

## ✅ CHECKLIST FINAL

- [ ] Conta Digital Ocean criada
- [ ] Método de pagamento adicionado
- [ ] Droplet criado (Ubuntu 22.04)
- [ ] SSH acesso funcionando
- [ ] Sistema atualizado
- [ ] Python + Chrome instalado
- [ ] Repo clonado
- [ ] Venv criado
- [ ] Requirements instalado
- [ ] .env configurado
- [ ] App testado (python app.py)
- [ ] Gunicorn instalado
- [ ] Serviço criado e ativado
- [ ] Firewall configurado
- [ ] App acessível em http://SEU_IP:8000
- [ ] Chrome funciona (sem erro!)

---

## 🎉 PRONTO!

Seu app está rodando **24/7** no Digital Ocean! 🚀

Custo: **$4/mês** apenas!

---

## 📞 PRÓXIMAS DÚVIDAS?

Você pode:
- ✅ Ver logs em tempo real
- ✅ Atualizar código com `git pull`
- ✅ Monitorar CPU/RAM
- ✅ Adicionar domínio customizado
- ✅ Fazer backup

Qualquer coisa, avisa! 💬
