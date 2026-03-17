"""Initial transport reliability schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


transport_mode = sa.Enum("train", "bus", "tram", "metro", name="transportmode", native_enum=False)
incident_type = sa.Enum(
    "delay",
    "cancellation",
    "signalling_issue",
    "weather",
    "staff_shortage",
    "congestion",
    "vehicle_fault",
    "other",
    name="incidenttype",
    native_enum=False,
)
severity = sa.Enum("low", "medium", "high", "critical", name="severity", native_enum=False)
incident_status = sa.Enum("open", "monitoring", "resolved", name="incidentstatus", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", "city", name="uq_station_name_city"),
    )

    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("origin_station_id", sa.Integer(), nullable=False),
        sa.Column("destination_station_id", sa.Integer(), nullable=False),
        sa.Column("transport_mode", transport_mode, nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["destination_station_id"], ["stations.id"]),
        sa.ForeignKeyConstraint(["origin_station_id"], ["stations.id"]),
        sa.CheckConstraint("origin_station_id <> destination_station_id", name="ck_route_distinct_endpoints"),
        sa.UniqueConstraint(
            "name",
            "origin_station_id",
            "destination_station_id",
            name="uq_route_name_origin_destination",
        ),
    )
    op.create_index("ix_routes_origin_station_id", "routes", ["origin_station_id"])
    op.create_index("ix_routes_destination_station_id", "routes", ["destination_station_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=True),
        sa.Column("incident_type", incident_type, nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("status", incident_status, server_default=sa.text("'open'"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"]),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
        sa.CheckConstraint("delay_minutes IS NULL OR delay_minutes >= 0", name="ck_incident_delay_non_negative"),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= occurred_at",
            name="ck_incident_resolved_after_occurred",
        ),
    )
    op.create_index("ix_incidents_route_id", "incidents", ["route_id"])
    op.create_index("ix_incidents_station_id", "incidents", ["station_id"])
    op.create_index("ix_incidents_incident_type", "incidents", ["incident_type"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_occurred_at", "incidents", ["occurred_at"])
    op.create_index("ix_incidents_route_occurred_at", "incidents", ["route_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_incidents_route_occurred_at", table_name="incidents")
    op.drop_index("ix_incidents_occurred_at", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_incident_type", table_name="incidents")
    op.drop_index("ix_incidents_station_id", table_name="incidents")
    op.drop_index("ix_incidents_route_id", table_name="incidents")
    op.drop_table("incidents")

    op.drop_index("ix_routes_destination_station_id", table_name="routes")
    op.drop_index("ix_routes_origin_station_id", table_name="routes")
    op.drop_table("routes")

    op.drop_table("stations")
