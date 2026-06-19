"""生成历史相关 API：列表、收藏、评分"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.generation_history import GenerationHistory
from app.models.generation_job import GenerationJob
from app.schemas.generation_job import GenerationJobResponse

router = APIRouter()


def _get_current_user_optional_auth(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """复用认证逻辑"""
    from app.core.security import decode_access_token
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证令牌")
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


@router.get("", response_model=dict)
def list_history(
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
) -> dict:
    """获取当前用户的生成历史列表（包含关联的任务信息）"""
    histories = (
        db.query(GenerationHistory)
        .filter(GenerationHistory.user_id == current_user.user_id)
        .order_by(GenerationHistory.viewed_at.desc())
        .all()
    )

    data = []
    for h in histories:
        item = {
            "history_id": h.history_id,
            "user_id": h.user_id,
            "job_id": h.job_id,
            "is_favorite": h.is_favorite,
            "rating": h.rating,
            "note": h.note,
            "viewed_at": h.viewed_at.isoformat() if h.viewed_at else None,
            "job": GenerationJobResponse.model_validate(h.job).model_dump() if h.job else None,
        }
        data.append(item)

    return {"code": 200, "message": "获取成功", "data": data}


@router.put("/{history_id}/favorite", response_model=dict)
def toggle_favorite(
    history_id: int,
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
) -> dict:
    """切换收藏状态"""
    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    if history.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权操作该记录")

    history.is_favorite = not history.is_favorite
    db.commit()
    db.refresh(history)

    return {
        "code": 200,
        "message": "收藏状态已更新",
        "data": {
            "history_id": history.history_id,
            "is_favorite": history.is_favorite,
        },
    }


@router.put("/{history_id}/rating", response_model=dict)
def set_rating(
    history_id: int,
    rating: int,
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
) -> dict:
    """为历史记录评分（1-5）"""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="评分必须在 1-5 之间")

    history = db.query(GenerationHistory).filter(GenerationHistory.history_id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    if history.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权操作该记录")

    history.rating = rating
    db.commit()
    db.refresh(history)

    return {
        "code": 200,
        "message": "评分已更新",
        "data": {
            "history_id": history.history_id,
            "rating": history.rating,
        },
    }
