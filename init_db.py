"""Prepara o banco de dados do projeto.

Uso:
    py init_db.py             cria o banco só se ele ainda não existir (nunca apaga dados)
    py init_db.py --recriar   apaga tudo e recria do zero (pede confirmação e faz backup antes)
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
BANCO = PASTA / 'database.db'
SCRIPT = PASTA / 'banco.sql'


def banco_tem_tabelas():
    """True se o database.db existe e já tem alguma tabela."""
    if not BANCO.exists():
        return False
    conn = sqlite3.connect(BANCO)
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    finally:
        conn.close()
    return total > 0


def criar_banco():
    conn = sqlite3.connect(BANCO)
    try:
        conn.executescript(SCRIPT.read_text(encoding='utf-8'))
        conn.commit()
    finally:
        conn.close()


def init_db(recriar=False):
    existe = banco_tem_tabelas()

    if existe and not recriar:
        print('O banco de dados já existe e foi mantido. Nenhum dado foi alterado.')
        print('Para apagar tudo e recriar do zero, use: py init_db.py --recriar')
        return

    if existe and recriar:
        print('ATENÇÃO: isto apaga categorias, produtos, usuários e pedidos.')
        try:
            resposta = input('Digite SIM para continuar: ')
        except EOFError:
            resposta = ''
        if resposta.strip().upper() != 'SIM':
            print('Cancelado. Nada foi alterado.')
            return
        backup = BANCO.with_name(f'database_backup_{datetime.now():%Y%m%d_%H%M%S}.db')
        shutil.copy2(BANCO, backup)
        print(f'Cópia de segurança salva em {backup.name}')

    criar_banco()
    print('Banco de dados inicializado com sucesso!')


if __name__ == '__main__':
    init_db(recriar='--recriar' in sys.argv)
