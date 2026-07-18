# AZOZ STORE - Catalogo Online (100% Gratuito)

Render Free + Supabase Free = Zero custo. Edicao online. Dados persistentes.

## O que voce precisa (tudo gratis)

1. **Conta no GitHub** (gratis)
2. **Conta no Supabase** (gratis) → https://supabase.com
3. **Conta no Render** (gratis) → https://render.com

## Arquitetura

```
[Seu celular/PC] --edita online--> [Render Free] --salva--> [Supabase Free]
                                         |
                                         +-- gera PDF --> voce baixa
```

- **Render** roda o app (plano Free, sem Disk)
- **Supabase** guarda os dados (PostgreSQL 500MB gratis) e fotos (Storage 1GB gratis)

## Passo a passo

### 1. Crie conta no Supabase

1. Acesse https://supabase.com e crie uma conta
2. Crie um novo projeto (gratis)
3. Va em **Settings > API**
4. Copie:
   - `Project URL` → sera o SUPABASE_URL
   - `anon public` → sera o SUPABASE_KEY

### 2. Configure o banco de dados

Opcao A - Script automatico:
```bash
pip install supabase python-dotenv
# Crie o arquivo .env com seus dados (veja .env.example)
python setup_supabase.py
```

Opcao B - Manual (mais confiavel):
1. No Supabase, va em **SQL Editor**
2. Cole o SQL do arquivo `setup_supabase.py`
3. Clique em **Run**
4. Va em **Storage > New bucket**, crie um bucket chamado `imagens`
5. Em **Storage > Policies**, adicione politica publica para leitura

### 3. Teste localmente

```bash
pip install -r requirements.txt

# No Windows, instale GTK3 para WeasyPrint:
# https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

# Crie o .env
cp .env.example .env
# Edite .env com seus dados do Supabase

python app.py
# Acesse: http://localhost:5000/admin
```

### 4. Deploy no Render

```bash
# Crie o repo no GitHub
git init
git add .
git commit -m "v1.0"
git remote add origin https://github.com/SEU_USUARIO/azoz-store.git
git push -u origin main
```

No Render:
1. https://dashboard.render.com → **New +** → **Web Service**
2. Conecte seu repo GitHub
3. **Runtime:** Docker (detecta automatico)
4. **Plan:** Free
5. Em **Environment**, adicione:
   - `SUPABASE_URL` = seu URL do Supabase
   - `SUPABASE_KEY` = sua chave anon do Supabase
   - `BUCKET_NAME` = imagens
6. **Create Web Service**

Pronto! Acesse:
- `https://seu-app.onrender.com/admin` → Painel de edicao
- `https://seu-app.onrender.com/pdf/M` → Baixar PDF

## Limites gratuitos

| Servico | Limite | Para um catalogo... |
|---------|--------|---------------------|
| Supabase DB | 500MB | ~10.000 produtos |
| Supabase Storage | 1GB | ~500 fotos de 2MB |
| Render | 512MB RAM | Suficiente |

## Se precisar atualizar o codigo

```bash
# Faca alteracoes localmente, teste, depois:
git add .
git commit -m "nova funcionalidade"
git push origin main
# O Render faz deploy automatico!
# Os dados no Supabase NUNCA sao apagados!
```

## Duvidas

**"E se eu apagar o projeto no Render?"**
→ Cria outro, aponta pro mesmo Supabase. Dados intactos.

**"E se eu apagar o projeto no Supabase?"**
→ Ai sim perde tudo. Mas o Supabase nao apaga sozinho.

**"Posso usar outro banco?"**
→ Sim! Neon, MongoDB Atlas, Firebase — todos tem plano gratis.
