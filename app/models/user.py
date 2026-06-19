"""User ORM 模型"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """用户表 ORM 模型"""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    midi_files: Mapped[List["MidiFile"]] = relationship("MidiFile", back_populates="user", cascade="all, delete-orphan")
    generation_jobs: Mapped[List["GenerationJob"]] = relationship("GenerationJob", back_populates="user")
    generation_histories: Mapped[List["GenerationHistory"]] = relationship("GenerationHistory", back_populates="user", cascade="all, delete-orphan")
