CREATE TABLE IF NOT EXISTS categoria(
   id integer primary key autoincrement,
   nome varchar(50) not null,
   descricao text, 
   ativo boolean,
   imagem blob,
   img varchar(100)
);

CREATE TABLE IF NOT EXISTS produto(
   id integer primary key autoincrement,
   nome varchar(50) not null,
   preco float,
   ativo boolean, 
   imagem blob,
   img varchar(100),
   id_categoria int,
   foreign key ('id_categoria') references categoria('id')
);

CREATE TABLE IF NOT EXISTS usuario (
    id integer primary key AUTOINCREMENT,
    nome varchar(50) not null,
    senha varchar (50) not null,
    ativo boolean

);

INSERT INTO categoria(nome, descricao, ativo)
SELECT 'Bebidas sem álcool', 'Refrigerantes e águas', 'True'
WHERE NOT EXISTS (SELECT 1 FROM categoria WHERE nome = 'Bebidas sem álcool');

INSERT INTO categoria(nome, descricao, ativo)
SELECT 'Bebidas alcoólicas', 'Cervejas', 'True'
WHERE NOT EXISTS (SELECT 1 FROM categoria WHERE nome = 'Bebidas alcoólicas');

INSERT INTO categoria(nome, descricao, ativo)
SELECT 'Petiscos', 'Salgadinhos e snacks', 'True'
WHERE NOT EXISTS (SELECT 1 FROM categoria WHERE nome = 'Petiscos');

INSERT INTO produto(nome, preco, ativo, id_categoria)
SELECT 'Coca-Cola', 6.50, 'True', (SELECT id FROM categoria WHERE nome = 'Bebidas sem álcool')
WHERE NOT EXISTS (SELECT 1 FROM produto WHERE nome = 'Coca-Cola');

INSERT INTO produto(nome, preco, ativo, id_categoria)
SELECT 'Água', 3.00, 'True', (SELECT id FROM categoria WHERE nome = 'Bebidas sem álcool')
WHERE NOT EXISTS (SELECT 1 FROM produto WHERE nome = 'Água');

INSERT INTO produto(nome, preco, ativo, id_categoria)
SELECT 'Cerveja', 7.00, 'True', (SELECT id FROM categoria WHERE nome = 'Bebidas alcoólicas')
WHERE NOT EXISTS (SELECT 1 FROM produto WHERE nome = 'Cerveja');

INSERT INTO produto(nome, preco, ativo, id_categoria)
SELECT 'Pipoca', 5.00, 'True', (SELECT id FROM categoria WHERE nome = 'Petiscos')
WHERE NOT EXISTS (SELECT 1 FROM produto WHERE nome = 'Pipoca');
