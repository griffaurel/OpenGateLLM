"""add the decision router type and the colibri provider type

Revision ID: c7d3a9e2f518
Revises: bf92da1a3246
Create Date: 2026-10-15 10:00:00.000000

Routers of type `decision` serve `/v1/systemone`, and providers of type `colibri`
are the servers that answer it. The PostgreSQL `routertype` and `providertype`
enums get the `DECISION` and `COLIBRI` members (members are stored by name).

The downgrade drops them again. It refuses to run while a router or a provider
still uses one: there is no other value those rows could be moved to.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c7d3a9e2f518"
down_revision: str | None = "bf92da1a3246"
branch_labels = None
depends_on = None

_ROUTERTYPE_WITHOUT_DECISION = (
    "AUTOMATIC_SPEECH_RECOGNITION",
    "IMAGE_TO_TEXT",
    "TEXT_CLASSIFICATION",
    "TEXT_EMBEDDINGS_INFERENCE",
    "TEXT_GENERATION",
)
_PROVIDERTYPE_WITHOUT_COLIBRI = ("ALBERT", "OPENAI", "TEI", "VLLM", "MISTRAL")


def upgrade() -> None:
    # A new enum member cannot be used in the transaction that adds it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE routertype ADD VALUE IF NOT EXISTS 'DECISION'")
        op.execute("ALTER TYPE providertype ADD VALUE IF NOT EXISTS 'COLIBRI'")


def _refuse_if_used(table: str, value: str) -> None:
    # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query -- table and value are constants of this file
    count = op.get_bind().execute(sa.text(f"SELECT count(*) FROM {table} WHERE type::text = '{value}'")).scalar_one()
    if count:
        raise RuntimeError(f"Cannot downgrade: {count} row(s) of '{table}' still have the type '{value}'. Delete them first.")


def _replace_enum(name: str, table: str, values: tuple[str, ...]) -> None:
    quoted = ", ".join(f"'{value}'" for value in values)
    op.execute(f"ALTER TYPE {name} RENAME TO {name}_old")
    # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query -- values come from constant tuples of this file
    op.execute(f"CREATE TYPE {name} AS ENUM ({quoted})")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN type TYPE {name} USING type::text::{name}")
    op.execute(f"DROP TYPE {name}_old")


def downgrade() -> None:
    _refuse_if_used(table="router", value="DECISION")
    _refuse_if_used(table="provider", value="COLIBRI")

    _replace_enum(name="routertype", table="router", values=_ROUTERTYPE_WITHOUT_DECISION)
    _replace_enum(name="providertype", table="provider", values=_PROVIDERTYPE_WITHOUT_COLIBRI)
