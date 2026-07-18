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
        {'id': 17, 'marca_id': 5, 'nome': 'CASACOS', 'ordem': 3}
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

    count = sb_table('produtos').select('*', count='exact').eq('marca_id', marca_id).eq('categoria_id', categoria_id).execute().count
    return f"{cat_prefix}{prefixo}{count + 1:02d}"

# Tamanhos disponiveis no catalogo (usados nos checkboxes do admin e nos PDFs por tamanho)
TAMANHOS = ['PP', 'P', 'M', 'G', 'GG', 'XGG']

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
    return tamanho.strip().upper() in disponiveis

def get_dados_completos(tamanho=None):
    if not supabase:
        return {'marcas': [], 'produtos': {}, 'looks': []}

    marcas_resp = sb_table('marcas').select('*').order('ordem').execute()
    marcas = marcas_resp.data or []

    produtos = {}
    for marca in marcas:
        cats_resp = sb_table('categorias').select('*').eq('marca_id', marca['id']).order('ordem').execute()
        categorias = {}
        for cat in cats_resp.data or []:
            prods_resp = sb_table('produtos').select('*').eq('marca_id', marca['id']).eq('categoria_id', cat['id']).eq('ativo', True).order('id').execute()
            prods = [p for p in (prods_resp.data or []) if _disponivel_no_tamanho(p, tamanho)]
            if prods:
                categorias[cat['nome']] = prods
        # Inclui a marca sempre, mesmo sem produtos, para que os links da capa
        # tenham sempre uma pagina de destino (PDF totalmente navegavel/clicavel)
        produtos[marca['nome']] = {'nome': marca['nome'], 'categorias': categorias}

    looks_resp = sb_table('looks').select('*').execute()
    looks = []
    for look in looks_resp.data or []:
        pecas_resp = sb_table('look_pecas').select('*').eq('look_id', look['id']).execute()
        look['pecas'] = pecas_resp.data or []
        looks.append(look)

    return {'marcas': [m['nome'] for m in marcas], 'produtos': produtos, 'looks': looks}

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

@app.route('/api/produtos/<int:marca_id>/<int:categoria_id>')
@requer_senha
def api_produtos(marca_id, categoria_id):
    if not supabase:
        return jsonify([])
    resp = sb_table('produtos').select('*').eq('marca_id', marca_id).eq('categoria_id', categoria_id).eq('ativo', True).order('id').execute()
    return jsonify(resp.data or [])

@app.route('/api/produto', methods=['POST'])
@requer_senha
def criar_produto():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json()
    ref = gerar_ref(data['marca_id'], data['categoria_id'])
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
        'tamanhos': data.get('tamanhos', ','.join(TAMANHOS)),
        'ativo': True
    }
    resp = sb_table('produtos').insert(insert_data).execute()
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else insert_data})

@app.route('/api/produto/<int:prod_id>', methods=['PUT'])
@requer_senha
def atualizar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json()
    update_data = {k: v for k, v in data.items() if k in ['nome', 'descricao', 'preco', 'imagem', 'imagem_detalhe', 'cores', 'tamanhos', 'ativo']}
    resp = sb_table('produtos').update(update_data).eq('id', prod_id).execute()
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else update_data})

@app.route('/api/produto/<int:prod_id>', methods=['DELETE'])
@requer_senha
def deletar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    sb_table('produtos').update({'ativo': False}).eq('id', prod_id).execute()
    return jsonify({'success': True})

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
    # Remove as pecas primeiro (FK) e depois o look
    sb_table('look_pecas').delete().eq('look_id', look_id).execute()
    sb_table('looks').delete().eq('id', look_id).execute()
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
    sb_table('look_pecas').update(update_data).eq('id', peca_id).execute()
    return jsonify({'success': True})

@app.route('/api/peca/<int:peca_id>', methods=['DELETE'])
@requer_senha
def deletar_peca(peca_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    sb_table('look_pecas').delete().eq('id', peca_id).execute()
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
