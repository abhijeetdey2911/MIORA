"""add_application_lifecycle_and_approval_fields

Revision ID: c9a1e83f2b45
Revises: b8e734c219aa
Create Date: 2026-11-05 13:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision: str = 'c9a1e83f2b45'
down_revision: Union[str, None] = 'b8e734c219aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to applications table
    op.add_column(
        'applications',
        sa.Column('approval_reference', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'applications',
        sa.Column('submission_attempted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'applications',
        sa.Column('external_application_id', sa.String(length=150), nullable=True),
    )
    op.add_column(
        'applications',
        sa.Column('submission_result', sa.String(length=50), nullable=True),
    )

    # 2. Audit and reconcile historical records that fabricated USER-APPROVED-RECEIPT as external confirmation
    conn = op.get_bind()

    # Find applications with USER-APPROVED-RECEIPT
    unconfirmed_records = conn.execute(
        text(
            "SELECT id, status, confirmation_evidence, notes "
            "FROM applications "
            "WHERE confirmation_evidence LIKE 'USER-APPROVED-RECEIPT%'"
        )
    ).fetchall()

    for row in unconfirmed_records:
        app_id, curr_status, receipt, notes = row
        # Preserve user approval reference in approval_reference column, clear false confirmation evidence
        conn.execute(
            text(
                "UPDATE applications "
                "SET approval_reference = :receipt, "
                "    confirmation_evidence = NULL, "
                "    status = 'Submission Unconfirmed', "
                "    submission_result = 'unconfirmed', "
                "    notes = 'Reconciled from Submitted to Submission Unconfirmed: missing external employer confirmation receipt.' "
                "WHERE id = :app_id"
            ),
            {"receipt": receipt, "app_id": app_id},
        )

        # Append audit history record
        conn.execute(
            text(
                "INSERT INTO application_status_history "
                "(id, application_id, previous_status, new_status, source, notes, created_at) "
                "VALUES (:hist_id, :app_id, :prev_status, 'Submission Unconfirmed', 'audit_reconciliation', "
                "'Reconciled status from Submitted to Submission Unconfirmed: Previous status was assigned based on internal approval receipt without external employer confirmation.', NOW())"
            ),
            {
                "hist_id": str(uuid.uuid4()),
                "app_id": str(app_id),
                "prev_status": curr_status,
            },
        )


def downgrade() -> None:
    op.drop_column('applications', 'submission_result')
    op.drop_column('applications', 'external_application_id')
    op.drop_column('applications', 'submission_attempted_at')
    op.drop_column('applications', 'approval_reference')

