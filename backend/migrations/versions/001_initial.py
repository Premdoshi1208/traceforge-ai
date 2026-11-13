"""Initial durable investigation and audit storage."""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("incident_runs", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scenario_id", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("session_hash", sa.String(64), nullable=False), sa.Column("idempotency_key", sa.String(128), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    for col in ("scenario_id", "status", "session_hash", "created_at"):
        op.create_index(f"ix_incident_runs_{col}", "incident_runs", [col])
    op.create_table("audit_entities", sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False), sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_audit_entities_run_id", "audit_entities", ["run_id"])
    op.create_index("ix_audit_entities_kind", "audit_entities", ["kind"])
    op.create_table("approvals", sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("approvals")
    op.drop_table("audit_entities")
    op.drop_table("incident_runs")
