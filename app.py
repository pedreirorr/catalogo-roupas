#!/usr/bin/env python3
"""
AZOZ STORE - Catalogo de Roupas em PDF
Python + Flask + Supabase (PostgreSQL + Storage) + WeasyPrint
100% gratuito: Render Free + Supabase Free
"""

import os
import hmac
import time
import threading
import urllib.request
from io import BytesIO
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, Response
from werkzeug.utils import secure_filename
from weasyprint import HTML
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'imagens')

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Senha do painel admin (obrigatoria em producao)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

# Numero do WhatsApp dos botoes de compra (sem + e sem espacos)
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '5562982103793')

# Limite de 8MB por upload
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
EXTENSOES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp'}

def requer_senha(f):
    """Protege rotas com Basic Auth. O navegador pede a senha uma vez e reenvia sozinho."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return Response('Configure a variavel ADMIN_PASSWORD no Render (Environment).', 500)
        auth = request.authorization
        if not auth or not hmac.compare_digest(auth.password or '', ADMIN_PASSWORD):
            return Response('Acesso restrito', 401, {'WWW-Authenticate': 'Basic realm="Azoz Admin"'})
        return f(*args, **kwargs)
    return wrapper

# ============ SUPABASE HELPERS ============

def sb_table(table):
    if not supabase:
        return None
    return supabase.table(table)

def init_supabase():
    """Cria tabelas e bucket se nao existirem. Rode localmente uma vez."""
    if not supabase:
        print("⚠️  SUPABASE_URL e SUPABASE_KEY nao configurados!")
        print("   Crie uma conta em https://supabase.com")
        print("   Crie um projeto, va em Settings > API, copie URL e anon key")
        print("   No Render, adicione como Environment Variables")
        return

    # Verificar/criar bucket
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [b['name'] if isinstance(b, dict) else getattr(b, 'name', None) for b in buckets]
        if BUCKET_NAME not in bucket_names:
            supabase.storage.create_bucket(BUCKET_NAME, {'public': True})
            print(f"✅ Bucket '{BUCKET_NAME}' criado")
    except Exception as e:
        print(f"Bucket check: {e}")

    # Inserir marcas padrao
    marcas = [
        {'id': 1, 'nome': 'LACOSTE', 'prefixo': 'L', 'ordem': 1},
        {'id': 2, 'nome': 'TOMMY HILFIGER', 'prefixo': 'T', 'ordem': 2},
        {'id': 3, 'nome': "LEVI'S", 'prefixo': 'V', 'ordem': 3},
        {'id': 4, 'nome': 'CALVIN KLEIN', 'prefixo': 'K', 'ordem': 4},
        {'id': 5, 'nome': 'AZOZ', 'prefixo': 'A', 'ordem': 5}
    ]
    for m in marcas:
        try:
            sb_table('marcas').upsert(m).execute()
        except Exception as e:
            print(f"Aviso ao inserir marca {m['nome']}: {e}")

    # Inserir categorias padrao
    cats = [
        {'id': 1, 'marca_id': 1, 'nome': 'CAMISETAS', 'ordem': 1},
        {'id': 2, 'marca_id': 1, 'nome': 'POLO', 'ordem': 2},
        {'id': 3, 'marca_id': 1, 'nome': 'CAMISAS', 'ordem': 3},
        {'id': 4, 'marca_id': 1, 'nome': 'CASACOS', 'ordem': 4},
        {'id': 5, 'marca_id': 2, 'nome': 'CAMISETAS', 'ordem': 1},
        {'id': 6, 'marca_id': 2, 'nome': 'POLO', 'ordem': 2},
        {'id': 7, 'marca_id': 2, 'nome': 'CAMISAS', 'ordem': 3},
        {'id': 8, 'marca_id': 2, 'nome': 'CASACOS', 'ordem': 4},
        {'id': 9, 'marca_id': 3, 'nome': 'CAMISETAS', 'ordem': 1},
        {'id': 10, 'marca_id': 3, 'nome': 'CAMISAS', 'ordem': 2},
        {'id': 11, 'marca_id': 3, 'nome': 'CASACOS', 'ordem': 3},
        {'id': 12, 'marca_id': 4, 'nome': 'CAMISETAS', 'ordem': 1},
        {'id': 13, 'marca_id': 4, 'nome': 'CAMISAS', 'ordem': 2},
        {'id': 14, 'marca_id': 4, 'nome': 'CASACOS', 'ordem': 3},
        {'id': 15, 'marca_id': 5, 'nome': 'CAMISETAS', 'ordem': 1},
        {'id': 16, 'marca_id': 5, 'nome': 'CAMISAS', 'ordem': 2},
        {'id': 17, 'marca_id': 5, 'nome': 'CASACOS', 'ordem': 3},
        # Novas subcategorias (com tamanhos numericos proprios)
        {'id': 18, 'marca_id': 1, 'nome': 'CALÇAS', 'ordem': 5},
        {'id': 19, 'marca_id': 2, 'nome': 'CALÇAS', 'ordem': 5},
        {'id': 20, 'marca_id': 3, 'nome': 'CALÇAS', 'ordem': 5},
        {'id': 21, 'marca_id': 4, 'nome': 'CALÇAS', 'ordem': 5},
        {'id': 22, 'marca_id': 5, 'nome': 'CALÇAS', 'ordem': 5},
        {'id': 23, 'marca_id': 1, 'nome': 'TÊNIS', 'ordem': 6},
        {'id': 24, 'marca_id': 2, 'nome': 'TÊNIS', 'ordem': 6},
        {'id': 25, 'marca_id': 3, 'nome': 'TÊNIS', 'ordem': 6},
        {'id': 26, 'marca_id': 4, 'nome': 'TÊNIS', 'ordem': 6},
        {'id': 27, 'marca_id': 5, 'nome': 'TÊNIS', 'ordem': 6}
    ]
    for cat in cats:
        try:
            sb_table('categorias').upsert(cat).execute()
        except Exception as e:
            print(f"Aviso ao inserir categoria {cat['nome']}: {e}")

    print("✅ Supabase inicializado!")

# ============ HELPERS ============

def gerar_ref(marca_id, categoria_id):
    if not supabase:
        return "REF000"

    marca = sb_table('marcas').select('*').eq('id', marca_id).single().execute().data
    prefixo = marca['prefixo'] if marca else 'X'

    cat = sb_table('categorias').select('*').eq('id', categoria_id).single().execute().data
    cat_nome = cat['nome'] if cat else 'OUTROS'

    # Cada categoria tem prefixo unico para a REF nunca se repetir
    cat_map = {'CAMISETAS': 'CT', 'POLO': 'PL', 'CAMISAS': 'CM', 'CASACOS': 'CS'}
    cat_prefix = cat_map.get(cat_nome, 'XX')

    # Numera a partir do maior sufixo ja existente (robusto a exclusoes de
    # produtos: evita gerar uma REF que ja pertence a outro produto).
    inicio = f"{cat_prefix}{prefixo}"
    existentes = sb_table('produtos').select('ref').eq('marca_id', marca_id).eq('categoria_id', categoria_id).execute().data or []
    maior = 0
    for p in existentes:
        ref = (p.get('ref') or '')
        sufixo = ref[len(inicio):]
        if ref.startswith(inicio) and sufixo.isdigit():
            maior = max(maior, int(sufixo))
    return f"{inicio}{maior + 1:02d}"

# Tamanhos padrao (roupas em geral) e tamanhos especificos por categoria.
TAMANHOS = ['PP', 'P', 'M', 'G', 'GG', 'XGG']
TAMANHOS_POR_CATEGORIA = {
    'CALCAS': ['38', '40', '42', '44', '46', '48'],
    'CALÇAS': ['38', '40', '42', '44', '46', '48'],
    'TENIS': ['38', '39', '40', '41', '42', '43'],
    'TÊNIS': ['38', '39', '40', '41', '42', '43'],
}

def tamanhos_da_categoria(cat_nome):
    return TAMANHOS_POR_CATEGORIA.get((cat_nome or '').strip().upper(), TAMANHOS)

def calcular_promo(preco, modo, valor):
    """Retorna (preco_final, percentual_desconto) ou None se nao ha promocao valida."""
    try:
        valor = float(valor or 0)
        preco = float(preco or 0)
    except (TypeError, ValueError):
        return None
    if valor <= 0 or preco <= 0:
        return None
    if modo == 'reais':
        if valor >= preco:
            return None  # desconto invalido: nao aplica
        final = preco - valor
        pct = (valor / preco) * 100
    else:  # 'pct'
        pct = min(valor, 99)
        final = preco * (1 - pct / 100)
    return (round(final, 2), pct)

# Disponibiliza o calculo de promocao para o template do PDF
app.jinja_env.globals['calcular_promo'] = calcular_promo

def _disponivel_no_tamanho(prod, tamanho):
    """Diz se o produto deve aparecer no PDF do tamanho pedido.

    - tamanho=None (preview geral) -> mostra tudo.
    - produtos sem a coluna 'tamanhos' (dados legados) -> aparecem em todos.
    - lista vazia de tamanhos (esgotado em todos) -> nao aparece em nenhum.
    """
    if not tamanho:
        return True
    val = prod.get('tamanhos')
    if val is None:
        return True
    disponiveis = [t.strip().upper() for t in val.split(',') if t.strip()]
    return str(tamanho).strip().upper() in disponiveis

def _montar_catalogo(filtro, incluir_looks=True):
    """Monta a estrutura do catalogo (marcas -> categorias -> produtos).

    filtro(prod, marca, cat) -> bool decide se o produto entra.
    """
    if not supabase:
        return {'marcas': [], 'produtos': {}, 'looks': []}

    marcas = sb_table('marcas').select('*').order('ordem').execute().data or []
    produtos = {}
    for marca in marcas:
        cats = sb_table('categorias').select('*').eq('marca_id', marca['id']).order('ordem').execute().data or []
        categorias = {}
        for cat in cats:
            prods = sb_table('produtos').select('*').eq('marca_id', marca['id']).eq('categoria_id', cat['id']).eq('ativo', True).order('id').execute().data or []
            prods = [p for p in prods if filtro(p, marca, cat)]
            if prods:
                categorias[cat['nome']] = prods
        # Inclui a marca sempre, para que os links da capa tenham destino.
        produtos[marca['nome']] = {'nome': marca['nome'], 'categorias': categorias}

    looks = []
    if incluir_looks:
        for look in (sb_table('looks').select('*').execute().data or []):
            look['pecas'] = sb_table('look_pecas').select('*').eq('look_id', look['id']).execute().data or []
            looks.append(look)

    return {'marcas': [m['nome'] for m in marcas], 'produtos': produtos, 'looks': looks}

def get_dados_completos(tamanho=None):
    """Catalogo por um unico tamanho (ou tudo, se tamanho=None)."""
    return _montar_catalogo(lambda p, m, c: _disponivel_no_tamanho(p, tamanho))

def get_dados_combo(itens):
    """Catalogo combinando varios filtros. Cada item: {marca_id?, categoria?, tamanho}.
    Um produto entra se casar QUALQUER item (uniao)."""
    def filtro(p, marca, cat):
        for it in itens:
            mid = it.get('marca_id')
            catname = (it.get('categoria') or '').strip().upper()
            if mid and marca['id'] != mid:
                continue
            if catname and (cat['nome'] or '').strip().upper() != catname:
                continue
            if not _disponivel_no_tamanho(p, it.get('tamanho')):
                continue
            return True
        return False
    return _montar_catalogo(filtro, incluir_looks=False)

# ============ ROTAS ============

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/health')
def health():
    """Endpoint publico e leve, usado pelo keep-alive e por monitores externos."""
    return jsonify({'status': 'ok'})

@app.route('/admin')
@requer_senha
def admin():
    return render_template('admin.html')

@app.route('/api/dados')
@requer_senha
def api_dados():
    return jsonify(get_dados_completos())

@app.route('/api/marcas')
@requer_senha
def api_marcas():
    if not supabase:
        return jsonify([])
    resp = sb_table('marcas').select('*').order('ordem').execute()
    return jsonify(resp.data or [])

@app.route('/api/categorias/<int:marca_id>')
@requer_senha
def api_categorias(marca_id):
    if not supabase:
        return jsonify([])
    resp = sb_table('categorias').select('*').eq('marca_id', marca_id).order('ordem').execute()
    return jsonify(resp.data or [])

# ============ MARCAS E CATEGORIAS (editaveis) ============

def _proximo_id(tabela):
    rows = sb_table(tabela).select('id').execute().data or []
    return (max(r['id'] for r in rows) + 1) if rows else 1

@app.route('/api/marca', methods=['POST'])
@requer_senha
def criar_marca():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({'error': 'Informe o nome da marca.'}), 400
    if sb_table('marcas').select('id').eq('nome', nome).execute().data:
        return jsonify({'error': 'Ja existe uma marca com esse nome.'}), 409
    novo = {'id': _proximo_id('marcas'), 'nome': nome,
            'prefixo': (data.get('prefixo') or nome[:1]).upper()[:2], 'ordem': data.get('ordem', 99)}
    try:
        resp = sb_table('marcas').insert(novo).execute()
    except Exception:
        return jsonify({'error': 'Nao foi possivel criar a marca (nome duplicado?).'}), 409
    return jsonify({'success': True, 'marca': resp.data[0] if resp.data else novo})

@app.route('/api/marca/<int:marca_id>', methods=['PUT'])
@requer_senha
def atualizar_marca(marca_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    update = {}
    if 'nome' in data:
        nome = (data.get('nome') or '').strip()
        if not nome:
            return jsonify({'error': 'Informe o nome da marca.'}), 400
        dup = sb_table('marcas').select('id').eq('nome', nome).execute().data or []
        if any(m['id'] != marca_id for m in dup):
            return jsonify({'error': 'Ja existe uma marca com esse nome.'}), 409
        update['nome'] = nome
    if 'prefixo' in data:
        update['prefixo'] = (data.get('prefixo') or '').upper()[:2]
    if 'ordem' in data:
        update['ordem'] = data['ordem']
    try:
        sb_table('marcas').update(update).eq('id', marca_id).execute()
    except Exception:
        return jsonify({'error': 'Nao foi possivel salvar (nome duplicado?).'}), 409
    return jsonify({'success': True})

@app.route('/api/marca/<int:marca_id>', methods=['DELETE'])
@requer_senha
def deletar_marca(marca_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    n_prod = sb_table('produtos').select('*', count='exact').eq('marca_id', marca_id).execute().count or 0
    n_cat = sb_table('categorias').select('*', count='exact').eq('marca_id', marca_id).execute().count or 0
    if n_prod > 0 or n_cat > 0:
        return jsonify({'error': f'Esta marca tem {n_cat} categoria(s) e {n_prod} produto(s). Mova ou exclua antes.'}), 409
    sb_table('marcas').delete().eq('id', marca_id).execute()
    return jsonify({'success': True})

@app.route('/api/categoria', methods=['POST'])
@requer_senha
def criar_categoria():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    if not data.get('marca_id'):
        return jsonify({'error': 'Marca obrigatoria.'}), 400
    nome = (data.get('nome') or '').strip()
    if not nome:
        return jsonify({'error': 'Informe o nome da categoria.'}), 400
    novo = {'id': _proximo_id('categorias'), 'marca_id': data['marca_id'], 'nome': nome,
            'ordem': data.get('ordem', 99),
            'tamanhos_padrao': data.get('tamanhos_padrao') or ','.join(tamanhos_da_categoria(nome))}
    resp = sb_table('categorias').insert(novo).execute()
    return jsonify({'success': True, 'categoria': resp.data[0] if resp.data else novo})

@app.route('/api/categoria/<int:cat_id>', methods=['PUT'])
@requer_senha
def atualizar_categoria(cat_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    update = {k: v for k, v in data.items() if k in ('nome', 'ordem', 'tamanhos_padrao')}
    if 'nome' in update:
        update['nome'] = (update['nome'] or '').strip()
        if not update['nome']:
            return jsonify({'error': 'Informe o nome da categoria.'}), 400
    sb_table('categorias').update(update).eq('id', cat_id).execute()
    return jsonify({'success': True})

@app.route('/api/categoria/<int:cat_id>', methods=['DELETE'])
@requer_senha
def deletar_categoria(cat_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    n_prod = sb_table('produtos').select('*', count='exact').eq('categoria_id', cat_id).execute().count or 0
    if n_prod > 0:
        return jsonify({'error': f'Esta categoria tem {n_prod} produto(s). Mova ou exclua antes.'}), 409
    sb_table('categorias').delete().eq('id', cat_id).execute()
    return jsonify({'success': True})

@app.route('/api/produtos/<int:marca_id>/<int:categoria_id>')
@requer_senha
def api_produtos(marca_id, categoria_id):
    if not supabase:
        return jsonify([])
    q = sb_table('produtos').select('*').eq('marca_id', marca_id).eq('categoria_id', categoria_id)
    # No painel admin (?incluir_rascunho=1) mostramos tambem os rascunhos (ativo=False).
    # O PDF continua usando get_dados_completos, que filtra ativo=True.
    if request.args.get('incluir_rascunho') != '1':
        q = q.eq('ativo', True)
    resp = q.order('id').execute()
    return jsonify(resp.data or [])

@app.route('/api/produto', methods=['POST'])
@requer_senha
def criar_produto():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json()
    ref = gerar_ref(data['marca_id'], data['categoria_id'])
    # Tamanhos padrao do produto novo vem da categoria (coluna tamanhos_padrao),
    # com fallback para o mapa fixo por nome (dados antigos).
    cat = sb_table('categorias').select('*').eq('id', data['categoria_id']).single().execute().data or {}
    tamanhos_padrao = cat.get('tamanhos_padrao') or ','.join(tamanhos_da_categoria(cat.get('nome', '')))
    insert_data = {
        'marca_id': data['marca_id'],
        'categoria_id': data['categoria_id'],
        'ref': ref,
        'nome': data.get('nome', 'Novo Produto'),
        'descricao': data.get('descricao', ''),
        'preco': data.get('preco', 0),
        'imagem': data.get('imagem', ''),
        'imagem_detalhe': data.get('imagem_detalhe', ''),
        'cores': data.get('cores', ''),
        'tamanhos': data.get('tamanhos', tamanhos_padrao),
        # Nasce como rascunho: nao entra no PDF ate ser publicado no painel.
        'ativo': data.get('ativo', False)
    }
    # Campos de promocao (so incluidos se enviados, para nao quebrar antes da migracao)
    for campo in ('promo_ativa', 'promo_modo', 'promo_valor'):
        if campo in data:
            insert_data[campo] = data[campo]
    # Validacao de desconto em reais
    if insert_data.get('promo_ativa') and insert_data.get('promo_modo') == 'reais':
        if float(insert_data.get('promo_valor') or 0) >= float(insert_data.get('preco') or 0):
            return jsonify({'error': 'O desconto em R$ nao pode ser maior ou igual ao preco.'}), 400
    resp = sb_table('produtos').insert(insert_data).execute()
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else insert_data})

def _nome_arquivo_do_url(url):
    """Extrai o nome do arquivo no bucket a partir da URL publica do Supabase."""
    if not url or not isinstance(url, str):
        return None
    url = url.split('?', 1)[0]  # tira querystring
    marcador = f'/{BUCKET_NAME}/'
    if marcador in url:
        nome = url.split(marcador, 1)[1].strip('/')
        return nome or None
    return None

def _apagar_arquivos_storage(urls):
    """Apaga do bucket os arquivos das URLs informadas (libera espaco). Tolerante a erro."""
    if not supabase:
        return
    nomes = []
    for u in urls:
        n = _nome_arquivo_do_url(u)
        if n:
            nomes.append(n)
    if not nomes:
        return
    try:
        supabase.storage.from_(BUCKET_NAME).remove(nomes)
    except Exception as e:
        print(f"Aviso ao apagar do storage: {e}")

@app.route('/api/produto/<int:prod_id>', methods=['PUT'])
@requer_senha
def atualizar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json()
    update_data = {k: v for k, v in data.items() if k in ['nome', 'descricao', 'preco', 'imagem', 'imagem_detalhe', 'cores', 'tamanhos', 'ativo', 'promo_ativa', 'promo_modo', 'promo_valor']}
    # Validacao de promocao em reais: desconto nao pode ser >= preco
    if update_data.get('promo_ativa') and update_data.get('promo_modo') == 'reais':
        preco = update_data.get('preco')
        if preco is None:
            atual_p = sb_table('produtos').select('preco').eq('id', prod_id).single().execute().data or {}
            preco = atual_p.get('preco')
        if float(update_data.get('promo_valor') or 0) >= float(preco or 0):
            return jsonify({'error': 'O desconto em R$ nao pode ser maior ou igual ao preco.'}), 400
    # Se uma foto esta sendo trocada ou removida, apaga o arquivo antigo do bucket.
    campos_foto = [c for c in ('imagem', 'imagem_detalhe') if c in update_data]
    antigos = []
    if campos_foto:
        atual = sb_table('produtos').select('imagem,imagem_detalhe').eq('id', prod_id).single().execute().data or {}
        for c in campos_foto:
            old = atual.get(c)
            if old and old != update_data.get(c):
                antigos.append(old)
    resp = sb_table('produtos').update(update_data).eq('id', prod_id).execute()
    _apagar_arquivos_storage(antigos)
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else update_data})

@app.route('/api/produto/<int:prod_id>', methods=['DELETE'])
@requer_senha
def deletar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    # Remocao definitiva. (ativo=False agora significa "rascunho", nao "removido".)
    prod = sb_table('produtos').select('imagem,imagem_detalhe').eq('id', prod_id).single().execute().data or {}
    sb_table('produtos').delete().eq('id', prod_id).execute()
    _apagar_arquivos_storage([prod.get('imagem'), prod.get('imagem_detalhe')])
    return jsonify({'success': True})

@app.route('/api/contagem')
@requer_senha
def api_contagem():
    """Quantos produtos publicados entram no PDF de cada tamanho."""
    contagem = {t: 0 for t in TAMANHOS}
    if not supabase:
        return jsonify(contagem)
    resp = sb_table('produtos').select('tamanhos').eq('ativo', True).execute()
    for p in resp.data or []:
        for t in TAMANHOS:
            if _disponivel_no_tamanho(p, t):
                contagem[t] += 1
    return jsonify(contagem)

@app.route('/api/storage')
@requer_senha
def api_storage():
    """Uso do Storage: soma o tamanho das fotos no bucket vs o limite free (1 GB)."""
    limite = 1024 * 1024 * 1024  # 1 GB (plano free do Supabase)
    resultado = {'usado_bytes': 0, 'limite_bytes': limite, 'arquivos': 0, 'ok': False}
    if not supabase:
        return jsonify(resultado)
    try:
        total = 0
        arquivos = 0
        offset = 0
        page = 100
        while True:
            itens = supabase.storage.from_(BUCKET_NAME).list('', {'limit': page, 'offset': offset}) or []
            for it in itens:
                meta = (it.get('metadata') if isinstance(it, dict) else None) or {}
                tam = meta.get('size')
                if tam is not None:
                    total += int(tam)
                    arquivos += 1
            if len(itens) < page:
                break
            offset += page
        resultado.update({'usado_bytes': total, 'arquivos': arquivos, 'ok': True})
    except Exception as e:
        resultado['erro'] = str(e)
    return jsonify(resultado)

@app.route('/api/resumo')
@requer_senha
def api_resumo():
    """Quantidade de produtos por marca e por categoria (para os contadores do painel)."""
    if not supabase:
        return jsonify({'marcas': {}, 'categorias': {}})
    prods = sb_table('produtos').select('marca_id,categoria_id').execute().data or []
    por_marca, por_cat = {}, {}
    for p in prods:
        mid, cid = str(p.get('marca_id')), str(p.get('categoria_id'))
        por_marca[mid] = por_marca.get(mid, 0) + 1
        por_cat[cid] = por_cat.get(cid, 0) + 1
    return jsonify({'marcas': por_marca, 'categorias': por_cat})

@app.route('/api/busca')
@requer_senha
def api_busca():
    """Busca produtos (inclui rascunhos) por nome ou REF, em todas as marcas."""
    q = (request.args.get('q') or '').strip().lower()
    if not supabase or not q:
        return jsonify([])
    prods = sb_table('produtos').select('*').execute().data or []
    marcas = {m['id']: m['nome'] for m in (sb_table('marcas').select('id,nome').execute().data or [])}
    cats = {c['id']: c['nome'] for c in (sb_table('categorias').select('id,nome').execute().data or [])}
    res = []
    for p in prods:
        if q in (p.get('nome') or '').lower() or q in (p.get('ref') or '').lower():
            p = dict(p)
            p['marca_nome'] = marcas.get(p.get('marca_id'), '')
            p['categoria_nome'] = cats.get(p.get('categoria_id'), '')
            res.append(p)
    return jsonify(res[:50])

# ============ LOOKS E PECAS ============

@app.route('/api/look', methods=['POST'])
@requer_senha
def criar_look():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    insert_data = {
        'nome': data.get('nome', 'NOVO LOOK'),
        'descricao': data.get('descricao', 'Curadoria Premium'),
    }
    resp = sb_table('looks').insert(insert_data).execute()
    return jsonify({'success': True, 'look': resp.data[0] if resp.data else insert_data})

@app.route('/api/look/<int:look_id>', methods=['PUT'])
@requer_senha
def atualizar_look(look_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    update_data = {k: v for k, v in data.items() if k in ['nome', 'descricao']}
    sb_table('looks').update(update_data).eq('id', look_id).execute()
    return jsonify({'success': True})

@app.route('/api/look/<int:look_id>', methods=['DELETE'])
@requer_senha
def deletar_look(look_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    # Remove as pecas primeiro (FK) e depois o look, apagando as fotos do bucket
    pecas = sb_table('look_pecas').select('imagem').eq('look_id', look_id).execute().data or []
    sb_table('look_pecas').delete().eq('look_id', look_id).execute()
    sb_table('looks').delete().eq('id', look_id).execute()
    _apagar_arquivos_storage([p.get('imagem') for p in pecas])
    return jsonify({'success': True})

@app.route('/api/look/<int:look_id>/peca', methods=['POST'])
@requer_senha
def criar_peca(look_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    insert_data = {
        'look_id': look_id,
        'ref': data.get('ref', ''),
        'marca': data.get('marca', ''),
        'nome': data.get('nome', 'Nova peca'),
        'descricao': data.get('descricao', ''),
        'preco': data.get('preco', 0),
        'imagem': data.get('imagem', ''),
    }
    resp = sb_table('look_pecas').insert(insert_data).execute()
    return jsonify({'success': True, 'peca': resp.data[0] if resp.data else insert_data})

@app.route('/api/peca/<int:peca_id>', methods=['PUT'])
@requer_senha
def atualizar_peca(peca_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json() or {}
    update_data = {k: v for k, v in data.items() if k in ['ref', 'marca', 'nome', 'descricao', 'preco', 'imagem']}
    antigo = None
    if 'imagem' in update_data:
        atual = sb_table('look_pecas').select('imagem').eq('id', peca_id).single().execute().data or {}
        old = atual.get('imagem')
        if old and old != update_data.get('imagem'):
            antigo = old
    sb_table('look_pecas').update(update_data).eq('id', peca_id).execute()
    _apagar_arquivos_storage([antigo])
    return jsonify({'success': True})

@app.route('/api/peca/<int:peca_id>', methods=['DELETE'])
@requer_senha
def deletar_peca(peca_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    peca = sb_table('look_pecas').select('imagem').eq('id', peca_id).single().execute().data or {}
    sb_table('look_pecas').delete().eq('id', peca_id).execute()
    _apagar_arquivos_storage([peca.get('imagem')])
    return jsonify({'success': True})

@app.route('/api/upload', methods=['POST'])
@requer_senha
def upload_imagem():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    if 'imagem' not in request.files:
        return jsonify({'error': 'Nenhuma imagem'}), 400
    file = request.files['imagem']
    if file.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in EXTENSOES_PERMITIDAS:
        return jsonify({'error': f'Formato nao permitido. Use: {", ".join(sorted(EXTENSOES_PERMITIDAS))}'}), 400
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}{ext}"

    file_bytes = file.read()
    supabase.storage.from_(BUCKET_NAME).upload(filename, file_bytes, {'content-type': file.content_type})

    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    return jsonify({'success': True, 'url': public_url})

@app.route('/pdf/<tamanho>')
def gerar_pdf(tamanho):
    tamanho = tamanho.upper()
    dados = get_dados_completos(tamanho)
    html = render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=f'TAMANHO {tamanho}', marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], whatsapp=WHATSAPP_NUMBER)

    # PDF gerado em memoria: nada fica gravado no disco do servidor
    pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
    return send_file(BytesIO(pdf_bytes), as_attachment=True, download_name=f'catalogo_{tamanho}.pdf', mimetype='application/pdf')

@app.route('/preview/<tamanho>')
def preview_pdf(tamanho):
    tamanho = tamanho.upper()
    dados = get_dados_completos(tamanho)
    return render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=f'TAMANHO {tamanho}', marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], whatsapp=WHATSAPP_NUMBER)

def _parse_combo_itens():
    """Le os itens do combo da querystring (?itens=<json>)."""
    import json
    try:
        itens = json.loads(request.args.get('itens', '[]'))
    except Exception:
        itens = []
    # normaliza marca_id para int quando vier
    norm = []
    for it in itens if isinstance(itens, list) else []:
        if not it.get('tamanho') and not it.get('categoria'):
            continue
        mid = it.get('marca_id')
        try:
            mid = int(mid) if mid not in (None, '', 'null') else None
        except Exception:
            mid = None
        norm.append({'marca_id': mid, 'categoria': it.get('categoria') or None, 'tamanho': it.get('tamanho') or None})
    return norm

def _combo_subtitulo(itens, marcas_nomes):
    partes = []
    for it in itens:
        p = it.get('categoria') or 'TAMANHO'
        if it.get('tamanho'):
            p = f"{p} {it['tamanho']}"
        partes.append(p)
    txt = ' + '.join(partes) if partes else 'COMBO'
    return txt.upper()[:70]

@app.route('/pdf-combo')
def gerar_pdf_combo():
    itens = _parse_combo_itens()
    dados = get_dados_combo(itens)
    subt = _combo_subtitulo(itens, dados['marcas'])
    html = render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=subt, marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], whatsapp=WHATSAPP_NUMBER)
    pdf_bytes = HTML(string=html, base_url=request.host_url).write_pdf()
    return send_file(BytesIO(pdf_bytes), as_attachment=True, download_name='catalogo_combo.pdf', mimetype='application/pdf')

@app.route('/preview-combo')
def preview_pdf_combo():
    itens = _parse_combo_itens()
    dados = get_dados_combo(itens)
    subt = _combo_subtitulo(itens, dados['marcas'])
    return render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=subt, marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], whatsapp=WHATSAPP_NUMBER)

# ============ KEEP-ALIVE (anti-sleep do Render Free) ============

def _keep_alive():
    """Evita que o Render Free hiberne apos 15 min de inatividade.

    Faz um auto-ping periodico na URL publica do proprio servico. Cada ping
    e uma requisicao de entrada que reinicia o contador de inatividade do
    Render, mantendo o servico acordado enquanto ele estiver rodando.
    """
    base = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if not base:
        return
    ping_url = f'{base}/health'
    intervalo = int(os.environ.get('KEEP_ALIVE_SECONDS', 10 * 60))
    while True:
        time.sleep(intervalo)
        try:
            with urllib.request.urlopen(ping_url, timeout=30) as resp:
                resp.read()
        except Exception:
            pass  # falha de ping nao deve derrubar o app

# So faz sentido no Render (onde RENDER_EXTERNAL_URL existe). Rodando sob o
# gunicorn, isto e iniciado no import do modulo (nao no bloco __main__).
if os.environ.get('RENDER_EXTERNAL_URL'):
    threading.Thread(target=_keep_alive, daemon=True).start()

if __name__ == '__main__':
    init_supabase()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
