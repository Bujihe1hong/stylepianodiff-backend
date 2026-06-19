"""
StylePianoDiff Web 平台 - 生成任务 API 路由
提供提交生成任务、查询任务状态、下载生成结果等接口
使用 SQLAlchemy ORM 与现有架构保持一致
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.composer_style import ComposerStyle
from app.models.generation_job import GenerationJob
from app.models.midi_file import MidiFile
from app.utils.midi_parser import parse_midi_to_json, get_midi_info
from app.worker import run_generation_async

router = APIRouter()


@router.post("", response_model=dict)
async def submit_generation(
    background_tasks: BackgroundTasks,
    file_id: int = Form(..., description="已上传的 MIDI 文件 ID"),
    composer_id: int = Form(..., description="作曲家风格 ID"),
    alpha: float = Form(default=1.0, description="风格强度"),
    temperature: float = Form(default=1.0, description="采样温度"),
    target_bars: int = Form(default=8, description="生成目标小节数"),
    user_id: int = Form(default=1, description="用户 ID（开发阶段默认 1）"),
    db: Session = Depends(get_db),
):
    """
    提交风格化钢琴片段生成任务

    流程：
    1. 从数据库查询已上传的 MIDI 文件
    2. 在 generation_jobs 表创建任务记录（ORM）
    3. 启动后台线程执行模型推理
    4. 立即返回任务信息给前端
    """
    # 1. 查询已上传的 MIDI 文件
    midi_record = db.query(MidiFile).filter(MidiFile.file_id == file_id).first()
    if not midi_record:
        raise HTTPException(status_code=404, detail="MIDI 文件不存在")

    # 确保文件在本地存在（如果只有数据库记录没有本地文件，则写出）
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    local_path = upload_dir / midi_record.file_name
    if not local_path.exists():
        try:
            local_path.write_bytes(midi_record.file_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"文件写出失败: {str(e)}")

    # 2. 创建 GenerationJob 记录
    try:
        job = GenerationJob(
            user_id=user_id,
            file_id=file_id,
            composer_id=composer_id,
            status="pending",
            alpha=alpha,
            temperature=temperature,
            target_bars=target_bars,
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.flush()  # 获取 job_id
        job_id = job.job_id
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")

    # 3. 查询作曲家名称
    composer = db.query(ComposerStyle).filter(ComposerStyle.composer_id == composer_id).first()
    composer_name = composer.name if composer else "Chopin"

    # 4. 启动后台生成任务
    background_tasks.add_task(
        _async_generation_wrapper,
        job_id=job_id,
        seed_path=str(local_path),
        composer_name=composer_name,
        alpha=alpha,
        temperature=temperature,
        target_bars=target_bars
    )

    return {
        "code": 202,
        "message": "生成任务已提交",
        "data": {
            "job_id": job_id,
            "file_id": file_id,
            "status": "pending",
            "composer": composer_name,
            "alpha": alpha,
            "target_bars": target_bars,
        }
    }


def _async_generation_wrapper(
    job_id: int,
    seed_path: str,
    composer_name: str,
    alpha: float,
    temperature: float,
    target_bars: int
):
    """
    后台任务包装器，用于 FastAPI BackgroundTasks 调用
    """
    run_generation_async(
        job_id=job_id,
        seed_path=seed_path,
        composer_name=composer_name,
        alpha=alpha,
        temperature=temperature,
        target_bars=target_bars,
        output_dir=str(settings.GENERATED_DIR)
    )


@router.get("/{job_id}", response_model=dict)
async def get_generation_status(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    查询生成任务状态
    """
    job = db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 计算耗时（秒）
    duration_sec = None
    if job.started_at and job.finished_at:
        duration_sec = int((job.finished_at - job.started_at).total_seconds())
    elif job.started_at:
        duration_sec = int((datetime.utcnow() - job.started_at).total_seconds())

    # 获取关联信息
    composer_name = job.composer.name if job.composer else None
    seed_file_name = job.midi_file.file_name if job.midi_file else None

    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "job_id": job.job_id,
            "status": job.status,
            "alpha": job.alpha,
            "temperature": job.temperature,
            "target_bars": job.target_bars,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "duration_seconds": duration_sec,
            "composer_name": composer_name,
            "seed_file_name": seed_file_name,
        }
    }


@router.get("/{job_id}/result")
async def download_result(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    下载生成结果的 MIDI 文件
    """
    job = db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {job.status}")

    if not job.result_preview:
        raise HTTPException(status_code=404, detail="生成结果文件信息缺失")

    # 从 result_preview JSON 中解析文件路径
    try:
        preview = json.loads(job.result_preview)
        file_path = preview.get("file_path")
    except (json.JSONDecodeError, TypeError):
        file_path = job.result_preview

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="生成结果文件不存在")

    return FileResponse(
        path=file_path,
        media_type="audio/midi",
        filename=f"generated_{job_id}.mid"
    )


@router.get("/{job_id}/preview", response_model=dict)
async def preview_result(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    获取生成结果 MIDI 的预览数据（钢琴卷帘 JSON 格式）
    """
    job = db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {job.status}")

    if not job.result_preview:
        raise HTTPException(status_code=404, detail="生成结果文件信息缺失")

    try:
        preview = json.loads(job.result_preview)
        file_path = preview.get("file_path")
    except (json.JSONDecodeError, TypeError):
        file_path = job.result_preview

    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="生成结果文件不存在")

    # 解析 MIDI 为钢琴卷帘 JSON
    try:
        midi_json = parse_midi_to_json(file_path)
        midi_info = get_midi_info(file_path)
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "job_id": job_id,
                "midi_data": midi_json,
                "midi_info": midi_info,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MIDI 解析失败: {str(e)}")


@router.get("", response_model=dict)
async def list_generations(
    user_id: int = 1,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    获取用户的生成任务列表
    """
    jobs = (
        db.query(GenerationJob)
        .filter(GenerationJob.user_id == user_id)
        .order_by(GenerationJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for job in jobs:
        duration_sec = None
        if job.started_at and job.finished_at:
            duration_sec = int((job.finished_at - job.started_at).total_seconds())
        elif job.started_at:
            duration_sec = int((datetime.utcnow() - job.started_at).total_seconds())

        results.append({
            "job_id": job.job_id,
            "status": job.status,
            "alpha": job.alpha,
            "temperature": job.temperature,
            "target_bars": job.target_bars,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "duration_seconds": duration_sec,
            "composer_name": job.composer.name if job.composer else None,
            "seed_file_name": job.midi_file.file_name if job.midi_file else None,
        })

    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "total": len(results),
            "items": results,
        }
    }
