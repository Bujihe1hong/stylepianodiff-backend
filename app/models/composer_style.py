"""ComposerStyle ORM 模型"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Integer, LargeBinary, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ComposerStyle(Base):
    """作曲家风格表 ORM 模型"""
    __tablename__ = "composer_styles"

    composer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    era: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_image: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    prototype_vector: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    generation_jobs: Mapped[List["GenerationJob"]] = relationship("GenerationJob", back_populates="composer")
