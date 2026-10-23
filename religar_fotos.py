"""Religa as fotos que estão em static/uploads aos registros do banco.

Use quando as fotos continuam na pasta, mas o banco ficou com img = None.
Os arquivos são nomeados pelo sistema como categoria_<id>_... e produto_<id>_...,
então o <id> no nome diz a qual registro cada foto pertence.
Só preenche registros que estão sem foto; não mexe nos que já têm.
"""
import sqlite3
from pathlib import Path

PASTA = Path(__file__).parent
UPLOADS = PASTA / 'static' / 'uploads'
conn = sqlite3.connect(PASTA / 'database.db')

for tabela, prefixo in (('categoria', 'categoria'), ('produto', 'produto')):
    for id_, nome, img in conn.execute(f'SELECT id, nome, img FROM {tabela}').fetchall():
        if img:
            continue
        arquivos = [f for f in UPLOADS.glob(f'{prefixo}_{id_}_*') if f.is_file()]
        if not arquivos:
            print(f'{tabela} {id_} ({nome}): nenhuma foto encontrada')
            continue
        recente = max(arquivos, key=lambda f: f.stat().st_mtime)
        conn.execute(f'UPDATE {tabela} SET img = ? WHERE id = ?', (f'uploads/{recente.name}', id_))
        print(f'{tabela} {id_} ({nome}): ligada a {recente.name}')

conn.commit()
conn.close()
