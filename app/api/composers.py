"""作曲家风格相关 API：列表、详情（公开接口，无需认证）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.composer_style import ComposerStyle
from app.schemas.composer_style import ComposerStyleResponse

router = APIRouter()


@router.get("", response_model=dict)
def list_composers(db: Session = Depends(get_db)) -> dict:
    """获取所有活跃的作曲家风格列表"""
    composers = db.query(ComposerStyle).filter(ComposerStyle.is_active == True).order_by(ComposerStyle.composer_id).all()
    data = [ComposerStyleResponse.model_validate(c).model_dump() for c in composers]
    return {"code": 200, "message": "获取成功", "data": data}


@router.get("/{composer_id}", response_model=dict)
def get_composer_detail(composer_id: int, db: Session = Depends(get_db)) -> dict:
    """获取作曲家风格详情"""
    composer = db.query(ComposerStyle).filter(ComposerStyle.composer_id == composer_id).first()
    if not composer:
        raise HTTPException(status_code=404, detail="作曲家风格不存在")

    return {
        "code": 200,
        "message": "获取成功",
        "data": ComposerStyleResponse.model_validate(composer).model_dump(),
    }
