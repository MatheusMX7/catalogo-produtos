from pathlib import Path
import sqlite3
import uuid

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['UPLOAD_FOLDER'] = Path(app.root_path) / 'static' / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)


def conexao():
    conn = sqlite3.connect(Path(app.root_path) / 'database.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def extensao_permitida(nome_arquivo):
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def salvar_imagem(arquivo, prefixo='imagem'):
    """Salva a imagem em static/uploads e retorna o caminho relativo usado pelo url_for('static')."""
    if not arquivo or not arquivo.filename:
        return None

    nome_original = secure_filename(arquivo.filename)
    if not extensao_permitida(nome_original):
        raise ValueError('Formato de imagem não permitido. Use PNG, JPG, JPEG, GIF ou WEBP.')

    extensao = nome_original.rsplit('.', 1)[1].lower()
    nome = f'{prefixo}_{uuid.uuid4().hex}.{extensao}'
    arquivo.save(app.config['UPLOAD_FOLDER'] / nome)
    return f'uploads/{nome}'


def excluir_imagem(caminho):
    """Remove apenas arquivos armazenados em static/uploads."""
    if not caminho or not caminho.startswith('uploads/'):
        return
    arquivo = Path(app.root_path) / 'static' / caminho
    if arquivo.exists() and arquivo.is_file():
        arquivo.unlink()


@app.route('/')
def index():
    return render_template('admin/index.html')


@app.route('/listar_categorias')
def listarCategoria():
    with conexao() as conn:
        categorias = conn.execute('SELECT * FROM categoria ORDER BY id DESC').fetchall()
    return render_template('admin/listar_categoria.html', categorias=categorias)


@app.route('/cadastrar_categorias', methods=['GET', 'POST'])
def cadastrarCategoria():
    if request.method == 'POST':
        nome_categoria = request.form.get('nome_categoria', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo', 'False')
        imagem = request.files.get('imagem')

        if not nome_categoria:
            flash('Informe o nome da categoria.', 'danger')
            return render_template('admin/cadastrar_categoria.html')

        try:
            caminho_imagem = salvar_imagem(imagem, 'categoria')
        except ValueError as erro:
            flash(str(erro), 'danger')
            return render_template('admin/cadastrar_categoria.html')

        with conexao() as conn:
            conn.execute(
                '''INSERT INTO categoria (nome, descricao, ativo, img)
                   VALUES (?, ?, ?, ?)''',
                (nome_categoria, descricao, ativo, caminho_imagem),
            )
            conn.commit()

        flash('Categoria cadastrada com sucesso.', 'success')
        return redirect(url_for('listarCategoria'))

    return render_template('admin/cadastrar_categoria.html')


@app.route('/editarcategoria/<int:id>', methods=['GET', 'POST'])
def editarCategoria(id):
    with conexao() as conn:
        categoria = conn.execute('SELECT * FROM categoria WHERE id = ?', (id,)).fetchone()

    if categoria is None:
        flash('Categoria não encontrada.', 'danger')
        return redirect(url_for('listarCategoria'))

    if request.method == 'POST':
        nome_categoria = request.form.get('nome_categoria', '').strip()
        descricao = request.form.get('descricao', '').strip()
        ativo = request.form.get('ativo', 'False')
        imagem = request.files.get('imagem')
        caminho_imagem = categoria['img']

        if not nome_categoria:
            flash('Informe o nome da categoria.', 'danger')
            return render_template('admin/editar_categoria.html', categoria=categoria)

        if imagem and imagem.filename:
            try:
                novo_caminho = salvar_imagem(imagem, f'categoria_{id}')
            except ValueError as erro:
                flash(str(erro), 'danger')
                return render_template('admin/editar_categoria.html', categoria=categoria)

            excluir_imagem(caminho_imagem)
            caminho_imagem = novo_caminho

        with conexao() as conn:
            conn.execute(
                '''UPDATE categoria
                   SET nome = ?, descricao = ?, ativo = ?, img = ?
                   WHERE id = ?''',
                (nome_categoria, descricao, ativo, caminho_imagem, id),
            )
            conn.commit()

        flash('Categoria atualizada com sucesso.', 'success')
        return redirect(url_for('listarCategoria'))

    return render_template('admin/editar_categoria.html', categoria=categoria)


@app.route('/excluir_categoria/<int:id>', methods=['GET', 'POST'])
def excluirCategoria(id):
    with conexao() as conn:
        categoria = conn.execute('SELECT * FROM categoria WHERE id = ?', (id,)).fetchone()

    if categoria is None:
        flash('Categoria não encontrada.', 'danger')
        return redirect(url_for('listarCategoria'))

    if request.method == 'POST':
        try:
            with conexao() as conn:
                conn.execute('DELETE FROM categoria WHERE id = ?', (id,))
                conn.commit()
        except sqlite3.IntegrityError:
            flash('Não é possível excluir: existem produtos nesta categoria.', 'danger')
            return redirect(url_for('listarCategoria'))
        excluir_imagem(categoria['img'])
        flash('Categoria excluída com sucesso.', 'success')
        return redirect(url_for('listarCategoria'))

    return render_template('admin/excluir_categoria.html', categoria=categoria)


@app.route('/listar_produtos')
def listarProduto():
    with conexao() as conn:
        produtos = conn.execute(
            '''SELECT produto.*, categoria.nome AS categoria_nome
               FROM produto
               LEFT JOIN categoria ON categoria.id = produto.id_categoria
               ORDER BY produto.id DESC'''
        ).fetchall()
    return render_template('admin/listar_produto.html', produtos=produtos)


def converter_preco(texto):
    """Converte '12,50' ou '12.50' em float. Retorna None se for inválido ou negativo."""
    try:
        valor = float(texto.strip().replace('.', '').replace(',', '.')) if ',' in texto else float(texto.strip())
    except (ValueError, AttributeError):
        return None
    return valor if valor >= 0 else None


def listar_categorias_ativas():
    with conexao() as conn:
        return conn.execute("SELECT id, nome FROM categoria WHERE ativo = 'True' ORDER BY nome").fetchall()


@app.route('/cadastrar_produtos', methods=['GET', 'POST'])
def cadastrarProduto():
    categorias = listar_categorias_ativas()

    if request.method == 'POST':
        nome = request.form.get('nome_produto', '').strip()
        preco = converter_preco(request.form.get('preco', ''))
        ativo = request.form.get('ativo', 'False')
        id_categoria = request.form.get('id_categoria') or None
        imagem = request.files.get('imagem')

        if not nome:
            flash('Informe o nome do produto.', 'danger')
            return render_template('admin/cadastrar_produto.html', categorias=categorias)
        if preco is None:
            flash('Informe um preço válido (ex.: 12,50).', 'danger')
            return render_template('admin/cadastrar_produto.html', categorias=categorias)

        try:
            caminho_imagem = salvar_imagem(imagem, 'produto')
        except ValueError as erro:
            flash(str(erro), 'danger')
            return render_template('admin/cadastrar_produto.html', categorias=categorias)

        with conexao() as conn:
            conn.execute(
                '''INSERT INTO produto (nome, preco, ativo, img, id_categoria)
                   VALUES (?, ?, ?, ?, ?)''',
                (nome, preco, ativo, caminho_imagem, id_categoria),
            )
            conn.commit()

        flash('Produto cadastrado com sucesso.', 'success')
        return redirect(url_for('listarProduto'))

    return render_template('admin/cadastrar_produto.html', categorias=categorias)


@app.route('/editarproduto/<int:id>', methods=['GET', 'POST'])
def editarProduto(id):
    with conexao() as conn:
        produto = conn.execute('SELECT * FROM produto WHERE id = ?', (id,)).fetchone()

    if produto is None:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('listarProduto'))

    categorias = listar_categorias_ativas()

    if request.method == 'POST':
        nome = request.form.get('nome_produto', '').strip()
        preco = converter_preco(request.form.get('preco', ''))
        ativo = request.form.get('ativo', 'False')
        id_categoria = request.form.get('id_categoria') or None
        imagem = request.files.get('imagem')
        caminho_imagem = produto['img']

        if not nome:
            flash('Informe o nome do produto.', 'danger')
            return render_template('admin/editar_produto.html', produto=produto, categorias=categorias)
        if preco is None:
            flash('Informe um preço válido (ex.: 12,50).', 'danger')
            return render_template('admin/editar_produto.html', produto=produto, categorias=categorias)

        if imagem and imagem.filename:
            try:
                novo_caminho = salvar_imagem(imagem, f'produto_{id}')
            except ValueError as erro:
                flash(str(erro), 'danger')
                return render_template('admin/editar_produto.html', produto=produto, categorias=categorias)
            excluir_imagem(caminho_imagem)
            caminho_imagem = novo_caminho

        with conexao() as conn:
            conn.execute(
                '''UPDATE produto
                   SET nome = ?, preco = ?, ativo = ?, img = ?, id_categoria = ?
                   WHERE id = ?''',
                (nome, preco, ativo, caminho_imagem, id_categoria, id),
            )
            conn.commit()

        flash('Produto atualizado com sucesso.', 'success')
        return redirect(url_for('listarProduto'))

    return render_template('admin/editar_produto.html', produto=produto, categorias=categorias)


@app.route('/excluir_produto/<int:id>', methods=['GET', 'POST'])
def excluirProduto(id):
    with conexao() as conn:
        produto = conn.execute('SELECT * FROM produto WHERE id = ?', (id,)).fetchone()

    if produto is None:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('listarProduto'))

    if request.method == 'POST':
        with conexao() as conn:
            conn.execute('DELETE FROM produto WHERE id = ?', (id,))
            conn.commit()
        excluir_imagem(produto['img'])
        flash('Produto excluído com sucesso.', 'success')
        return redirect(url_for('listarProduto'))

    return render_template('admin/excluir_produto.html', produto=produto)


if __name__ == '__main__':
    app.run(debug=True, port=5005)
