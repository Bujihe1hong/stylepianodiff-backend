"""MidiFile ORM 模型"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Integer, LargeBinary, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MidiFile(Base):
    """MIDI 文件表 ORM 模型"""
    __tablename__ = "midi_files"

    file_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    composer_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="midi_files")
    generation_jobs: Mapped[List["GenerationJob"]] = relationship("GenerationJob", back_populates="midi_file")
