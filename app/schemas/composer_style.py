"""ComposerStyle 相关 Pydantic Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ComposerStyleResponse(BaseModel):
    """作曲家风格响应 Schema"""
    model_config = ConfigDict(from_attributes=True)

    composer_id: int
    name: str
    era: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
