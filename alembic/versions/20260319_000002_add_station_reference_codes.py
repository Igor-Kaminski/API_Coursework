"""add station reference codes"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_000002"
down_revision = "20260319_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stations", sa.Column("tiploc_code", sa.String(length=32), nullable=True))
    op.add_column("stations", sa.Column("crs_code", sa.String(length=3), nullable=True))
    op.create_unique_constraint("uq_stations_tiploc_code", "stations", ["tiploc_code"])
    op.create_unique_constraint("uq_stations_crs_code", "stations", ["crs_code"])


def downgrade() -> None:
    op.drop_constraint("uq_stations_crs_code", "stations", type_="unique")
    op.drop_constraint("uq_stations_tiploc_code", "stations", type_="unique")
    op.drop_column("stations", "crs_code")
    op.drop_column("stations", "tiploc_code")
