import sqlite3
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent
ARQUIVO_BANCO = PASTA_PROJETO / "database.db"
ARQUIVO_SQL = PASTA_PROJETO / "banco.sql"


def init_db():
    # Preserve the existing catalog instead of running DROP TABLE statements
    # over a database that already contains data.
    if ARQUIVO_BANCO.exists():
        print(f"Banco existente preservado: {ARQUIVO_BANCO}")
        return

    with sqlite3.connect(ARQUIVO_BANCO) as conn:
        conn.executescript(ARQUIVO_SQL.read_text(encoding="utf-8"))

    print("Banco de dados inicializado com sucesso!")


if __name__ == "__main__":
    init_db()
