from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardQuery(BaseModel):
    days: int = Field(default=30, ge=1, le=365)


class DashboardRange(BaseModel):
    start_at: datetime
    end_at: datetime
    days: int
