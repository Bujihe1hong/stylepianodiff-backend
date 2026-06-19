"""
StylePianoDiff Web 平台 - 生成服务封装
负责调用核心模型推理脚本 sample.py，管理生成任务生命周期
使用 SQLAlchemy ORM 更新数据库状态
"""

import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.generation_job import GenerationJob


def _update_job_status(
    job_id: int,
    status: str,
    result_file: Optional[str] = None,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None
) -> None:
    """
    更新数据库中生成任务的状态
    使用独立的 Session，避免线程间 Session 冲突

    Args:
        job_id: 任务 ID
        status: 状态字符串 (pending, running, done, failed)
        result_file: 生成结果文件路径（存入 result_preview JSON）
        error_message: 错误信息
        started_at: 开始时间
        finished_at: 完成时间
    """
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
        if not job:
            print(f"[GenerationService] 任务 {job_id} 不存在，无法更新状态")
            return

        job.status = status

        if error_message is not None:
            job.error_message = error_message[:500]  # 限制长度

        if started_at is not None:
            job.started_at = started_at

        if finished_at is not None:
            job.finished_at = finished_at

        if result_file is not None:
            import json
            job.result_preview = json.dumps({"file_path": result_file}, ensure_ascii=False)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[GenerationService] 更新任务 {job_id} 状态失败: {e}")
    finally:
        db.close()


def run_generation(
    job_id: int,
    seed_path: str,
    composer_name: str,
    alpha: float = 1.0,
    temperature: float = 1.0,
    target_bars: int = 8,
    output_dir: Optional[str] = None
) -> dict:
    """
    执行模型生成任务，调用 stylepianodiff/scripts/sample.py 进行推理

    Args:
        job_id: 数据库任务记录 ID
        seed_path: 种子 MIDI 文件路径
        composer_name: 作曲家风格名称（如 Chopin）
        alpha: 风格强度，默认 1.0
        temperature: 采样温度，默认 1.0
        target_bars: 生成目标小节数，默认 8
        output_dir: 生成结果输出目录，默认使用 settings.GENERATED_DIR

    Returns:
        字典，包含:
        - success: bool 是否成功
        - result_file: str 生成结果文件路径（成功时）
        - error_message: str 错误信息（失败时）
    """
    seed_path = Path(seed_path)
    if not seed_path.exists():
        error_msg = f"种子 MIDI 文件不存在: {seed_path}"
        _update_job_status(job_id, "failed", error_message=error_msg, finished_at=datetime.utcnow())
        return {"success": False, "error_message": error_msg}

    # 检查模型 checkpoint 是否存在
    if not settings.CHECKPOINT_PATH.exists():
        error_msg = f"模型 checkpoint 不存在: {settings.CHECKPOINT_PATH}"
        _update_job_status(job_id, "failed", error_message=error_msg, finished_at=datetime.utcnow())
        return {"success": False, "error_message": error_msg}

    # 检查模型配置文件是否存在
    if not settings.MODEL_CONFIG_PATH.exists():
        error_msg = f"模型配置文件不存在: {settings.MODEL_CONFIG_PATH}"
        _update_job_status(job_id, "failed", error_message=error_msg, finished_at=datetime.utcnow())
        return {"success": False, "error_message": error_msg}

    # 确定输出目录
    if output_dir is None:
        output_dir = settings.GENERATED_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 构建生成结果文件路径（使用 job_id 命名避免冲突）
    result_file = output_dir / f"generated_{job_id}.mid"

    # 构建命令行参数
    cmd = [
        "python",
        str(settings.MODEL_PROJECT_PATH / "scripts" / "sample.py"),
        "--checkpoint", str(settings.CHECKPOINT_PATH),
        "--config", str(settings.MODEL_CONFIG_PATH),
        "--seed", str(seed_path),
        "--style", composer_name,
        "--alpha", str(alpha),
        "--output", str(output_dir),
    ]

    # 更新任务状态为运行中
    _update_job_status(job_id, "running", started_at=datetime.utcnow())

    try:
        # 执行模型推理子进程
        process = subprocess.run(
            cmd,
            cwd=str(settings.MODEL_PROJECT_PATH),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=settings.GENERATION_TIMEOUT,
        )

        if process.returncode != 0:
            # 子进程执行失败
            stderr = process.stderr.strip() if process.stderr else "未知错误"
            error_msg = f"模型推理失败 (exit code {process.returncode}): {stderr}"
            _update_job_status(
                job_id,
                "failed",
                error_message=error_msg[:500],
                finished_at=datetime.utcnow()
            )
            return {"success": False, "error_message": error_msg}

        # 检查输出文件是否生成
        # sample.py 的输出文件名可能不是完全可控的，这里做模糊匹配
        if not result_file.exists():
            # 尝试查找 sample.py 生成的其他文件
            mid_files = sorted(
                output_dir.glob("*.mid"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if mid_files:
                # 将最新生成的文件重命名为我们的目标文件名
                latest = mid_files[0]
                # 如果文件名不同则重命名
                if latest.name != result_file.name:
                    latest.rename(result_file)
            else:
                error_msg = "模型推理完成但未找到生成的 MIDI 文件"
                _update_job_status(
                    job_id,
                    "failed",
                    error_message=error_msg,
                    finished_at=datetime.utcnow()
                )
                return {"success": False, "error_message": error_msg}

        # 更新任务状态为完成
        _update_job_status(
            job_id,
            "done",
            result_file=str(result_file),
            finished_at=datetime.utcnow()
        )

        return {"success": True, "result_file": str(result_file)}

    except subprocess.TimeoutExpired:
        error_msg = f"模型推理超时（超过 {settings.GENERATION_TIMEOUT} 秒）"
        _update_job_status(
            job_id,
            "failed",
            error_message=error_msg,
            finished_at=datetime.utcnow()
        )
        return {"success": False, "error_message": error_msg}

    except Exception as e:
        error_msg = f"生成任务异常: {str(e)}\n{traceback.format_exc()}"
        _update_job_status(
            job_id,
            "failed",
            error_message=error_msg[:500],
            finished_at=datetime.utcnow()
        )
        return {"success": False, "error_message": error_msg}
