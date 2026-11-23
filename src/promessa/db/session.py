"""Engine, sessão, criação do banco e triggers de imutabilidade.

Rodar: `python -m promessa.db.session --reset` apaga e recria o banco de `PROMESSA_DB_URL`
(é o que a tarefa `db-reset` do tasks.py faz).
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import DDL, Engine, create_engine, event, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from promessa.config import get_settings
from promessa.db.models import Base

IMMUTABLE_TABLES = ("product_facts", "content_piece", "review_event")

_MESSAGES = {
    "product_facts": "a ficha é imutável; crie uma nova versão",
    "content_piece": "a peça é imutável; envie uma nova peça com parent_piece_id",
    "review_event": "o registro de revisão é só de inserção",
}

# Triggers SQLite: RAISE(ABORT) desfaz o comando e devolve erro de restrição.
# Equivalente em Postgres (não usado no MVP):
#   CREATE FUNCTION forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
#   BEGIN RAISE EXCEPTION '% é imutável', TG_TABLE_NAME; END $$;
#   CREATE TRIGGER <tabela>_no_update BEFORE UPDATE ON <tabela>
#     FOR EACH ROW EXECUTE FUNCTION forbid_change();
#   CREATE TRIGGER <tabela>_no_delete BEFORE DELETE ON <tabela>
#     FOR EACH ROW EXECUTE FUNCTION forbid_change();
for _table in IMMUTABLE_TABLES:
    for _op in ("UPDATE", "DELETE"):
        event.listen(
            Base.metadata,
            "after_create",
            DDL(
                f"CREATE TRIGGER IF NOT EXISTS {_table}_no_{_op.lower()} "
                f"BEFORE {_op} ON {_table} "
                f"BEGIN SELECT RAISE(ABORT, '{_table}: {_MESSAGES[_table]}'); END"
            ).execute_if(dialect="sqlite"),
        )


def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(url: str | None = None) -> Engine:
    """Engine para `url` (padrão: `PROMESSA_DB_URL`). Em SQLite, liga as chaves estrangeiras.

    `sqlite://` (banco temporário, sem arquivo) usa uma conexão compartilhada, para todas as
    sessões verem o mesmo banco.
    """
    url = url or get_settings().promessa_db_url
    parsed = make_url(url)
    kwargs = {}
    if parsed.get_backend_name() == "sqlite":
        if parsed.database in (None, "", ":memory:"):
            kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
        else:
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if parsed.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def init_db(engine: Engine) -> None:
    """Cria as tabelas e os triggers (idempotente)."""
    Base.metadata.create_all(engine)


def get_session(engine: Engine | None = None) -> Session:
    """Nova sessão. Quem chama fecha (`with get_session() as s:`)."""
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False)()


def reset_db(url: str | None = None) -> Engine:
    """Apaga o arquivo SQLite (se houver) e recria tabelas e triggers."""
    url = url or get_settings().promessa_db_url
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or parsed.database in (None, "", ":memory:"):
        raise SystemExit(f"reset só funciona com SQLite em arquivo: {parsed.render_as_string()}")
    Path(parsed.database).unlink(missing_ok=True)
    engine = get_engine(url)
    init_db(engine)
    return engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banco do Promessa Rastreável")
    parser.add_argument("--reset", action="store_true", help="apaga e recria o banco")
    args = parser.parse_args(argv)
    if args.reset:
        engine = reset_db()
    else:
        engine = get_engine()
        init_db(engine)
    tables = sorted(inspect(engine).get_table_names())
    print(f"banco: {engine.url.database}")
    print(f"{len(tables)} tabelas: {' '.join(tables)}")
    engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
