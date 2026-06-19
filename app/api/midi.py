"""MIDI 文件相关 API：上传、下载、列表"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.midi_file import MidiFile
from app.schemas.midi_file import MidiFileResponse

router = APIRouter()


def _get_current_user_optional_auth(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """复用 users 模块的认证逻辑"""
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


@router.post("/upload", response_model=dict)
async def upload_midi(
    file: UploadFile = File(...),
    composer_tag: Optional[str] = None,
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
) -> dict:
    """上传 MIDI 文件，保存到本地磁盘并写入数据库 VARBINARY 字段"""
    # 校验文件类型
    if not file.filename or not file.filename.lower().endswith((".mid", ".midi")):
        raise HTTPException(status_code=400, detail="仅支持 .mid 或 .midi 文件")

    # 读取文件内容
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"文件大小超过 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB 限制")

    # 保存到本地 uploads 目录
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    local_path = upload_dir / f"{current_user.user_id}_{safe_name}"
    local_path.write_bytes(contents)

    # 写入数据库（课程要求：同时保存为 VARBINARY）
    midi_record = MidiFile(
        user_id=current_user.user_id,
        file_name=safe_name,
        file_data=contents,
        composer_tag=composer_tag,
        duration_sec=None,  # 可由前端或后续解析填充
    )
    db.add(midi_record)
    db.commit()
    db.refresh(midi_record)

    return {
        "code": 200,
        "message": "上传成功",
        "data": MidiFileResponse.model_validate(midi_record).model_dump(),
    }


@router.get("/{file_id}")
def download_midi(
    file_id: int,
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
):
    """下载 MIDI 文件，返回二进制流"""
    midi = db.query(MidiFile).filter(MidiFile.file_id == file_id).first()
    if not midi:
        raise HTTPException(status_code=404, detail="文件不存在")
    if midi.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权访问该文件")

    from fastapi.responses import Response
    return Response(
        content=midi.file_data,
        media_type="audio/midi",
        headers={"Content-Disposition": f'attachment; filename="{midi.file_name}"'},
    )


@router.get("", response_model=dict)
def list_midi(
    current_user: User = Depends(_get_current_user_optional_auth),
    db: Session = Depends(get_db),
) -> dict:
    """获取当前用户的 MIDI 文件列表"""
    midis = db.query(MidiFile).filter(MidiFile.user_id == current_user.user_id).order_by(MidiFile.upload_time.desc()).all()
    data = [MidiFileResponse.model_validate(m).model_dump() for m in midis]
    return {"code": 200, "message": "获取成功", "data": data}
