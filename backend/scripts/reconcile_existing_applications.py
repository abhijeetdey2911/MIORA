"""Audit and reconcile existing JobHunter applications in PostgreSQL.

Audits any records where:
1. Status is 'Submitted' with fabricated 'USER-APPROVED-RECEIPT%' as confirmation evidence.
2. Specifically audits Finom and Emma – The Sleep Company records if present.

Action:
- Migrates internal approval proof to `approval_reference`.
- Clears `confirmation_evidence` to NULL (since no external confirmation was received).
- Sets status to 'Submission Unconfirmed'.
- Sets submission_result to 'unconfirmed'.
- Inserts an immutable audit history record into `application_status_history`.

Run:
    python scripts/reconcile_existing_applications.py
"""

from datetime import datetime, timezone
import logging
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

# Allow importing from backend app
sys.path.insert(0, ".")

from app.db.session import SessionLocal
from app.models.multi_agent import Application, ApplicationStatusHistory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconciliation")


def reconcile_applications(db: Session) -> int:
    """Audit and reconcile applications with fabricated internal confirmation receipts."""
    stmt = select(Application).where(
        (Application.confirmation_evidence.ilike("USER-APPROVED-RECEIPT%"))
        | (
            Application.company.in_(["Finom", "Emma – The Sleep Company"])
            & (Application.status == "Submitted")
            & (Application.confirmation_evidence.ilike("%USER%"))
        )
    )
    apps = list(db.scalars(stmt).all())

    if not apps:
        logger.info("Audit complete: No records requiring reconciliation found.")
        return 0

    reconciled_count = 0
    now = datetime.now(timezone.utc)

    for app in apps:
        logger.info(
            "Reconciling application ID=%s, Company='%s', Title='%s', Current Status='%s'",
            app.id,
            app.company,
            app.job_title,
            app.status,
        )
        old_status = app.status
        old_evidence = app.confirmation_evidence

        # Preserve the internal approval token in approval_reference
        app.approval_reference = old_evidence
        # Clear fake confirmation evidence
        app.confirmation_evidence = None
        # Transition to Submission Unconfirmed
        app.status = "Submission Unconfirmed"
        app.submission_result = "unconfirmed"
        app.notes = (
            "Reconciled from 'Submitted' to 'Submission Unconfirmed': "
            "Previous status was assigned based on internal approval receipt "
            f"({old_evidence}) without verified external employer confirmation."
        )

        # Append audit history entry
        history_entry = ApplicationStatusHistory(
            id=uuid.uuid4(),
            application_id=app.id,
            previous_status=old_status,
            new_status="Submission Unconfirmed",
            source="audit_reconciliation",
            notes=app.notes,
            created_at=now,
        )
        db.add(history_entry)
        reconciled_count += 1

    db.commit()
    logger.info("Successfully reconciled %d applications to 'Submission Unconfirmed'.", reconciled_count)
    return reconciled_count


if __name__ == "__main__":
    db = SessionLocal()
    try:
        count = reconcile_applications(db)
        print(f"Reconciliation completed successfully. Reconciled records: {count}")
    finally:
        db.close()
