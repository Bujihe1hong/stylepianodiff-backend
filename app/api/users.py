"""用户相关 API：注册、登录、获取当前用户"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """从 Authorization Header 中提取并验证 JWT，返回当前用户"""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证令牌")

    # 支持 "Bearer <token>" 格式
    token = authorization
    if authorization.lower().startswith("bearer "):
        token = authorization[7:]

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")

    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌中无用户信息")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return user


@router.post("/register", response_model=dict)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> dict:
    """用户注册"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"code": 200, "message": "注册成功", "data": {"user_id": new_user.user_id}}


@router.post("/login", response_model=dict)
def login_user(user_in: UserLogin, db: Session = Depends(get_db)) -> dict:
    """用户登录，返回 JWT 令牌"""
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(data={"sub": user.username})
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(),
        },
    }


@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """获取当前登录用户信息"""
    return {
        "code": 200,
        "message": "获取成功",
        "data": UserResponse.model_validate(current_user).model_dump(),
    }
