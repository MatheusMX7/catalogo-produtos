# Catálogo-Produtos

Sistema web de catálogo e vendas feito com **Flask** e **SQLite**. Tem um painel para o administrador cadastrar categorias e produtos, e uma loja para o cliente ver os produtos, montar o carrinho e finalizar a compra. O acesso é por login: cada usuário entra na área do seu perfil.

> Projeto desenvolvido como atividade acadêmica.

## Funcionalidades

**Login**
- Entrada com usuário e senha. O administrador vai para o painel e o cliente vai para a loja.
- Criação de conta de cliente na tela de cadastro.
- Rotas protegidas: sem login nada abre, e o cliente não acessa as telas do administrador.

**Administrador** (`/admin`)
- Cadastro, edição e exclusão de **categorias**, com imagem.
- Cadastro, edição e exclusão de **produtos**, com preço, categoria, status e imagem.
- Link para ver a loja como o cliente enxerga.

**Cliente** (`/loja`)
- Página inicial com as categorias e as novidades.
- Lista de categorias e lista de produtos, com filtro por categoria.
- **Carrinho**: adicionar produtos, mudar a quantidade, remover itens e ver o total.
- **Compra**: escolha da forma de pagamento (Pix, Cartão ou Dinheiro) e finalização do pedido.
- **Meus pedidos**: histórico e detalhe de cada compra.

## Tecnologias

- Python e Flask
- SQLite
- Jinja2 (templates)
- AdminLTE 4 e Bootstrap 5 (visual)

## Como rodar

Você precisa do **Python 3.9 ou superior**. No terminal, dentro da pasta do projeto:

**Windows**

```bash
py -m venv .venv
.venv\Scripts\activate
pip install flask
py app.py
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask
python3 app.py
```

Depois abra no navegador: **http://127.0.0.1:5005**

O repositório já inclui o `database.db`, com categorias, produtos e fotos de exemplo, então o sistema abre pronto para testar.

## Logins para teste

Na primeira execução, o sistema cria dois usuários, se a tabela de usuários estiver vazia:

| Perfil | Usuário | Senha | Vai para |
|---|---|---|---|
| Administrador | `admin` | `admin123` | `/admin` (painel) |
| Cliente | `cliente` | `cliente123` | `/loja` (loja) |

Também é possível criar novos clientes em **Criar conta de cliente**, na tela de login. Esses logins são só para teste e desenvolvimento.

## Estrutura do projeto

```
catalogo-produtos/
├── app.py                 # rotas, login, carrinho e acesso ao banco
├── banco.sql              # estrutura das tabelas e dados iniciais
├── database.db            # banco SQLite
├── init_db.py             # cria o banco, só se ele ainda não existir
├── religar_fotos.py       # religa as fotos da pasta uploads ao banco
├── static/
│   ├── css/               # AdminLTE e Bootstrap
│   ├── img/
│   └── uploads/           # imagens enviadas pelo sistema
└── templates/
    ├── admin/             # telas do administrador
    ├── cliente/           # telas da loja
    ├── auth_base.html     # base das telas de login
    ├── login.html
    └── registrar.html
```

## Rotas principais

| Rota | Quem acessa | O que mostra |
|---|---|---|
| `/login` | todos | tela de login |
| `/registrar` | todos | criação de conta de cliente |
| `/admin` | administrador | painel |
| `/listar_categorias`, `/listar_produtos` | administrador | listas e cadastros |
| `/loja` | cliente e administrador | início da loja |
| `/loja/produtos` | cliente e administrador | produtos com filtro |
| `/loja/carrinho` | cliente e administrador | carrinho e finalização |
| `/loja/pedidos` | cliente e administrador | pedidos do usuário |
| `/sair` | logado | encerra a sessão |

## Banco de dados

Tabelas: `categoria`, `produto`, `usuario`, `pedido` e `item_pedido`.

- O item do pedido guarda o nome e o preço da hora da compra, então mudar um produto depois não altera pedidos antigos.
- O `init_db.py` **nunca apaga dados**. Se o `database.db` já existe, ele só avisa e mantém tudo como está. Ele cria o banco a partir do `banco.sql` apenas quando o arquivo ainda não existe. Como o `database.db` já vem no repositório, normalmente não é preciso rodá-lo.
- Para recriar o banco do zero de propósito, use `py init_db.py --recriar`. O script pede confirmação (digite `SIM`) e salva antes uma cópia de segurança chamada `database_backup_AAAAMMDD_HHMMSS.db`.
- Se as imagens perderem a ligação com os itens (por exemplo, depois de recriar o banco) e continuarem na pasta `static/uploads`, o `religar_fotos.py` religa cada foto ao seu item, pelo número que está no nome do arquivo:

```bash
py religar_fotos.py
```

## Segurança

- As senhas são guardadas **criptografadas** (hash), nunca em texto.
- A chave que assina a sessão do login é gerada automaticamente no arquivo `.secret_key`, que fica fora do repositório pelo `.gitignore`.
- O preço de cada compra é lido do banco na hora de finalizar, e não do que o navegador envia.
- O envio de imagens aceita PNG, JPG, JPEG, GIF e WEBP, com até 5 MB.

## Observações

- O pagamento é apenas um registro no pedido, sem cobrança de verdade.
- O carrinho fica guardado na sessão e esvazia quando o usuário clica em **Sair**.
- O servidor roda em modo de desenvolvimento (`debug=True`), próprio para uso local.

## Próximos passos

- Tela de **Pedidos** no painel do administrador.
- Controle de estoque dos produtos.

## Autor

**Matheus Soares** · [github.com/MatheusMX7](https://github.com/MatheusMX7)
