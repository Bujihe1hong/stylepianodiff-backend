"""User 相关 Pydantic Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """用户注册请求 Schema"""
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    """用户登录请求 Schema"""
    username: str
    password: str


class UserResponse(UserBase):
    """用户响应 Schema"""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class Token(BaseModel):
    """JWT 令牌响应 Schema"""
    access_token: str
    token_type: str = "bearer"
