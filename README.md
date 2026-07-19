# AZOZ STORE - Catalogo Online (100% Gratuito)

Render Free + Supabase Free = Zero custo. Edicao online pelo celular. Dados persistentes.
Gera catalogos em PDF clicaveis (botao de compra abre o WhatsApp).

## O que voce precisa (tudo gratis)

1. **Conta no GitHub** → https://github.com
2. **Conta no Supabase** → https://supabase.com
3. **Conta no Render** → https://render.com

## Arquitetura

```
[Seu celular/PC] --edita online--> [Render Free] --salva--> [Supabase Free]
                                         |
                                         +-- gera PDF --> voce baixa e envia
```

- **Render** roda o app (plano Free, Docker, sem Disk)
- **Supabase** guarda os dados (PostgreSQL) e as fotos (Storage)

---

## Instalacao

### 1. Crie o projeto no Supabase

1. Acesse https://supabase.com e crie um projeto (gratis)
2. Va em **Settings > API** e copie:
   - `Project URL` → sera o `SUPABASE_URL`
   - **`service_role`** (secret) → sera o `SUPABASE_KEY`

> ⚠️ **Use a chave `service_role`, NAO a `anon`.** As tabelas usam RLS sem policies,
> entao so a `service_role` (usada pelo servidor) le e escreve. Com a chave `anon` o
> catalogo apareceria sempre vazio. Essa chave e secreta — fica so no Render, nunca no
> codigo/navegador.

### 2. Crie as tabelas e o bucket

No Supabase, va em **SQL Editor > New query**, cole o SQL que esta dentro de
`setup_supabase.py` e clique em **Run**. Isso cria as tabelas (`marcas`, `categorias`,
`produtos`, `looks`, `look_pecas`) com marcas/categorias padrao.

Depois va em **Storage > New bucket**, crie um bucket **publico** chamado `imagens`.

> Alternativa: rodar `python setup_supabase.py` localmente (com o `.env` preenchido) —
> ele imprime o SQL e tenta criar o bucket.

### 3. Deploy no Render

1. Suba o codigo para um repo no GitHub.
2. No Render: **New +** → **Web Service** → conecte o repo.
3. **Runtime:** Docker (detecta sozinho pelo `Dockerfile`) · **Plan:** Free ·
   **Root Directory:** deixe **vazio** (o projeto esta na raiz).
4. Em **Environment**, adicione as variaveis:

| Variavel | Valor |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | chave **service_role** |
| `BUCKET_NAME` | `imagens` |
| `ADMIN_PASSWORD` | senha do painel `/admin` (escolha uma forte) |
| `WHATSAPP_NUMBER` | numero do WhatsApp, so digitos (ex.: `5562999998888`) |

5. **Create Web Service**. O Render builda e publica.

Pronto:
- `https://seu-app.onrender.com/admin` → painel de edicao (pede a senha)
- `https://seu-app.onrender.com/pdf/M` → baixa o PDF do tamanho M

> O app se mantem acordado sozinho (auto-ping em `/health` a cada 10 min usando a
> `RENDER_EXTERNAL_URL`, que o Render define automaticamente). Para reforcar, aponte um
> monitor externo (UptimeRobot / cron-job.org) para `/health`.

---

## Como usar o painel (`/admin`)

### Cadastrar um produto
1. Escolha a **Marca** e a **Categoria** no topo (os numeros mostram quantos produtos ha
   em cada uma).
2. Clique em **+ Adicionar Produto**. Ele nasce como **RASCUNHO** (selo laranja) e **nao
   aparece no PDF** ainda.
3. Preencha **Nome, Descricao, Preco, Cores** e marque os **Tamanhos disponiveis**
   (`PP, P, M, G, GG, XGG`).
4. Em **Foto**, escolha a imagem: abre a ferramenta de **corte** para enquadrar no layout.
   O **Detalhe** e uma segunda foto opcional (corte quadrado).
5. Nao precisa clicar em salvar a cada campo — o **autosave** grava sozinho ("Salvo ✓").
6. Quando estiver pronto, clique em **Publicar**. So agora ele entra no PDF.

> **Rascunho vs Publicado:** rascunho fica escondido do catalogo enquanto voce trabalha.
> **Despublicar** tira do PDF sem apagar. **Duplicar** clona o produto (foto, textos,
> preco, tamanhos) como um novo rascunho — otimo para variacao de cor.

### Controle de estoque por tamanho
Cada produto guarda em quais tamanhos existe. Esgotou o **P**? Abra o produto, **desmarque
o P** e salve — ele some do **PDF do tamanho P**, mas continua nos outros.

### Buscar
Use o campo **🔎 Buscar** para achar por nome ou REF em todas as marcas (inclui rascunhos).
O botao **Abrir** leva direto ao produto.

### Looks (sugestoes de look)
Na aba **Looks**: **+ Adicionar Look**, depois **+ Add produto** (escolhe um produto
existente) ou **+ Peca manual**. Cada peca tem foto e campos proprios. O PDF mostra o look
com botao "Comprar o look completo".

### Gerar o PDF
Na aba **Produtos**, cada botao de tamanho mostra quantos produtos publicados entram nele
(ex.: `PDF M (8)`). Um clique baixa o PDF daquele tamanho. Cada botao **Comprar** no PDF
abre o WhatsApp com a REF na mensagem.

---

## Referencia rapida

| Rota | O que faz |
|---|---|
| `/admin` | Painel de edicao (protegido por `ADMIN_PASSWORD`) |
| `/pdf/<tamanho>` | Baixa o catalogo em PDF (ex.: `/pdf/GG`) |
| `/preview/<tamanho>` | Preview em HTML do catalogo |
| `/health` | Checagem de saude (usada pelo keep-alive) |

Tamanhos: `PP, P, M, G, GG, XGG`.

---

## Atualizar o codigo

```bash
git add .
git commit -m "nova funcionalidade"
git push origin main   # o Render faz deploy automatico
```

Os dados no Supabase nao sao afetados por deploys.

### Migracoes ja incluidas
Se voce criou o banco antes destas versoes, rode no **SQL Editor** para garantir a coluna
de tamanhos (tambem esta em `setup_supabase.py`):

```sql
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS tamanhos TEXT DEFAULT 'PP,P,M,G,GG,XGG';
```

---

## Rodar localmente (opcional)

```bash
pip install -r requirements.txt
# WeasyPrint precisa das libs do sistema (Linux: libpango, libgdk-pixbuf...).
# No Docker/Render ja vem tudo pronto pelo Dockerfile.

cp .env.example .env   # preencha com seus dados do Supabase
python app.py          # http://localhost:5000/admin
```

---

## Limites gratuitos

| Servico | Limite | Da para... |
|---|---|---|
| Supabase DB | 500 MB | ~10.000 produtos |
| Supabase Storage | 1 GB | centenas de fotos |
| Render Free | 512 MB RAM | suficiente |

> Dica de peso do PDF: as fotos sao cortadas em ate 1500px. Um catalogo de 30-45 fotos
> costuma ficar em ~20-50 MB. O WhatsApp aceita ate ~100 MB por documento.

## Duvidas

**"E se eu apagar o projeto no Render?"**
→ Cria outro, aponta pro mesmo Supabase. Dados intactos.

**"E se eu apagar o projeto no Supabase?"**
→ Ai sim perde tudo. Mas o Supabase nao apaga sozinho.

**"Meu catalogo esta vazio, por que?"**
→ Confira se a `SUPABASE_KEY` e a **service_role** e se os produtos foram **publicados**
(rascunho nao entra no PDF).
