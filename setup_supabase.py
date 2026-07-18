#!/usr/bin/env python3
"""
Script para criar tabelas no Supabase.
Rode UMA VEZ apos criar o projeto no Supabase.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env")
    print("   Exemplo:")
    print("   SUPABASE_URL=https://seu-projeto.supabase.co")
    print("   SUPABASE_KEY=sua_chave_anon_aqui")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🚀 Criando tabelas no Supabase...")
print("   (Use o SQL Editor do Supabase se der erro de permissao)")
print()

# SQL para criar tabelas
sql = """
-- Tabela de marcas
CREATE TABLE IF NOT EXISTS marcas (
    id INTEGER PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL,
    prefixo TEXT NOT NULL,
    ordem INTEGER DEFAULT 0
);

-- Tabela de categorias
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    marca_id INTEGER NOT NULL REFERENCES marcas(id),
    nome TEXT NOT NULL,
    ordem INTEGER DEFAULT 0
);

-- Tabela de produtos
CREATE TABLE IF NOT EXISTS produtos (
    id SERIAL PRIMARY KEY,
    marca_id INTEGER NOT NULL REFERENCES marcas(id),
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    ref TEXT NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL DEFAULT 0,
    imagem TEXT DEFAULT '',
    imagem_detalhe TEXT DEFAULT '',
    cores TEXT DEFAULT '',
    ativo BOOLEAN DEFAULT TRUE,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de looks
CREATE TABLE IF NOT EXISTS looks (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT DEFAULT 'Curadoria Premium'
);

-- Tabela de pecas dos looks
CREATE TABLE IF NOT EXISTS look_pecas (
    id SERIAL PRIMARY KEY,
    look_id INTEGER NOT NULL REFERENCES looks(id),
    ref TEXT,
    marca TEXT,
    nome TEXT,
    descricao TEXT,
    preco REAL DEFAULT 0,
    imagem TEXT DEFAULT ''
);

-- Inserir marcas padrao
INSERT INTO marcas (id, nome, prefixo, ordem) VALUES
(1, 'LACOSTE', 'L', 1),
(2, 'TOMMY HILFIGER', 'T', 2),
(3, 'LEVI''S', 'V', 3),
(4, 'CALVIN KLEIN', 'K', 4),
(5, 'AZOZ', 'A', 5)
ON CONFLICT (id) DO NOTHING;

-- Inserir categorias padrao
INSERT INTO categorias (id, marca_id, nome, ordem) VALUES
(1, 1, 'CAMISETAS', 1), (2, 1, 'POLO', 2), (3, 1, 'CAMISAS', 3), (4, 1, 'CASACOS', 4),
(5, 2, 'CAMISETAS', 1), (6, 2, 'POLO', 2), (7, 2, 'CAMISAS', 3), (8, 2, 'CASACOS', 4),
(9, 3, 'CAMISETAS', 1), (10, 3, 'CAMISAS', 2), (11, 3, 'CASACOS', 3),
(12, 4, 'CAMISETAS', 1), (13, 4, 'CAMISAS', 2), (14, 4, 'CASACOS', 3),
(15, 5, 'CAMISETAS', 1), (16, 5, 'CAMISAS', 2), (17, 5, 'CASACOS', 3)
ON CONFLICT (id) DO NOTHING;

-- Ativar Row Level Security: sem policies, so a service_role (usada pelo servidor) acessa.
-- Isso impede que alguem com a anon key leia/escreva direto no banco.
ALTER TABLE marcas ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos ENABLE ROW LEVEL SECURITY;
ALTER TABLE looks ENABLE ROW LEVEL SECURITY;
ALTER TABLE look_pecas ENABLE ROW LEVEL SECURITY;
"""

try:
    # Tentar executar via RPC (pode nao funcionar sem permissao)
    supabase.rpc('exec_sql', {'sql': sql}).execute()
    print("✅ Tabelas criadas via RPC!")
except Exception as e:
    print(f"⚠️  RPC falhou (normal): {e}")
    print()
    print("👉 Cole o SQL abaixo manualmente no Supabase:")
    print("   1. Acesse https://app.supabase.com")
    print("   2. Va em seu projeto > SQL Editor")
    print("   3. Cole o SQL e clique em 'Run'")
    print()
    print("=" * 60)
    print(sql)
    print("=" * 60)

# Criar bucket
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'imagens')
try:
    buckets = supabase.storage.list_buckets()
    bucket_names = [b['name'] for b in buckets]
    if BUCKET_NAME not in bucket_names:
        supabase.storage.create_bucket(BUCKET_NAME, {'public': True})
        print(f"✅ Bucket '{BUCKET_NAME}' criado!")
    else:
        print(f"✅ Bucket '{BUCKET_NAME}' ja existe")
except Exception as e:
    print(f"⚠️  Bucket: {e}")
    print("   Crie manualmente em Storage > New bucket > 'imagens'")

print()
print("🎉 Setup completo!")
