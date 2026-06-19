"""GenerationJob 相关 Pydantic Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GenerationJobCreate(BaseModel):
    """生成任务创建请求 Schema"""
    file_id: int
    composer_id: int
    alpha: float = Field(default=1.0, ge=0.0, le=2.0)
    temperature: float = Field(default=1.0, ge=0.1, le=2.0)
    target_bars: int = Field(default=8, ge=1, le=32)


class GenerationJobResponse(BaseModel):
    """生成任务响应 Schema"""
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    user_id: int
    file_id: int
    composer_id: int
    status: str
    alpha: float
    temperature: float
    target_bars: int
    result_preview: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
