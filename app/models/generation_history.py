"""GenerationHistory ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GenerationHistory(Base):
    """生成历史表 ORM 模型"""
    __tablename__ = "generation_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("generation_jobs.job_id"), nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="generation_histories")
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="histories")
