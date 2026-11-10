"""First-party, privacy-light traffic analytics.

One row per page view/heartbeat. No IP addresses, cookies or cross-site identifiers are stored: the
``visitor_id`` is the browser's own random local id (or a session id), used only to count unique
visitors and how many are active in a time window.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.models.base import Base, UUIDPk


class SiteVisit(UUIDPk, Base):
    __tablename__ = "site_visits"
    __table_args__ = (
        Index("ix_site_visits_visitor_created", "visitor_id", "created_at"),
        Index("ix_site_visits_created", "created_at"),
    )

    visitor_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    path: Mapped[str] = mapped_column(String(300))
    referrer: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
