from datetime import datetime
from pathlib import Path
import secrets
import sqlite3
import uuid

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Chave da sessão: gerada uma vez e guardada em .secret_key (não fica fixa no código)
_arquivo_chave = Path(app.root_path) / '.secret_key'
if not _arquivo_chave.exists():
    _arquivo_chave.write_text(secrets.token_hex(32))
app.config['SECRET_KEY'] = _arquivo_chave.read_text().strip()
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


def preparar_usuarios():
    """Cria a tabela usuario se faltar, garante a coluna 'tipo' e cria os usuários padrão se estiver vazia."""
    with conexao() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS usuario (
                   id integer primary key AUTOINCREMENT,
                   nome varchar(50) not null,
                   senha varchar(255) not null,
                   ativo boolean,
                   tipo varchar(10) not null default 'cliente')"""
        )
        colunas = [c['name'] for c in conn.execute('PRAGMA table_info(usuario)')]
        if 'tipo' not in colunas:
            conn.execute("ALTER TABLE usuario ADD COLUMN tipo varchar(10) NOT NULL DEFAULT 'cliente'")
        if conn.execute('SELECT COUNT(*) FROM usuario').fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO usuario (nome, senha, ativo, tipo) VALUES (?, ?, 'True', ?)",
                [('admin', generate_password_hash('admin123'), 'admin'),
                 ('cliente', generate_password_hash('cliente123'), 'cliente')],
            )
        conn.commit()


def preparar_pedidos():
    """Cria as tabelas de pedidos se ainda não existirem."""
    with conexao() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pedido (
                id integer primary key autoincrement,
                id_usuario int not null,
                data datetime not null,
                total float not null,
                pagamento varchar(20) not null,
                status varchar(20) not null default 'Realizado',
                foreign key (id_usuario) references usuario(id)
            );
            CREATE TABLE IF NOT EXISTS item_pedido (
                id integer primary key autoincrement,
                id_pedido int not null,
                id_produto int,
                nome varchar(50) not null,
                preco float not null,
                quantidade int not null,
                foreign key (id_pedido) references pedido(id) on delete cascade
            );
        """)


preparar_usuarios()
preparar_pedidos()


@app.template_filter('data_br')
def formatar_data(valor):
    try:
        return datetime.strptime(valor, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
    except (TypeError, ValueError):
        return valor or ''


@app.context_processor
def dados_do_carrinho():
    return {'qtd_carrinho': sum(session.get('carrinho', {}).values())}


@app.template_filter('brl')
def formatar_real(valor):
    if valor is None:
        return '—'
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


ENDPOINTS_PUBLICOS = {'login', 'registrar', 'static'}


@app.before_request
def proteger_rotas():
    endpoint = request.endpoint
    if endpoint is None or endpoint in ENDPOINTS_PUBLICOS:
        return None
    if 'usuario_id' not in session:
        flash('Faça login para continuar.', 'warning')
        return redirect(url_for('login'))
    if endpoint in ('raiz', 'sair') or endpoint.startswith('cliente_'):
        return None
    if session.get('tipo') != 'admin':
        flash('Esta área é restrita ao administrador.', 'danger')
        return redirect(url_for('cliente_inicio'))
    return None


def destino_do_usuario(tipo):
    return url_for('index') if tipo == 'admin' else url_for('cliente_inicio')


@app.route('/')
def raiz():
    return redirect(destino_do_usuario(session.get('tipo')))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(destino_do_usuario(session.get('tipo')))

    if request.method == 'POST':
        nome = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        with conexao() as conn:
            usuario = conn.execute(
                "SELECT * FROM usuario WHERE nome = ? COLLATE NOCASE AND ativo = 'True'", (nome,)
            ).fetchone()

        if usuario is None or not check_password_hash(usuario['senha'], senha):
            flash('Usuário ou senha incorretos.', 'danger')
            return render_template('login.html', usuario=nome)

        session.clear()
        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome']
        session['tipo'] = usuario['tipo']
        return redirect(destino_do_usuario(usuario['tipo']))

    return render_template('login.html')


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmar', '')

        if len(nome) < 3:
            erro = 'O usuário precisa ter pelo menos 3 caracteres.'
        elif len(senha) < 6:
            erro = 'A senha precisa ter pelo menos 6 caracteres.'
        elif senha != confirmar:
            erro = 'As senhas não conferem.'
        else:
            erro = None
            with conexao() as conn:
                existe = conn.execute(
                    'SELECT 1 FROM usuario WHERE nome = ? COLLATE NOCASE', (nome,)
                ).fetchone()
                if existe:
                    erro = 'Já existe um usuário com esse nome.'
                else:
                    conn.execute(
                        "INSERT INTO usuario (nome, senha, ativo, tipo) VALUES (?, ?, 'True', 'cliente')",
                        (nome, generate_password_hash(senha)),
                    )
                    conn.commit()

        if erro:
            flash(erro, 'danger')
            return render_template('registrar.html', usuario=nome)

        flash('Conta criada. Entre com o seu usuário e senha.', 'success')
        return redirect(url_for('login'))

    return render_template('registrar.html')


@app.route('/sair')
def sair():
    session.clear()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('login'))


PRODUTOS_ATIVOS = """SELECT produto.*, categoria.nome AS categoria_nome
    FROM produto LEFT JOIN categoria ON categoria.id = produto.id_categoria
    WHERE produto.ativo = 'True' AND (categoria.id IS NULL OR categoria.ativo = 'True')"""


@app.route('/loja')
def cliente_inicio():
    with conexao() as conn:
        categorias = conn.execute("SELECT * FROM categoria WHERE ativo = 'True' ORDER BY nome").fetchall()
        novidades = conn.execute(PRODUTOS_ATIVOS + ' ORDER BY produto.id DESC LIMIT 4').fetchall()
    return render_template('cliente/index.html', categorias=categorias, novidades=novidades)


@app.route('/loja/categorias')
def cliente_categorias():
    with conexao() as conn:
        categorias = conn.execute("SELECT * FROM categoria WHERE ativo = 'True' ORDER BY nome").fetchall()
    return render_template('cliente/listar_categoria.html', categorias=categorias)


@app.route('/loja/produtos')
def cliente_produtos():
    id_categoria = request.args.get('categoria', type=int)
    sql, parametros = PRODUTOS_ATIVOS, []
    if id_categoria:
        sql += ' AND produto.id_categoria = ?'
        parametros.append(id_categoria)
    with conexao() as conn:
        categorias = conn.execute("SELECT * FROM categoria WHERE ativo = 'True' ORDER BY nome").fetchall()
        produtos = conn.execute(sql + ' ORDER BY produto.nome', parametros).fetchall()
    return render_template('cliente/listar_produto.html', categorias=categorias,
                           produtos=produtos, categoria_atual=id_categoria)


PAGAMENTOS = ['Pix', 'Cartão', 'Dinheiro']


def destino_seguro(valor, padrao):
    """Só aceita caminhos internos do próprio site (evita redirecionar para outro endereço)."""
    if valor and valor.startswith('/') and not valor.startswith('//') and '\\' not in valor:
        return valor
    return padrao


def ler_carrinho():
    """Monta os itens do carrinho com os preços atuais do banco."""
    carrinho = session.get('carrinho', {})
    if not carrinho:
        return [], 0
    ids = [int(i) for i in carrinho]
    with conexao() as conn:
        produtos = conn.execute(
            PRODUTOS_ATIVOS + ' AND produto.id IN (%s)' % ','.join('?' * len(ids)), ids
        ).fetchall()
    itens, total = [], 0
    for p in produtos:
        quantidade = carrinho[str(p['id'])]
        preco = p['preco'] or 0
        itens.append({'produto': p, 'preco': preco, 'quantidade': quantidade, 'subtotal': round(preco * quantidade, 2)})
        total += preco * quantidade
    return itens, round(total, 2)


@app.route('/loja/carrinho')
def cliente_carrinho():
    itens, total = ler_carrinho()
    return render_template('cliente/carrinho.html', itens=itens, total=total, pagamentos=PAGAMENTOS)


@app.route('/loja/carrinho/adicionar/<int:id_produto>', methods=['POST'])
def cliente_adicionar(id_produto):
    quantidade = max(request.form.get('quantidade', 1, type=int), 1)
    with conexao() as conn:
        produto = conn.execute(PRODUTOS_ATIVOS + ' AND produto.id = ?', (id_produto,)).fetchone()
    if produto is None:
        flash('Esse produto não está disponível.', 'danger')
        return redirect(url_for('cliente_produtos'))
    carrinho = dict(session.get('carrinho', {}))
    chave = str(id_produto)
    carrinho[chave] = min(carrinho.get(chave, 0) + quantidade, 99)
    session['carrinho'] = carrinho
    flash(f"{produto['nome']} foi adicionado ao carrinho.", 'success')
    return redirect(destino_seguro(request.form.get('volta'), url_for('cliente_produtos')))


@app.route('/loja/carrinho/atualizar/<int:id_produto>', methods=['POST'])
def cliente_atualizar(id_produto):
    quantidade = request.form.get('quantidade', 0, type=int)
    carrinho = dict(session.get('carrinho', {}))
    chave = str(id_produto)
    if chave in carrinho:
        if quantidade <= 0:
            del carrinho[chave]
        else:
            carrinho[chave] = min(quantidade, 99)
    session['carrinho'] = carrinho
    return redirect(url_for('cliente_carrinho'))


@app.route('/loja/carrinho/remover/<int:id_produto>', methods=['POST'])
def cliente_remover(id_produto):
    carrinho = dict(session.get('carrinho', {}))
    carrinho.pop(str(id_produto), None)
    session['carrinho'] = carrinho
    flash('Item removido do carrinho.', 'success')
    return redirect(url_for('cliente_carrinho'))


@app.route('/loja/finalizar', methods=['POST'])
def cliente_finalizar():
    itens, total = ler_carrinho()
    if not itens:
        flash('Seu carrinho está vazio.', 'warning')
        return redirect(url_for('cliente_carrinho'))
    pagamento = request.form.get('pagamento')
    if pagamento not in PAGAMENTOS:
        flash('Escolha a forma de pagamento.', 'danger')
        return redirect(url_for('cliente_carrinho'))

    with conexao() as conn:
        cursor = conn.execute(
            "INSERT INTO pedido (id_usuario, data, total, pagamento, status) "
            "VALUES (?, datetime('now', 'localtime'), ?, ?, 'Realizado')",
            (session['usuario_id'], total, pagamento),
        )
        id_pedido = cursor.lastrowid
        conn.executemany(
            'INSERT INTO item_pedido (id_pedido, id_produto, nome, preco, quantidade) VALUES (?, ?, ?, ?, ?)',
            [(id_pedido, i['produto']['id'], i['produto']['nome'], i['preco'], i['quantidade']) for i in itens],
        )
        conn.commit()

    session.pop('carrinho', None)
    flash('Compra realizada com sucesso!', 'success')
    return redirect(url_for('cliente_pedido', id_pedido=id_pedido))


@app.route('/loja/pedidos')
def cliente_pedidos():
    with conexao() as conn:
        pedidos = conn.execute(
            'SELECT * FROM pedido WHERE id_usuario = ? ORDER BY id DESC', (session['usuario_id'],)
        ).fetchall()
    return render_template('cliente/listar_pedido.html', pedidos=pedidos)


@app.route('/loja/pedido/<int:id_pedido>')
def cliente_pedido(id_pedido):
    with conexao() as conn:
        pedido = conn.execute('SELECT * FROM pedido WHERE id = ?', (id_pedido,)).fetchone()
        if pedido is None or (pedido['id_usuario'] != session['usuario_id'] and session.get('tipo') != 'admin'):
            flash('Pedido não encontrado.', 'danger')
            return redirect(url_for('cliente_pedidos'))
        itens = conn.execute('SELECT * FROM item_pedido WHERE id_pedido = ?', (id_pedido,)).fetchall()
    return render_template('cliente/pedido.html', pedido=pedido, itens=itens)


@app.route('/admin')
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
