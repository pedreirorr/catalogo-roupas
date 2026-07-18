#!/usr/bin/env python3
"""
AZOZ STORE - Catalogo de Roupas em PDF
Python + Flask + Supabase (PostgreSQL + Storage) + WeasyPrint
100% gratuito: Render Free + Supabase Free
"""

import os
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
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
        bucket_names = [b['name'] for b in buckets]
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
        except:
            pass

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
        except:
            pass

    print("✅ Supabase inicializado!")

# ============ HELPERS ============

def gerar_ref(marca_id, categoria_id):
    if not supabase:
        return "REF000"

    marca = sb_table('marcas').select('*').eq('id', marca_id).single().execute().data
    prefixo = marca['prefixo'] if marca else 'X'

    cat = sb_table('categorias').select('*').eq('id', categoria_id).single().execute().data
    cat_nome = cat['nome'] if cat else 'OUTROS'

    cat_map = {'CAMISETAS': 'CM', 'POLO': 'PL', 'CAMISAS': 'CM', 'CASACOS': 'CS'}
    cat_prefix = cat_map.get(cat_nome, 'XX')

    count = sb_table('produtos').select('*', count='exact').eq('marca_id', marca_id).eq('categoria_id', categoria_id).execute().count
    return f"{cat_prefix}{prefixo}{count + 1:02d}"

def get_dados_completos():
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
            prods = prods_resp.data or []
            if prods:
                categorias[cat['nome']] = prods
        if categorias:
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

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/dados')
def api_dados():
    return jsonify(get_dados_completos())

@app.route('/api/marcas')
def api_marcas():
    if not supabase:
        return jsonify([])
    resp = sb_table('marcas').select('*').order('ordem').execute()
    return jsonify(resp.data or [])

@app.route('/api/categorias/<int:marca_id>')
def api_categorias(marca_id):
    if not supabase:
        return jsonify([])
    resp = sb_table('categorias').select('*').eq('marca_id', marca_id).order('ordem').execute()
    return jsonify(resp.data or [])

@app.route('/api/produtos/<int:marca_id>/<int:categoria_id>')
def api_produtos(marca_id, categoria_id):
    if not supabase:
        return jsonify([])
    resp = sb_table('produtos').select('*').eq('marca_id', marca_id).eq('categoria_id', categoria_id).eq('ativo', True).order('id').execute()
    return jsonify(resp.data or [])

@app.route('/api/produto', methods=['POST'])
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
        'ativo': True
    }
    resp = sb_table('produtos').insert(insert_data).execute()
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else insert_data})

@app.route('/api/produto/<int:prod_id>', methods=['PUT'])
def atualizar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    data = request.get_json()
    update_data = {k: v for k, v in data.items() if k in ['nome', 'descricao', 'preco', 'imagem', 'imagem_detalhe', 'cores', 'ativo']}
    resp = sb_table('produtos').update(update_data).eq('id', prod_id).execute()
    return jsonify({'success': True, 'produto': resp.data[0] if resp.data else update_data})

@app.route('/api/produto/<int:prod_id>', methods=['DELETE'])
def deletar_produto(prod_id):
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    sb_table('produtos').update({'ativo': False}).eq('id', prod_id).execute()
    return jsonify({'success': True})

@app.route('/api/upload', methods=['POST'])
def upload_imagem():
    if not supabase:
        return jsonify({'error': 'Supabase nao configurado'}), 500
    if 'imagem' not in request.files:
        return jsonify({'error': 'Nenhuma imagem'}), 400
    file = request.files['imagem']
    if file.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400

    ext = os.path.splitext(secure_filename(file.filename))[1]
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}{ext}"

    file_bytes = file.read()
    supabase.storage.from_(BUCKET_NAME).upload(filename, file_bytes, {'content-type': file.content_type})

    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    return jsonify({'success': True, 'url': public_url})

@app.route('/pdf/<tamanho>')
def gerar_pdf(tamanho):
    tamanho = tamanho.upper()
    dados = get_dados_completos()
    html = render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=f'TAMANHO {tamanho}', marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], base_url=request.host_url.rstrip('/'))

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        HTML(string=html, base_url=request.host_url).write_pdf(tmp.name)
        tmp_path = tmp.name

    return send_file(tmp_path, as_attachment=True, download_name=f'catalogo_{tamanho}.pdf')

@app.route('/preview/<tamanho>')
def preview_pdf(tamanho):
    tamanho = tamanho.upper()
    dados = get_dados_completos()
    return render_template('catalogo.html', titulo='AZOZ STORE', subtitulo=f'TAMANHO {tamanho}', marcas=dados['marcas'], produtos=dados['produtos'], looks=dados['looks'], base_url=request.host_url.rstrip('/'))

if __name__ == '__main__':
    init_supabase()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
