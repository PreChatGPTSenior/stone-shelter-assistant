"""Create Stone Shelter Assistant schema

Revision ID: 396662a1f4c7
Revises: e9ada39a7f45
Create Date: 2026-10-29 11:29:13.014805

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.schema import CreateSchema, DropSchema

# revision identifiers, used by Alembic.
revision: str = "396662a1f4c7"
down_revision: str | Sequence[str] | None = "e9ada39a7f45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(CreateSchema("stone_shelter_assistant"))


def downgrade() -> None:
    op.execute(DropSchema("stone_shelter_assistant"))
