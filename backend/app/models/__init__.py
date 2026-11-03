"""Database ORM models package.

In Phase 1, only the base declarative model is configured.
Business entities (Jobs, Resumes, Applications, Agents) will be added in subsequent phases.
"""

from app.db.base import Base

__all__ = ["Base"]
