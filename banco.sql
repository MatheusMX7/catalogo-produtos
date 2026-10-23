DROP TABLE IF EXISTS item_pedido;
DROP TABLE IF EXISTS pedido;
DROP TABLE IF EXISTS produto;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS usuario;


CREATE TABLE categoria(
   id integer primary key autoincrement,
   nome varchar(50) not null,
   descricao text, 
   ativo boolean,
   imagem blob,
   img varchar(100)
);

CREATE TABLE produto(
   id integer primary key autoincrement,
   nome varchar(50) not null,
   preco float,
   ativo boolean, 
   imagem blob,
   img varchar(100),
   id_categoria int,
   foreign key ('id_categoria') references categoria('id')
);

CREATE TABLE usuario (
    id integer primary key AUTOINCREMENT,
    nome varchar(50) not null,
    senha varchar(255) not null,
    ativo boolean,
    tipo varchar(10) not null default 'cliente'
);

CREATE TABLE pedido (
    id integer primary key autoincrement,
    id_usuario int not null,
    data datetime not null,
    total float not null,
    pagamento varchar(20) not null,
    status varchar(20) not null default 'Realizado',
    foreign key (id_usuario) references usuario(id)
);

CREATE TABLE item_pedido (
    id integer primary key autoincrement,
    id_pedido int not null,
    id_produto int,
    nome varchar(50) not null,
    preco float not null,
    quantidade int not null,
    foreign key (id_pedido) references pedido(id) on delete cascade
);

insert into categoria(nome, descricao, ativo) values
  ('Bebidas sem álcool', 'Refrigerantes e águas', 'True'),
  ('Bebidas alcoólicas', 'Cervejas', 'True'),
  ('Petiscos', 'Salgadinhos e snacks', 'True');

insert into produto(nome, preco, ativo, id_categoria) values
  ('Coca-Cola', 6.50, 'True', (select id from categoria where nome = 'Bebidas sem álcool')),
  ('Água', 3.00, 'True', (select id from categoria where nome = 'Bebidas sem álcool')),
  ('Cerveja', 7.00, 'True', (select id from categoria where nome = 'Bebidas alcoólicas')),
  ('Pipoca', 5.00, 'True', (select id from categoria where nome = 'Petiscos'));
