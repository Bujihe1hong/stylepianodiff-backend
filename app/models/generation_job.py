"""GenerationJob ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, LargeBinary, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GenerationJob(Base):
    """生成任务表 ORM 模型"""
    __tablename__ = "generation_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("midi_files.file_id"), nullable=False)
    composer_id: Mapped[int] = mapped_column(Integer, ForeignKey("composer_styles.composer_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    alpha: Mapped[float] = mapped_column(Float, default=1.0)
    temperature: Mapped[float] = mapped_column(Float, default=1.0)
    target_bars: Mapped[int] = mapped_column(Integer, default=8)
    result_file: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    result_preview: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="generation_jobs")
    midi_file: Mapped["MidiFile"] = relationship("MidiFile", back_populates="generation_jobs")
    composer: Mapped["ComposerStyle"] = relationship("ComposerStyle", back_populates="generation_jobs")
    histories: Mapped[list["GenerationHistory"]] = relationship("GenerationHistory", back_populates="job")
