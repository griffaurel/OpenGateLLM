"""add the decision router type

Revision ID: c7d3a9e2f518
Revises: bf92da1a3246
Create Date: 2026-10-15 10:00:00.000000

Routers of type `decision` serve `/v1/systemone`. The PostgreSQL `routertype`
enum gets the `DECISION` member (members are stored by name).

The downgrade drops that member again. It refuses to run while a router still
uses it: there is no other type those routers could be moved to.
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


def upgrade() -> None:
    # A new enum member cannot be used in the transaction that adds it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE routertype ADD VALUE IF NOT EXISTS 'DECISION'")


def downgrade() -> None:
    routers = op.get_bind().execute(sa.text("SELECT count(*) FROM router WHERE type = 'DECISION'")).scalar_one()
    if routers:
        raise RuntimeError(f"Cannot downgrade: {routers} router(s) still have the 'decision' type. Delete them first.")

    quoted = ", ".join(f"'{value}'" for value in _ROUTERTYPE_WITHOUT_DECISION)
    op.execute("ALTER TYPE routertype RENAME TO routertype_old")
    # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query -- values come from a constant tuple of this file
    op.execute(f"CREATE TYPE routertype AS ENUM ({quoted})")
    op.execute("ALTER TABLE router ALTER COLUMN type TYPE routertype USING type::text::routertype")
    op.execute("DROP TYPE routertype_old")
