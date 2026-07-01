"""initial schema: analyses, resources, findings

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_meta", sa.JSON(), nullable=True),
        sa.Column("total_monthly_savings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("aggregate", sa.JSON(), nullable=True),
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_id", sa.String(), sa.ForeignKey("analyses.id"), index=True),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("instance_type", sa.String(), nullable=True),
        sa.Column("monthly_cost", sa.Float(), nullable=True),
        sa.Column("utilization", sa.Float(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
    )
    op.create_table(
        "findings",
        sa.Column("pk", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.String(), index=True, nullable=False),
        sa.Column("analysis_id", sa.String(), sa.ForeignKey("analyses.id"), index=True),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("detector", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("risk", sa.String(), nullable=False),
        sa.Column("current_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("projected_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monthly_savings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("remediation_diff", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("explanation", sa.String(), nullable=True),
        sa.Column("explanation_source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("resources")
    op.drop_table("analyses")
