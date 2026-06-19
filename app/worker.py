"""
StylePianoDiff Web 平台 - 后台任务 Worker（简化版）
不使用 Celery，使用 threading 在后台线程中执行模型推理
使用 SQLAlchemy ORM 更新数据库状态
"""

import threading
import traceback
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.generation_job import GenerationJob
from app.services.generation_service import run_generation


def _update_job_status(
    job_id: int,
    status: str,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None
) -> None:
    """
    更新数据库中生成任务的状态（内部辅助函数）
    使用独立 Session，避免线程间 Session 冲突
    """
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.job_id == job_id).first()
        if not job:
            print(f"[Worker] 任务 {job_id} 不存在，无法更新状态")
            return

        job.status = status

        if error_message is not None:
            job.error_message = error_message[:500]

        if started_at is not None:
            job.started_at = started_at

        if finished_at is not None:
            job.finished_at = finished_at

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Worker] 更新任务 {job_id} 状态失败: {e}")
    finally:
        db.close()


def _run_generation_thread(
    job_id: int,
    seed_path: str,
    composer_name: str,
    alpha: float,
    temperature: float,
    target_bars: int,
    output_dir: Optional[str] = None
) -> None:
    """
    在后台线程中执行生成任务的内部函数
    """
    print(f"[Worker] 任务 {job_id} 开始执行: composer={composer_name}, alpha={alpha}")

    try:
        result = run_generation(
            job_id=job_id,
            seed_path=seed_path,
            composer_name=composer_name,
            alpha=alpha,
            temperature=temperature,
            target_bars=target_bars,
            output_dir=output_dir
        )

        if result["success"]:
            print(f"[Worker] 任务 {job_id} 完成: {result.get('result_file')}")
        else:
            print(f"[Worker] 任务 {job_id} 失败: {result.get('error_message', '未知错误')}")

    except Exception as e:
        error_msg = f"后台线程异常: {str(e)}\n{traceback.format_exc()}"
        print(f"[Worker] 任务 {job_id} 异常: {error_msg}")
        _update_job_status(
            job_id,
            "failed",
            error_message=error_msg[:500],
            finished_at=datetime.utcnow()
        )


def run_generation_async(
    job_id: int,
    seed_path: str,
    composer_name: str,
    alpha: float = 1.0,
    temperature: float = 1.0,
    target_bars: int = 8,
    output_dir: Optional[str] = None
) -> threading.Thread:
    """
    异步启动生成任务，在后台线程中执行模型推理

    Args:
        job_id: 数据库任务记录 ID
        seed_path: 种子 MIDI 文件路径
        composer_name: 作曲家风格名称
        alpha: 风格强度
        temperature: 采样温度
        target_bars: 生成目标小节数
        output_dir: 生成结果输出目录

    Returns:
        后台线程对象，可用于检查线程状态
    """
    thread = threading.Thread(
        target=_run_generation_thread,
        args=(job_id, seed_path, composer_name, alpha, temperature, target_bars, output_dir),
        name=f"generation-job-{job_id}",
        daemon=True  # 设置为守护线程，主进程退出时自动结束
    )
    thread.start()
    return thread


# 线程池，用于跟踪活跃的后台生成任务（可选，用于调试和监控）
_active_threads: dict[int, threading.Thread] = {}


def run_generation_async_tracked(
    job_id: int,
    seed_path: str,
    composer_name: str,
    alpha: float = 1.0,
    temperature: float = 1.0,
    target_bars: int = 8,
    output_dir: Optional[str] = None
) -> threading.Thread:
    """
    带跟踪的异步生成任务启动，将线程存入活跃任务字典
    """
    thread = run_generation_async(
        job_id=job_id,
        seed_path=seed_path,
        composer_name=composer_name,
        alpha=alpha,
        temperature=temperature,
        target_bars=target_bars,
        output_dir=output_dir
    )
    _active_threads[job_id] = thread
    return thread


def get_active_job_threads() -> dict[int, threading.Thread]:
    """
    获取当前活跃的后台生成任务线程
    """
    # 清理已结束的线程
    ended = [jid for jid, t in _active_threads.items() if not t.is_alive()]
    for jid in ended:
        del _active_threads[jid]
    return _active_threads.copy()


def is_job_running(job_id: int) -> bool:
    """
    检查指定 job_id 的任务是否正在后台运行
    """
    thread = _active_threads.get(job_id)
    if thread is None:
        return False
    return thread.is_alive()
