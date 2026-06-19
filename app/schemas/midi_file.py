"""MidiFile 相关 Pydantic Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MidiFileCreate(BaseModel):
    """MIDI 文件创建请求 Schema"""
    file_name: str
    composer_tag: Optional[str] = None
    duration_sec: Optional[float] = None


class MidiFileResponse(BaseModel):
    """MIDI 文件响应 Schema"""
    model_config = ConfigDict(from_attributes=True)

    file_id: int
    user_id: int
    file_name: str
    composer_tag: Optional[str] = None
    duration_sec: Optional[float] = None
    upload_time: Optional[datetime] = None
